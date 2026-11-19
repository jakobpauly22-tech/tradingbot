"""Zugriff auf YAML-Konfiguration (config/) und Geheimnisse (.env)."""
from __future__ import annotations

import copy
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from ruamel.yaml import YAML

PROJEKT_WURZEL = Path(__file__).resolve().parents[2]


class KonfigurationsFehler(RuntimeError):
    """Fehlende oder ungültige Konfiguration."""


_GELESEN: dict[Path, tuple[tuple[int, int], dict]] = {}


def lade_konfiguration(name: str) -> dict:
    """Liest config/<name>.yaml als Dictionary.

    Laufzeit (Jakob 19.11.2026): Die Datei wird nur neu geparst, wenn sich Änderungszeit oder Größe geändert haben; sonst
    kommt eine tiefe Kopie des zuletzt gelesenen Inhalts zurück. Jeder Aufrufer bekommt also wie bisher ein eigenes
    Dictionary, und eine geänderte Datei wirkt sofort. (Vorher: ein Tageslauf parste dieselben Dateien über 2.300-mal.)
    """
    pfad = PROJEKT_WURZEL / "config" / f"{name}.yaml"
    try:
        st = pfad.stat()
    except FileNotFoundError:
        raise KonfigurationsFehler(f"Konfiguration fehlt: {pfad}") from None
    stand = (st.st_mtime_ns, st.st_size)
    gelesen = _GELESEN.get(pfad)
    if gelesen is None or gelesen[0] != stand:
        with pfad.open(encoding="utf-8") as datei:
            inhalt = YAML(typ="safe", pure=True).load(datei) or {}
        _GELESEN[pfad] = gelesen = (stand, inhalt)
    return copy.deepcopy(gelesen[1])


@lru_cache(maxsize=1)
def _env_laden() -> None:
    load_dotenv(PROJEKT_WURZEL / ".env", override=False)


def geheimnis(name: str) -> str:
    """Liest einen Schlüssel aus der Umgebung bzw. .env. Der Wert wird nie geloggt."""
    _env_laden()
    wert = os.environ.get(name, "").strip()
    if not wert:
        raise KonfigurationsFehler(f"{name} fehlt in .env (siehe .env.example)")
    return wert
