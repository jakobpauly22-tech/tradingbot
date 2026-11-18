"""Eigener Kurs-Cache des Betriebs (Befund 5 der unabhängigen Prüfung; Plan freigegeben von Jakob 16.11.2026, Ergänzung
17.11.2026).

Problem: Tageslauf, Senden, Fundamental-Bewertung und Regimebuch luden Kurse über den Standard-Cache `daten/cache/kurse`,
den auch die Backtests lesen. Passt beim Nachladen die Überlappung nicht (neuer Split, Yahoo-Korrektur), lädt
`daten.kurse.lade_kurse` die ganze Historie neu und ersetzt damit auch die Entwicklungsdaten bis 2024. Ein Betriebslauf
konnte so die Datenbasis eines späteren Backtests verändern.

Regel:
- Im Betriebsmodus (`backtest.tresor.betriebsmodus`) liest und schreibt `lade_kurse` ohne ausdrücklich übergebenen Cache
  nur noch `daten/betrieb/cache/kurse` (alle Betriebswege). Außerhalb des Betriebsmodus bleibt alles beim Standard-Cache.
- Einmalige Übernahme: Beim ersten Zugriff werden alle Kursdateien aus `daten/cache/kurse` kopiert, ohne Downloads.
  Eine Marke (`UEBERNAHME.json`) hält Zeitpunkt, Quelle und Zahl der Dateien fest; danach wird nie wieder kopiert, der
  Betrieb schreibt nur noch in seinen eigenen Cache. Auslöser ist der erste Lauf im Betriebsmodus, also auch ein
  Probelauf (`--kopie`, `--probe`); das Protokoll des Laufs nennt die Zahl der übernommenen Dateien (Jakob 17.11.2026).
- Die Marke wird erst nach der letzten Datei geschrieben. Bricht eine Übernahme ab, wiederholt der nächste Lauf sie
  vollständig (dieselben Quelldateien, jede Datei atomar ersetzt).
"""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from tradingbot.daten.cache import ParquetCache

BEREICH = "kurse"
MARKE = "UEBERNAHME.json"


def _quelle() -> Path:
    from tradingbot.daten.cache import standard_cache

    return standard_cache().wurzel / BEREICH


def _wurzel() -> Path:
    """`daten/betrieb/cache` (außerhalb des Betriebsmodus gesperrt, siehe betrieb/speicher.py)."""
    from tradingbot.betrieb.speicher import betriebspfad

    return betriebspfad("cache/x").parent


def uebernehmen(quelle: Path, ziel: Path, *, jetzt: datetime | None = None) -> dict:
    """Kopiert einmalig alle Kursdateien (*.parquet) von `quelle` nach `ziel` und schreibt die Marke. Gibt den Inhalt der
    Marke zurück, mit `neu` = True, wenn in diesem Aufruf kopiert wurde."""
    from tradingbot.daten.schicht import lesepfad, schreibpfad

    if lesepfad(ziel / MARKE).exists():                      # Probe: Marke aus Schicht oder Betrieb (Befund 20)
        return {**json.loads(lesepfad(ziel / MARKE).read_text(encoding="utf-8")), "neu": False}
    ziel = schreibpfad(ziel)                                 # Probe: Übernahme nur in die Schicht
    marke = ziel / MARKE
    ziel.mkdir(parents=True, exist_ok=True)
    dateien = sorted(quelle.glob("*.parquet")) if quelle.exists() else []
    for datei in dateien:
        temporaer = ziel / (datei.name + ".kopie")
        shutil.copy2(datei, temporaer)
        os.replace(temporaer, ziel / datei.name)
    inhalt = {"uebernommen_am": (jetzt or datetime.now()).isoformat(timespec="seconds"), "quelle": str(quelle),
              "dateien": len(dateien), "grund": "Befund 5: eigener Kurs-Cache des Betriebs, einmalige Übernahme ohne Downloads"}
    temporaer = marke.with_suffix(".tmp")
    temporaer.write_text(json.dumps(inhalt, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(temporaer, marke)
    return {**inhalt, "neu": True}


def sicherstellen() -> dict:
    """Übernahme, falls noch nicht geschehen (nur im Betriebsmodus). Siehe `uebernehmen`."""
    return uebernehmen(_quelle(), _wurzel() / BEREICH)


def betriebs_kurscache() -> ParquetCache:
    """Kurs-Cache des Betriebs (`daten/betrieb/cache`, Bereich `kurse`); stellt vorher die Übernahme sicher."""
    sicherstellen()
    return ParquetCache(_wurzel())


def protokollzeile(info: dict) -> str:
    """Eine Zeile fürs Protokoll des Laufs."""
    am = datetime.fromisoformat(info["uebernommen_am"])
    if info.get("neu"):
        return (f"Kurs-Cache des Betriebs angelegt: einmalige Übernahme von {info['dateien']} Kursdateien aus daten/cache/kurse "
                "(ohne Downloads); der Betrieb schreibt ab jetzt nur in daten/betrieb/cache/kurse")
    return f"Kurs-Cache des Betriebs: daten/betrieb/cache/kurse (übernommen am {am:%d.%m.%Y %H:%M}, {info['dateien']} Dateien)"
