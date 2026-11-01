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


def test_sec_apple_point_in_time(cache, tmp_path):
    from tradingbot.daten.sec import SecClient, kennzahl_jahreswerte, lade_erstmeldungen, stammdaten
    from tradingbot.konfiguration import lade_konfiguration

    try:
        client = SecClient(cache_wurzel=tmp_path / "sec")
    except KonfigurationsFehler:
        pytest.skip("SEC_USER_AGENT fehlt in .env")
    k = lade_konfiguration("fundamental")["kennzahlen"]
    erst = lade_erstmeldungen(320193, client=client, cache=cache)
    assert kennzahl_jahreswerte(erst, k["umsatz"], "2019-10-31").index.max() < pd.Timestamp("2019-09-28")   # 10-K vom 31.10.2019 noch nicht bekannt
    umsatz = kennzahl_jahreswerte(erst, k["umsatz"], "2019-11-01")
    assert umsatz.loc["2019-09-28", "wert"] == 260_174_000_000
    assert kennzahl_jahreswerte(erst, k["bilanzsumme"], "2019-11-01").loc["2019-09-28", "wert"] == 338_516_000_000
    assert stammdaten(320193, client=client)["sic"] == 3571


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
