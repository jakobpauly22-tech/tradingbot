"""Teilportfolio (Core oder Satellite) mit eigenem Cash und Kaufposten nach FIFO.

Die Kaufposten sind die Grundlage für das Steuermodul (in Deutschland gilt FIFO, § 20 Abs. 4 S. 7 EStG).
Einstand und Erlös enthalten Nebenkosten (Gebühren, Währungstausch); Spread und Slippage stecken im Preis.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

TOLERANZ = 1e-9


@dataclass
class Kaufposten:
    datum: pd.Timestamp
    stueck: float
    einstand_je_stueck: float  # EUR inklusive Nebenkosten


@dataclass
class Verkaufsergebnis:
    erloes: float               # nach Nebenkosten
    einstand: float             # FIFO-Anschaffungskosten der verkauften Stücke
    gewinn: float               # erloes − einstand
    verbrauchte_posten: list[Kaufposten]


@dataclass
class Teilportfolio:
    name: str
    cash: float
    posten: dict[str, list[Kaufposten]] = field(default_factory=dict)

    def stueck(self, ticker: str) -> float:
        return sum(p.stueck for p in self.posten.get(ticker, []))

    def bestand(self) -> dict[str, float]:
        return {t: s for t in self.posten if (s := self.stueck(t)) > TOLERANZ}

    def kaufen(self, datum, ticker: str, stueck: float, preis: float, nebenkosten: float) -> float:
        """Bucht einen Kauf; gibt den Gesamtbetrag (Kurswert plus Nebenkosten) zurück."""
        if stueck <= 0:
            raise ValueError("Stückzahl muss positiv sein")
        betrag = stueck * preis + nebenkosten
        if betrag > self.cash + TOLERANZ:
            raise ValueError(f"{self.name}: Cash {self.cash:.2f} reicht nicht für {betrag:.2f} (keine Margin)")
        self.cash -= betrag
        self.posten.setdefault(ticker, []).append(Kaufposten(pd.Timestamp(datum), stueck, betrag / stueck))
        return betrag

    def verkaufen(self, datum, ticker: str, stueck: float, preis: float, nebenkosten: float) -> Verkaufsergebnis:
        """Bucht einen Verkauf nach FIFO (älteste Kaufposten zuerst)."""
        vorhanden = self.stueck(ticker)
        if stueck <= 0 or stueck > vorhanden + TOLERANZ:
            raise ValueError(f"{self.name}: Verkauf von {stueck} {ticker}, Bestand {vorhanden} (nur long)")
        rest, einstand, verbraucht = stueck, 0.0, []
        liste = self.posten[ticker]
        while rest > TOLERANZ:
            posten = liste[0]
            menge = min(rest, posten.stueck)
            einstand += menge * posten.einstand_je_stueck
            verbraucht.append(Kaufposten(posten.datum, menge, posten.einstand_je_stueck))
            posten.stueck -= menge
            rest -= menge
            if posten.stueck <= TOLERANZ:
                liste.pop(0)
        if not liste:
            del self.posten[ticker]
        erloes = stueck * preis - nebenkosten
        self.cash += erloes
        return Verkaufsergebnis(erloes, einstand, erloes - einstand, verbraucht)

    def wert(self, preise: pd.Series) -> float:
        return self.cash + sum(s * float(preise[t]) for t, s in self.bestand().items())
