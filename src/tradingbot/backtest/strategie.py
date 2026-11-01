"""Strategie-Schnittstelle und einfache Referenzstrategien.

Eine Strategie bekommt nach Börsenschluss den Stichtag und eine `Sicht` (Daten bis zum Stichtag) und gibt
Zielgewichte zurück: Anteil am Wert des Teilportfolios je Ticker, nur long (>= 0), Summe <= 1, Rest Cash.
`None` heißt: keine Änderung. Ausgeführt wird zur Eröffnung des nächsten Handelstags.
Strategien dürfen Zustand haben; für jeden Lauf eine neue Instanz erzeugen.
"""
from __future__ import annotations

from typing import Protocol

import pandas as pd

from tradingbot.backtest.marktdaten import Sicht


class Strategie(Protocol):
    name: str

    def zielgewichte(self, stichtag: pd.Timestamp, sicht: Sicht) -> pd.Series | None: ...


class BuyAndHold:
    """Kauft am ersten Tag die Zielgewichte und hält dann unverändert."""

    def __init__(self, gewichte: dict[str, float]):
        self.gewichte = pd.Series(gewichte, dtype=float)
        self.name = "Buy & Hold " + ", ".join(f"{t} {w:.0%}" for t, w in self.gewichte.items())
        self._gekauft = False

    def zielgewichte(self, stichtag, sicht):
        if self._gekauft:
            return None
        self._gekauft = True
        return self.gewichte


class FesteGewichte:
    """Feste Zielgewichte mit Rebalancing je Periode („M“ Monat, „Q“ Quartal, „Y“ Jahr).

    Das Signal entsteht am ersten Handelstag einer neuen Periode (der letzte Handelstag einer Periode ist
    am Stichtag noch nicht bekannt), ausgeführt wird am Tag danach.
    """

    def __init__(self, gewichte: dict[str, float], rebalancing: str = "Q"):
        if rebalancing not in ("M", "Q", "Y"):
            raise ValueError("rebalancing muss M, Q oder Y sein")
        self.gewichte = pd.Series(gewichte, dtype=float)
        self.rebalancing = rebalancing
        self.name = f"Feste Gewichte ({rebalancing}) " + ", ".join(f"{t} {w:.0%}" for t, w in self.gewichte.items())
        self._letzte_periode = None

    def zielgewichte(self, stichtag, sicht):
        periode = pd.Timestamp(stichtag).to_period(self.rebalancing)
        if periode == self._letzte_periode:
            return None
        self._letzte_periode = periode
        return self.gewichte
