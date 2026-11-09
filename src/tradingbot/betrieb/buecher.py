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
    kern: str = ""                # Kernaussage in einem Satz (Kurzzeile)
    details: str = ""             # Detail-These mit Zahlen, „Was dagegen spricht“, „Widerlegt, wenn“


def _pz(x) -> str:
    return "–" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.1%}".replace(".", ",")


def _z(x, n=2) -> str:
    return "–" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:,.{n}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def details_text(zahlen: list[str], dagegen: list[str], widerlegt: str) -> str:
    return "\n".join(["Zahlen:"] + [f"  • {z}" for z in zahlen] + ["Was dagegen spricht:"]
                      + [f"  • {d}" for d in (dagegen or ["nichts Besonderes"])] + [f"Widerlegt, wenn: {widerlegt}"])


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
    bv = BuchVorschlag(v, waehrung, None)
    bv.kern = f"{eur} EUR in {waehrung} tauschen, damit die {waehrung}-Käufe ohne Kredit bezahlt werden."
    bv.details = details_text([f"Geplante Käufe in {waehrung} zum Limit inkl. Gebühren: {_z(kaeufe)}", f"Puffer {_pz(puffer)}",
                               f"Vorhandene {waehrung}-Kasse {_z(kasse_waehrung)}, Verkaufserlöse {_z(erloese)}",
                               f"Kurs ≈ {_z(fx, 4)} {waehrung} je EUR → ≈ {_z(eur * fx)} {waehrung}"],
                              ["Tauschkosten (mindestens 2 USD); Kursrisiko EUR/USD"], "die Käufe nicht freigegeben werden (Rest bleibt in USD-Kasse).")
    return bv


