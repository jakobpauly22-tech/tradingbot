"""Performance- und Risikokennzahlen für Backtest, Paper Trading und Journal.

Konventionen:
- Eingabe sind Tageswerte eines Portfolios (Wertreihe) oder Tagesrenditen.
- Renditen werden geometrisch annualisiert (wissen/01_Bewertung_und_Corporate_Finance.md, Abschnitt 5 und
  „Bezug zum Trading-Bot“: Backtest-Kennzahlen immer geometrisch ausweisen).
- Volatilität: Standardabweichung der Tagesrenditen (N − 1) · √252.
- Funktionen mit Namen aus tests/musterloesungen/referenz.py haben dieselbe Signatur.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

HANDELSTAGE = 252


# --- Grundformeln wie in referenz.py -------------------------------------------------------------
def sharpe_ratio(r, rf, sigma):
    """Sharpe Ratio SR = (μ_p − r_f) / σ_p.

    Quelle: wissen/09_Oekonometrie.md, Abschnitt 6; wissen/04_Finanzielles_Risikomanagement.md, Abschnitt 2.
    """
    return (r - rf) / sigma


def beta(cov_im, var_m):
    """Marktbeta β = Cov(r_i, r_M) / Var(r_M). Quelle: wissen/01_Bewertung_und_Corporate_Finance.md, Abschnitt 5."""
    return cov_im / var_m


def capm_alpha(r, rf, beta_i, rm):
    """Jensens Alpha α = r − (r_f + β (r_M − r_f)). Quelle: wissen/09_Oekonometrie.md, Abschnitt 6."""
    return r - (rf + beta_i * (rm - rf))


# --- Renditen ------------------------------------------------------------------------------------
def tagesrenditen(werte: pd.Series) -> pd.Series:
    """r_t = W_t / W_{t−1} − 1."""
    return werte.pct_change().dropna()


def cagr(werte: pd.Series) -> float:
    """Geometrische Jahresrendite CAGR = (W_T / W_0)^(365,25 / Kalendertage) − 1."""
    tage = (werte.index[-1] - werte.index[0]).days
    if tage <= 0:
        return float("nan")
    return (werte.iloc[-1] / werte.iloc[0]) ** (365.25 / tage) - 1


def annualisiert_geometrisch(renditen: pd.Series) -> float:
    """(Π (1 + r_t))^(252 / n) − 1 für Tagesrenditen."""
    n = len(renditen)
    return float(np.prod(1 + renditen.to_numpy()) ** (HANDELSTAGE / n) - 1) if n else float("nan")


def volatilitaet(renditen: pd.Series) -> float:
    """σ_annual = s(r_t) · √252, s mit N − 1 (wissen/01, Abschnitt 5)."""
    return float(renditen.std(ddof=1) * math.sqrt(HANDELSTAGE))


def risikofreie_tagesrendite(zins_prozent: pd.Series, index: pd.DatetimeIndex) -> pd.Series:
    """Tagesrendite aus einem Jahreszins in Prozent: r_f,t = (1 + i/100)^(1/252) − 1.

    Annahme: Zins gilt ab seinem Datum bis zur nächsten Änderung (vorwärts gefüllt, kein Blick nach vorn).
    """
    zins = zins_prozent.reindex(zins_prozent.index.union(index)).ffill().reindex(index)
    return (1 + zins / 100) ** (1 / HANDELSTAGE) - 1


def monatsrenditen(werte: pd.Series) -> pd.DataFrame:
    """Tabelle Jahr × Monat der geometrischen Monatsrenditen, letzte Spalte Jahresrendite."""
    monatsende = werte.resample("ME").last()
    start = pd.Series([werte.iloc[0]], index=[werte.index[0] - pd.offsets.MonthEnd(1)])
    monate = pd.concat([start, monatsende]).pct_change().dropna()
    tabelle = pd.DataFrame({"jahr": monate.index.year, "monat": monate.index.month, "r": monate.to_numpy()})
    tabelle = tabelle.pivot(index="jahr", columns="monat", values="r")
    tabelle["Jahr"] = (1 + tabelle.fillna(0)).prod(axis=1) - 1
    return tabelle


# --- Drawdown und Extremrisiko -------------------------------------------------------------------
def drawdown(werte: pd.Series) -> pd.Series:
    """DD_t = W_t / max_{s≤t} W_s − 1 (Verlust vom letzten Höchststand, ROADMAP „Was Risiko im Bot bedeutet“)."""
    return werte / werte.cummax() - 1


def max_drawdown(werte: pd.Series) -> dict:
    """Größter Drawdown mit Höchststand, Tiefpunkt und Erholung (None, wenn noch nicht erholt)."""
    dd = drawdown(werte)
    tief = dd.idxmin()
    hoch = werte.loc[:tief].idxmax()
    danach = werte.loc[tief:]
    erholt = danach[danach >= werte.loc[hoch]]
    return {
        "max_drawdown": float(dd.min()),
        "hoch": hoch,
        "tief": tief,
        "erholt": erholt.index[0] if len(erholt) else None,
        "dauer_tage": ((erholt.index[0] if len(erholt) else werte.index[-1]) - hoch).days,
    }


def calmar_ratio(werte: pd.Series) -> float:
    """Calmar = CAGR / |Max Drawdown| (Standarddefinition, nicht in wissen/)."""
    mdd = max_drawdown(werte)["max_drawdown"]
    return cagr(werte) / abs(mdd) if mdd < 0 else float("nan")


def var_cvar_historisch(renditen: pd.Series, niveau: float = 0.95) -> tuple[float, float]:
    """Historischer VaR und CVaR (Expected Shortfall) als positive Verlustquoten je Tag.

    VaR = −Quantil_{1−α}(r); CVaR = −Mittelwert(r | r ≤ Quantil_{1−α}).
    Quelle: wissen/04_Finanzielles_Risikomanagement.md, Abschnitte 1 und 3 (historische Simulation).
    """
    grenze = float(np.quantile(renditen.to_numpy(), 1 - niveau))
    return -grenze, -float(renditen[renditen <= grenze].mean())


def sortino_ratio(renditen: pd.Series, rf_tag: pd.Series) -> float:
    """Sortino = (μ_p − r_f) / Downside-Abweichung, Downside = √(Mittel(min(r − r_f, 0)²)) · √252.

    Zähler geometrisch wie bei der Sharpe Ratio. Standarddefinition (Sortino/Price 1994), nicht in wissen/.
    """
    ueber = renditen - rf_tag.reindex(renditen.index).fillna(0.0)
    unten = math.sqrt(float((np.minimum(ueber, 0.0) ** 2).mean())) * math.sqrt(HANDELSTAGE)
    zaehler = annualisiert_geometrisch(renditen) - annualisiert_geometrisch(rf_tag.reindex(renditen.index).fillna(0.0))
    return zaehler / unten if unten > 0 else float("nan")


# --- Vergleich mit der Benchmark ---------------------------------------------------------------
def newey_west_lags(n: int) -> int:
    """Faustregel L = ⌊4 · (n/100)^(2/9)⌋ (Newey/West 1994)."""
    return int(math.floor(4 * (n / 100) ** (2 / 9)))


def ols_newey_west(y: np.ndarray, x: np.ndarray, lags: int) -> tuple[np.ndarray, np.ndarray]:
    """OLS mit Newey-West-Standardfehlern (robust gegen Heteroskedastizität und Autokorrelation).

    β̂ = (X′X)⁻¹X′y;  V̂ = (X′X)⁻¹ Ŝ (X′X)⁻¹,
    Ŝ = Σ_t û_t² x_t x_t′ + Σ_{l=1..L} w_l Σ_t û_t û_{t−l} (x_t x_{t−l}′ + x_{t−l} x_t′),  w_l = 1 − l/(L+1).
    Quelle: wissen/09_Oekonometrie.md, Abschnitt 2 (Annahmenverletzungen, Newey-West) und „Bezug zum Trading-Bot“.
    """
    xtx_inv = np.linalg.inv(x.T @ x)
    koeff = xtx_inv @ x.T @ y
    u = y - x @ koeff
    xu = x * u[:, None]
    s = xu.T @ xu
    for l in range(1, lags + 1):
        w = 1 - l / (lags + 1)
        g = xu[l:].T @ xu[:-l]
        s += w * (g + g.T)
    kov = xtx_inv @ s @ xtx_inv
    return koeff, np.sqrt(np.diag(kov))


def jensens_alpha(r_p: pd.Series, r_m: pd.Series, rf_tag: pd.Series, lags: int | None = None) -> dict:
    """Regression der Überrenditen r_p − r_f = α + β (r_M − r_f) + ε auf Tagesbasis.

    α wird mit 252 annualisiert (arithmetisch, wie in der Regression geschätzt); t-Werte mit Newey-West.
    Quelle: wissen/09_Oekonometrie.md, Abschnitt 6.
    """
    daten = pd.concat({"p": r_p, "m": r_m, "f": rf_tag}, axis=1).dropna()
    y = (daten["p"] - daten["f"]).to_numpy()
    x = np.column_stack([np.ones(len(daten)), (daten["m"] - daten["f"]).to_numpy()])
    lags = newey_west_lags(len(daten)) if lags is None else lags
    koeff, se = ols_newey_west(y, x, lags)
    return {
        "alpha_pa": float(koeff[0] * HANDELSTAGE),
        "beta": float(koeff[1]),
        "t_alpha": float(koeff[0] / se[0]) if se[0] > 0 else float("nan"),
        "t_beta": float(koeff[1] / se[1]) if se[1] > 0 else float("nan"),
        "n": len(daten),
        "lags": lags,
    }


def tracking_error(r_p: pd.Series, r_m: pd.Series) -> float:
    """TE = s(r_p − r_M) · √252 (Standarddefinition, nicht in wissen/)."""
    differenz = (r_p - r_m).dropna()
    return float(differenz.std(ddof=1) * math.sqrt(HANDELSTAGE))


def information_ratio(r_p: pd.Series, r_m: pd.Series) -> float:
    """IR = (geometrische Jahresrendite p − Benchmark) / Tracking Error (Standarddefinition, nicht in wissen/)."""
    gemeinsam = pd.concat({"p": r_p, "m": r_m}, axis=1).dropna()
    te = tracking_error(gemeinsam["p"], gemeinsam["m"])
    if te == 0:
        return float("nan")
    return (annualisiert_geometrisch(gemeinsam["p"]) - annualisiert_geometrisch(gemeinsam["m"])) / te


def rollierender_rueckstand(werte_p: pd.Series, werte_m: pd.Series, fenster: int = HANDELSTAGE) -> pd.Series:
    """12-Monats-Rendite Portfolio minus Benchmark (Prozentpunkte als Dezimalzahl).

    Für die Core-Notbremse (CLAUDE.md): Review, wenn der Wert unter −0,10 liegt.
    """
    gemeinsam = pd.concat({"p": werte_p, "m": werte_m}, axis=1).dropna()
    return (gemeinsam["p"].pct_change(fenster) - gemeinsam["m"].pct_change(fenster)).dropna()


# --- Zusammenfassung ----------------------------------------------------------------------------
def kennzahlen(werte: pd.Series, benchmark: pd.Series | None = None, rf_tag: pd.Series | None = None) -> dict:
    """Standardkennzahlen einer Wertreihe, optional gegen eine Benchmark-Wertreihe."""
    r = tagesrenditen(werte)
    rf_tag = rf_tag.reindex(r.index).fillna(0.0) if rf_tag is not None else pd.Series(0.0, index=r.index)
    rf_pa = annualisiert_geometrisch(rf_tag)
    vola = volatilitaet(r)
    var95, cvar95 = var_cvar_historisch(r)
    mdd = max_drawdown(werte)
    ergebnis = {
        "start": werte.index[0].date(),
        "ende": werte.index[-1].date(),
        "endwert": float(werte.iloc[-1]),
        "gesamtrendite": float(werte.iloc[-1] / werte.iloc[0] - 1),
        "cagr": cagr(werte),
        "volatilitaet": vola,
        "sharpe": sharpe_ratio(annualisiert_geometrisch(r), rf_pa, vola) if vola > 0 else float("nan"),
        "sortino": sortino_ratio(r, rf_tag),
        "max_drawdown": mdd["max_drawdown"],
        "max_drawdown_hoch": mdd["hoch"].date(),
        "max_drawdown_tief": mdd["tief"].date(),
        "max_drawdown_dauer_tage": mdd["dauer_tage"],
        "calmar": calmar_ratio(werte),
        "var95_tag": var95,
        "cvar95_tag": cvar95,
    }
    if benchmark is not None:
        b = benchmark.reindex(werte.index).ffill()
        r_m = tagesrenditen(b)
        regression = jensens_alpha(r, r_m, rf_tag)
        rueckstand = rollierender_rueckstand(werte, b)
        ergebnis.update(
            {
                "benchmark_cagr": cagr(b),
                "differenz_cagr": cagr(werte) - cagr(b),
                "beta": regression["beta"],
                "alpha_pa": regression["alpha_pa"],
                "t_alpha": regression["t_alpha"],
                "tracking_error": tracking_error(r, r_m),
                "information_ratio": information_ratio(r, r_m),
                "schlechtester_12m_rueckstand": float(rueckstand.min()) if len(rueckstand) else float("nan"),
                "tage_notbremse_core": int((rueckstand < -0.10).sum()),
            }
        )
    return ergebnis


def zeitgewichtete_rendite(werte: pd.Series, einzahlungen: pd.Series | None = None) -> pd.Series:
    """Zeitgewichtete Rendite (TWR) als Index (Start 1,0): Einzahlungen verzerren die Rendite nicht.

    Formel: r_t = (V_t − E_t) / V_{t−1} − 1,  TWR-Index_t = Π_{s ≤ t} (1 + r_s)
    V_t = Depotwert am Ende von Tag t, E_t = Einzahlung am Tagesbeginn von Tag t (externer Zufluss).
    Quelle: Performance-Messung mit Ein- und Auszahlungen bei täglicher Bewertung, vgl. wissen/02 (Rendite und Risiko);
    Gegenstück zur geldgewichteten Rendite (`xirr`).
    """
    e = (einzahlungen if einzahlungen is not None else pd.Series(0.0, index=werte.index)).reindex(werte.index).fillna(0.0)
    r = (werte - e) / werte.shift(1) - 1
    return (1 + r.fillna(0.0)).cumprod()


def xirr(zahlungen: pd.Series) -> float:
    """Interner Zinsfuß unregelmäßiger Zahlungen (geldgewichtete Rendite, p.a.).

    Formel: Σ_i C_i / (1 + r)^((t_i − t_0) / 365,25) = 0;  C_i aus Sicht des Anlegers (Einzahlung negativ, Endwert
    positiv). Lösung per Bisektion auf [−0,99; 10]. Quelle: interner Zins, wissen/01 (Kapitalwert und IRR; `npv` in
    tests/musterloesungen/referenz.py mit Jahresperioden); hier mit taggenauen Zeitpunkten.
    """
    z = zahlungen.sort_index()
    t = np.array([(d - z.index[0]).days / 365.25 for d in z.index])
    c = z.to_numpy(dtype=float)

    def kapitalwert(r):
        return float(np.sum(c / (1 + r) ** t))

    unten, oben = -0.99, 10.0
    if kapitalwert(unten) * kapitalwert(oben) > 0:
        return float("nan")
    for _ in range(200):
        mitte = (unten + oben) / 2
        if kapitalwert(unten) * kapitalwert(mitte) <= 0:
            oben = mitte
        else:
            unten = mitte
    return (unten + oben) / 2
