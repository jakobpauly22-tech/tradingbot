"""Marktdaten für die Simulation und die Sicht einer Strategie auf sie (Look-ahead-Schutz).

Alle Preise liegen in Euro vor (Umrechnung siehe `tradingbot.daten.kurse.in_euro`). Für Gebühren in
Fremdwährung hält `Marktdaten` zusätzlich die Wechselkurse (Einheiten Fremdwährung je 1 EUR).
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from tradingbot.backtest.tresor import TresorFreigabe, pruefe_zeitraum


class LookAheadFehler(RuntimeError):
    """Eine Strategie wollte Daten nach ihrem Stichtag sehen."""


@dataclass(frozen=True)
class Instrument:
    ticker: str
    klasse: str = "etf"  # Spread-Klasse: etf | aktie | klein (config/backtest.yaml)
    # Steuerart: aktie | aktienfonds | mischfonds | sonstiger_fonds | etc (backtest/steuern.py).
    # Ohne Angabe: ETF = Aktienfonds, sonst Aktie. Anleihe-ETFs als sonstiger_fonds, ETCs als etc angeben.
    steuerart: str | None = None

    def __post_init__(self):
        if self.steuerart is None:
            object.__setattr__(self, "steuerart", "aktienfonds" if self.klasse == "etf" else "aktie")


@dataclass(frozen=True)
class Delisting:
    """Ende der Kursreihe eines Titels (Rückfall-Regel, daten/delisting.py): Position wird am nächsten Handelstag nach
    `letzter_tag` zum letzten Schlusskurs · (1 + `rendite`) geschlossen, ohne Gebühren (Barabfindung oder Ausbuchung)."""
    letzter_tag: pd.Timestamp
    rendite: float          # 0,0 bei Übernahme/Fusion, −0,30 bei Pleite/Performance/unbekannt
    grund: str


class Marktdaten:
    def __init__(self, kurse: dict[str, pd.DataFrame], waehrungen: dict[str, str] | None = None, fx: dict[str, pd.Series] | None = None,
                 datenstand: dict[str, str | None] | None = None, delistings: dict[str, Delisting] | None = None):
        self.kurse = {t: k.sort_index() for t, k in kurse.items()}
        self.delistings = delistings or {}
        self.datenstand = datenstand or {t: k.attrs.get("abgerufen_um") for t, k in kurse.items()}  # Abrufzeit je Ticker
        self.waehrungen = {t: (waehrungen or {}).get(t, "EUR") for t in kurse}
        self.fx = fx or {}
        kalender = pd.DatetimeIndex([])
        for k in self.kurse.values():
            kalender = kalender.union(k.index)
        self.kalender = pd.DatetimeIndex(kalender, name="datum")
        # Schlusskurse aller Titel auf dem gemeinsamen Kalender, Lücken mit dem letzten Kurs gefüllt (nur rückwärts)
        self.schluss = pd.DataFrame({t: k["close"] for t, k in self.kurse.items()}).reindex(self.kalender).ffill()

    def kerze(self, ticker: str, tag: pd.Timestamp) -> pd.Series | None:
        """Kerze des Tages oder None, wenn der Titel an diesem Tag nicht gehandelt wurde."""
        kurse = self.kurse[ticker]
        if tag in kurse.index:
            return kurse.loc[tag]
        return None

    def eur_kurs(self, waehrung: str, tag: pd.Timestamp) -> float:
        """Einheiten `waehrung` je 1 EUR am Tag (letzter bekannter Kurs)."""
        if waehrung == "EUR":
            return 1.0
        reihe = self.fx[waehrung].loc[:tag]
        if reihe.empty:
            raise KeyError(f"Kein Wechselkurs EUR/{waehrung} bis {tag.date()}")
        return float(reihe.iloc[-1])


class Sicht:
    """Was eine Strategie am Stichtag (nach Börsenschluss) wissen kann: alle Daten bis einschließlich Stichtag."""

    def __init__(self, marktdaten: Marktdaten, stichtag: pd.Timestamp, bestand: dict[str, float] | None = None, cash: float = 0.0):
        self._marktdaten = marktdaten
        self.stichtag = pd.Timestamp(stichtag)
        self.bestand = dict(bestand or {})   # eigener Bestand (Stück) nach Börsenschluss des Stichtags
        self.cash = cash

    def gewichte(self) -> pd.Series:
        """Anteil jedes gehaltenen Titels am Wert des Teilportfolios zum Schluss des Stichtags."""
        schluss = self._marktdaten.schluss.loc[self.stichtag]
        werte = pd.Series({t: s * float(schluss[t]) for t, s in self.bestand.items()}, dtype=float)
        gesamt = self.cash + werte.sum()
        return werte / gesamt if gesamt > 0 else werte

    @property
    def ticker(self) -> list[str]:
        return list(self._marktdaten.kurse)

    def kurse(self, ticker: str) -> pd.DataFrame:
        return self._marktdaten.kurse[ticker].loc[: self.stichtag].copy()

    def schlusskurse(self) -> pd.DataFrame:
        return self._marktdaten.schluss.loc[: self.stichtag].copy()

    def kurs_am(self, ticker: str, tag) -> float:
        tag = pd.Timestamp(tag)
        if tag > self.stichtag:
            raise LookAheadFehler(f"{ticker}: Kurs vom {tag.date()} angefragt, Stichtag ist {self.stichtag.date()}")
        return float(self._marktdaten.schluss.loc[:tag, ticker].iloc[-1])


def lade_marktdaten(
    instrumente: list[Instrument],
    start,
    ende,
    *,
    tresor_freigabe: TresorFreigabe | None = None,
    konfig_backtest: dict | None = None,
    konfig_daten: dict | None = None,
    **kwargs,
) -> Marktdaten:
    """Lädt Kurse in Euro (plus Wechselkurse) für die Simulation. Prüft vorher den Tresor."""
    from tradingbot.daten.kurse import lade_kurse, lade_kurse_eur
    from tradingbot.konfiguration import lade_konfiguration

    pruefe_zeitraum(ende, freigabe=tresor_freigabe, konfig=konfig_backtest)
    konfig_daten = konfig_daten or lade_konfiguration("daten")
    kurse, waehrungen, fx = {}, {}, {}
    for instrument in instrumente:
        k = lade_kurse_eur(instrument.ticker, start, ende, konfig=konfig_daten, **kwargs)
        kurse[instrument.ticker] = k
        waehrung = k.attrs.get("originalwaehrung", "EUR")
        waehrungen[instrument.ticker] = waehrung
        if waehrung != "EUR" and waehrung not in fx:
            fx_ticker = konfig_daten["kurse"]["wechselkurse"].get(waehrung, f"EUR{waehrung}=X")
            fx[waehrung] = lade_kurse(fx_ticker, pd.Timestamp(start) - pd.Timedelta(days=10), ende, **kwargs)["close"]
    return Marktdaten(kurse, waehrungen, fx)
