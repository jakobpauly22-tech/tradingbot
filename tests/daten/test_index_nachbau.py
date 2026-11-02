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


# --- Korrekturen nach dem ersten Gegenprobe-Lauf (Jakob 02.11.2026) -------------------------------------------------
def test_fehler_feiertag_26_12_2018_und_korrektur():
    from tradingbot.daten.index_nachbau import handelstage

    # Kurse an echten US-Handelstagen: 24.12.2018 halber Tag, 25.12. geschlossen, 26.12. +5 %
    tage_mit_kurs = pd.to_datetime(["2018-12-21", "2018-12-24", "2018-12-26", "2018-12-27"])
    schluss = pd.DataFrame({"A": [100.0, 97.0, 101.85, 102.0], "B": [50.0, 49.0, 51.45, 51.0]}, index=tage_mit_kurs)
    renditen = schluss.pct_change()
    marktwerte = schluss * 10

    # Fehler des ersten Laufs: Kalender = alle Werktage → am 25.12. kein Marktwert → 26.12. ohne Gewichte → Rendite 0
    werktage = pd.bdate_range("2018-12-21", "2018-12-27")
    alt = marktwert_index(renditen.reindex(werktage), marktwerte.reindex(werktage), pd.DataFrame(True, index=werktage, columns=["A", "B"]))
    assert alt["index"].pct_change().loc["2018-12-26"] == 0.0

    # Korrektur: nur echte Handelstage
    tage = handelstage(schluss, "2018-12-21", "2018-12-27")
    assert pd.Timestamp("2018-12-25") not in tage
    neu = marktwert_index(renditen.reindex(tage), marktwerte.reindex(tage), pd.DataFrame(True, index=tage, columns=["A", "B"]))
    assert neu["index"].pct_change().loc["2018-12-26"] == pytest.approx(0.05)


def test_fehler_messtag_vor_beginn_des_nachbaus_und_korrektur():
    from tradingbot.daten.index_nachbau import marktwerte_aus_streubesitz

    # Apple: Streubesitz gemessen am 27.03.2015, eingereicht 28.10.2015; Nachbau beginnt am 04.01.2016
    reihe = pd.DataFrame({"wert": [709.923e9], "filed": pd.to_datetime(["2015-10-28"])}, index=pd.to_datetime(["2015-03-27"]))
    voll = pd.Series(100.0, index=pd.bdate_range("2015-01-02", "2016-01-29"))
    voll.loc["2016-01-04":] = 110.0
    # Fehler des ersten Laufs: Kurse erst ab Beginn des Nachbaus → kein Kurs am Messtag → kein Marktwert
    nur_ab_2016 = voll.loc["2016-01-04":].to_frame("AAPL")
    assert marktwerte_aus_streubesitz(nur_ab_2016, {"AAPL": reihe})["AAPL"].isna().all()
    # Korrektur: Kurse ab dem ersten Messtag laden
    mw = marktwerte_aus_streubesitz(voll.to_frame("AAPL"), {"AAPL": reihe})["AAPL"]
    assert mw.loc["2016-01-04"] == pytest.approx(709.923e9 * 110 / 100)


def _reihe(werte):
    return pd.DataFrame({"wert": [w for _, w, _ in werte], "filed": pd.to_datetime([f for _, _, f in werte])},
                        index=pd.to_datetime([e for e, _, _ in werte]))


def test_streubesitz_garmin_echte_werte():
    """Echte SEC-Werte (Cache, 02.11.2026): 2015, 2017, 2018 das 1.000-Fache; 2015 und 2017 auch die Aktienzahl falsch."""
    from tradingbot.daten.index_nachbau import streubesitz_pruefen

    reihe = _reihe([("2014-06-28", 7.5512e9, "2015-02-18"), ("2015-06-27", 5.63443e12, "2016-02-17"),
                    ("2016-06-25", 4.93974e9, "2017-02-22"), ("2017-07-01", 6.12944e12, "2018-02-21"),
                    ("2018-06-30", 7.7535e12, "2019-02-20"), ("2019-06-29", 1.1181e10, "2020-02-19"),
                    ("2020-06-27", 1.4141e10, "2021-02-17")])
    schluss = pd.Series([60.59, 45.57, 40.77, 51.03, 61.00, 79.80, 94.86], index=reihe.index)
    aktien = pd.Series([1.92616e8, 190936, 1.88877e8, 187703, 1.88797e8, 1.90102e8, 1.91223e8], index=reihe.index)
    gueltig, verworfen = streubesitz_pruefen(reihe, schluss, aktien)
    assert [d.year for d in verworfen.index] == [2015, 2017, 2018]
    assert "Vorjahr" in verworfen.loc["2015-06-27", "grund"]          # Aktienzahl ebenfalls falsch → Vorjahresvergleich
    assert "Börsenwerts" in verworfen.loc["2018-06-30", "grund"]       # Aktienzahl richtig → Abgleich mit dem Börsenwert
    assert [d.year for d in gueltig.index] == [2014, 2016, 2019, 2020]


