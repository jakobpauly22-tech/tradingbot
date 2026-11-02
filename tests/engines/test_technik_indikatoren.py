"""Indikatoren der Technik-Engine, von Hand nachgerechnet."""
import numpy as np
import pandas as pd
import pytest

from tradingbot.engines.technik.indikatoren import (adx, atr, donchian_hoch, donchian_tief, momentum_12_1, rsi, sma,
                                                    true_range, wilder_glaettung)

TAGE = pd.bdate_range("2024-01-01", periods=5)


def test_sma_und_wilder():
    x = pd.Series([1.0, 2, 3, 4, 5], index=TAGE)
    assert sma(x, 3).tolist()[2:] == [2.0, 3.0, 4.0] and sma(x, 3).isna().sum() == 2
    w = wilder_glaettung(x, 3)
    # Start = (1+2+3)/3 = 2; dann 2 + (4−2)/3 = 2,6667; 2,6667 + (5−2,6667)/3 = 3,4444
    assert w.iloc[2:].tolist() == pytest.approx([2.0, 8 / 3, 8 / 3 + (5 - 8 / 3) / 3])


def test_true_range_und_atr():
    k = pd.DataFrame({"high": [10, 12, 11.0], "low": [9, 10, 8.0], "close": [9.5, 11, 10.0]}, index=TAGE[:3])
    # Tag 2: max(2, |12−9,5|, |10−9,5|) = 2,5; Tag 3: max(3, |11−11|, |8−11|) = 3
    assert true_range(k).tolist() == [1.0, 2.5, 3.0]
    assert atr(k, 2).iloc[1:].tolist() == pytest.approx([1.75, 1.75 + (3 - 1.75) / 2])


def test_rsi2_von_hand():
    c = pd.Series([10, 11, 10.5, 11.5, 11.0], index=TAGE)
    # Gewinne 1, 0, 1, 0; Verluste 0, 0,5, 0, 0,5 → RS 2, 6, 1,2
    assert rsi(c, 2).iloc[2:].tolist() == pytest.approx([100 - 100 / 3, 100 - 100 / 7, 100 - 100 / 2.2])
    assert rsi(pd.Series([1.0, 2, 3, 4], index=TAGE[:4]), 2).iloc[-1] == 100.0


def test_adx_dauerhafter_aufwaertstrend_ist_100():
    tage = pd.bdate_range("2024-01-01", periods=60)
    hoch = pd.Series(np.arange(60) + 11.0, index=tage)
    k = pd.DataFrame({"high": hoch, "low": hoch - 2, "close": hoch - 1})
    a = adx(k, 14)
    assert a.dropna().iloc[-1] == pytest.approx(100.0)
    assert a.isna().sum() == 1 + 13 + 13          # erster Tag ohne Differenz, je 13 Tage Anlauf für DI und ADX


def test_adx_seitwaerts_niedrig():
    tage = pd.bdate_range("2024-01-01", periods=120)
    rng = np.random.default_rng(3)
    c = pd.Series(100 + rng.normal(0, 0.5, 120), index=tage)
    k = pd.DataFrame({"high": c + 0.5, "low": c - 0.5, "close": c})
    assert adx(k, 14).iloc[-1] < 25


def test_momentum_12_1():
    tage = pd.bdate_range("2023-01-02", "2024-03-29")
    # Kurs je Monat konstant 100, 101, … (Jan 2023 = 100): im März 2024 (M) gilt C(Ende M−2 = Jan 2024) / C(Ende M−13 = Feb 2023) − 1
    c = pd.Series(100.0 + (tage.year - 2023) * 12 + tage.month - 1, index=tage)
    m = momentum_12_1(c)
    assert m.loc["2024-03-15"] == pytest.approx(112 / 101 - 1)
    assert m.loc["2024-02-15"] == pytest.approx(111 / 100 - 1)
    assert np.isnan(m.loc["2023-12-15"])                       # Ende Nov 2022 fehlt


def test_donchian_ohne_heutigen_tag():
    h = pd.Series([1.0, 5, 3, 4, 2], index=TAGE)
    assert donchian_hoch(h, 3).tolist()[3:] == [5.0, 5.0]
    assert donchian_tief(h, 2).tolist()[2:] == [1.0, 3.0, 3.0]
