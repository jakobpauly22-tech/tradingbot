"""Signale und Monatslogik der Regime-Engine. Alle Regeln und Schwellen stehen in docs/REGIME.md (Abschnitte 1–3, 7a) und
wurden vor dem ersten Lauf festgelegt; hier wird nichts optimiert.

Jedes Signal liefert True („aus“), False („an“) oder None (zu wenig Historie – dann gibt es keinen Zustand).

    V1: Risiko aus  ⇔  Trend aus  UND  (Zinskurve aus ODER Kreditaufschlag aus ODER Arbeitsmarkt aus)

Point-in-time: Marktreihen (Wert des Tages d gilt ab d + 1) mit dem Stand des Bewertungstags t; revidierte Reihen mit dem
ALFRED-Stand von t − 1 Tag (ein Wert zählt ab dem Handelstag nach der Veröffentlichung).
"""
from __future__ import annotations

from typing import Callable

import pandas as pd

TREND_MONATE = 10          # Faber (2007): Monatsschluss gegen den Durchschnitt der letzten 10 Monatsschlüsse
KREDIT_MONATE = 10         # gleiche Bauart wie der Trend
SAHM_SCHWELLE = 0.50       # Sahm (2019): Prozentpunkte
SAHM_FENSTER = 12          # Monate vor dem jüngsten Monat
HALTEPFLICHT_MONATE = 2    # nach einem Wechsel am Monatsende m frühestens wieder am Monatsende m + 2
VARIANTEN = ("V1", "D1", "D2", "D3", "D4")
SIGNALE = ("trend_aus", "kurve_aus", "kredit_aus", "arbeit_aus")
REIHEN = {"kurve": "T10Y3M", "kredit": "BAA10Y", "arbeit": "UNRATE"}

# MakroStand: (Reihe, Stichtag) -> Werte, wie sie am Stichtag bekannt waren (Index = Beobachtungsdatum)
MakroStand = Callable[[str, pd.Timestamp], pd.Series]


def monatsenden(tage: pd.DatetimeIndex, *, letzter_monat_abgeschlossen: bool = True) -> pd.DatetimeIndex:
    """Letzter Handelstag je Kalendermonat. Ist der letzte Monat der Reihe noch nicht abgeschlossen, entfällt er."""
    tage = pd.DatetimeIndex(sorted(tage))
    enden = pd.Series(tage, index=tage).groupby(tage.to_period("M")).max()
    if not letzter_monat_abgeschlossen:
        enden = enden.iloc[:-1]
    return pd.DatetimeIndex(enden.to_numpy())


def trend_aus(monatsschluesse: pd.Series) -> bool | None:
    """Trend „aus“: C_m < (1/10) · Σ_{i=0..9} C_{m−i} (aktueller Monat eingeschlossen). Quelle: Faber (2007),
    „A Quantitative Approach to Tactical Asset Allocation“; docs/REGIME.md, Abschnitt 2."""
    c = monatsschluesse.dropna()
    if len(c) < TREND_MONATE:
        return None
    return bool(c.iloc[-1] < c.iloc[-TREND_MONATE:].mean())


def _monatsmittel(tageswerte: pd.Series) -> pd.Series:
    w = tageswerte.dropna()
    return w.groupby(w.index.to_period("M")).mean()


def zinskurve_aus(tageswerte: pd.Series, tag) -> bool | None:
    """Zinskurve „aus“: Durchschnitt der bis zum Bewertungstag bekannten Tageswerte des laufenden Monats von
    10 Jahre − 3 Monate < 0. Quelle: Estrella/Mishkin (1998); docs/REGIME.md, Abschnitt 2."""
    mittel = _monatsmittel(tageswerte)
    monat = pd.Timestamp(tag).to_period("M")
    if monat not in mittel.index:
        return None
    return bool(mittel.loc[monat] < 0)


def kredit_aus(tageswerte: pd.Series, tag) -> bool | None:
    """Kreditaufschlag „aus“: Monatsdurchschnitt > Durchschnitt der letzten 10 Monatsdurchschnitte (aktueller Monat
    eingeschlossen, ohne Lücke). docs/REGIME.md, Abschnitt 2."""
    mittel = _monatsmittel(tageswerte)
    monat = pd.Timestamp(tag).to_period("M")
    fenster = mittel.reindex(pd.period_range(monat - (KREDIT_MONATE - 1), monat, freq="M"))
    if fenster.isna().any():
        return None
    return bool(fenster.iloc[-1] > fenster.mean())


def sahm_wert(monatswerte: pd.Series) -> float | None:
    """Sahm-Regel: S = Ū3_m − min(Ū3_{m−12}, …, Ū3_{m−1}) mit Ū3 = 3-Monats-Mittel der Arbeitslosenquote und m = jüngster
    bekannter Monat. Alle Werte aus einem Datenstand (Echtzeit). Quelle: Sahm (2019), „Direct Stimulus Payments to
    Individuals“; docs/REGIME.md, Abschnitte 2 und 7a."""
    u = monatswerte.dropna().sort_index()
    if u.empty:
        return None
    letzter = u.index[-1].to_period("M")
    fenster = pd.period_range(letzter - (SAHM_FENSTER + 2), letzter, freq="M")
    u = pd.Series(u.to_numpy(), index=u.index.to_period("M")).reindex(fenster)
    if u.isna().any():
        return None
    mittel = u.rolling(3).mean().dropna()            # 13 Werte: 12 Vormonate und der jüngste
    return float(mittel.iloc[-1] - mittel.iloc[:-1].min())


