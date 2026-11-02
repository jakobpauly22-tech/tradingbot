"""Kurse des Satellite-ETF-Universums: Laden, Datenprüfung, Beginn des gewerteten Backtests.

Datenregel (docs/DATENQUALITAET.md): Auffälligkeiten werden gemeldet, nicht still korrigiert; eine Abweichung braucht
eine Entscheidung von Jakob (in config/technik.yaml unter `universum.datenfreigaben` dokumentiert).
"""
from __future__ import annotations

import pandas as pd

from tradingbot.daten.pruefung import pruefe_kurse

MAX_TAGESSPRUNG_ETF = 0.20         # breite ETFs: größte Tagesbewegung 2012–2024 unter 12 % (März 2020)
MAX_GLEICHE_SCHLUESSE = 10         # mehr als 10 gleiche Schlusskurse in Folge: Kurs eingefroren


def pruefe_etf_kurse(kurse: pd.DataFrame, waehrung_erwartet: str = "EUR") -> list[str]:
    """Befunde einer ETF-Kursreihe (leere Liste = unauffällig). Alter der Daten wird nicht geprüft."""
    befunde = [str(b) for b in pruefe_kurse(kurse, max_tagessprung=MAX_TAGESSPRUNG_ETF) if b.pruefung != "veraltet"]
    waehrung = kurse.attrs.get("originalwaehrung", kurse.attrs.get("waehrung"))
    if waehrung and waehrung != waehrung_erwartet:
        befunde.append(f"[währung] Kurse in {waehrung}, erwartet {waehrung_erwartet} (Xetra-Notierung)")
    c = kurse["close"]
    gleich = c.diff() == 0
    laenge = gleich.groupby((~gleich).cumsum()).cumsum()
    if len(laenge) and laenge.max() >= MAX_GLEICHE_SCHLUESSE:
        ende = laenge.idxmax()
        befunde.append(f"[eingefroren] {int(laenge.max()) + 1} gleiche Schlusskurse in Folge bis {ende.date()}")
    return befunde


def gewerteter_beginn(kurse: dict[str, pd.DataFrame], daten_ab, monate: int = 12) -> pd.Timestamp:
    """Erster Handelstag, an dem alle Reihen mindestens `monate` Monate Historie ab `daten_ab` haben."""
    daten_ab = pd.Timestamp(daten_ab)
    erste = max(k.index[k.index >= daten_ab][0] for k in kurse.values())
    grenze = erste + pd.DateOffset(months=monate)
    alle_tage = sorted(set().union(*[k.index for k in kurse.values()]))
    return next(t for t in alle_tage if t >= grenze)


def haelften(start, ende, anzahl: int = 2) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Teilt [start, ende] in gleich lange Kalenderabschnitte."""
    start, ende = pd.Timestamp(start), pd.Timestamp(ende)
    grenzen = [start + (ende - start) * i / anzahl for i in range(anzahl + 1)]
    return [(grenzen[i].normalize() if i else grenzen[i], grenzen[i + 1].normalize()) for i in range(anzahl)]
