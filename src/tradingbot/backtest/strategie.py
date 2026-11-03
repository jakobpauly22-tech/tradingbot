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


class SparplanKern:
    """Realbuch (Phase 2): Kasse in ganzen Anteilen eines ETF anlegen, sobald es für mindestens ein Stück zum Limit plus
    Gebühr reicht und die Gebühr höchstens 1 % des Orderwerts ist; Rest bleibt Kasse (Entscheidungen 02./03.11.2026).

    `mit_limit`: Referenzpreis = Vortagesschluss · (1 + Aufschlag), abgerundet (Limit-Order); sonst der Schlusskurs
    (Zwilling mit Market-Order). Signal am Schluss, Ausführung zur Eröffnung des nächsten Handelstags (Simulation).
    """

    def __init__(self, ticker: str, gebuehr, *, aufschlag: float = 0.02, mit_limit: bool = True, max_gebuehr_anteil: float = 0.01):
        self.ticker, self.gebuehr, self.aufschlag, self.mit_limit, self.max_anteil = ticker, gebuehr, aufschlag, mit_limit, max_gebuehr_anteil
        self.name = f"Sparplan {ticker} ({'Limit' if mit_limit else 'Market'})"

    def zielgewichte(self, stichtag, sicht):
        import math

        kurs = sicht.kurs_am(self.ticker, stichtag)
        preis = math.floor(kurs * (1 + self.aufschlag) * 100 + 1e-9) / 100 if self.mit_limit else kurs
        n = int(sicht.cash // preis)
        while n > 0 and n * preis + self.gebuehr(n, n * preis) > sicht.cash + 1e-9:
            n -= 1
        if n < 1 or self.gebuehr(n, n * preis) > self.max_anteil * n * preis + 1e-12:
            return None
        return pd.Series({self.ticker: 1.0})
