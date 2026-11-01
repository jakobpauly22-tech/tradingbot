"""Renditen aus Kursdaten."""
from __future__ import annotations

import pandas as pd


def simple_return(p0, p1, d1=0.0):
    """Einfache (diskrete) Periodenrendite inklusive Ausschüttung.

    Formel:  r = (P1 + D1 − P0) / P0
    Annahmen: Die Ausschüttung D1 fließt am Periodenende zu; keine Steuern und Kosten.
    Funktioniert mit Zahlen und mit pandas-Objekten (elementweise).
    Quelle: wissen/02_Kapitalmarkttheorie_Portfolio_Anleihen.md, Abschnitt 2 (Risiko, Rendite und
    Diversifikation); gleiche Signatur wie tests/musterloesungen/referenz.py::simple_return.
    """
    return (p1 + d1 - p0) / p0


def total_return_index(kurse: pd.DataFrame, basis: float = 100.0) -> pd.Series:
    """Gesamtrendite-Index (Kurs plus reinvestierte Dividenden) aus Tageskerzen.

    Formel:  r_t = (C_t + D_t − C_{t−1}) / C_{t−1}      (simple_return je Handelstag)
             TRI_t = TRI_{t−1} · (1 + r_t),  TRI_0 = basis
    Annahmen: Dividende D_t wird am Ex-Tag zum Schlusskurs reinvestiert, ohne Quellensteuer,
    Abgeltungsteuer und Kosten (die rechnet das Backtest-Modul). C_t ist splitbereinigt, D_t von
    Yahoo ebenfalls, daher sind keine weiteren Split-Korrekturen nötig.
    Quelle: wie `simple_return`.
    """
    rendite = simple_return(kurse["close"].shift(1), kurse["close"], kurse["dividende"]).fillna(0.0)
    index = basis * (1.0 + rendite).cumprod()
    index.name = "total_return_index"
    return index