# --- Realbuch ---------------------------------------------------------------------------------------------------
def realbuch(tag, ticker: str, kurs_eur: float, kasse: float, aufschlag: float, gebuehr) -> list[BuchVorschlag]:
    limit = limit_preis(kurs_eur, aufschlag)
    n = stueck_fuer(kasse, kasse, limit, gebuehr)
    if n <= 0:
        return []
    these = (f"Core: freie Kasse ({kasse:.2f} €) in {n} ganzen Anteilen {ticker} (MSCI ACWI IMI, Hauptbenchmark) anlegen; "
             "Rest bleibt Kasse. Widerlegt, wenn sich die Core-Regel ändert (Review bei 12 Monaten > 10 Pp. hinter ACWI IMI).")
    bv = _kauf("real", tag, ticker, n, kurs_eur, kurs_eur, "EUR", aufschlag, "etf", these)
    rest = kasse - n * limit - gebuehr(n, n * limit)
    bv.kern = "Freie Kasse in den Core-ETF (MSCI ACWI IMI = Hauptbenchmark) anlegen."
    bv.details = details_text([f"Kurs {_z(kurs_eur)} €, Limit {_z(limit)} € (Vortagesschluss + 2 %, abgerundet)",
                               f"{n} Stück ≈ {_z(n * limit)} €, Gebühr {_z(gebuehr(n, n * limit))} €, Restkasse ≈ {_z(rest)} €"],
                              ([f"Ganze Stücke: {_z(rest)} € bleiben Kasse bis zum nächsten Betrag"] if rest > 0 else []),
                              "sich die Core-Regel ändert (Review, wenn der Core 12 Monate mehr als 10 Pp. hinter dem ACWI IMI liegt).")
    return [bv]


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
                gebuehr, gesperrt_titel: set[str] = frozenset(), reserviert: float = 0.0,
                nachkauf: set[str] = frozenset(), verpasste_tage=()) -> tuple[list[BuchVorschlag], dict]:
    """`kasse` = freie Kasse (nach Orders unterwegs), `reserviert` = durch Orders unterwegs gebundene Kasse; der Buchwert
    für Zielgewichte und 1-%-Risiko enthält beides (Korrektur 03.11.2026: sonst halbe Stückzahlen bei Orders unterwegs).

    `verpasste_tage` (Jakob 09.11.2026): Handelstage ohne Lauf seit dem letzten Signaltag. Die Strategie prüft deren
    Schlusskurse der Reihe nach wie im Backtest; Ausstiege (Stop, Signalende, Zeit-Stop) werden zum heutigen Abend
    nachgeholt und im Vorschlag vermerkt („Stop … gerissen am 06.11., nachgeholt“). Einstiege verpasster Tage werden
    verworfen; eingestiegen wird nur, wenn das Signal am aktuellen Tag gilt (Monatsprüfung Momentum am aktuellen Tag)."""
    from tradingbot.backtest.marktdaten import Marktdaten, Sicht

    tag = pd.Timestamp(tag)
    s = SatelliteStrategie([regel], kurse_eur, konfig_technik)
    zustand_laden(s, zustand, tag, erster_handelstag_im_monat("xetra", tag))
    m = Marktdaten(kurse_eur)
    gehalten = {t: v for t, v in bestand.items() if v > 0}
    nachgeholt: dict[str, tuple[pd.Timestamp, str]] = {}
    if gehalten and verpasste_tage:
        pruefmonate = {n: dict(r.pruefmonat) for n, r in s.regeln.items() if hasattr(r, "pruefmonat")}
        for d in sorted(pd.Timestamp(x) for x in verpasste_tage):
            if d >= tag or any(d not in s.ind[t].index for t in gehalten if t in s.ind):
                continue
            vorher = set(s.pos)
            z_d = s.zielgewichte(d, Sicht(m, d, gehalten, kasse))
            z_d = {} if z_d is None else z_d
            for t, w in dict(z_d.items()).items():
                if w == 0 and t in gehalten and t not in nachgeholt:
                    g = next((p["grund"] for p in reversed(s.protokoll) if p["ticker"] == t and pd.Timestamp(p["tag"]) == d
                              and p["aktion"] == "verkaufen"), "Ausstieg")
                    nachgeholt[t] = (d, g)
            for t in set(s.pos) - vorher:                 # Einstiege verpasster Tage verwerfen
                if t not in gehalten:
                    del s.pos[t]
        for n, pm in pruefmonate.items():                  # Monatsprüfung (Einstiege) am aktuellen Tag
            s.regeln[n].pruefmonat = pm
    ziel = s.zielgewichte(tag, Sicht(m, tag, gehalten, kasse))
    vorschlaege = []
    wert = kasse + reserviert + sum(st * float(kurse_eur[t]["close"].loc[:tag].iloc[-1]) for t, st in bestand.items())
    # Nachkauf (Jakob 04.11.2026): abgelehnte oder verfallene Käufe erneut, solange das Signal gilt (Crossover: SMA50 über
    # SMA200; Momentum: 12−1 > 0 aus der letzten Monatsprüfung). Gewicht wie bei der Strategie, begrenzt auf den freien Anteil.
    ziel = {} if ziel is None else dict(ziel.items())
    regel_n = s.regeln.get(regel)
    belegt = sum(st * float(kurse_eur[t]["close"].loc[:tag].iloc[-1]) for t, st in bestand.items()) / wert if wert > 0 else 0.0
    belegt += reserviert / wert if wert > 0 else 0.0
    frei_anteil = max(0.0, 1.0 - belegt - sum(w for w in ziel.values() if not math.isnan(w) and w > 0) - 0.005)
    for t in sorted(nachkauf):
        if t in ziel or t in s.pos or t in gesperrt_titel or bestand.get(t, 0) > 0 or t not in s.ind or tag not in s.ind[t].index or regel_n is None:
            continue
        aktiv = regel_n.gilt_noch(t, tag) if hasattr(regel_n, "gilt_noch") else regel_n.einstieg(t, tag) is not None
        if regel == "crossover":
            aktiv = regel_n._ueber(t, tag)
        w = min(s._gewicht(t, tag), frei_anteil) if aktiv else 0.0
        if w <= 0:
            continue
        ziel[t] = w
        frei_anteil -= w
        s.pos[t] = Position(regel, tag, atr_signal=float(s.ind[t].loc[tag, "atr"]))
        s._log(tag, t, "kaufen", regel, "Nachkauf nach Ablehnung/Verfall, Signal gilt noch", w)
    for t, (d, g) in nachgeholt.items():
        if t not in gesperrt_titel:
            ziel[t] = 0.0
    if ziel:
        protokoll = {p["ticker"]: p for p in s.protokoll if pd.Timestamp(p["tag"]) == tag}
        for t, (d, g) in nachgeholt.items():
            protokoll[t] = {"ticker": t, "grund": f"{g} gerissen am {d:%d.%m.}, nachgeholt" if g.startswith("Stop")
                            else f"{g} am {d:%d.%m.}, nachgeholt"}
        frei = kasse
        for t, w in ziel.items():
            if math.isnan(w):
                continue
            z = s.ind[t].loc[tag]
            kurs_eur = float(z["close"])
            w_ccy = waehrung.get(t, "EUR")
            f = fx.get(w_ccy, 1.0)
            grund = protokoll.get(t, {}).get("grund", "")
            if w == 0 and bestand.get(t, 0) > 0 and t not in gesperrt_titel:
                these = f"{regel}: Ausstieg {t} – {grund}."
                bv = _verkauf(buch, tag, t, bestand[t], kurs_eur, w_ccy, "etf", these, fx=f)
                bv.kern = f"Ausstieg: {grund}."
                bv.details = details_text([f"Schluss {_z(kurs_eur)} €, SMA50 {_z(z['sma_schnell'])} €, SMA200 {_z(z['sma_langsam'])} €",
                                           f"Bestand {bestand[t]:g} Stück ≈ {_z(bestand[t] * kurs_eur)} €"], [],
                                          "– (Ausstiege sind immer erlaubt)")
                vorschlaege.append(bv)
            elif w > 0:
                limit_eur = limit_preis(orderkurs[t], aufschlag) / (f if w_ccy != "EUR" else 1.0)
                stop = kurs_eur - float(konfig_technik["satellite"]["stop_atr_faktor"]) * float(z["atr"])
                n = stueck_fuer(w * wert, frei, limit_eur, gebuehr)
                # 1-%-Regel vom Limit aus (schlechtester Einstieg bis Stop, Jakob 03.11.2026)
                if limit_eur > stop:
                    n = min(n, int(math.floor(float(konfig_technik["satellite"]["risiko_je_trade"]) * wert / (limit_eur - stop) + 1e-9)))
                if n <= 0 or t in gesperrt_titel:
                    continue
                these = (f"{regel}: Einstieg {t} ({grund}); Ziel {w:.1%} des Buchs, Stop etwa {stop:.2f} € (2 × ATR). "
                         f"Widerlegt bei Schluss unter dem Stop oder wenn das Signal erlischt"
                         + (" (SMA50 unter SMA200)." if regel == "crossover" else " (12−1 ≤ 0 bei der Monatsprüfung)."))
                bv = _kauf(buch, tag, t, n, kurs_eur, orderkurs[t], w_ccy, aufschlag, "etf", these, stop=stop, fx=f)
                abstand = z["sma_schnell"] / z["sma_langsam"] - 1 if z["sma_langsam"] else float("nan")
                bv.kern = (f"Trend intakt: SMA50 {_pz(abstand)} über SMA200." if regel == "crossover"
                           else f"Momentum 12−1 positiv ({_pz(z['mom'])}).")
                zahlen = [f"Schluss {_z(kurs_eur)} €, Limit {_z(limit_eur)} €" + (f" ({_z(bv.limit_order)} {w_ccy})" if w_ccy != "EUR" else ""),
                          f"SMA50 {_z(z['sma_schnell'])} €, SMA200 {_z(z['sma_langsam'])} € (Abstand {_pz(abstand)})",
                          f"Momentum 12−1: {_pz(z['mom'])}",
                          f"ATR(20) {_z(z['atr'])} €, Stop ≈ {_z(stop)} € (Abstand {_pz(stop / kurs_eur - 1)})",
                          f"Maximaler Verlust bis Stop ≈ {_z(n * (limit_eur - stop))} € ({_pz(n * (limit_eur - stop) / wert)} des Buchs)",
                          f"{n} Stück ≈ {_z(n * limit_eur)} € = {_pz(n * limit_eur / wert)} des Buchs (Ziel {_pz(w)})"]
                dagegen = []
                if n * limit_eur < 0.9 * w * wert:
                    dagegen.append(f"Ganze Stücke/Kasse: nur {_pz(n * limit_eur / wert)} statt {_pz(w)} des Buchs")
                if regel == "momentum" and z["sma_langsam"] and z["close"] < z["sma_langsam"]:
                    dagegen.append("Kurs unter SMA200 (kurzfristig schwächer als das 12−1-Signal)")
                if regel == "crossover" and not math.isnan(z["mom"]) and z["mom"] < 0:
                    dagegen.append(f"Momentum 12−1 negativ ({_pz(z['mom'])})")
                bv.details = details_text(zahlen, dagegen, "der Schluss unter dem Stop liegt oder das Signal erlischt"
                                          + (" (SMA50 unter SMA200)." if regel == "crossover" else " (12−1 ≤ 0 bei der Monatsprüfung)."))
                vorschlaege.append(bv)
                frei -= n * limit_eur + gebuehr(n, n * limit_eur)
    return vorschlaege, zustand_speichern(s)


