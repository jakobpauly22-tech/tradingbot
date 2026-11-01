"""Steuermodul: handgerechnete Beispiele (Abgeltungsteuer 25 %, Soli 5,5 % → 26,375 %)."""
import numpy as np
import pandas as pd
import pytest

from conftest import kerzen
from tradingbot.backtest.marktdaten import Instrument, Marktdaten
from tradingbot.backtest.simulation import Ausfuehrungsregeln, TeilportfolioDefinition, simuliere
from tradingbot.backtest.steuern import (
    Steuerereignis,
    Steuerregeln,
    berechne_jahressteuer,
    erster_werktag,
    vorabpauschale_je_anteil,
)
from tradingbot.backtest.strategie import BuyAndHold

R = Steuerregeln(basiszins={2023: 0.0255, 2024: 0.0229})
SATZ = 0.25 * 1.055


def _e(datum, art, steuerart, betrag, quellensteuer=0.0, tp="core"):
    return Steuerereignis(pd.Timestamp(datum), tp, "X", art, steuerart, betrag, quellensteuer)


def test_etf_gewinn_mit_teilfreistellung_und_pauschbetrag():
    tabelle = berechne_jahressteuer([_e("2023-05-02", "veraeusserung", "aktienfonds", 2000.0)], R)
    zeile = tabelle.loc[2023]
    assert zeile.allgemein_nach_teilfreistellung == pytest.approx(1400.0)    # 30 % steuerfrei
    assert zeile.pauschbetrag_genutzt == pytest.approx(1000.0)
    assert zeile.steuer == pytest.approx(400.0 * SATZ)                      # 105,50 €


def test_verlusttoepfe_und_vortrag():
    ereignisse = [
        _e("2023-03-01", "veraeusserung", "aktie", -500.0),        # Aktienverlust: nur mit Aktiengewinnen
        _e("2023-06-01", "veraeusserung", "aktienfonds", 1000.0),  # ETF-Gewinn → 700 € nach Teilfreistellung
        _e("2024-03-01", "veraeusserung", "aktie", 2000.0),        # Aktiengewinn − Vortrag 500 = 1.500
        _e("2024-06-01", "veraeusserung", "aktienfonds", -1000.0), # ETF-Verlust → −700, mindert auch Aktiengewinne
    ]
    t = berechne_jahressteuer(ereignisse, R, pauschbetrag=0.0)
    assert t.loc[2023, "steuerpflichtig"] == pytest.approx(700.0)          # Aktienverlust darf den ETF-Gewinn nicht mindern
    assert t.loc[2023, "vortrag_aktien"] == pytest.approx(500.0)
    assert t.loc[2024, "steuerpflichtig"] == pytest.approx(800.0)          # 2.000 − 500 − 700
    assert t.loc[2024, "vortrag_aktien"] == 0.0 and t.loc[2024, "vortrag_allgemein"] == 0.0
    assert t.loc[2024, "steuer"] == pytest.approx(800.0 * SATZ)


def test_allgemeiner_verlust_wird_vorgetragen():
    t = berechne_jahressteuer([_e("2023-06-01", "veraeusserung", "aktienfonds", -1000.0),
                               _e("2024-06-01", "veraeusserung", "aktienfonds", 2000.0)], R, pauschbetrag=0.0)
    assert t.loc[2023, "vortrag_allgemein"] == pytest.approx(700.0)
    assert t.loc[2024, "steuerpflichtig"] == pytest.approx(1400.0 - 700.0)


def test_quellensteuer_wird_angerechnet():
    t = berechne_jahressteuer([_e("2023-08-15", "dividende", "aktie", 1000.0, quellensteuer=150.0)], R, pauschbetrag=0.0)
    assert t.loc[2023, "quellensteuer_angerechnet"] == pytest.approx(150.0)
    assert t.loc[2023, "steuer"] == pytest.approx((250.0 - 150.0) * 1.055)


