"""Lokaler Parquet-Cache für Zeitreihen, mit Metadaten (Quelle, Zeitraum, Abrufzeit).

Ablage: <wurzel>/<bereich>/<schluessel>.parquet, z.B. daten/cache/kurse/SPYI.DE.parquet.
Die Metadaten stehen im Parquet-Schema, damit Daten und Herkunft nie auseinanderlaufen.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

_META_FELD = b"tradingbot"


class ParquetCache:
    def __init__(self, wurzel: Path | str):
        self.wurzel = Path(wurzel)

    def pfad(self, bereich: str, schluessel: str) -> Path:
        dateiname = re.sub(r"[^A-Za-z0-9._-]", "_", schluessel)
        return self.wurzel / bereich / f"{dateiname}.parquet"

    def lesen(self, bereich: str, schluessel: str) -> tuple[pd.DataFrame | None, dict]:
        """Gibt (Daten, Metadaten) zurück, oder (None, {}) wenn nichts im Cache liegt."""
        pfad = self.pfad(bereich, schluessel)
        if not pfad.exists():
            return None, {}
        tabelle = pq.read_table(pfad)
        meta = json.loads((tabelle.schema.metadata or {}).get(_META_FELD, b"{}"))
        if meta.get("schluessel") != schluessel:  # Namenskollision nach Ersetzen von Sonderzeichen
            return None, {}
        return tabelle.to_pandas(), meta

    def schreiben(self, bereich: str, schluessel: str, daten: pd.DataFrame, meta: dict) -> None:
        """Schreibt atomar (erst temporäre Datei, dann umbenennen), damit kein halber Cache entsteht."""
        pfad = self.pfad(bereich, schluessel)
        pfad.parent.mkdir(parents=True, exist_ok=True)
        tabelle = pa.Table.from_pandas(daten)
        schema_meta = dict(tabelle.schema.metadata or {})
        schema_meta[_META_FELD] = json.dumps({**meta, "schluessel": schluessel}, default=str).encode()
        tabelle = tabelle.replace_schema_metadata(schema_meta)
        temporaer = pfad.with_suffix(".tmp")
        pq.write_table(tabelle, temporaer)
        os.replace(temporaer, pfad)


def standard_cache() -> ParquetCache:
    from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration

    return ParquetCache(PROJEKT_WURZEL / lade_konfiguration("daten")["cache"]["pfad"])
