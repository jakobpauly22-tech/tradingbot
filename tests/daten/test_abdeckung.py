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