# --- Fundamental-Bücher ----------------------------------------------------------------------------------------
SIGNALNAMEN = {"roa": "ROA > 0", "cfo": "CFO > 0", "delta_roa": "ROA steigt", "accrual": "CFO > Jahresüberschuss",
               "delta_lever": "Verschuldung sinkt", "delta_liquid": "Liquidität steigt", "eq_offer": "keine neuen Aktien",
               "delta_margin": "Bruttomarge steigt", "delta_turn": "Kapitalumschlag steigt"}


def _wert(z, spalte):
    v = z.get(spalte) if hasattr(z, "get") else None
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else v


def details_fundamental(ticker, z, med, variante, rang, kurs_usd, n, limit_eur, zielwert) -> str:
    sig = _wert(z, "piotroski_signale") or {}
    erfuellt = [SIGNALNAMEN.get(k, k) for k, v in sig.items() if v == 1]
    verfehlt = [SIGNALNAMEN.get(k, k) for k, v in sig.items() if v == 0]
    fehlt = [SIGNALNAMEN.get(k, k) for k, v in sig.items() if v is None]
    ep, ev, acc = _wert(z, "ep"), _wert(z, "ebit_ev"), _wert(z, "accruals")
    m = (lambda c: None if med is None or c not in med.index or (isinstance(med[c], float) and math.isnan(med[c])) else float(med[c]))
    kgv = (1 / ep) if ep and ep > 0 else None
    kgv_med = (1 / m("ep")) if m("ep") and m("ep") > 0 else None
    mw = _wert(z, "marktwert_usd")
    zahlen = [f"Branche SIC {int(z['sic'])} (Vergleichsgruppe {_wert(z, 'gruppe') or '–'}), Kurs {_z(kurs_usd)} USD"
              + (f", Marktkapitalisierung {_z(mw / 1e9, 1)} Mrd. USD" if mw else ""),
              f"Rang {rang} im gefilterten S&P 500 (ohne Finanzwerte), Gesamtscore {z['gesamt']:.2f} = "
              + ("nur Qualität" if variante == "B" else "½ Qualität + ½ Bewertung") + f"; Qualität {z['qualitaet']:.2f}, Bewertung {z['bewertung']:.2f}",
              f"Piotroski {_z(_wert(z, 'piotroski_filter'), 0)} von 9" + (f" (hochgerechnet aus {_wert(z, 'piotroski_n')} Signalen)" if _wert(z, "piotroski_hoch") else "")
              + (f"; erfüllt: {', '.join(erfuellt)}" if erfuellt else "") + (f"; nicht erfüllt: {', '.join(verfehlt)}" if verfehlt else "")
              + (f"; nicht berechenbar: {', '.join(fehlt)}" if fehlt else ""),
              f"Accruals {_pz(acc)} (Branchenmedian {_pz(m('accruals'))}; niedriger ist besser)",
              f"KGV {_z(kgv, 1)} (Branchenmedian {_z(kgv_med, 1)}), EBIT/EV {_pz(ev)} (Branchenmedian {_pz(m('ebit_ev'))})",
              f"Altman {_wert(z, 'altman_variante') or '–'} {_z(_wert(z, 'altman'))} ({_wert(z, 'altman_zone') or 'nicht berechenbar'}), "
              f"Beneish {_z(_wert(z, 'beneish'))} (Grenze −1,78)",
              f"Jahresabschluss bis {pd.Timestamp(z['geschaeftsjahr_ende']).date():%d.%m.%Y}" if _wert(z, "geschaeftsjahr_ende") is not None else "Jahresabschluss: –",
              (f"Daten bekannt ab {pd.Timestamp(z['bekannt_ab']).date():%d.%m.%Y} (Tag nach der SEC-Einreichung)" if _wert(z, "bekannt_ab") is not None else ""),
              f"{n} Stück ≈ {_z(n * limit_eur)} € (Ziel ≈ {_z(zielwert)} €)"]
    dagegen = list(_wert(z, "hinweise") or [])
    if z.get("ersetzt"):
        dagegen.append(f"Median-Ersatz für: {z['ersetzt']} (fehlende Werte zählen neutral)")
    if n * limit_eur < 0.8 * zielwert:
        dagegen.append(f"Ganze Stücke: nur {_z(n * limit_eur)} € statt {_z(zielwert)} € investiert")
    if variante == "B":
        dagegen.append(f"Bewertung zählt in Buch B nicht (Bewertungsrang {z['bewertung']:.2f})")
    return details_text([x for x in zahlen if x], dagegen,
                        "ein Filter die Aktie ausschließt (Piotroski ≤ 3, Altman, Beneish) oder ihr Rang am nächsten Quartalsstichtag über 30 liegt.")
