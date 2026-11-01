"""Zugriff auf YAML-Konfiguration (config/) und Geheimnisse (.env)."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from ruamel.yaml import YAML

PROJEKT_WURZEL = Path(__file__).resolve().parents[2]


class KonfigurationsFehler(RuntimeError):
    """Fehlende oder ungültige Konfiguration."""


def lade_konfiguration(name: str) -> dict:
    """Liest config/<name>.yaml als Dictionary."""
    pfad = PROJEKT_WURZEL / "config" / f"{name}.yaml"
    if not pfad.exists():
        raise KonfigurationsFehler(f"Konfiguration fehlt: {pfad}")
    with pfad.open(encoding="utf-8") as datei:
        return YAML(typ="safe", pure=True).load(datei) or {}


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
