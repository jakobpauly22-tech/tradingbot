"""Integrationstests gegen die echten Quellen. Ausführen mit: pytest -m netz"""
from datetime import date

import pandas as pd
import pytest

from tradingbot.daten.cache import ParquetCache
from tradingbot.daten.kurse import lade_kurse, lade_kurse_eur
from tradingbot.daten.makro import makro_am_stichtag
from tradingbot.daten.pruefung import pruefe_kurse
from tradingbot.konfiguration import KonfigurationsFehler, geheimnis

pytestmark = pytest.mark.netz


@pytest.fixture
def cache(tmp_path):
    return ParquetCache(tmp_path)


def test_benchmark_etf_von_yahoo(cache):
    kurse = lade_kurse("SPYI.DE", "2024-06-03", "2024-06-28", cache=cache)
    assert kurse.attrs["waehrung"] == "EUR"
    assert 18 <= len(kurse) <= 20
    assert pruefe_kurse(kurse) == []


def test_us_aktie_in_euro(cache):
    kurse = lade_kurse_eur("AAPL", "2024-06-03", "2024-06-28", cache=cache)
    assert kurse.attrs["originalwaehrung"] == "USD"
    assert kurse["close"].between(150, 250).all()  # Plausibilität: Apple lag im Juni 2024 bei ca. 180–200 €


def test_fred_revision_und_marktdaten(cache):
    try:
        geheimnis("FRED_API_KEY")
    except KonfigurationsFehler:
        pytest.skip("FRED_API_KEY fehlt in .env")
    gdp_mai_2023 = makro_am_stichtag("GDP", "2023-05-01", cache=cache)
    assert gdp_mai_2023[pd.Timestamp("2023-01-01")] == pytest.approx(26465.865)
    dgs10 = makro_am_stichtag("DGS10", date(2024, 6, 5), cache=cache)
    assert dgs10.index[-1] == pd.Timestamp("2024-06-04")
    assert dgs10.iloc[-1] == pytest.approx(4.33)
