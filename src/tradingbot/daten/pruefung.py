"""Plausibilitätschecks für Kursdaten. yfinance ist inoffiziell, deshalb wird jeder Abruf geprüft.

Die Checks melden Auffälligkeiten (Befunde), sie korrigieren nichts. Ob ein Befund ein Datenfehler
ist, entscheidet ein Mensch oder eine spätere, explizite Regel.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Befund:
    pruefung: str
    text: str
    datum: date | None = None

    def __str__(self) -> str:
        wann = f" am {self.datum}" if self.datum else ""
        return f"[{self.pruefung}]{wann}: {self.text}"


def _werktage_zwischen(frueher: pd.Timestamp, spaeter: pd.Timestamp) -> int:
    """Werktage (Mo–Fr) strikt zwischen zwei Tagen. Feiertage zählen mit, daher nur eine Näherung."""
    return int(np.busday_count((frueher + pd.Timedelta(days=1)).date(), spaeter.date()))


def pruefe_kurse(
    kurse: pd.DataFrame,
    *,
    heute: date | None = None,
    max_tagessprung: float = 0.25,
    max_luecke_werktage: int = 4,
    max_alter_werktage: int = 5,
) -> list[Befund]:
    """Prüft Tageskerzen auf typische Datenfehler. Leere Liste = unauffällig.

    - leer, doppelte oder unsortierte Tage
    - fehlende oder nicht positive Preise; Hoch unter Tief; Schluss außerhalb der Tagesspanne
    - Tagesänderung über `max_tagessprung` (Standard 25 %) ohne Split an diesem Tag
    - Lücke von mehr als `max_luecke_werktage` Werktagen (längere Börsenpausen sind selten)
    - letzter Kurs älter als `max_alter_werktage` Werktage vor `heute`
    """
    befunde: list[Befund] = []
    if kurse.empty:
        return [Befund("leer", "keine Kurse vorhanden")]

    index = kurse.index
    for tag in index[index.duplicated()].unique():
        befunde.append(Befund("doppelt", "Tag mehrfach vorhanden", tag.date()))
    if not index.is_monotonic_increasing:
        befunde.append(Befund("sortierung", "Tage nicht aufsteigend sortiert"))
        kurse = kurse.sort_index()
    kurse = kurse[~kurse.index.duplicated(keep="last")]

    preise = kurse[["open", "high", "low", "close"]]
    for tag in preise.index[preise.isna().any(axis=1)]:
        befunde.append(Befund("fehlwert", "Preis fehlt", tag.date()))
    for tag in preise.index[(preise <= 0).any(axis=1)]:
        befunde.append(Befund("nicht_positiv", "Preis null oder negativ", tag.date()))
    for tag in kurse.index[kurse["high"] < kurse["low"]]:
        befunde.append(Befund("spanne", "Hoch unter Tief", tag.date()))
    toleranz = 1e-6 * kurse["close"].abs()
    ausserhalb = (kurse["close"] > kurse["high"] + toleranz) | (kurse["close"] < kurse["low"] - toleranz)
    for tag in kurse.index[ausserhalb]:
        befunde.append(Befund("spanne", "Schlusskurs außerhalb von Hoch/Tief", tag.date()))

    aenderung = kurse["close"].pct_change()
    sprung = (aenderung.abs() > max_tagessprung) & (kurse["split"].fillna(0) == 0)
    for tag in kurse.index[sprung]:
        befunde.append(Befund("sprung", f"Tagesänderung {aenderung[tag]:+.1%} ohne Split", tag.date()))

    for frueher, spaeter in zip(kurse.index[:-1], kurse.index[1:]):
        luecke = _werktage_zwischen(frueher, spaeter)
        if luecke > max_luecke_werktage:
            befunde.append(Befund("luecke", f"{luecke} Werktage ohne Kurs seit {frueher.date()}", spaeter.date()))

    if heute is not None:
        alter = _werktage_zwischen(kurse.index[-1], pd.Timestamp(heute))
        if alter > max_alter_werktage:
            befunde.append(Befund("veraltet", f"letzter Kurs {alter} Werktage alt", kurse.index[-1].date()))
    return befunde