def quartalsstichtag(tag) -> bool:
    """Erster NYSE-Handelstag eines Quartals (Rebalancing wie im Backtest)."""
    t = pd.Timestamp(tag)
    if t.month not in (1, 4, 7, 10):
        return False
    return erster_handelstag_im_monat("nyse", t)


def fundamentalbuch(buch: str, variante: str, tag, rangliste: pd.DataFrame, kurse_usd: dict[str, float], eurusd: float,
                    kasse: float, bestand: dict[str, float], zustand: dict, konfig_fundamental: dict, aufschlag: float,
                    gebuehr, gesperrt_titel: set[str] = frozenset(), reserviert: float = 0.0,
                    nachkauf: set[str] = frozenset()) -> tuple[list[BuchVorschlag], dict, str]:
    """Erster Lauf: sofort aufbauen; danach nur am Quartalsstichtag. Gibt Vorschläge, neuen Zustand und Begründung zurück."""
    tag = pd.Timestamp(tag)
    # aufgebaut mit Bestand oder mit gesendeten, noch nicht ausgeführten Orders („unterwegs“); verfallene Aufbauten wiederholen
    aufgebaut = any(v > 0 for v in bestand.values()) or bool(gesperrt_titel)
    sp = konfig_fundamental["schattenportfolio"]
    nachkauf_ziel = {t: w for t, w in (zustand.get("ziel") or {}).items() if t in nachkauf}
    if aufgebaut and not quartalsstichtag(tag):
        if not nachkauf_ziel:
            return [], zustand, "kein Quartalsstichtag"
        return _fundamental_nachkauf(buch, variante, tag, rangliste, kurse_usd, eurusd, kasse, reserviert, bestand, zustand,
                                     nachkauf_ziel, aufschlag, gebuehr)
    wert_pos = {t: st * kurse_usd[t] / eurusd for t, st in bestand.items() if t in kurse_usd}
    wert = kasse + reserviert + sum(wert_pos.values())          # Buchwert inkl. Kasse für Orders unterwegs
    gewichte = pd.Series({t: v / wert for t, v in wert_pos.items()}, dtype=float)
    ziel, protokoll = auswahl(rangliste, gewichte, titel=int(sp["titel"]), puffer=int(sp["puffer_rang"]),
                              max_je_branche=int(float(sp["max_branchenanteil"]) * int(sp["titel"])),
                              band=tuple(float(x) for x in sp["drift_band"]))
    zeilen = rangliste.set_index("ticker")
    gruende = {p["ticker"]: p for p in protokoll}
    spalten_median = [c for c in ("ep", "ebit_ev", "accruals", "piotroski_filter") if c in rangliste.columns]
    median = rangliste.groupby("gruppe")[spalten_median].median() if "gruppe" in rangliste.columns and spalten_median else pd.DataFrame()
    vorschlaege, frei, nicht_kaufbar = [], kasse, []
    for t, w in sorted(ziel.items(), key=lambda x: x[1] if not math.isnan(x[1]) else 1):   # Verkäufe zuerst
        if math.isnan(w) or t in gesperrt_titel:
            continue
        kurs_eur = kurse_usd[t] / eurusd
        if w == 0 and bestand.get(t, 0) > 0:
            these = f"Fundamental {variante}: Verkauf {t} – {gruende[t]['grund']}."
            bv = _verkauf(buch, tag, t, bestand[t], kurs_eur, "USD", "aktie", these, fx=eurusd, plan="USD")
            bv.kern = f"Verkauf: {gruende[t]['grund']}."
            bv.details = details_text([f"Kurs {_z(kurse_usd[t])} USD, Bestand {bestand[t]:g} Stück"], [], "– (Ausstiege sind immer erlaubt)")
            vorschlaege.append(bv)
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
            bv = _kauf(buch, tag, t, n, kurs_eur, kurse_usd[t], "USD", aufschlag, "aktie", these, fx=eurusd, plan="USD")
            bv.kern = (f"Rang {gruende[t].get('rang')}: " + (f"Qualität {z['qualitaet']:.2f} (Buch B: nur Qualitätshälfte zählt)." if variante == "B"
                       else f"Qualität {z['qualitaet']:.2f} und Bewertung {z['bewertung']:.2f} im oberen Bereich der Branche."))
            bv.details = details_fundamental(t, z, median.loc[z["gruppe"]] if z.get("gruppe") in median.index else None, variante,
                                             gruende[t].get("rang"), kurse_usd[t], n, limit_eur, w * wert)
            vorschlaege.append(bv)
            frei -= n * limit_eur + gebuehr(n, n * limit_eur)
    grund = "Aufbau" if not aufgebaut else "Quartalsstichtag"
    if nicht_kaufbar:
        grund += "; nicht kaufbar, ein Anteil teurer als die Zielposition (Platz bleibt Kasse): " + ", ".join(nicht_kaufbar)
    # Zielportfolio bis zum nächsten Quartalsstichtag merken (Nachkauf abgelehnter/verfallener Käufe, 04.11.2026)
    halten = {t: (w if not math.isnan(w) else float(gewichte.get(t, 0.0))) for t, w in ziel.items()}
    neu_ziel = {t: float(w) for t, w in halten.items() if w and w > 0}
    raenge = {t: gruende[t].get("rang") for t in neu_ziel if t in gruende}
    return vorschlaege, {"letzter_signaltag": str(tag.date()), "ziel": neu_ziel, "rang": raenge}, grund


