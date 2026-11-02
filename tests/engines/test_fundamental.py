"""Fundamental-Engine: Rechenwege an echten 10-K, Plausibilitätsfälle, Grenzfälle, Point-in-Time-Regeln, Multiples.

Echte Werte (Mio. USD) aus den SEC-Erstmeldungen; Fundstellen (10-K, Accession) in docs/rechenwege/*.md zum Nachrechnen.
"""
import numpy as np
import pandas as pd
import pytest

from tradingbot.engines.fundamental.kennzahlen import abschluesse_am
from tradingbot.engines.fundamental.multiples import marktwert_am, multiples, perzentil_raenge, sic_division
from tradingbot.engines.fundamental.scores import accruals_quote, altman, beneish, piotroski

MIO = 1e6


def _abschluss(enden, werte: dict) -> pd.DataFrame:
    """Breitformat wie abschluesse_am: Zeile 0 = jüngstes Geschäftsjahr; Werte in Mio. USD."""
    return pd.DataFrame({k: [v * MIO if v is not None else np.nan for v in vs] for k, vs in werte.items()},
                        index=pd.to_datetime(enden))


# Apple GJ 2019/2018/2017, 10-K 0000320193-19-000119 (docs/rechenwege/apple_gj2019.md)
APPLE = _abschluss(["2019-09-28", "2018-09-29", "2017-09-30"], {
    "jahresueberschuss": [55256, 59531, 48351], "operativer_cashflow": [69391, 77434, 63598],
    "bilanzsumme": [338516, 365725, 375319], "langfristige_finanzschulden": [91807, 93735, 97207],
    "umlaufvermoegen": [162819, 131339, 128645], "kurzfristige_verbindlichkeiten": [105718, 116866, 100814],
    "gewichtete_aktien": [4618, 4955, 5217], "bruttoergebnis": [98392, 101839, 88186], "umsatz": [260174, 265595, 229234],
    "forderungen": [22926, 23186, 17874], "sachanlagen_netto": [37378, 41304, 33783], "abschreibungen": [12547, 10903, 8200],
    "vertriebs_verwaltungskosten": [18245, 16705, 15261], "gewinnruecklagen": [45898, 70400, 98330],
    "operatives_ergebnis": [63930, 70898, 61344], "verbindlichkeiten": [248028, 258578, 241272],
    "eigenkapital_inkl_minderheiten": [90488, 107147, 134047], "zahlungsmittel": [48844, 25913, 20289],
    "kurzfristige_finanzschulden": [16240, 20748, 18473],
})
APPLE_MARKTWERT = 1_136_676 * MIO      # 255,82 USD × 4.443.265.000 Aktien am 01.11.2019

# Walmart GJ 2020 (Ende 31.01.2020), SIC 5331 → Z'' (docs/rechenwege/walmart_gj2020.md)
WALMART = _abschluss(["2020-01-31", "2019-01-31", "2018-01-31"], {
    "umlaufvermoegen": [61806, 61897, 59664], "kurzfristige_verbindlichkeiten": [77790, 77477, 78521],
    "gewinnruecklagen": [83943, 80785, 85107], "operatives_ergebnis": [20568, 21957, 20437],
    "bilanzsumme": [236495, 219295, 204522], "verbindlichkeiten": [154943, 139661, 123700],
    "eigenkapital_inkl_minderheiten": [81552, 79634, 80822],
})

# Sears Holdings GJ 2017 (Ende 03.02.2018), 10-K vom März 2018; Insolvenzantrag Oktober 2018 (SIC 5311 → Z'')
SEARS = _abschluss(["2018-02-03", "2017-01-28", "2016-01-30"], {
    "jahresueberschuss": [-383, -2221, -1129], "operativer_cashflow": [-1842, -1381, -2167],
    "bilanzsumme": [7262, 9362, 11337], "langfristige_finanzschulden": [3217, 4163, 2179],
    "umlaufvermoegen": [3812, 4996, 6045], "kurzfristige_verbindlichkeiten": [4915, 4681, 5438],
    "gewichtete_aktien": [107, 107, 107], "bruttoergebnis": [3527, 4686, 5810], "umsatz": [16702, 22138, 25146],
    "gewinnruecklagen": [-5895, -5512, -3291], "operatives_ergebnis": [-430, -1978, -1000],
    "verbindlichkeiten": [10985, 13186, 13293], "eigenkapital_inkl_minderheiten": [-3723, -3824, -1956],
})

# Johnson & Johnson GJ 2019 (SIC 2834 → Z 1968), Marktwert am 02.03.2020
JNJ = _abschluss(["2019-12-29"], {
    "umlaufvermoegen": [45274], "kurzfristige_verbindlichkeiten": [35964], "gewinnruecklagen": [110659],
    "operatives_ergebnis": [17646], "bilanzsumme": [157728], "verbindlichkeiten": [98257], "umsatz": [82059],
})
JNJ_MARKTWERT = 368_913.68 * MIO


