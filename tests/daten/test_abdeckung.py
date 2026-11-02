"""Auswertung der Kursabdeckung: nicht kaufbare Mitglieder je Stichtag und Rückfall-Fälle."""
import pandas as pd
import pytest

from tradingbot.daten.abdeckung import SCHWELLE_GEWICHT, nicht_kaufbar_je_stichtag, rebalancing_stichtage, rueckfall_faelle


def test_stichtage_erster_werktag_je_quartal_ohne_tresor():
    tage = rebalancing_stichtage()
    assert tage[0] == pd.Timestamp("2012-01-02") and tage[-1] == pd.Timestamp("2024-10-01")
    assert len(tage) == 52 and (tage < pd.Timestamp("2025-01-01")).all()


def test_anzahl_und_gewicht_ohne_gueltige_kurse():
    # Vier Mitglieder; B ohne gültige Kurse (Gewicht 10 %), F ist Finanzwert ohne Kurse (zählt nicht fürs Investierbare)
    mitglieder = pd.DataFrame({"ticker": ["A", "B", "C", "F"]}, index=[1, 2, 3, 4])
    gueltig = pd.Series({1: True, 2: False, 3: True, 4: False})
    streubesitz = {1: 600.0, 2: 100.0, 3: 300.0, 4: 1000.0}
    finanz = {1: False, 2: False, 3: False, 4: True}
    t = nicht_kaufbar_je_stichtag(lambda tag: mitglieder, gueltig, lambda n, tag: streubesitz[n],
                                  lambda n, tag: finanz[n], [pd.Timestamp("2015-01-02")]).iloc[0]
    assert t.ohne_gueltige_kurse == 2 and t.gewicht_ohne_kurse == pytest.approx(1100 / 2000)
    assert t.investierbar == 3 and t.investierbar_ohne_kurse == 1
    assert t.gewicht_investierbar_ohne_kurse == pytest.approx(0.10) and bool(t.ueber_schwelle)
    assert SCHWELLE_GEWICHT == 0.02


def test_fehlender_streubesitz_wird_gezaehlt_und_unbekannte_branche_ist_nicht_investierbar():
    mitglieder = pd.DataFrame({"ticker": ["A", "B"]}, index=[1, 2])
    t = nicht_kaufbar_je_stichtag(lambda tag: mitglieder, pd.Series({1: True}), lambda n, tag: 100.0 if n == 1 else None,
                                  lambda n, tag: None if n == 2 else False, [pd.Timestamp("2015-01-02")]).iloc[0]
    assert t.ohne_streubesitzwert == 1 and t.investierbar == 1 and t.investierbar_ohne_kurse == 0
    assert t.gewicht_investierbar_ohne_kurse == 0.0 and not bool(t.ueber_schwelle)


def test_rueckfall_faelle_je_jahr_und_grund():
    status = pd.DataFrame({"index": [1, 2, 3, 4], "gueltig": [True, True, True, False],
                           "letzter_kurs": ["2017-12-29", "2020-04-23", "2026-10-30", "2015-01-02"]})
    t = rueckfall_faelle(status, {1: "uebernahme", 2: "pleite"})
    assert t.loc[2017, "uebernahme"] == 1 and t.loc[2020, "pleite"] == 1
    assert t.values.sum() == 2                                   # weiterlaufende und ungültige Reihen zählen nicht


