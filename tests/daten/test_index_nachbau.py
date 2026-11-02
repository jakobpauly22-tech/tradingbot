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


def _index(renditen, start="2012-01-03"):
    tage = pd.bdate_range(start, periods=len(renditen))
    return pd.Series(100 * np.cumprod(1 + np.asarray(renditen)), index=tage)


def test_abnahme_bestanden_bei_nahezu_gleichem_verlauf():
    from tradingbot.daten.index_nachbau import abnahme_gegenprobe

    rng = np.random.default_rng(3)
    r = rng.normal(0.0005, 0.01, 3270)                              # ca. 2012–2024, gewertet ab 01.04.2016
    referenz = _index(r)
    nachbau = _index(r + rng.normal(0, 0.0002, len(r)))              # 0,02 % Rauschen je Tag (≈ 0,3 Pp. p.a.), keine Drift
    a = abnahme_gegenprobe(nachbau, referenz)
    assert a["kriterien"]["korrelation"]["wert"] > 0.99 and a["bestanden"]
    assert list(a["jahre"].index) == list(range(2016, 2025)) and a["zeitraum"][0] >= pd.Timestamp("2016-04-01").date()


def test_abnahme_verfehlt_bei_drift_und_bei_einem_ausreisserjahr():
    from tradingbot.daten.index_nachbau import abnahme_gegenprobe

    rng = np.random.default_rng(4)
    r = rng.normal(0.0005, 0.01, 3270)
    referenz = _index(r)
    drift = abnahme_gegenprobe(_index(r + 0.0001), referenz)         # +0,01 % je Tag ≈ +2,5 Pp. p.a.
    assert not drift["kriterien"]["annualisiert_abweichung"]["bestanden"] and not drift["bestanden"]
    ausreisser = r.copy()
    tag = 1600                                                       # ein Tag mit +3 % zusätzlich, im Abnahmezeitraum
    ausreisser[tag] += 0.03
    jahr = referenz.index[tag].year
    assert 2016 < jahr < 2024
    einzel = abnahme_gegenprobe(_index(ausreisser), referenz)
    assert not einzel["kriterien"]["jahresabweichung_max"]["bestanden"]
    assert einzel["jahre"]["abweichung"].abs().idxmax() == jahr
    assert einzel["kriterien"]["korrelation"]["bestanden"]          # Korrelation allein hätte es nicht bemerkt


def test_marktwert_aus_streubesitz_fortgeschrieben():
    from tradingbot.daten.index_nachbau import marktwerte_aus_streubesitz

    tage = pd.bdate_range("2019-06-27", "2019-07-05")
    schluss = pd.DataFrame({"A": [100.0, 100.0, 110.0, 120.0, 120.0, 132.0, 132.0]}, index=tage)
    reihe = pd.DataFrame({"wert": [5e10, 3e19], "filed": pd.to_datetime(["2019-07-01", "2019-07-03"])},
                         index=pd.to_datetime(["2019-06-28", "2019-07-02"]))       # zweiter Wert unplausibel
    mw = marktwerte_aus_streubesitz(schluss, {"A": reihe})["A"]
    assert mw.loc[:"2019-07-01"].isna().all()                                     # erst ab dem Tag nach filed
    assert mw.loc["2019-07-02"] == pytest.approx(5e10 * 120 / 100)               # Kurs am Messtag 28.06.: 100
    assert mw.loc["2019-07-05"] == pytest.approx(5e10 * 132 / 100)               # 3·10¹⁹ verworfen, alter Wert läuft weiter
