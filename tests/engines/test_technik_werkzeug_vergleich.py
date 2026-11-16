"""Vergleichstabelle im Technik-Werkzeug (tools/backtest_technik.py): nur Zeilen derselben Art paaren (Fehler 16.11.2026)."""
import importlib.util
from pathlib import Path

import pandas as pd


def _werkzeug():
    pfad = Path(__file__).parents[2] / "tools" / "backtest_technik.py"
    spec = importlib.util.spec_from_file_location("werkzeug_backtest_technik", pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _kriterien(sharpe_nach: float, sharpe_ohne: float) -> pd.DataFrame:
    return pd.DataFrame([
        {"variante": "crossover", "art": "nach Kosten", "abschnitt": "gesamt", "cagr": 0.01, "sharpe": sharpe_nach, "max_dd": -0.2},
        {"variante": "crossover", "art": "ohne Kosten", "abschnitt": "gesamt", "cagr": 0.02, "sharpe": sharpe_ohne, "max_dd": -0.1},
    ])


def test_vergleichspaare_nur_nach_kosten():
    paare = _werkzeug().vergleichspaare(_kriterien(0.3, 0.5), _kriterien(0.2, 0.5))
    assert len(paare) == 1
    vorher, jetzt = paare[0]
    assert vorher.art == "nach Kosten" and vorher.sharpe == 0.3
    assert jetzt["sharpe"] == 0.2
