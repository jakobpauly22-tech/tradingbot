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
