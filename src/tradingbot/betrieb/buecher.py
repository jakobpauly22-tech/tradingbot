"""Vorschläge je Buch für den Tageslauf (Entscheidungen Jakob 02.11.2026, config/betrieb.yaml `buecher`).

- Realbuch: Kasse in ganzen SPYI-Anteilen anlegen (Rest bleibt Kasse und wird mit dem nächsten Betrag investiert).
- Technik-Bücher (Crossover, Momentum): dieselbe SatelliteStrategie wie im Backtest, Zustand (Positionen, Stops,
  Sperren, Monatsprüfung) zwischen den Tagen im Journal. Ein leeres Buch baut beim ersten Lauf sofort auf: Crossover mit
  allen aktiven Signalen nach Stärke, Momentum mit dem Ergebnis der letzten Monatsprüfung; danach Monatsrhythmus am ersten
  Xetra-Handelstag (Entscheidung Jakob 03.11.2026). Wiederholte Läufe am selben Signaltag starten vom Zustand vor dem Tag.
- Fundamental-Bücher (A: Originalscore, B: nur Qualitätshälfte): beim ersten Lauf sofort mit dem aktuellen Signal
  aufbauen, danach am ersten NYSE-Handelstag jedes Quartals mit der Auswahlregel des Backtests (20 Titel, Puffer 30,
  Drift-Band 2,5–7,5 %, höchstens 25 % je zweistelliger SIC).

Alle Werte für den Risk-Manager in EUR; das Limit der Order in der Handelswährung (Vortagesschluss + 2 %).
Jeder Vorschlag trägt eine Investment-These: Grund, Signal und was die These widerlegen würde.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from tradingbot.betrieb.kalender import ist_handelstag
from tradingbot.engines.fundamental.schatten import auswahl
from tradingbot.engines.technik.strategien import Position, SatelliteStrategie
from tradingbot.risiko.manager import OrderVorschlag


@dataclass
class BuchVorschlag:
    vorschlag: OrderVorschlag     # Werte in EUR (Risk-Manager)
    waehrung: str                 # Handelswährung der Order
    limit_order: float | None     # Limit in der Handelswährung


def limit_preis(kurs: float, aufschlag: float) -> float:
    """Kauflimit = Vortagesschluss · (1 + Aufschlag), auf Cent ABGERUNDET (nie über der 2-%-Grenze des Risk-Managers)."""
    return math.floor(kurs * (1 + aufschlag) * 100 + 1e-9) / 100


def vorschlag_id(buch: str, tag, ticker: str, richtung: int) -> str:
    return f"{buch}-{pd.Timestamp(tag):%Y%m%d}-{ticker}-{'K' if richtung > 0 else 'V'}"


def _kauf(buch, tag, ticker, stueck, kurs_eur, kurs_order, waehrung, aufschlag, art, these, *, stop=None, fx=1.0, plan="EUR"):
    limit_order = limit_preis(kurs_order, aufschlag)
    v = OrderVorschlag(vorschlag_id(buch, tag, ticker, 1), pd.Timestamp(tag), buch, ticker, 1, int(stueck), float(kurs_eur), art,
                       limit=limit_order / fx if waehrung != "EUR" else limit_order, stop=stop, gebuehrenplan=plan,
                       eur_kurs=fx if (plan != "EUR" or waehrung != "EUR") else 1.0, waehrung=waehrung, these=these)
    return BuchVorschlag(v, waehrung, limit_order)


def _verkauf(buch, tag, ticker, stueck, kurs_eur, waehrung, art, these, *, fx=1.0, plan="EUR"):
    v = OrderVorschlag(vorschlag_id(buch, tag, ticker, -1), pd.Timestamp(tag), buch, ticker, -1, int(stueck), float(kurs_eur), art,
                       gebuehrenplan=plan, eur_kurs=fx if (plan != "EUR" or waehrung != "EUR") else 1.0, waehrung=waehrung, these=these)
    return BuchVorschlag(v, waehrung, None)


def stueck_fuer(zielwert: float, kasse: float, limit_eur: float, gebuehr) -> int:
    """Ganze Stücke für einen Zielwert, so dass Kurswert zum Limit plus Gebühr in die Kasse passen."""
    n = max(int(math.floor(min(zielwert, kasse) / limit_eur)), 0)
    while n > 0 and n * limit_eur + gebuehr(n, n * limit_eur) > kasse + 1e-9:
        n -= 1
    return n


# --- Devisentausch -----------------------------------------------------------------------------------------------
def tausch_vorschlag(buch: str, tag, vorschlaege: list[BuchVorschlag], kasse_waehrung: float, fx: float, puffer: float,
                     gebuehr_usd, waehrung: str = "USD") -> BuchVorschlag | None:
    """Tausch EUR → Fremdwährung vor den Käufen (Entscheidung Jakob 03.11.2026): geplante Käufe zum Limit plus Gebühren,
    plus Puffer, abzüglich vorhandener Kasse und Erlöse aus Verkäufen derselben Währung. Stück = zu verkaufende EUR."""
    eigene = [x for x in vorschlaege if x.vorschlag.buch == buch and x.waehrung == waehrung]
    kaeufe = sum(x.vorschlag.stueck * x.limit_order + gebuehr_usd(x.vorschlag) for x in eigene if x.vorschlag.richtung > 0)
    erloese = sum(x.vorschlag.stueck * x.vorschlag.letzter_kurs * fx for x in eigene if x.vorschlag.richtung < 0)
    netto = kaeufe * (1 + puffer) - kasse_waehrung - erloese
    if kaeufe <= 0 or netto <= 0:
        return None
    eur = int(math.ceil(netto / fx))
    these = (f"Devisentausch {eur} EUR → etwa {eur * fx:,.0f} {waehrung} für die geplanten Käufe ({kaeufe:,.0f} {waehrung} zum Limit "
             f"inkl. Gebühren, Puffer {puffer:.0%}, abzüglich vorhandener {waehrung}-Kasse {kasse_waehrung:,.0f} und Verkaufserlöse "
             f"{erloese:,.0f}). Keine Währung darf negativ werden.")
    v = OrderVorschlag(vorschlag_id(buch, tag, f"EUR.{waehrung}", -1), pd.Timestamp(tag), buch, f"EUR.{waehrung}", -1, eur, 1.0, "fx",
                       eur_kurs=fx, waehrung=waehrung, these=these)
    return BuchVorschlag(v, waehrung, None)


# --- Realbuch ---------------------------------------------------------------------------------------------------
def realbuch(tag, ticker: str, kurs_eur: float, kasse: float, aufschlag: float, gebuehr) -> list[BuchVorschlag]:
    limit = limit_preis(kurs_eur, aufschlag)
    n = stueck_fuer(kasse, kasse, limit, gebuehr)
    if n <= 0:
        return []
    these = (f"Core: freie Kasse ({kasse:.2f} €) in {n} ganzen Anteilen {ticker} (MSCI ACWI IMI, Hauptbenchmark) anlegen; "
             "Rest bleibt Kasse. Widerlegt, wenn sich die Core-Regel ändert (Review bei 12 Monaten > 10 Pp. hinter ACWI IMI).")
    return [_kauf("real", tag, ticker, n, kurs_eur, kurs_eur, "EUR", aufschlag, "etf", these)]


# --- Technik-Bücher --------------------------------------------------------------------------------------------
def zustand_laden(s: SatelliteStrategie, zustand: dict, tag: pd.Timestamp, erster_handelstag_monat: bool):
    for t, p in (zustand.get("positionen") or {}).items():
        s.pos[t] = Position(p["regel"], pd.Timestamp(p["signal_tag"]), pd.Timestamp(p["kauf_tag"]) if p.get("kauf_tag") else None,
                            p.get("stop"), float(p.get("atr_signal", math.nan)))
    for r in s.regeln.values():
        if hasattr(r, "gesperrt"):
            r.gesperrt = {t: pd.Timestamp(d) for t, d in (zustand.get("gesperrt") or {}).items()}
        if hasattr(r, "pruefmonat"):
            gespeichert = zustand.get("pruefmonat")
            if gespeichert is None:
                # erster Lauf eines neuen Buchs: sofort mit dem Ergebnis der letzten Monatsprüfung aufbauen (12−1 bis zum
                # letzten Monatsende, Entscheidung Jakob 03.11.2026), danach Monatsrhythmus
                r.pruefmonat = {}
            else:
                r.pruefmonat = {t: pd.Period(m) for t, m in gespeichert.items()}


def zustand_speichern(s: SatelliteStrategie) -> dict:
    z = {"positionen": {t: {"regel": p.regel, "signal_tag": str(p.signal_tag.date()), "kauf_tag": str(p.kauf_tag.date()) if p.kauf_tag is not None else None,
                            "stop": p.stop, "atr_signal": p.atr_signal} for t, p in s.pos.items()}}
    for r in s.regeln.values():
        if hasattr(r, "gesperrt"):
            z["gesperrt"] = {t: str(d.date()) for t, d in r.gesperrt.items()}
        if hasattr(r, "pruefmonat"):
            z["pruefmonat"] = {t: str(m) for t, m in r.pruefmonat.items()}
    return z


def erster_handelstag_im_monat(boerse: str, tag) -> bool:
    d = pd.Timestamp(tag).date().replace(day=1)
    while not ist_handelstag(boerse, d):
        d += pd.Timedelta(days=1)
    return d == pd.Timestamp(tag).date()


def technikbuch(buch: str, regel: str, tag, kurse_eur: dict[str, pd.DataFrame], orderkurs: dict[str, float], waehrung: dict[str, str],
                fx: dict[str, float], kasse: float, bestand: dict[str, float], zustand: dict, konfig_technik: dict, aufschlag: float,
                gebuehr) -> tuple[list[BuchVorschlag], dict]:
    from tradingbot.backtest.marktdaten import Marktdaten, Sicht

    tag = pd.Timestamp(tag)
    s = SatelliteStrategie([regel], kurse_eur, konfig_technik)
    zustand_laden(s, zustand, tag, erster_handelstag_im_monat("xetra", tag))
    m = Marktdaten(kurse_eur)
    ziel = s.zielgewichte(tag, Sicht(m, tag, {t: v for t, v in bestand.items() if v > 0}, kasse))
    vorschlaege = []
    if ziel is not None:
        wert = kasse + sum(st * float(kurse_eur[t]["close"].loc[:tag].iloc[-1]) for t, st in bestand.items())
        protokoll = {p["ticker"]: p for p in s.protokoll if pd.Timestamp(p["tag"]) == tag}
        frei = kasse
        for t, w in ziel.items():
            if math.isnan(w):
                continue
            z = s.ind[t].loc[tag]
            kurs_eur = float(z["close"])
            w_ccy = waehrung.get(t, "EUR")
            f = fx.get(w_ccy, 1.0)
            grund = protokoll.get(t, {}).get("grund", "")
            if w == 0 and bestand.get(t, 0) > 0:
                these = f"{regel}: Ausstieg {t} – {grund}."
                vorschlaege.append(_verkauf(buch, tag, t, bestand[t], kurs_eur, w_ccy, "etf", these, fx=f))
            elif w > 0:
                limit_eur = limit_preis(orderkurs[t], aufschlag) / (f if w_ccy != "EUR" else 1.0)
                n = stueck_fuer(w * wert, frei, limit_eur, gebuehr)
                if n <= 0:
                    continue
                stop = kurs_eur - float(konfig_technik["satellite"]["stop_atr_faktor"]) * float(z["atr"])
                these = (f"{regel}: Einstieg {t} ({grund}); Ziel {w:.1%} des Buchs, Stop etwa {stop:.2f} € (2 × ATR). "
                         f"Widerlegt bei Schluss unter dem Stop oder wenn das Signal erlischt"
                         + (" (SMA50 unter SMA200)." if regel == "crossover" else " (12−1 ≤ 0 bei der Monatsprüfung)."))
                vorschlaege.append(_kauf(buch, tag, t, n, kurs_eur, orderkurs[t], w_ccy, aufschlag, "etf", these, stop=stop, fx=f))
                frei -= n * limit_eur + gebuehr(n, n * limit_eur)
    return vorschlaege, zustand_speichern(s)


# --- Fundamental-Bücher ----------------------------------------------------------------------------------------
def quartalsstichtag(tag) -> bool:
    """Erster NYSE-Handelstag eines Quartals (Rebalancing wie im Backtest)."""
    t = pd.Timestamp(tag)
    if t.month not in (1, 4, 7, 10):
        return False
    return erster_handelstag_im_monat("nyse", t)


def fundamentalbuch(buch: str, variante: str, tag, rangliste: pd.DataFrame, kurse_usd: dict[str, float], eurusd: float,
                    kasse: float, bestand: dict[str, float], zustand: dict, konfig_fundamental: dict, aufschlag: float,
                    gebuehr) -> tuple[list[BuchVorschlag], dict, str]:
    """Erster Lauf: sofort aufbauen; danach nur am Quartalsstichtag. Gibt Vorschläge, neuen Zustand und Begründung zurück."""
    tag = pd.Timestamp(tag)
    aufgebaut = any(v > 0 for v in bestand.values())      # aufgebaut erst mit Bestand (nicht ausgeführte Aufbauten wiederholen)
    if aufgebaut and not quartalsstichtag(tag):
        return [], zustand, "kein Quartalsstichtag"
    sp = konfig_fundamental["schattenportfolio"]
    wert_pos = {t: st * kurse_usd[t] / eurusd for t, st in bestand.items() if t in kurse_usd}
    wert = kasse + sum(wert_pos.values())
    gewichte = pd.Series({t: v / wert for t, v in wert_pos.items()}, dtype=float)
    ziel, protokoll = auswahl(rangliste, gewichte, titel=int(sp["titel"]), puffer=int(sp["puffer_rang"]),
                              max_je_branche=int(float(sp["max_branchenanteil"]) * int(sp["titel"])),
                              band=tuple(float(x) for x in sp["drift_band"]))
    zeilen = rangliste.set_index("ticker")
    gruende = {p["ticker"]: p for p in protokoll}
    vorschlaege, frei, nicht_kaufbar = [], kasse, []
    for t, w in sorted(ziel.items(), key=lambda x: x[1] if not math.isnan(x[1]) else 1):   # Verkäufe zuerst
        if math.isnan(w):
            continue
        kurs_eur = kurse_usd[t] / eurusd
        if w == 0 and bestand.get(t, 0) > 0:
            these = f"Fundamental {variante}: Verkauf {t} – {gruende[t]['grund']}."
            vorschlaege.append(_verkauf(buch, tag, t, bestand[t], kurs_eur, "USD", "aktie", these, fx=eurusd, plan="USD"))
            frei += bestand[t] * kurs_eur
        elif w > 0:
            ist = bestand.get(t, 0) * kurs_eur
            limit_eur = limit_preis(kurse_usd[t], aufschlag) / eurusd
            n = stueck_fuer(max(w * wert - ist, 0), frei, limit_eur, gebuehr)
            if n <= 0:
                if bestand.get(t, 0) == 0:
                    nicht_kaufbar.append(f"{t} ({kurse_usd[t]:.0f} USD je Anteil)")
                continue
            z = zeilen.loc[t]
            these = (f"Fundamental {variante}: Rang {gruende[t].get('rang')} im gefilterten S&P 500, Gesamtscore {z['gesamt']:.2f} "
                     f"(Qualität {z['qualitaet']:.2f}, Bewertung {z['bewertung']:.2f})"
                     + (f", Median-Ersatz: {z['ersetzt']}" if z.get("ersetzt") else "")
                     + ". Widerlegt bei Ausschluss durch einen Filter oder Rang über 30 am nächsten Quartalsstichtag.")
            vorschlaege.append(_kauf(buch, tag, t, n, kurs_eur, kurse_usd[t], "USD", aufschlag, "aktie", these, fx=eurusd, plan="USD"))
            frei -= n * limit_eur + gebuehr(n, n * limit_eur)
    grund = "Aufbau" if not aufgebaut else "Quartalsstichtag"
    if nicht_kaufbar:
        grund += "; nicht kaufbar, ein Anteil teurer als die Zielposition (Platz bleibt Kasse): " + ", ".join(nicht_kaufbar)
    return vorschlaege, {"letzter_signaltag": str(tag.date())}, grund
