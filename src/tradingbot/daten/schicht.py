"""Schicht-Cache der Probe (Befund 20, Schritt 4; Regel Jakob 17.11.2026: eine Probe darf keinerlei Betriebsdaten
verändern, also keine Kurse, kein Wikipedia, kein Universum, keine SIC- und SEC-Daten und kein Tiingo).

Solange `probe_schicht(wurzel)` aktiv ist, gilt für jede Datei unter `daten/` (außer der Schicht selbst):
- **lesen:** zuerst `<wurzel>/<Pfad relativ zu daten/>`, gibt es die Datei dort nicht, das Original;
- **schreiben:** nur in die Schicht, das Original bleibt byteweise unverändert.

Die Schicht liegt unter `daten/betrieb/probe/cache/` und wird zu Beginn jedes Probelaufs geleert
(tools/tageslauf.py). Alle Cache-Stellen fragen über `lesepfad` und `schreibpfad`: daten/cache.py (Parquet: Kurse,
Universum, SIC, SEC-Tabellen, Makro), daten/sec.py, daten/tiingo.py, daten/universum.py (Wikipedia, SEC-Namen),
daten/kursquellen.py (Yahoo-Namen), betrieb/kurscache.py und betrieb/universum_betrieb.py. Ohne aktive Schicht sind
beide Funktionen die Identität.
"""
from __future__ import annotations

import shutil
from contextlib import contextmanager
from pathlib import Path

# prozessweit, nicht je Kontext: Fensteraktionen der Probe können in eigenen Threads laufen. Probe und echter Lauf sind
# immer getrennte Prozesse (Laufsperre, tools/tageslauf.py).
_SCHICHT: Path | None = None


def _daten() -> Path:
    from tradingbot.konfiguration import PROJEKT_WURZEL

    return (PROJEKT_WURZEL / "daten").resolve()


def standard_wurzel() -> Path:
    """`daten/betrieb/probe/cache`."""
    return _daten() / "betrieb" / "probe" / "cache"


def aktive_schicht() -> Path | None:
    return _SCHICHT


@contextmanager
def probe_schicht(wurzel: Path | None = None, *, leeren: bool = False):
    """Schicht für die Dauer des Blocks aktivieren; `leeren`: vorher alles in der Schicht löschen (Beginn einer Probe)."""
    wurzel = Path(wurzel or standard_wurzel()).resolve()
    if leeren and wurzel.exists():
        shutil.rmtree(wurzel)
    wurzel.mkdir(parents=True, exist_ok=True)
    global _SCHICHT
    vorher, _SCHICHT = _SCHICHT, wurzel
    try:
        yield wurzel
    finally:
        _SCHICHT = vorher


def _in_schicht(pfad: Path) -> Path | None:
    """Gegenstück in der Schicht, oder None (keine Schicht aktiv, Pfad nicht unter daten/ oder schon in der Schicht)."""
    schicht = _SCHICHT
    if schicht is None:
        return None
    voll = Path(pfad).resolve()
    if voll == schicht or schicht in voll.parents:
        return None
    try:
        relativ = voll.relative_to(_daten())
    except ValueError:
        return None
    return schicht / relativ


def lesepfad(pfad: Path) -> Path:
    """Pfad zum Lesen: die Schicht-Datei, falls die Probe sie schon geschrieben hat, sonst das Original."""
    s = _in_schicht(pfad)
    return s if s is not None and s.exists() else Path(pfad)


def schreibpfad(pfad: Path) -> Path:
    """Pfad zum Schreiben: in der Probe immer die Schicht (Ordner wird angelegt), sonst das Original."""
    s = _in_schicht(pfad)
    if s is None:
        return Path(pfad)
    s.parent.mkdir(parents=True, exist_ok=True)
    return s