def _fundamental_nachkauf(buch, variante, tag, rangliste, kurse_usd, eurusd, kasse, reserviert, bestand, zustand, nachkauf_ziel,
                          aufschlag, gebuehr):
    """Abgelehnte/verfallene Käufe des letzten Aufbaus bzw. Stichtags neu vorschlagen (Gewicht wie am Stichtag)."""
    wert = kasse + reserviert + sum(st * kurse_usd[t] / eurusd for t, st in bestand.items() if t in kurse_usd)
    vorschlaege, frei, fehlt = [], kasse, []
    zeilen = rangliste.set_index("ticker") if "ticker" in rangliste.columns else pd.DataFrame()
    for t, w in sorted(nachkauf_ziel.items()):
        if t not in kurse_usd:
            fehlt.append(t)
            continue
        kurs_eur = kurse_usd[t] / eurusd
        limit_eur = limit_preis(kurse_usd[t], aufschlag) / eurusd
        n = stueck_fuer(w * wert, frei, limit_eur, gebuehr)
        if n <= 0:
            continue
        rang = (zustand.get("rang") or {}).get(t)
        these = (f"Fundamental {variante}: Nachkauf {t} (Rang {rang} am letzten Stichtag {zustand.get('letzter_signaltag')}); "
                 f"der Kauf wurde abgelehnt oder ist verfallen, das Signal gilt bis zum nächsten Quartalsstichtag.")
        bv = _kauf(buch, tag, t, n, kurs_eur, kurse_usd[t], "USD", aufschlag, "aktie", these, fx=eurusd, plan="USD")
        bv.kern = f"Nachkauf: Rang {rang} am Stichtag {zustand.get('letzter_signaltag')}, Kauf abgelehnt oder verfallen."
        bv.details = (details_fundamental(t, zeilen.loc[t], None, variante, rang, kurse_usd[t], n, limit_eur, w * wert)
                      if t in zeilen.index else f"Zahlen:\n  • Kurs {_z(kurse_usd[t])} USD, {n} Stück ≈ {_z(n * limit_eur)} €")
        vorschlaege.append(bv)
        frei -= n * limit_eur + gebuehr(n, n * limit_eur)
    grund = f"Nachkauf {len(vorschlaege)} Titel (abgelehnt/verfallen)" + (f"; ohne Kurs: {', '.join(fehlt)}" if fehlt else "")
    return vorschlaege, zustand, grund
