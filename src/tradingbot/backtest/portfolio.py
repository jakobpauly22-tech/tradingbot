"""Teilportfolio (Core oder Satellite) mit eigenem Cash und Kaufposten nach FIFO.

Die Kaufposten sind die Grundlage für das Steuermodul (in Deutschland gilt FIFO, § 20 Abs. 4 S. 7 EStG).
Einstand und Erlös enthalten die Ordergebühr; Spread und Slippage stecken im Preis.

Währungen (Entscheidung Jakob 02.11.2026): Neben der EUR-Kasse (`cash`) führt das Teilportfolio eine Kasse je
Fremdwährung (`fremdkasse`, Beträge in Fremdwährung). Käufe und Verkäufe von Fremdwährungswerten werden über diese Kasse
abgerechnet; getauscht wird nur über `tauschen` (Netto-Saldo am Ausführungstag, Ein- und Auszahlung), nicht je Order.
Einstand und Erlös bleiben in EUR zum Kurs des Handelstags (Grundlage der Abgeltungsteuer).
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
    vorabpauschale_je_stueck: float = 0.0  # schon versteuerte Vorabpauschalen, mindern den Veräußerungsgewinn


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
    fremdkasse: dict[str, float] = field(default_factory=dict)   # Betrag in Fremdwährung je Währung

    def verfuegbar_eur(self, waehrung: str = "EUR", eur_kurs: float = 1.0) -> float:
        """Kasse in der Abrechnungswährung, in EUR bewertet (`eur_kurs` = Einheiten Fremdwährung je 1 EUR)."""
        return self.cash if waehrung == "EUR" else self.fremdkasse.get(waehrung, 0.0) / eur_kurs

    def kasse_eur(self, eur_kurse: dict[str, float] | None = None) -> float:
        """EUR-Kasse plus Fremdwährungskassen, bewertet zu `eur_kurse`."""
        return self.cash + sum(b / (eur_kurse or {})[w] for w, b in self.fremdkasse.items() if abs(b) > TOLERANZ)

    def _buchen(self, waehrung: str, eur_kurs: float, betrag_eur: float):
        if waehrung == "EUR":
            self.cash += betrag_eur
        else:
            self.fremdkasse[waehrung] = self.fremdkasse.get(waehrung, 0.0) + betrag_eur * eur_kurs

    def tauschen(self, von: str, nach: str, betrag_von: float, eur_kurs: float, kosten_eur: float):
        """Tauscht `betrag_von` (in Währung `von`) zum Kurs `eur_kurs` (Fremdwährung je EUR); Kosten gehen von der EUR-Kasse ab."""
        if betrag_von <= 0:
            return
        if von == "EUR":
            if betrag_von + kosten_eur > self.cash + TOLERANZ:
                raise ValueError(f"{self.name}: EUR-Kasse {self.cash:.2f} reicht nicht für den Tausch")
            self.cash -= betrag_von + kosten_eur
            self.fremdkasse[nach] = self.fremdkasse.get(nach, 0.0) + betrag_von * eur_kurs
        else:
            if betrag_von > self.fremdkasse.get(von, 0.0) + TOLERANZ:
                raise ValueError(f"{self.name}: {von}-Kasse reicht nicht für den Tausch")
            self.fremdkasse[von] -= betrag_von
            self.cash += betrag_von / eur_kurs - kosten_eur

    def stueck(self, ticker: str) -> float:
        return sum(p.stueck for p in self.posten.get(ticker, []))

    def bestand(self) -> dict[str, float]:
        return {t: s for t in self.posten if (s := self.stueck(t)) > TOLERANZ}

    def kaufen(self, datum, ticker: str, stueck: float, preis: float, nebenkosten: float,
               waehrung: str = "EUR", eur_kurs: float = 1.0) -> float:
        """Bucht einen Kauf (Preis und Nebenkosten in EUR, abgerechnet über die Kasse der Handelswährung);
        gibt den Gesamtbetrag in EUR zurück."""
        if stueck <= 0:
            raise ValueError("Stückzahl muss positiv sein")
        betrag = stueck * preis + nebenkosten
        verfuegbar = self.verfuegbar_eur(waehrung, eur_kurs)
        if betrag > verfuegbar + TOLERANZ:
            raise ValueError(f"{self.name}: Cash {verfuegbar:.2f} reicht nicht für {betrag:.2f} (keine Margin)")
        self._buchen(waehrung, eur_kurs, -betrag)
        self.posten.setdefault(ticker, []).append(Kaufposten(pd.Timestamp(datum), stueck, betrag / stueck))
        return betrag

    def verkaufen(self, datum, ticker: str, stueck: float, preis: float, nebenkosten: float,
                  waehrung: str = "EUR", eur_kurs: float = 1.0) -> Verkaufsergebnis:
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
            verbraucht.append(Kaufposten(posten.datum, menge, posten.einstand_je_stueck, posten.vorabpauschale_je_stueck))
            posten.stueck -= menge
            rest -= menge
            if posten.stueck <= TOLERANZ:
                liste.pop(0)
        if not liste:
            del self.posten[ticker]
        erloes = stueck * preis - nebenkosten
        self._buchen(waehrung, eur_kurs, erloes)
        return Verkaufsergebnis(erloes, einstand, erloes - einstand, verbraucht)

    def wert(self, preise: pd.Series, eur_kurse: dict[str, float] | None = None) -> float:
        return self.kasse_eur(eur_kurse) + sum(s * float(preise[t]) for t, s in self.bestand().items())