def arbeitsmarkt_aus(monatswerte: pd.Series) -> bool | None:
    """Arbeitsmarkt „aus“: Sahm-Wert ≥ 0,50 Prozentpunkte (siehe `sahm_wert`)."""
    s = sahm_wert(monatswerte)
    return None if s is None else bool(s >= SAHM_SCHWELLE - 1e-9)


def rohzustand(variante: str, trend: bool | None, kurve: bool | None, kredit: bool | None, arbeit: bool | None) -> bool | None:
    """Risiko aus (True) ohne Haltepflicht. Fehlt ein benötigtes Signal, gibt es keinen Zustand (None)."""
    if variante not in VARIANTEN:
        raise ValueError(f"unbekannte Variante {variante!r}, erlaubt: {VARIANTEN}")
    if variante != "V1":
        return {"D1": trend, "D2": kurve, "D3": kredit, "D4": arbeit}[variante]
    if None in (trend, kurve, kredit, arbeit):
        return None
    return trend and (kurve or kredit or arbeit)


def mit_haltepflicht(roh: pd.Series) -> pd.Series:
    """Zustand je Monatsende mit Haltepflicht: Die erste Bewertung setzt den Zustand und zählt als Wechsel; nach einem
    Wechsel am Monatsende m bleibt der Zustand am Monatsende m + 1, der nächste Wechsel ist frühestens bei m + 2 möglich.
    Monate ohne Rohzustand (None) vor Beginn haben keinen Zustand; fehlt er danach, bricht die Rechnung laut ab."""
    zustand, seit_wechsel, aktuell = {}, 0, None
    for tag, wert in roh.items():
        if wert is None or pd.isna(wert):
            if aktuell is not None:
                raise ValueError(f"Regime: kein Rohzustand am {pd.Timestamp(tag).date()} nach Beginn der Reihe")
            zustand[tag] = None
            continue
        wert = bool(wert)
        if aktuell is None:
            aktuell, seit_wechsel = wert, 0
        else:
            seit_wechsel += 1
            if wert != aktuell and seit_wechsel >= HALTEPFLICHT_MONATE:
                aktuell, seit_wechsel = wert, 0
        zustand[tag] = aktuell
    return pd.Series(zustand, dtype=object, name="risiko_aus")


def signale_am(tag, monatsschluesse: pd.Series, makro: MakroStand) -> dict:
    """Die vier Signale am Bewertungstag `tag` (Monatsende). `monatsschluesse`: Schlusskurse des gehaltenen Instruments
    an den Monatsenden; genutzt werden nur Werte bis `tag`."""
    tag = pd.Timestamp(tag).normalize()
    vortag = tag - pd.Timedelta(days=1)
    return {
        "trend_aus": trend_aus(monatsschluesse.loc[:tag]),
        "kurve_aus": zinskurve_aus(makro(REIHEN["kurve"], tag), tag),
        "kredit_aus": kredit_aus(makro(REIHEN["kredit"], tag), tag),
        "arbeit_aus": arbeitsmarkt_aus(makro(REIHEN["arbeit"], vortag)),
    }


def regime_verlauf(schlusskurse: pd.Series, makro: MakroStand, *, variante: str = "V1",
                   letzter_monat_abgeschlossen: bool = True) -> pd.DataFrame:
    """Signale, Rohzustand und Zustand mit Haltepflicht je Monatsende des Instruments (Tagesschlusskurse `schlusskurse`).
    Spalten: trend_aus, kurve_aus, kredit_aus, arbeit_aus, roh_aus, risiko_aus (True = Risiko aus, None = kein Zustand)."""
    c = schlusskurse.dropna().sort_index()
    enden = monatsenden(c.index, letzter_monat_abgeschlossen=letzter_monat_abgeschlossen)
    monat = c.loc[enden]
    zeilen = {tag: signale_am(tag, monat, makro) for tag in enden}
    v = pd.DataFrame.from_dict(zeilen, orient="index", columns=list(SIGNALE)).astype(object)
    v["roh_aus"] = pd.Series({t: rohzustand(variante, *(z[s] for s in SIGNALE)) for t, z in zeilen.items()}, dtype=object)
    v["risiko_aus"] = mit_haltepflicht(v["roh_aus"])
    v.index.name = "monatsende"
    return v


def makro_stand_aus_cache(reihen=tuple(REIHEN.values()), **kwargs) -> MakroStand:
    """MakroStand aus dem Makro-Cache: jede Tabelle einmal laden (ein fester Datenstand je Lauf), Stand mit Tresor."""
    from tradingbot.daten.makro import lade_makro_tabelle, stand_mit_tresor

    tabellen = {r: lade_makro_tabelle(r, **kwargs) for r in reihen}
    return lambda reihe, stichtag: stand_mit_tresor(tabellen[reihe], stichtag)