# --- Rechenwege an echten 10-K -----------------------------------------------------------------
def test_piotroski_apple_gj2019():
    p = piotroski(APPLE)
    assert p["wert"] == 6
    assert p["signale"] == {"roa": 1, "cfo": 1, "delta_roa": 0, "accrual": 1, "delta_lever": 0, "delta_liquid": 1,
                            "eq_offer": 1, "delta_margin": 0, "delta_turn": 1}
    assert p["zwischenwerte"]["roa"] == pytest.approx(55256 / 365725)
    assert p["zwischenwerte"]["roa_vj"] == pytest.approx(59531 / 375319)


def test_beneish_apple_gj2019():
    b = beneish(APPLE)
    assert b["wert"] == pytest.approx(-2.8125, abs=1e-4)
    assert b["variablen"]["dsri"] == pytest.approx((22926 / 260174) / (23186 / 265595))
    assert b["variablen"]["tata"] == pytest.approx((55256 - 69391) / 338516)


def test_altman_z_apple_gj2019_mit_marktwert():
    a = altman(APPLE, industrie=True, marktwert_ek=APPLE_MARKTWERT)
    assert a["variante"] == "Z" and a["zone"] == "sicher"
    assert a["wert"] == pytest.approx(4.5337, abs=1e-3)
    assert a["x"][3] == pytest.approx(APPLE_MARKTWERT / (248028 * MIO))


def test_altman_z2_walmart_gj2020():
    a = altman(WALMART, industrie=False)
    assert a["variante"] == "Z''" and a["zone"] == "grau"
    assert a["wert"] == pytest.approx(1.8508, abs=1e-3)
    assert a["x"][3] == pytest.approx(81552 / 154943)                       # Buchwert EK / Verbindlichkeiten


# --- Plausibilitätsfälle -----------------------------------------------------------------------
def test_sears_vor_insolvenz_in_der_gefahrenzone():
    a = altman(SEARS, industrie=False)
    assert a["zone"] == "gefahr" and a["wert"] < 0                            # −4,40 bei negativem Eigenkapital
    assert piotroski(SEARS)["wert"] <= 3                                       # Filter F ≤ 3 → raus
    assert accruals_quote(SEARS)["wert"] == pytest.approx((-383 + 1842) / 7262)


def test_stabile_grosskonzerne_sicher():
    assert altman(JNJ, industrie=True, marktwert_ek=JNJ_MARKTWERT)["zone"] == "sicher"
    assert altman(APPLE, industrie=True, marktwert_ek=APPLE_MARKTWERT)["zone"] == "sicher"


# --- Grenzfälle --------------------------------------------------------------------------------
def test_fehlende_posten_ergeben_keinen_score_sondern_eine_liste():
    ohne = APPLE.drop(columns=["bruttoergebnis"])
    assert "delta_margin:bruttoergebnis@t" in piotroski(ohne)["fehlend"]
    assert beneish(ohne)["wert"] is None
    assert altman(APPLE, industrie=True)["fehlend"] == ["marktwert_ek"]      # Z braucht den Marktwert
    nur_zwei = APPLE.iloc[:2]
    p = piotroski(nur_zwei)                                                   # ohne t−2: ΔROA, ΔLEVER, ΔTURN fehlen
    assert p["anzahl_signale"] == 6 and p["wert"] is None and p["wert_hochgerechnet"] is None   # < 7 → Filter überspringen


def test_piotroski_hochrechnen_bei_sieben_oder_acht_signalen():
    ohne_marge = piotroski(APPLE.drop(columns=["bruttoergebnis"]))           # wie viele Dienstleister: kein Bruttoergebnis
    assert ohne_marge["anzahl_signale"] == 8 and ohne_marge["wert"] is None and ohne_marge["hochgerechnet"]
    assert ohne_marge["wert_hochgerechnet"] == pytest.approx(6 * 9 / 8)       # Apple ohne ΔMARGIN: 6 von 8 → 6,75
    sieben = piotroski(APPLE.drop(columns=["bruttoergebnis", "gewichtete_aktien"]))
    assert sieben["anzahl_signale"] == 7 and sieben["wert_hochgerechnet"] == pytest.approx(5 * 9 / 7)
    voll = piotroski(APPLE)
    assert voll["wert"] == 6 and voll["wert_hochgerechnet"] == 6 and not voll["hochgerechnet"]


def test_division_durch_null_und_negatives_eigenkapital():
    null = APPLE.copy()
    null.loc[null.index[0], "bilanzsumme"] = 0.0
    assert altman(null, industrie=False)["wert"] is None
    assert accruals_quote(null)["wert"] is None
    null_umsatz = APPLE.copy()
    null_umsatz.loc[null_umsatz.index[1], "umsatz"] = 0.0
    assert beneish(null_umsatz)["wert"] is None
    assert altman(SEARS, industrie=False)["x"][3] < 0                         # negatives EK ist erlaubt


# --- Kennzahlen point-in-time ----------------------------------------------------------------
def _werte(zeilen):
    return pd.DataFrame(zeilen, columns=["kennzahl", "ende", "wert", "bekannt_ab", "konzept", "rang"]).assign(
        ende=lambda d: pd.to_datetime(d.ende), bekannt_ab=lambda d: pd.to_datetime(d.bekannt_ab))


