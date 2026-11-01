"""Gemeinsame Hilfen für die Daten-Tests: eine simulierte Yahoo-Quelle, ohne Internet."""
from datetime import date

import numpy as np
import pandas as pd
import pytest

from tradingbot.daten.cache import ParquetCache

HEUTE = date(2024, 7, 1)  # Montag


def yahoo_rohdaten(start="2024-01-01", ende="2024-06-30", tz="Europe/Berlin", basis=100.0) -> pd.DataFrame:
    """Kerzen im Yahoo-Format (Spaltennamen, Zeitzone), Werktage, leicht steigender Kurs."""
    tage = pd.bdate_range(start, ende, tz=tz)
    close = basis * (1.0005 ** np.arange(len(tage)))
    return pd.DataFrame(
        {
            "Open": close * 0.999,
            "High": close * 1.01,
            "Low": close * 0.99,
            "Close": close,
            "Adj Close": close * 0.97,
            "Volume": 1000.0,
            "Dividends": 0.0,
            "Stock Splits": 0.0,
        },
        index=pd.DatetimeIndex(tage, name="Date"),
    )


class SimulierteQuelle:
    """Verhält sich wie yfinance_abruf und merkt sich jeden Abruf."""

    def __init__(self, rohdaten: pd.DataFrame, waehrung="EUR"):
        self.rohdaten = rohdaten
        self.waehrung = waehrung
        self.abrufe: list[tuple[date, date]] = []

    def __call__(self, ticker, start, ende):
        self.abrufe.append((start, ende))
        tage = self.rohdaten.index.tz_localize(None).normalize()
        maske = (tage >= pd.Timestamp(start)) & (tage <= pd.Timestamp(ende))
        return self.rohdaten[maske], self.waehrung


@pytest.fixture
def cache(tmp_path):
    return ParquetCache(tmp_path / "cache")


@pytest.fixture
def quelle():
    return SimulierteQuelle(yahoo_rohdaten())
