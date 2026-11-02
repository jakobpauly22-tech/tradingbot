"""Gesamtscore der Fundamental-Engine (Entscheidungen Jakob 03.11.2026, config/fundamental.yaml `score`).

    Gesamt   = w_Q · Qualität + w_B · Bewertung                    (w_Q = w_B = 0,5)
    Qualität = ½ · Rang(Piotroski) + ½ · Rang(−Accruals)
    Bewertung = ½ · Rang(E/P) + ½ · Rang(EBIT/EV)

Rang = Perzentil-Rang (0–1, höher = besser) innerhalb der Vergleichsgruppe im gefilterten Universum: zweistellige SIC mit
mindestens 5 Firmen im gefilterten Universum, sonst SIC-Division (wie bei den Multiples, wissen/01); eine gemeinsame
Gruppe für alle vier Ränge. E/P und EBIT/EV werden vorher auf das 1./99. Perzentil gekappt.
Piotroski geht mit dem Wert ein, den auch der Filter nutzt (exakt oder hochgerechnet und kaufmännisch gerundet).
Accruals = (Jahresüberschuss − operativer Cashflow) / Bilanzsumme; niedrige Accruals gelten als bessere Ertragsqualität
(Sloan 1996), daher Rang von −Accruals.

Fehlender Rang (Score nicht berechenbar, EBIT/EV bei negativem EV): Median der Ränge seiner Vergleichsgruppe, nie besser;
hat die Gruppe keinen Wert, 0,5. Jeder Ersatz wird in `ersetzt` vermerkt.
"""
from __future__ import annotations

import pandas as pd

from tradingbot.engines.fundamental.multiples import sic_division

RAENGE = ("piotroski", "accruals", "ep", "ebit_ev")


def vergleichsgruppe(sic: pd.Series, min_firmen: int = 5) -> pd.Series:
    """Gemeinsame Vergleichsgruppe je Firma: „SIC nn“ bei mindestens `min_firmen` Firmen, sonst „Division X“."""
    sic2 = sic.map(lambda s: int(s) // 100)
    groesse = sic2.map(sic2.value_counts())
    return pd.Series([f"SIC {s:02d}" if g >= min_firmen else f"Division {sic_division(int(x))}"
                      for s, g, x in zip(sic2, groesse, sic)], index=sic.index, dtype=object)


def gesamtscore(tabelle: pd.DataFrame, konfig: dict) -> pd.DataFrame:
    """Gesamtscore je Firma eines Stichtags.

    `tabelle`: gefiltertes Universum (eine Zeile je Firma) mit Spalten `sic`, `piotroski_filter`, `accruals`, `ep`,
    `ebit_ev`. Ergebnis: Kopie mit `gruppe`, `rang_<x>` (nach Ersatz), `ersetzt` (Liste der ersetzten Ränge),
    `qualitaet`, `bewertung`, `gesamt`, absteigend nach `gesamt` sortiert (Gleichstand: kleinere Firma-ID zuerst).
    """
    s, m = konfig["score"], konfig["multiples"]
    t = tabelle.copy()
    if t.empty:
        return t.assign(gruppe=[], ersetzt=[], qualitaet=[], bewertung=[], gesamt=[])
    t["gruppe"] = vergleichsgruppe(t["sic"], m["gruppe_min_firmen"])
    roh = pd.DataFrame(index=t.index)
    roh["piotroski"] = t["piotroski_filter"].astype(float).groupby(t["gruppe"]).rank(pct=True)
    roh["accruals"] = (-t["accruals"].astype(float)).groupby(t["gruppe"]).rank(pct=True)
    unten, oben = m["kappung_perzentile"]
    for spalte in ("ep", "ebit_ev"):
        werte = t[spalte].astype(float)
        gekappt = werte.clip(lower=werte.quantile(unten), upper=werte.quantile(oben))
        roh[spalte] = gekappt.groupby(t["gruppe"]).rank(pct=True)

    ersetzt = [[] for _ in range(len(t))]
    for spalte in RAENGE:
        median = roh[spalte].groupby(t["gruppe"]).transform("median").fillna(0.5)
        fehlt = roh[spalte].isna()
        for i in fehlt.to_numpy().nonzero()[0]:
            ersetzt[i].append(spalte)
        t[f"rang_{spalte}"] = roh[spalte].where(~fehlt, median)
    t["ersetzt"] = [";".join(e) for e in ersetzt]
    q, b = s["qualitaet"], s["bewertung"]
    t["qualitaet"] = t[[f"rang_{x}" for x in q]].mean(axis=1)
    t["bewertung"] = t[[f"rang_{x}" for x in b]].mean(axis=1)
    t["gesamt"] = s["gewichte"]["qualitaet"] * t["qualitaet"] + s["gewichte"]["bewertung"] * t["bewertung"]
    sortier = ["gesamt", "firma"] if "firma" in t.columns else ["gesamt"]
    return t.sort_values(sortier, ascending=[False] + [True] * (len(sortier) - 1)).reset_index(drop=True)