def test_zwei_gattungen_zaehlen_beim_gewicht_einmal():
    # GOOGL und GOOG (gleiche CIK) plus Firma X; Streubesitz gilt je Firma
    mitglieder = pd.DataFrame({"ticker": ["GOOGL", "GOOG", "X"]}, index=[1, 2, 3])
    firma = {1: 1652044, 2: 1652044, 3: 99}
    streubesitz = {1652044: 900.0, 99: 100.0}
    def lauf(gueltig):
        return nicht_kaufbar_je_stichtag(lambda tag: mitglieder, pd.Series(gueltig), lambda n, tag: streubesitz[firma[n]],
                                         lambda n, tag: False, [pd.Timestamp("2016-01-04")], firma_fn=firma.get).iloc[0]
    t = lauf({1: True, 2: False, 3: False})
    assert t.firmen == 2 and t.mitglieder == 3
    assert t.gattungen_ohne_gueltige_kurse == 2 and t.ohne_gueltige_kurse == 1          # Alphabet über GOOGL kaufbar
    assert t.gewicht_investierbar_ohne_kurse == pytest.approx(0.10)                     # 100 / (900 + 100), nicht / 1900
    t = lauf({1: False, 2: False, 3: True})
    assert t.ohne_gueltige_kurse == 1 and t.gewicht_investierbar_ohne_kurse == pytest.approx(0.90)


def test_streubesitz_unplausible_werte_werden_verworfen():
    from tradingbot.daten.abdeckung import streubesitz_am

    reihe = pd.DataFrame({"wert": [2.0e10, 3.1e19, 9.7e6, 2.4e10],
                          "filed": pd.to_datetime(["2018-02-01", "2019-02-01", "2020-02-01", "2021-02-01"])},
                         index=pd.to_datetime(["2017-06-30", "2018-06-30", "2019-06-30", "2020-06-30"]))
    assert streubesitz_am(reihe, "2018-03-01") == 2.0e10
    assert streubesitz_am(reihe, "2019-03-01") == 2.0e10          # 3·10¹⁹ verworfen, älterer plausibler Wert gilt
    assert streubesitz_am(reihe, "2020-03-01") == 2.0e10          # 9,7 Mio. (falsche Einheit) verworfen
    assert streubesitz_am(reihe, "2021-02-01") == 2.0e10          # am Einreichungstag noch nicht bekannt
    assert streubesitz_am(reihe, "2021-02-02") == 2.4e10
    assert streubesitz_am(reihe, "2017-01-01") is None and streubesitz_am(pd.DataFrame(), "2020-01-01") is None


def test_gewerteter_beginn_nach_der_2_prozent_regel():
    from tradingbot.daten.abdeckung import gewerteter_beginn

    def tab(werte):
        tage = ["2016-01-04", "2016-04-01", "2016-07-01", "2016-10-03", "2017-01-02", "2017-04-03"]
        return pd.DataFrame({"stichtag": pd.to_datetime(tage[: len(werte)]).date, "gewicht_investierbar_ohne_kurse": werte})

    # heutige Lage: 2016-04 und 2016-07 über 2 % → Beginn mit dem Stichtag 03.10.2016 = Quartalsbeginn 01.10.2016
    assert gewerteter_beginn(tab([0.036, 0.0268, 0.0228, 0.0183, 0.0168, 0.0127])) == pd.Timestamp("2016-10-01")
    # ein späterer Ausreißer über 2 % verschiebt den Beginn hinter ihn (alle FOLGENDEN müssen unter 2 % liegen)
    assert gewerteter_beginn(tab([0.01, 0.01, 0.01, 0.01, 0.025, 0.01])) == pd.Timestamp("2017-04-01")
    assert gewerteter_beginn(tab([0.01, 0.01, 0.01])) == pd.Timestamp("2016-01-01")
    assert gewerteter_beginn(tab([0.01, 0.01, 0.03])) is None                  # letzter Stichtag über 2 %: kein Beginn
    assert gewerteter_beginn(tab([0.02, 0.02])) == pd.Timestamp("2016-01-01")  # genau 2 % ist nicht „über“


def test_abnahmezeitraum_kommt_aus_der_konfiguration():
    from tradingbot.daten.index_nachbau import ABNAHME_ZEITRAUM
    from tradingbot.konfiguration import lade_konfiguration

    b = lade_konfiguration("fundamental")["backtest"]
    assert ABNAHME_ZEITRAUM == (str(b["gewertet_ab"]), str(b["gewertet_bis"])) == ("2016-10-01", "2024-12-31")