def test_vorabpauschale_formel():
    # Basisertrag = 100 · 2,55 % · 0,7 = 1,785
    assert vorabpauschale_je_anteil(100, 110, 0.0, 0.0255) == pytest.approx(1.785)
    assert vorabpauschale_je_anteil(100, 110, 0.0, 0.0255, erwerbsmonat=3) == pytest.approx(1.785 * 10 / 12)
    assert vorabpauschale_je_anteil(100, 101, 0.0, 0.0255) == pytest.approx(1.0)       # gedeckelt auf den Mehrbetrag
    assert vorabpauschale_je_anteil(100, 95, 0.0, 0.0255) == 0.0                       # Kursverlust
    assert vorabpauschale_je_anteil(100, 110, 1.0, 0.0255) == pytest.approx(0.785)     # minus Ausschüttung
    assert vorabpauschale_je_anteil(100, 110, 0.0, -0.0045) == 0.0                     # negativer Basiszins
    assert erster_werktag(2024) == pd.Timestamp("2024-01-02") and erster_werktag(2022) == pd.Timestamp("2022-01-03")


def _etf_zwei_jahre():
    tage = pd.bdate_range("2023-01-02", "2024-06-28")
    schluss = np.where(tage.year == 2023, np.linspace(100.0, 110.0, (tage.year == 2023).sum()).tolist() + [0] * (tage.year == 2024).sum(), 110.0)
    return Marktdaten({"ETF": kerzen(schluss[: len(tage)], start="2023-01-02")})


def test_vorabpauschale_in_der_simulation_und_abzug_beim_verkauf(konfig, ohne_kosten):
    class KaufenUndJuniVerkaufen:
        name = "Test"

        def zielgewichte(self, stichtag, sicht):
            if stichtag == pd.Timestamp("2023-01-02"):
                return pd.Series({"ETF": 1.0})
            if stichtag == pd.Timestamp("2024-06-03"):
                return pd.Series({"ETF": 0.0})
            return None

    m = _etf_zwei_jahre()
    e = simuliere([TeilportfolioDefinition("core", 1000.0, KaufenUndJuniVerkaufen(), [Instrument("ETF")])], m,
                  "2023-01-02", "2024-06-28", kosten=ohne_kosten,
                  regeln=Ausfuehrungsregeln(max_gebuehr_anteil=1.0, ganze_stuecke=False),
                  steuern=Steuerregeln(basiszins={2023: 0.0255, 2024: 0.0229}, sparer_pauschbetrag=0.0), konfig=konfig)["core"]
    stueck = e.trades.iloc[0].stueck
    vp = e.steuerereignisse[e.steuerereignisse.art == "vorabpauschale"].iloc[0]
    assert vp.datum == pd.Timestamp("2024-01-02")
    assert vp.betrag == pytest.approx(stueck * 100.0 * 0.0255 * 0.7)        # Jahresanfang = erster Kurs (Auflage)
    verkauf = e.steuerereignisse[e.steuerereignisse.art == "veraeusserung"].iloc[0]
    roher_gewinn = e.trades.iloc[1].gewinn_realisiert
    assert verkauf.betrag == pytest.approx(roher_gewinn - vp.betrag)       # keine Doppelbesteuerung
    # Steuer 2024: (Vorabpauschale + Veräußerung) · 70 % = roher Gewinn · 70 %
    assert e.steuern_gruppe.loc[2024, "steuer"] == pytest.approx(roher_gewinn * 0.7 * SATZ)
    assert e.steuern_gruppe.loc[2023, "steuer"] == 0.0
    assert e.werte.loc["2024-06-28", "wert_nach_steuern"] == pytest.approx(e.wert.iloc[-1] - roher_gewinn * 0.7 * SATZ)


