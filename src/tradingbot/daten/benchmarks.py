"""Benchmark-Kurse für den Core (MSCI ACWI IMI und Vergleichsindizes über ETFs, siehe config/daten.yaml)."""
from __future__ import annotations

from datetime import date

import pandas as pd

from tradingbot.daten.kurse import lade_kurse_eur


def _konfig(konfig: dict | None) -> dict:
    if konfig is None:
        from tradingbot.konfiguration import lade_konfiguration

        konfig = lade_konfiguration("daten")
    return konfig


def historie_ab(konfig: dict | None = None) -> date:
    """Frühester Tag, ab dem Benchmark-Kurse verwendet werden."""
    return pd.Timestamp(str(_konfig(konfig)["benchmarks"]["historie_ab"])).date()


def core_benchmarks(konfig: dict | None = None) -> list[dict]:
    """Hauptbenchmark zuerst, dann die Vergleichsindizes; jeweils {name, ticker, rolle}."""
    core = _konfig(konfig)["benchmarks"]["core"]
    return [{**core["haupt"], "rolle": "haupt"}] + [{**v, "rolle": "vergleich"} for v in core["vergleich"]]


def lade_benchmark(ticker: str, start, ende=None, *, konfig: dict | None = None, **kwargs) -> pd.DataFrame:
    """Benchmark-Kurse in Euro; ein früherer Start wird auf `historie_ab` angehoben."""
    konfig = _konfig(konfig)
    start = max(pd.Timestamp(start).date(), historie_ab(konfig))
    return lade_kurse_eur(ticker, start, ende, konfig=konfig, **kwargs)
