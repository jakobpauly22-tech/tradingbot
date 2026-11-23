"""Eigener SEC-Cache des Betriebs (SEC-Aktualisierung, Schritt 1; Festlegung Jakob 23.11.2026, docs/BETRIEB.md).

Problem: Die Fundamental-Bewertung des Betriebs las SEC-Daten (companyfacts, Erstmeldungen, Aktienfakten, SIC-Historie)
aus dem Standard-Cache, den auch die Backtests lesen, und Betriebs- und Probeläufe schrieben dort hinein (submissions
16.11.2026, SIC-Historie 19.11.2026; Abschnitt „Datenstand des Entwicklungs-Caches“).

Regel:
- Im Betriebsmodus lesen und schreiben alle SEC-Wege ohne ausdrücklich übergebenen Cache nur unter `daten/betrieb/cache/`
  (`daten.sec.sec_cache`, `daten.sec.sec_rohwurzel`). Außerhalb des Betriebsmodus ändert sich nichts.
- Einmalige Übernahme wie beim Kurs-Cache (Befund 5): beim ersten Zugriff im Betriebsmodus, auch in einer Probe, werden
  die Bereiche aus `BEREICHE` byteweise kopiert, ohne Downloads. Die Marke `sec/UEBERNAHME.json` hält Zeitpunkt, Quelle
  und Dateizahl je Bereich fest und wird erst nach der letzten Datei geschrieben; danach wird nie wieder kopiert.
  Bricht eine Übernahme ab, wiederholt der nächste Lauf sie vollständig (jede Datei atomar ersetzt).
- In der Probe geht die Übernahme nur in die Schicht (daten/schicht.py, Befund 20).
"""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from tradingbot.daten.cache import ParquetCache

# Bereiche relativ zur Cache-Wurzel (daten/cache bzw. daten/betrieb/cache): Ordner werden mit allen Dateien darunter
# übernommen, Einzeldateien einzeln. sec/volltext_* (8-K-Volltexte der Entwicklungswerkzeuge) braucht der Betrieb nicht.
BEREICHE = (
    "sec/companyfacts",
    "sec/submissions",
    "sec/koepfe",
    "sec/suche",
    "sec/company_tickers.json.gz",
    "sec_erstmeldungen",
    "sec_aktienfakten",
    "sec_aktienfakten_quartale",
    "universum/sic_historie.parquet",
)
MARKE = Path("sec") / "UEBERNAHME.json"


def _quelle() -> Path:
    from tradingbot.daten.cache import standard_cache

    return standard_cache().wurzel


def _wurzel() -> Path:
    """`daten/betrieb/cache` (außerhalb des Betriebsmodus gesperrt, siehe betrieb/speicher.py)."""
    from tradingbot.betrieb.speicher import betriebspfad

    return betriebspfad("cache/x").parent


def _dateien(quelle: Path, bereich: str) -> list[Path]:
    """Alle zu übernehmenden Dateien eines Bereichs (ohne halbe .tmp-Dateien), sortiert."""
    pfad = quelle / bereich
    if pfad.is_file():
        return [pfad]
    if not pfad.is_dir():
        return []
    return sorted(p for p in pfad.rglob("*") if p.is_file() and not p.name.endswith((".tmp", ".kopie")))


def uebernehmen(quelle: Path, ziel: Path, *, jetzt: datetime | None = None) -> dict:
    """Kopiert einmalig alle Dateien der `BEREICHE` von `quelle` nach `ziel` (Cache-Wurzeln) und schreibt die Marke.
    Gibt den Inhalt der Marke zurück, mit `neu` = True, wenn in diesem Aufruf kopiert wurde."""
    from tradingbot.daten.schicht import lesepfad, schreibpfad

    if lesepfad(ziel / MARKE).exists():                      # Probe: Marke aus Schicht oder Betrieb (Befund 20)
        return {**json.loads(lesepfad(ziel / MARKE).read_text(encoding="utf-8")), "neu": False}
    je_bereich = {}
    for bereich in BEREICHE:
        dateien = _dateien(quelle, bereich)
        for datei in dateien:
            zieldatei = schreibpfad(ziel / datei.relative_to(quelle))   # Probe: nur in die Schicht
            zieldatei.parent.mkdir(parents=True, exist_ok=True)
            temporaer = zieldatei.with_name(zieldatei.name + ".kopie")
            shutil.copy2(datei, temporaer)
            os.replace(temporaer, zieldatei)
        je_bereich[bereich] = len(dateien)
    inhalt = {"uebernommen_am": (jetzt or datetime.now()).isoformat(timespec="seconds"), "quelle": str(quelle),
              "dateien": sum(je_bereich.values()), "je_bereich": je_bereich,
              "grund": "SEC-Aktualisierung Schritt 1: eigener SEC-Cache des Betriebs, einmalige Übernahme ohne Downloads"}
    marke = schreibpfad(ziel / MARKE)
    marke.parent.mkdir(parents=True, exist_ok=True)
    temporaer = marke.with_suffix(".tmp")
    temporaer.write_text(json.dumps(inhalt, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(temporaer, marke)
    return {**inhalt, "neu": True}


def sicherstellen() -> dict:
    """Übernahme, falls noch nicht geschehen (nur im Betriebsmodus). Siehe `uebernehmen`."""
    return uebernehmen(_quelle(), _wurzel())


def betriebs_secwurzel() -> Path:
    """Wurzel der SEC-Rohdaten des Betriebs (`daten/betrieb/cache/sec`); stellt vorher die Übernahme sicher."""
    sicherstellen()
    return _wurzel() / "sec"


def betriebs_seccache() -> ParquetCache:
    """Parquet-Cache des Betriebs für die SEC-Tabellen (Bereiche sec_*, universum/sic_historie); Übernahme vorher."""
    sicherstellen()
    return ParquetCache(_wurzel())


def protokollzeile(info: dict) -> str:
    """Eine Zeile fürs Protokoll des Laufs."""
    am = datetime.fromisoformat(info["uebernommen_am"])
    if info.get("neu"):
        return (f"SEC-Cache des Betriebs angelegt: einmalige Übernahme von {info['dateien']} Dateien aus daten/cache "
                "(ohne Downloads); der Betrieb liest und schreibt SEC-Daten ab jetzt nur in daten/betrieb/cache")
    return f"SEC-Cache des Betriebs: daten/betrieb/cache (übernommen am {am:%d.%m.%Y %H:%M}, {info['dateien']} Dateien)"
