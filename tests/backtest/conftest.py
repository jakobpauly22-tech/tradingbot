"""Hilfen für Backtest-Tests: kleine, von Hand nachrechenbare Marktdaten."""
import pandas as pd
import pytest

from tradingbot.backtest.kosten import Kostenmodell
from tradingbot.backtest.simulation import Ausfuehrungsregeln

KONFIG_TEST = {
    "tresor": {"gesperrt_ab": "2025-01-01", "protokoll": None},  # Pfad setzt die Fixture
    "kosten": {
        "gebuehren": {
            "EUR": {"satz": 0.0005, "minimum": 1.25, "maximum": 29.0},
            "USD": {"je_stueck": 0.005, "minimum": 1.0, "max_anteil": 0.01},
        },
        "spread": {"etf": 0.0005, "aktie": 0.0010, "klein": 0.0025},
        "slippage": 0.0005,
        "waehrungstausch": {"satz": 0.00002, "minimum_usd": 2.0},
    },
    "ausfuehrung": {"max_gebuehr_anteil": 0.01, "ganze_stuecke": True},
    "steuern": {
        "abgeltungsteuer": 0.25,
        "soli": 0.055,
        "kirchensteuer": 0.0,
        "sparer_pauschbetrag": 1000.0,
        "teilfreistellung": {"aktienfonds": 0.30, "mischfonds": 0.15, "sonstiger_fonds": 0.0},
        "quellensteuer": {"USD": 0.15},
        "pauschbetrag_anteil": {"depot": 1.0, "schatten": 0.0},
        "basiszins_prozent": {2023: 2.55, 2024: 2.29},
    },
}


def kerzen(schluss, start="2024-01-01", eroeffnung=None, dividende=None) -> pd.DataFrame:
    """Kerzen an Werktagen; Eröffnung standardmäßig = Schluss des Vortags (erster Tag: eigener Schluss)."""
    tage = pd.bdate_range(start, periods=len(schluss), name="datum")
    schluss = pd.Series(schluss, index=tage, dtype=float)
    offen = pd.Series(eroeffnung, index=tage, dtype=float) if eroeffnung is not None else schluss.shift(1).fillna(schluss.iloc[0])
    return pd.DataFrame(
        {
            "open": offen,
            "high": pd.concat([offen, schluss], axis=1).max(axis=1),
            "low": pd.concat([offen, schluss], axis=1).min(axis=1),
            "close": schluss,
            "volume": 1000.0,
            "dividende": dividende if dividende is not None else 0.0,
            "split": 0.0,
        },
        index=tage,
    )


@pytest.fixture
def konfig(tmp_path):
    k = {key: (dict(v) if isinstance(v, dict) else v) for key, v in KONFIG_TEST.items()}
    k["tresor"] = {"gesperrt_ab": "2025-01-01", "protokoll": str(tmp_path / "TRESOR_PROTOKOLL.md")}
    return k


@pytest.fixture
def ohne_kosten():
    return Kostenmodell.ohne_kosten()


@pytest.fixture
def mit_kosten(konfig):
    return Kostenmodell.aus_konfig(konfig)


@pytest.fixture
def bruchteile():
    return Ausfuehrungsregeln(max_gebuehr_anteil=1.0, ganze_stuecke=False)
