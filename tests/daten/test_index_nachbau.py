"""Index-Nachbau: von Hand nachrechenbare Beispiele."""
import numpy as np
import pandas as pd
import pytest

from tradingbot.daten.index_nachbau import aktien_splitbereinigt, gesamtrenditen, marktwert_index


def test_aktien_splitbereinigt():
    aktien = pd.Series([100.0, 110.0], index=pd.to_datetime(["2014-01-31", "2014-08-01"]))
    splits = pd.Series([0.0, 7.0, 0.0], index=pd.to_datetime(["2014-05-01", "2014-06-09", "2014-07-01"]))
    neu = aktien_splitbereinigt(aktien, splits)
    assert neu.tolist() == [700.0, 110.0]                    # vor dem Split gemeldet → mal 7


def test_marktwert_index_von_hand():
    tage = pd.bdate_range("2024-01-01", periods=3)
    renditen = pd.DataFrame({"A": [np.nan, 0.10, 0.00], "B": [np.nan, 0.00, 0.20]}, index=tage)
    marktwerte = pd.DataFrame({"A": [300.0, 330.0, 330.0], "B": [100.0, 100.0, 120.0]}, index=tage)
    mitglied = pd.DataFrame(True, index=tage, columns=["A", "B"])
    i = marktwert_index(renditen, marktwerte, mitglied)
    # Tag 2: Gewichte 0,75/0,25 → 7,5 %; Tag 3: Gewichte 330/430 und 100/430 → 0,2 · 100/430
    assert i["index"].tolist() == pytest.approx([100.0, 107.5, 107.5 * (1 + 0.2 * 100 / 430)])
    assert i["abdeckung"].iloc[1] == 1.0


def test_ausschluss_und_fehlende_kurse():
    tage = pd.bdate_range("2024-01-01", periods=3)
    renditen = pd.DataFrame({"A": [np.nan, 0.10, 0.10], "F": [np.nan, -0.50, -0.50]}, index=tage)
    marktwerte = pd.DataFrame({"A": [100.0, 110.0, 121.0], "F": [100.0, 50.0, 25.0]}, index=tage)
    ohne_fin = pd.DataFrame({"A": True, "F": False}, index=tage)
    assert marktwert_index(renditen, marktwerte, ohne_fin)["index"].iloc[-1] == pytest.approx(121.0)
    luecke = renditen.copy()
    luecke.loc[tage[2], "A"] = np.nan
    i = marktwert_index(luecke, marktwerte, pd.DataFrame(True, index=tage, columns=["A", "F"]))
    assert i["abdeckung"].iloc[2] == 0.5                      # A ohne Kurs: zählt zur Lücke, wird nicht aufgefüllt


def test_gesamtrendite_mit_dividende():
    tage = pd.bdate_range("2024-01-01", periods=3)
    k = pd.DataFrame({"close": [100.0, 98.0, 99.0], "dividende": [0.0, 3.0, 0.0]}, index=tage)
    r = gesamtrenditen({"A": k}, tage)["A"]
    assert r.iloc[1] == pytest.approx(0.01) and r.iloc[2] == pytest.approx(99 / 98 - 1)