def test_liquidation_am_ende_und_abfluss_ohne_zwangsverkauf(konfig, ohne_kosten, bruchteile):
    m = Marktdaten({"ETF": kerzen(np.linspace(100.0, 200.0, 120), start="2024-01-01")})
    e = simuliere([TeilportfolioDefinition("core", 1000.0, BuyAndHold({"ETF": 1.0}), [Instrument("ETF")])], m,
                  "2024-01-01", "2024-06-14", kosten=ohne_kosten, regeln=bruchteile, konfig=konfig)["core"]
    assert e.meta["steuern_gezahlt"] == 0.0                                 # nichts realisiert, keine Vorabpauschale im Jahr
    gewinn = e.meta["liquidationswert"] - 1000.0
    erwartet = max(gewinn * 0.7 - 1000.0, 0.0) * SATZ
    assert e.meta["liquidationssteuer"] == pytest.approx(erwartet)
    assert e.meta["wert_nach_liquidation_und_steuern"] == pytest.approx(e.meta["liquidationswert"] - erwartet)
    assert (e.werte["cash"] >= 0).all()


def test_us_dividende_mit_quellensteuer(konfig, ohne_kosten, bruchteile):
    dividende = [0.0] * 10
    dividende[5] = 2.0
    m = Marktdaten({"US": kerzen([100.0] * 10, dividende=dividende)}, waehrungen={"US": "USD"},
                   fx={"USD": pd.Series([1.0], index=pd.to_datetime(["2023-12-29"]))})
    e = simuliere([TeilportfolioDefinition("core", 1000.0, BuyAndHold({"US": 1.0}), [Instrument("US", "aktie")])], m,
                  "2024-01-01", "2024-01-12", kosten=ohne_kosten, regeln=bruchteile, konfig=konfig)["core"]
    d = e.dividenden.iloc[0]
    assert d.betrag == pytest.approx(20.0) and d.quellensteuer == pytest.approx(3.0)
    assert e.werte["cash"].iloc[-1] == pytest.approx(17.0)
    assert e.steuern_gruppe.loc[2024, "quellensteuer_gezahlt"] == pytest.approx(3.0)


def test_steuergruppe_teilt_den_pauschbetrag(konfig, ohne_kosten, bruchteile):
    class KaufenVerkaufen:
        name = "kv"

        def zielgewichte(self, stichtag, sicht):
            return pd.Series({"ETF": 1.0}) if stichtag == pd.Timestamp("2024-01-01") else (
                pd.Series({"ETF": 0.0}) if stichtag == pd.Timestamp("2024-05-31") else None)

    m = Marktdaten({"ETF": kerzen(np.linspace(100.0, 200.0, 120), start="2024-01-01")})

    def lauf(gruppe_b):
        return simuliere([TeilportfolioDefinition("a", 1000.0, KaufenVerkaufen(), [Instrument("ETF")]),
                          TeilportfolioDefinition("b", 1000.0, KaufenVerkaufen(), [Instrument("ETF")], steuergruppe=gruppe_b)],
                         m, "2024-01-01", "2024-06-14", kosten=ohne_kosten, regeln=bruchteile, konfig=konfig)

    gemeinsam = lauf("depot")
    gewinn = gemeinsam["a"].trades.iloc[1].gewinn_realisiert
    gruppe = (2 * gewinn * 0.7 - 1000.0) * SATZ
    assert gemeinsam["a"].steuern_gruppe.loc[2024, "steuer"] == pytest.approx(gruppe)
    assert gemeinsam["a"].meta["steuern_gezahlt"] + gemeinsam["b"].meta["steuern_gezahlt"] == pytest.approx(gruppe)

    getrennt = lauf("schatten")  # Schatten-Gruppe ohne Pauschbetrag (pauschbetrag_anteil 0)
    assert getrennt["a"].meta["steuern_gezahlt"] == pytest.approx(max(gewinn * 0.7 - 1000.0, 0.0) * SATZ)
    assert getrennt["b"].meta["steuern_gezahlt"] == pytest.approx(gewinn * 0.7 * SATZ)