def test_zuerst_gemeldeter_begriff_gilt_und_nur_bekanntes():
    # wie Walmart: Ergebnis vor Steuern GJ 2020 im 10-K 03/2020 unter Begriff 2, unter Begriff 1 erst im 10-K 03/2022
    w = _werte([("umsatz", "2020-01-31", 524e9, "2020-03-21", "Revenues", 0),
                ("ergebnis_vor_steuern", "2020-01-31", 20.116e9, "2022-03-19", "Begriff1", 0),
                ("ergebnis_vor_steuern", "2020-01-31", 20.116e9, "2020-03-21", "Begriff2", 1),
                ("umsatz", "2021-01-31", 559e9, "2021-03-20", "Revenues", 0)])
    t, info = abschluesse_am(w, "2020-03-25")
    assert t.index[0] == pd.Timestamp("2020-01-31") and t["ergebnis_vor_steuern"].iloc[0] == 20.116e9
    assert abschluesse_am(w, "2020-03-20")[1]["grund"] == "kein Geschäftsjahr bekannt"   # vor dem 10-K nichts
    assert abschluesse_am(w, "2021-03-21")[0].index[0] == pd.Timestamp("2021-01-31")


def test_aktualitaet_und_ableitungen_markiert():
    w = _werte([("umsatz", "2018-12-31", 100.0, "2019-02-20", "R", 0), ("umsatzkosten", "2018-12-31", 60.0, "2019-02-20", "C", 0),
                ("bilanzsumme", "2018-12-31", 500.0, "2019-02-20", "A", 0), ("eigenkapital_inkl_minderheiten", "2018-12-31", 200.0, "2019-02-20", "E", 0)])
    t, info = abschluesse_am(w, "2019-06-28")
    assert t["bruttoergebnis"].iloc[0] == 40.0 and t["verbindlichkeiten"].iloc[0] == 300.0
    assert t["langfristige_finanzschulden"].iloc[0] == 0.0                    # fehlt → 0 (schuldenfrei), markiert
    assert {"bruttoergebnis@2018-12-31", "verbindlichkeiten@2018-12-31", "langfristige_finanzschulden@2018-12-31"} <= set(info["abgeleitet"])
    assert not info["veraltet"] and abschluesse_am(w, "2020-05-01")[1]["veraltet"]   # > 15 Monate


# --- Multiples ----------------------------------------------------------------------------------
def test_marktwert_plausibel_gegen_streubesitz():
    tage = pd.bdate_range("2019-06-24", "2019-11-01")
    schluss = pd.Series(50.0, index=tage)
    aktien = pd.Series([1.0e9], index=[pd.Timestamp("2019-08-01")])
    sb = pd.DataFrame({"wert": [4.5e10], "filed": [pd.Timestamp("2019-10-30")]}, index=[pd.Timestamp("2019-06-28")])
    assert marktwert_am("2019-11-01", schluss, aktien, sb) == (50e9, None)              # Streubesitz 90 %
    falsch = pd.Series([1.0e6], index=[pd.Timestamp("2019-08-01")])                      # Aktienzahl in Tausend
    mw, grund = marktwert_am("2019-11-01", schluss, falsch, sb)
    assert mw is None and "Aktienzahl unplausibel" in grund


def test_ep_ebit_ev_und_negativer_ev():
    m = multiples(APPLE, APPLE_MARKTWERT)
    ev = APPLE_MARKTWERT + (91807 + 16240 - 48844) * MIO
    assert m["ev"] == pytest.approx(ev) and m["ebit_ev"] == pytest.approx(63930 * MIO / ev)
    assert m["ep"] == pytest.approx(55256 * MIO / APPLE_MARKTWERT)
    reich = APPLE.copy()
    reich.loc[reich.index[0], "zahlungsmittel"] = 2e12                       # mehr Cash als Marktwert + Schulden
    r = multiples(reich, APPLE_MARKTWERT)
    assert r["ev_negativ"] and r["ebit_ev"] is None and r["ep"] is not None


def test_perzentil_rang_je_gruppe_mit_rueckfall_auf_division_und_kappung():
    sic = [2834] * 6 + [3571, 3672] + [5331]
    ep = [0.01, 0.02, 0.03, 0.04, 0.05, 9.0, 0.06, 0.02, 0.05]               # 9,0 ist ein Ausreißer
    t = perzentil_raenge(pd.DataFrame({"sic": sic, "ep": ep, "ebit_ev": ep}), spalten=("ep",))
    assert (t["gruppe_ep"].iloc[:6] == "SIC 28").all()                       # 6 Firmen ≥ 5 → eigene Gruppe
    assert t["gruppe_ep"].iloc[6] == "Division D" and t["gruppe_ep"].iloc[8] == "Division G"
    assert t["rang_ep"].iloc[5] == 1.0 and t["rang_ep"].iloc[0] == pytest.approx(1 / 6)
    assert sic_division(2834) == "D" and sic_division(5331) == "G" and sic_division(None) is None