def test_streubesitz_nvidia_echter_wachstumsfall_bleibt_gueltig():
    """Echte SEC- und Kurswerte (Cache, 02.11.2026); Kurse splitbereinigt, Aktienzahl daher mal 40 (Splits 2021, 2024)."""
    from tradingbot.daten.index_nachbau import streubesitz_pruefen

    reihe = _reihe([("2015-07-24", 9.91835e9, "2016-03-17"), ("2016-07-29", 2.8978e10, "2017-03-01"),
                    ("2017-07-28", 9.43112e10, "2018-02-28"), ("2018-07-27", 1.4666e11, "2019-02-21"),
                    ("2019-07-26", 1.0215e11, "2020-02-20"), ("2020-07-24", 2.4121e11, "2021-02-26")])
    schluss = pd.Series([0.4855, 1.4275, 4.1097, 6.3005, 4.3767, 10.1945], index=reihe.index)
    aktien = pd.Series([5.39081e8, 5.35002e8, 6.00171e8, 6.08e8, 6.09e8, 6.17e8],
                       index=pd.to_datetime(["2015-08-14", "2016-08-19", "2017-08-18", "2018-08-10", "2019-08-09", "2020-08-14"])) * 40
    gueltig, verworfen = streubesitz_pruefen(reihe, schluss, aktien)
    assert verworfen.empty and len(gueltig) == 6                       # trotz Wachstum um mehr als das 24-Fache


def test_streubesitz_ohne_brauchbare_aktienzahl_nutzt_vorjahresvergleich():
    from tradingbot.daten.index_nachbau import streubesitz_pruefen

    # Künstliche Zahlen, angelehnt an Berkshire: gemeldet nur A-Aktien (ca. 1,6 Mio.) → Kurs × Zahl unplausibel → Vorjahresvergleich
    reihe = _reihe([("2018-06-29", 4.0e11, "2019-02-25"), ("2019-06-28", 4.3e11, "2020-02-24"), ("2020-06-30", 4.1e13, "2021-03-01")])
    schluss = pd.Series([186.0, 213.0, 178.0], index=reihe.index)
    aktien = pd.Series([1.64e6, 1.63e6, 1.62e6], index=reihe.index)
    gueltig, verworfen = streubesitz_pruefen(reihe, schluss, aktien)
    assert list(gueltig.index.year) == [2018, 2019]
    assert "außerhalb" in verworfen.loc["2020-06-30", "grund"]


def test_streubesitz_pruefen_mit_doppelter_aktienzahl_von_vorgaenger_cik():
    from tradingbot.daten.index_nachbau import streubesitz_pruefen

    reihe = _reihe([("2019-06-28", 5.0e10, "2020-02-20")])
    aktien = pd.Series([1.0e9, 1.0e9], index=pd.to_datetime(["2019-06-28", "2019-06-28"]))   # Firma und Vorgänger
    gueltig, verworfen = streubesitz_pruefen(reihe, pd.Series([60.0], index=reihe.index), aktien)
    assert len(gueltig) == 1 and verworfen.empty                                             # 50 / 60 = 83 %


def test_streubesitz_obergrenze_130_prozent():
    from tradingbot.daten.index_nachbau import STREUBESITZ_ANTEIL_MAX, streubesitz_pruefen

    assert STREUBESITZ_ANTEIL_MAX == 1.30
    reihe = _reihe([("2019-06-28", 7.2e10, "2020-02-20"), ("2020-06-30", 8.0e10, "2021-02-20")])
    schluss = pd.Series([60.0, 60.0], index=reihe.index)
    aktien = pd.Series([1.0e9, 1.0e9], index=reihe.index)                      # Börsenwert jeweils 60 Mrd.
    gueltig, verworfen = streubesitz_pruefen(reihe, schluss, aktien)
    assert list(gueltig.index.year) == [2019]                                   # 120 % gilt jetzt
    assert "133%" in verworfen.loc["2020-06-30", "grund"]                       # 133 % weiterhin verworfen
