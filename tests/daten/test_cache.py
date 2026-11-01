import pandas as pd

from tradingbot.daten.cache import ParquetCache


def test_schreiben_und_lesen_behaelt_daten_index_und_meta(tmp_path):
    cache = ParquetCache(tmp_path)
    daten = pd.DataFrame({"close": [1.0, 2.0]}, index=pd.DatetimeIndex(["2024-01-02", "2024-01-03"], name="datum"))
    cache.schreiben("kurse", "EURUSD=X", daten, {"quelle": "test", "von": "2024-01-01"})

    gelesen, meta = cache.lesen("kurse", "EURUSD=X")

    pd.testing.assert_frame_equal(gelesen, daten, check_freq=False)
    assert meta["quelle"] == "test" and meta["von"] == "2024-01-01"
    assert not list(tmp_path.rglob("*.tmp"))


def test_fehlender_eintrag_gibt_none(tmp_path):
    assert ParquetCache(tmp_path).lesen("kurse", "XYZ") == (None, {})


def test_namenskollision_nach_sonderzeichen_wird_erkannt(tmp_path):
    cache = ParquetCache(tmp_path)
    daten = pd.DataFrame({"close": [1.0]})
    cache.schreiben("kurse", "A=B", daten, {})
    assert cache.pfad("kurse", "A=B") == cache.pfad("kurse", "A_B")
    assert cache.lesen("kurse", "A_B") == (None, {})
