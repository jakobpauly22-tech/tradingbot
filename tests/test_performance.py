import importlib.util
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tradingbot.kennzahlen import performance as P

_pfad = Path(__file__).parent / "musterloesungen" / "referenz.py"
_spec = importlib.util.spec_from_file_location("referenz_performance", _pfad)
referenz = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(referenz)


def test_gleiche_formeln_wie_referenz():
    assert P.sharpe_ratio(0.0954, 0.0341, 0.3345) == referenz.sharpe_ratio(0.0954, 0.0341, 0.3345)
    assert P.beta(0.05, 0.04) == referenz.beta(0.05, 0.04)
    assert P.capm_alpha(0.0954, 0.0341, 0.91, 0.0678) == referenz.capm_alpha(0.0954, 0.0341, 0.91, 0.0678)


def test_cagr_und_drawdown_von_hand():
    werte = pd.Series([100.0, 120.0, 90.0, 95.0, 130.0], index=pd.to_datetime(
        ["2020-01-01", "2020-06-01", "2021-01-01", "2021-06-01", "2022-01-01"]))
    assert P.cagr(werte) == pytest.approx(1.3 ** (365.25 / 731) - 1)
    mdd = P.max_drawdown(werte)
    assert mdd["max_drawdown"] == pytest.approx(90 / 120 - 1)
    assert mdd["hoch"] == pd.Timestamp("2020-06-01") and mdd["tief"] == pd.Timestamp("2021-01-01")
    assert mdd["erholt"] == pd.Timestamp("2022-01-01")


def test_var_cvar():
    r = pd.Series(np.arange(-0.10, 0.10, 0.001))  # 200 gleichverteilte Renditen
    var, cvar = P.var_cvar_historisch(r, 0.95)
    assert var == pytest.approx(-np.quantile(r, 0.05))
    assert cvar == pytest.approx(-r[r <= np.quantile(r, 0.05)].mean())
    assert cvar > var


def test_jensens_alpha_findet_bekanntes_alpha_und_beta():
    rng = np.random.default_rng(7)
    tage = pd.bdate_range("2015-01-01", periods=2000)
    r_m = pd.Series(rng.normal(0.0004, 0.01, len(tage)), index=tage)
    rf = pd.Series(0.00005, index=tage)
    r_p = rf + 0.0002 + 1.2 * (r_m - rf) + pd.Series(rng.normal(0, 0.002, len(tage)), index=tage)
    erg = P.jensens_alpha(r_p, r_m, rf)
    assert erg["beta"] == pytest.approx(1.2, abs=0.01)
    assert erg["alpha_pa"] == pytest.approx(0.0002 * 252, abs=0.015)
    assert erg["t_alpha"] > 2


def test_newey_west_ohne_lags_ist_white():
    rng = np.random.default_rng(3)
    x = np.column_stack([np.ones(500), rng.normal(size=500)])
    y = x @ np.array([0.5, 2.0]) + rng.normal(size=500) * (1 + np.abs(x[:, 1]))
    koeff, se = P.ols_newey_west(y, x, lags=0)
    u = y - x @ koeff
    xtx_inv = np.linalg.inv(x.T @ x)
    white = xtx_inv @ (x.T * u**2) @ x @ xtx_inv
    assert se == pytest.approx(np.sqrt(np.diag(white)))


def test_rf_und_monatsrenditen():
    tage = pd.bdate_range("2024-01-01", "2024-03-31")
    rf = P.risikofreie_tagesrendite(pd.Series([4.0], index=pd.to_datetime(["2023-09-20"])), tage)
    assert (1 + rf).prod() ** (252 / len(tage)) == pytest.approx(1.04)
    werte = pd.Series(100.0, index=tage)
    werte.loc["2024-02-01":] = 110.0
    tabelle = P.monatsrenditen(werte)
    assert tabelle.loc[2024, 1] == pytest.approx(0.0) and tabelle.loc[2024, 2] == pytest.approx(0.10)
    assert tabelle.loc[2024, "Jahr"] == pytest.approx(0.10)


def test_kennzahlen_ohne_schwankung():
    # Ein Teilportfolio, das nie handeln konnte (nur Cash), darf die Auswertung nicht abbrechen
    tage = pd.bdate_range("2020-01-01", periods=300)
    nur_cash = pd.Series(150.0, index=tage)
    markt = pd.Series(100 * np.cumprod(1 + np.random.default_rng(2).normal(0.0003, 0.01, 300)), index=tage)
    k = P.kennzahlen(nur_cash, markt)
    assert math.isnan(k["sharpe"]) and k["volatilitaet"] == 0.0 and k["beta"] == pytest.approx(0.0)


def test_kennzahlen_gegen_sich_selbst():
    tage = pd.bdate_range("2020-01-01", periods=600)
    werte = pd.Series(100 * np.cumprod(1 + np.random.default_rng(5).normal(0.0003, 0.01, 600)), index=tage)
    k = P.kennzahlen(werte, benchmark=werte)
    assert k["beta"] == pytest.approx(1.0) and k["tracking_error"] == pytest.approx(0.0)
    assert k["differenz_cagr"] == 0.0 and k["tage_notbremse_core"] == 0
    assert math.isnan(k["information_ratio"])
