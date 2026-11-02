"""Gemeinsamer Nachbau-Code: Finanzwert-Kennzeichen point-in-time."""
import pandas as pd

from tradingbot.daten.sp500_nachbau import finanzwert_maske


def test_finanzwert_maske_point_in_time():
    tage = pd.bdate_range("2011-12-28", "2012-03-05")
    # wie American Tower: bis zum 10-K vom 29.02.2012 Funktürme (4899), danach REIT (6798)
    sic = {"AMT": [(pd.Timestamp("2010-03-01"), 4899), (pd.Timestamp("2012-02-29"), 6798)], "AAPL": [(pd.Timestamp("2010-10-27"), 3571)],
           "OHNE": []}
    m = finanzwert_maske(sic, tage, ["AMT", "AAPL", "OHNE"])
    assert not m.loc["2012-02-28", "AMT"] and m.loc["2012-02-29", "AMT"] and m.loc["2012-03-05", "AMT"]
    assert not m["AAPL"].any() and not m["OHNE"].any()
    frueh = finanzwert_maske({"X": [(pd.Timestamp("2013-01-01"), 6022)]}, tage, ["X"])
    assert frueh["X"].all()                                                    # vor dem ersten 10-K gilt der erste Code


def test_benchmark_laden_aus_dem_cache(tmp_path, monkeypatch):
    import pytest

    import tradingbot.daten.sp500_nachbau as N
    from tradingbot.daten.cache import ParquetCache

    cache = ParquetCache(tmp_path)
    monkeypatch.setattr(N, "standard_cache", lambda: cache)
    with pytest.raises(LookupError, match="nachbau_sp500_ohne_finanzwerte"):
        N.lade_benchmark_sp500_ohne_finanzwerte()
    tabelle = pd.DataFrame({"index_usd": [100.0, 101.0], "index_eur": [100.0, 100.5], "abdeckung": [0.95, 0.96]},
                           index=pd.DatetimeIndex(pd.to_datetime(["2016-10-03", "2016-10-04"]), name="datum"))
    cache.schreiben("benchmarks", N.BENCHMARK_SCHLUESSEL, tabelle, {"gegenprobe": "Lauf 4 bestanden"})
    geladen = N.lade_benchmark_sp500_ohne_finanzwerte()
    assert geladen["index_eur"].iloc[-1] == 100.5 and geladen.attrs["gegenprobe"] == "Lauf 4 bestanden"
