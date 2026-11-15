import pandas as pd
import pytest

from tradingbot.backtest.obergrenze_scheinverluste import (bestand_zum_vortag, gesamtrendite, kandidatentage, korrigierte_werte,
                                                           lies_ereignisse, neutralisiere, schlechteste_rendite)

BERICHT = """# Teil c1
## Probe
| XX (1) | Falsch | 2015-01-01 | -50.0% | 8-K |
## Treffer

| Ticker (CIK) | Name | Tage | Gesamtrendite (schlechteste) | SEC-Beleg (S2) |
| --- | --- | --- | --- | --- |
| CSC (23082) | Computer Sciences Corporation | 2015-11-30 bis 2015-12-03 | -39.8% | 8-K 2015-11-04 (0000023082-15-000060): spin-off |
| AET (1122304) | Aetna | 2017-02-17 | -3.3% | 8-K 2017-02-22 (0000950103-17-001608): spin-off |

## Unklar (≤ −15 % ohne SEC-Beleg)

| Ticker (CIK) | Name | Tage | Gesamtrendite |
| --- | --- | --- | --- |
| DISCK (1437107) | Discovery, Inc. | 2021-03-23 bis 2021-03-29 | -34.1% |
"""


def kurse(schluss, dividende=None, split=None):
    tage = pd.bdate_range("2020-01-01", periods=len(schluss))
    return pd.DataFrame({"close": schluss, "dividende": dividende or [0.0] * len(schluss), "split": split or [0.0] * len(schluss)}, index=tage)


def test_lies_ereignisse_treffer_und_unklar():
    e = lies_ereignisse(BERICHT)
    assert list(e["liste"]) == ["treffer", "treffer", "unklar"]
    assert list(e["ticker"]) == ["CSC", "AET", "DISCK"]
    assert e.iloc[0]["cik"] == 23082 and e.iloc[0]["bis"] == pd.Timestamp("2015-12-03")
    assert e.iloc[1]["von"] == e.iloc[1]["bis"] == pd.Timestamp("2017-02-17")
    assert e.iloc[2]["rendite"] == pytest.approx(-0.341)


def test_kandidatentage_einzeltag_und_zwei_tage_fenster():
    k = kurse([100, 95, 98, 96.5, 95, 100])          # Tag 1: −5 %; Tage 3+4: −1,5 % und −1,6 %, zusammen −3,1 %
    t = kandidatentage(k, k.index[0], k.index[-1])
    assert list(t.index) == [k.index[1], k.index[3], k.index[4]]
    assert t.iloc[0] == pytest.approx(-0.05)


def test_kandidatentage_nur_im_fenster_ohne_split_und_nur_negativ():
    k = kurse([100, 50, 49, 60, 50], split=[0, 2.0, 0, 0, 0])
    t = kandidatentage(k, k.index[1], k.index[3])      # Split-Tag zählt nicht, Tag 4 liegt außerhalb
    assert t.empty
    k2 = kurse([100, 98, 100, 96])                     # Paar (Tag 2, Tag 3): +2 % und −4 %; nur der negative Tag
    t2 = kandidatentage(k2, k2.index[3], k2.index[3])
    assert list(t2.index) == [k2.index[3]]


def test_dividende_zaehlt_zur_gesamtrendite():
    k = kurse([100, 96, 96], dividende=[0, 3.0, 0])    # −4 % Kurs, +3 Dividende → −1 %
    assert kandidatentage(k, k.index[0], k.index[-1]).empty
    assert schlechteste_rendite(k, k.index[1], k.index[1]) == pytest.approx(-0.01)


def test_neutralisiere_setzt_rendite_null_und_laesst_schluss():
    k = kurse([100, 60, 61])
    n = neutralisiere(k, [k.index[1]])
    assert gesamtrendite(n).iloc[1] == pytest.approx(0.0)
    assert gesamtrendite(n).iloc[2] == pytest.approx(gesamtrendite(k).iloc[2])
    assert list(n["close"]) == list(k["close"])


def test_bestand_zum_vortag():
    tage = pd.bdate_range("2020-01-01", periods=4)
    trades = pd.DataFrame({"datum": [tage[1], tage[2]], "ticker": ["A", "A"], "richtung": [1, -1], "stueck": [10, 4]})
    b = bestand_zum_vortag(trades, tage)
    assert list(b["A"]) == [0, 0, 10, 6]


def test_korrigierte_werte():
    tage = pd.bdate_range("2020-01-01", periods=3)
    w = pd.Series([100.0, 90.0, 99.0], index=tage)
    k = pd.Series([0.05], index=[tage[1]])            # Tag 1: −10 % + 5 Pp. = −5 %
    neu = korrigierte_werte(w, k)
    assert list(neu.round(6)) == [100.0, 95.0, 104.5]
