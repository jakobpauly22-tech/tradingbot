"""Schattenbuch „regime“ im Paper Trading (Jakob 15.11.2026; docs/REGIME.md, Abschnitt 9).

V1 genau aus dem Festlegungs-Commit b628678: Signale, Rohzustand und Haltepflicht kommen unverändert aus
`engines/regime/signale.py` (Prüfsumme im Test). V1 hat den Backtest nicht bestanden; das Buch beobachtet nur und
begründet nie echte Trades.

- Bewertung am letzten Xetra-Handelstag des Monats, nach Börsenschluss; die Order gilt für den nächsten Handelstag.
  Verpasste Abende werden nachgeholt: Die Signale eines Monatsendes nutzen den Wissensstand dieses Tages (ALFRED).
- Protokoll im Journal (Buchzustand `protokoll`, je Monat die vier Signale, Rohzustand und Zustand mit Haltepflicht).
  Für protokollierte Monate gilt das Protokoll. Weicht eine Neuberechnung ab (z. B. geänderte Yahoo-Kurse), wird das
  einmal laut gemeldet und nichts übernommen; das Buch läuft weiter.
- Beim ersten Lauf wird die Vorgeschichte ab der ersten möglichen Bewertung (Kurse ab 2012, wie im Backtest)
  protokolliert und die Position sofort nach dem aktuellen Zustand eingenommen.
- Makrodaten (FRED/ALFRED) werden nur geladen, wenn eine Bewertung ansteht, und liegen im Betriebsbereich. Ohne Daten
  gibt es keinen neuen Zustand: Position bleibt, Meldung, Bewertung am nächsten Abend.
- Orders: „Risiko an“ ohne Bestand → Kauf in ganzen Stücken, Limit = Vortagesschluss + 2 %; „Risiko aus“ mit Bestand →
  Verkauf des ganzen Bestands, Limit = Vortagesschluss − 2 % (aufgerundet). Passt der Bestand nicht zum Zustand und ist
  keine Order unterwegs, kommt der Vorschlag am nächsten Abend wieder. Kasse wird mit 0 % verzinst.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import timedelta

import pandas as pd

from tradingbot.betrieb.buecher import BuchVorschlag, _kauf, _z, details_text, limit_preis, stueck_fuer, vorschlag_id
from tradingbot.betrieb.kalender import ist_handelstag
from tradingbot.engines.regime import signale
from tradingbot.risiko.manager import OrderVorschlag

BUCH = "regime"
VARIANTE = "V1"
FESTLEGUNG = "b628678"
KURSE_AB = "2012-01-01"          # wie im Backtest (Yahoo-Kurse von SPYI.DE davor fehlerhaft)
FELDER = signale.SIGNALE + ("roh_aus",)
SIGNALNAMEN = {"trend_aus": "Trend", "kurve_aus": "Zinskurve", "kredit_aus": "Kreditaufschlag", "arbeit_aus": "Arbeitsmarkt"}
HINWEIS = "V1 hat den Backtest nicht bestanden (docs/REGIME.md); das Buch beobachtet nur und begründet nie echte Trades."


@dataclass
class Stand:
    """Ergebnis einer Bewertung. `risiko_aus`: True/False, None = kein Zustand (keine Orders)."""
    risiko_aus: bool | None = None
    monat: str | None = None                                 # Monat der letzten Bewertung (JJJJ-MM)
    eintrag: dict = field(default_factory=dict)              # Protokolleintrag dieses Monats
    neu: list[str] = field(default_factory=list)             # in diesem Lauf bewertete Monate (ohne Vorgeschichte)
    wechsel: bool = False                                    # Zustand hat in diesem Lauf gewechselt
    start: bool = False                                      # erster Lauf (Vorgeschichte protokolliert)
    meldungen: list[str] = field(default_factory=list)
    laut: list[str] = field(default_factory=list)            # Sofortmeldungen (Ausfall, Abweichung, Wechsel)


def zustand_text(aus: bool | None) -> str:
    return "kein Zustand" if aus is None else ("Risiko aus" if aus else "Risiko an")


def ist_monatsende(tag) -> bool:
    """Letzter Xetra-Handelstag des Kalendermonats (danach folgt im selben Monat kein Handelstag mehr)."""
    d = pd.Timestamp(tag).date()
    monat, d = d.month, d + timedelta(days=1)
    while d.month == monat:
        if ist_handelstag("xetra", d):
            return False
        d += timedelta(days=1)
    return True


def _schluesse(schlusskurse: pd.Series, tag) -> pd.Series:
    c = schlusskurse.dropna().sort_index()
    return c.loc[: pd.Timestamp(tag)]


def faellige_monate(schlusskurse: pd.Series, tag, protokoll: dict) -> list[str]:
    """Abgeschlossene Monate der Kursreihe (bis `tag`) nach dem letzten protokollierten Monat. Ohne Protokoll: alle."""
    c = _schluesse(schlusskurse, tag)
    if c.empty:
        return []
    enden = signale.monatsenden(c.index, letzter_monat_abgeschlossen=ist_monatsende(c.index[-1]))
    monate = [str(e.to_period("M")) for e in enden]
    return [m for m in monate if not protokoll or m > max(protokoll)]


def signale_text(eintrag: dict) -> str:
    return ", ".join(f"{SIGNALNAMEN[s]} {'aus' if eintrag.get(s) else 'an'}" for s in signale.SIGNALE)


def bewerten(tag, schlusskurse: pd.Series, makro_laden, zustand: dict) -> tuple[dict, Stand]:
    """Zustand des Buchs am Signaltag `tag`. `makro_laden()` liefert den MakroStand und wird nur gerufen, wenn eine
    Bewertung ansteht. Gibt den neuen Buchzustand (fürs Journal) und den Stand zurück. Fehler (keine Makrodaten, Lücke)
    werfen eine Ausnahme; der Aufrufer behält dann den alten Zustand."""
    tag = pd.Timestamp(tag)
    protokoll: dict = dict(zustand.get("protokoll") or {})
    gemeldet = list(zustand.get("abweichungen_gemeldet") or [])
    stand = Stand(start=not protokoll)
    faellig = faellige_monate(schlusskurse, tag, protokoll)
    if faellig:
        c = _schluesse(schlusskurse, tag)
        verlauf = signale.regime_verlauf(c, makro_laden(), variante=VARIANTE, letzter_monat_abgeschlossen=ist_monatsende(c.index[-1]))
        verlauf = verlauf[verlauf["roh_aus"].notna()]
        neu_gerechnet = {str(pd.Timestamp(e).to_period("M")): (pd.Timestamp(e), z) for e, z in verlauf.iterrows()}
        # Protokoll gegen Neuberechnung: das Protokoll gilt, jede Abweichung wird einmal laut gemeldet
        for monat in sorted(set(protokoll) & set(neu_gerechnet)):
            for f in FELDER:
                kennung = f"{monat}:{f}"
                if bool(neu_gerechnet[monat][1][f]) != bool(protokoll[monat][f]) and kennung not in gemeldet:
                    gemeldet.append(kennung)
                    stand.laut.append(f"regime: Neuberechnung weicht vom Protokoll ab ({monat}, {SIGNALNAMEN.get(f, 'Rohzustand')}: "
                                      f"protokolliert {'aus' if protokoll[monat][f] else 'an'}, neu gerechnet "
                                      f"{'aus' if neu_gerechnet[monat][1][f] else 'an'}) – das Protokoll gilt, nichts übernommen; "
                                      "Ursache prüfen (geänderte Kurshistorie?)")
        fehlend = [m for m in faellig if m not in neu_gerechnet]
        if stand.start:
            fehlend = [m for m in fehlend if neu_gerechnet and m > min(neu_gerechnet)]    # Vorlauf ohne Zustand ist in Ordnung
        if fehlend or not neu_gerechnet:
            raise ValueError(f"kein Rohzustand für {', '.join(fehlend) or 'die Kursreihe'} (Signal ohne Daten)")
        vorher = protokoll[max(protokoll)]["risiko_aus"] if protokoll else None
        for monat in [m for m in faellig if m in neu_gerechnet]:
            ende, z = neu_gerechnet[monat]
            if protokoll and pd.Period(monat, "M") != pd.Period(max(protokoll), "M") + 1:
                raise ValueError(f"Lücke im Protokoll zwischen {max(protokoll)} und {monat}")
            protokoll[monat] = {"monatsende": str(ende.date()), **{f: bool(z[f]) for f in FELDER}, "bewertet_am": str(tag.date()),
                                "art": "start" if stand.start else ("bewertung" if ende == tag else "nachgeholt")}
            if not stand.start:
                stand.neu.append(monat)
        # Haltepflicht über die protokollierten Rohzustände (eingefrorene Funktion); protokollierte Monate bleiben unverändert
        monate = sorted(protokoll)
        mit = signale.mit_haltepflicht(pd.Series([protokoll[m]["roh_aus"] for m in monate], index=monate, dtype=object))
        for m in monate:
            protokoll[m].setdefault("risiko_aus", bool(mit[m]))
        stand.wechsel = vorher is not None and protokoll[monate[-1]]["risiko_aus"] != vorher
    if protokoll:
        stand.monat = max(protokoll)
        stand.eintrag = protokoll[stand.monat]
        stand.risiko_aus = bool(stand.eintrag["risiko_aus"])
    if stand.start and protokoll:
        stand.meldungen.append(f"regime: Start – Vorgeschichte {min(protokoll)} bis {max(protokoll)} protokolliert ({len(protokoll)} Monate); "
                               f"aktueller Zustand {zustand_text(stand.risiko_aus)} ({signale_text(stand.eintrag)})")
    for monat in stand.neu:
        e = protokoll[monat]
        nach = "" if e["art"] == "bewertung" else f", nachgeholt am {tag:%d.%m.%Y} mit dem Wissensstand vom {pd.Timestamp(e['monatsende']):%d.%m.%Y}"
        stand.meldungen.append(f"regime: Monatsbewertung {monat}{nach}: {zustand_text(e['risiko_aus'])} ({signale_text(e)}; "
                               f"Rohzustand {'aus' if e['roh_aus'] else 'an'})")
    if stand.wechsel:
        stand.laut.append(f"regime: Wechsel auf {zustand_text(stand.risiko_aus)} ({signale_text(stand.eintrag)}) – Vorschlag im Tageslauf. {HINWEIS}")
    neu = {**zustand, "protokoll": protokoll, "variante": VARIANTE, "festlegung": FESTLEGUNG, "abweichungen_gemeldet": gemeldet}
    return neu, stand


def naechste_bewertung(tag) -> pd.Timestamp:
    """Nächster Bewertungstag nach `tag`: letzter Xetra-Handelstag des laufenden oder des nächsten Monats."""
    d = pd.Timestamp(tag).date() + timedelta(days=1)
    while not (ist_handelstag("xetra", d) and ist_monatsende(d)):
        d += timedelta(days=1)
    return pd.Timestamp(d)


def limit_verkauf(kurs: float, abschlag: float) -> float:
    """Verkaufslimit = Vortagesschluss · (1 − Abschlag), auf Cent AUFGERUNDET (nie mehr als der Abschlag unter dem Kurs)."""
    return math.ceil(kurs * (1 - abschlag) * 100 - 1e-9) / 100


def vorschlaege(tag, ticker: str, kurs: float, stand: Stand, bestand: float, kasse_frei: float, aufschlag: float, abschlag: float,
                gebuehr) -> list[BuchVorschlag]:
    """Order zum Zustand: nur wenn der Bestand nicht zum Zustand passt (wie `RegimeStrategie` im Backtest)."""
    if stand.risiko_aus is None:
        return []
    e = stand.eintrag
    zahlen = [f"Zustand seit der Bewertung {stand.monat}: {zustand_text(stand.risiko_aus)} (Rohzustand {'aus' if e.get('roh_aus') else 'an'}, "
              "zwei Monate Haltepflicht nach einem Wechsel)",
              f"Signale am {pd.Timestamp(e['monatsende']):%d.%m.%Y}: {signale_text(e)}",
              "Regel V1: Risiko aus, wenn der Trend aus ist und zugleich Zinskurve, Kreditaufschlag oder Arbeitsmarkt aus zeigen"]
    if stand.risiko_aus and bestand > 0:
        limit = limit_verkauf(kurs, abschlag)
        n = int(bestand)
        these = (f"Regime V1: Risiko aus seit der Bewertung {stand.monat} ({signale_text(e)}) – ganzer Bestand in Kasse (0 %). "
                 "Widerlegt, wenn der Markt ohne Rückgang weiter steigt (Fehlsignal wie 2015/16).")
        v = OrderVorschlag(vorschlag_id(BUCH, tag, ticker, -1), pd.Timestamp(tag), BUCH, ticker, -1, n, float(kurs), "etf", limit=limit, these=these)
        bv = BuchVorschlag(v, "EUR", limit)
        bv.kern = f"Risiko aus: {ticker} ganz verkaufen ({signale_text(e)})."
        bv.details = details_text(zahlen + [f"Kurs {_z(kurs)} €, Verkaufslimit {_z(limit)} € (Vortagesschluss − 2 %, aufgerundet)",
                                            f"{n} Stück ≈ {_z(n * kurs)} €; verfällt das Limit, kommt der Vorschlag am nächsten Abend wieder"],
                                  ["Fehlsignale kosten Rendite und Steuern (Backtest 2015/16)", HINWEIS],
                                  "der Markt ohne Rückgang weiter steigt; Wiedereinstieg frühestens nach zwei Monaten Haltepflicht.")
        return [bv]
    if not stand.risiko_aus and bestand <= 0:
        limit = limit_preis(kurs, aufschlag)
        n = stueck_fuer(kasse_frei, kasse_frei, limit, gebuehr)
        if n <= 0:
            return []
        these = (f"Regime V1: Risiko an seit der Bewertung {stand.monat} ({signale_text(e)}) – Kasse in {n} ganzen Anteilen {ticker} anlegen. "
                 "Widerlegt, wenn der Trend bricht und zugleich ein Makrosignal aus zeigt (nächste Monatsbewertung).")
        bv = _kauf(BUCH, tag, ticker, n, kurs, kurs, "EUR", aufschlag, "etf", these)
        rest = kasse_frei - n * limit - gebuehr(n, n * limit)
        bv.kern = f"Risiko an: Kasse in {ticker} anlegen ({signale_text(e)})."
        bv.details = details_text(zahlen + [f"Kurs {_z(kurs)} €, Limit {_z(limit)} € (Vortagesschluss + 2 %, abgerundet)",
                                            f"{n} Stück ≈ {_z(n * limit)} €, Gebühr {_z(gebuehr(n, n * limit))} €, Restkasse ≈ {_z(rest)} € (0 % Zins)"],
                                  ["Später Einstieg nach einer Erholung möglich (Backtest 2020)", HINWEIS],
                                  "der Trend bricht und zugleich ein Makrosignal aus zeigt (nächste Monatsbewertung).")
        return [bv]
    return []


# --- Standard-Datenquellen (nur im Betriebsmodus) --------------------------------------------------------------------
def daten_betrieb(tag, ticker: str):
    """Schlusskurse ab 2012 (Yahoo, splitbereinigt und damit in sich stimmig) und ein Lader für den Makrostand aus dem
    Betriebsbereich (daten/betrieb/cache/makro, getrennt vom Backtest-Cache). Der Makrostand wird bei jedem Aufruf neu
    von FRED/ALFRED geholt; ein Ausfall wirft eine Ausnahme."""
    from tradingbot.betrieb.speicher import betriebspfad
    from tradingbot.daten.cache import ParquetCache
    from tradingbot.daten.kurse import lade_kurse
    from tradingbot.daten.makro import lade_makro_tabelle, stand_am

    cache = ParquetCache(betriebspfad("cache/makro/x").parent.parent)        # außerhalb des Betriebsmodus gesperrt
    bis = pd.Timestamp(tag).date()
    schluss = lade_kurse(ticker, KURSE_AB, bis, heute=bis + timedelta(days=1))["close"]

    def makro_laden():
        tabellen = {r: lade_makro_tabelle(r, cache=cache, max_alter_stunden=0.0) for r in signale.REIHEN.values()}
        return lambda reihe, stichtag: stand_am(tabellen[reihe], stichtag)

    return schluss, makro_laden
