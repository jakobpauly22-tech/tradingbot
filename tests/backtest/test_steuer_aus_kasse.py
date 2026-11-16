"""Steuer aus der Kasse (Korrektur 16.11.2026, docs/berichte/2026-11-16_steuer_aus_kasse.md): handgerechnete Fälle.

Aktie ohne Kosten, Bruchteile, Pauschbetrag 0: Steuer = realisierter Gewinn · 26,375 %. Kurs 100 bis Ende Mai 2023,
danach 150; Kauf zu 100, Verkauf zu 150 → Gewinn 500 € auf 1.000 €, Steuer 131,875 €.
"""
import numpy as np
import pandas as pd
import pytest

from conftest import kerzen
from tradingbot.backtest.marktdaten import Instrument, Marktdaten
from tradingbot.backtest.simulation import TeilportfolioDefinition, simuliere
from tradingbot.backtest.steuern import Steuerregeln
from tradingbot.kennzahlen.performance import zeitgewichtete_rendite

SATZ = 0.25 * 1.055
STEUER = 500.0 * SATZ
TAGE = pd.bdate_range("2023-01-02", "2024-06-28")
ZAHLTAG_2023 = TAGE[TAGE.year == 2023][-1]


def _kurse(ticker=("A",)):
    schluss = np.where(TAGE < pd.Timestamp("2023-06-01"), 100.0, 150.0)
    return Marktdaten({t: kerzen(schluss, start="2023-01-02") for t in ticker})


class Plan:
    """Zielgewichte je Stichtag (Ausführung zur Eröffnung des nächsten Handelstags)."""
    name = "plan"

    def __init__(self, plan: dict):
        self.plan = {pd.Timestamp(t): g for t, g in plan.items()}

    def zielgewichte(self, stichtag, sicht):
        g = self.plan.get(stichtag)
        return None if g is None else pd.Series(g, dtype=float)


def _lauf(plan, konfig, ohne_kosten, bruchteile, *, zahlung="jahresende_aus_kasse", ticker=("A",), einzahlungen=None, ende=TAGE[-1]):
    d = TeilportfolioDefinition("core", 1000.0, Plan(plan), [Instrument(t, "aktie") for t in ticker], einzahlungen=einzahlungen)
    return simuliere([d], _kurse(ticker), TAGE[0], ende, kosten=ohne_kosten, regeln=bruchteile,
                     steuern=Steuerregeln(sparer_pauschbetrag=0.0, zahlung=zahlung), konfig={**konfig, "steuern": {**konfig["steuern"], "pauschbetrag_anteil": {}}})["core"]


def test_steuer_fliesst_am_jahresende_aus_der_kasse(konfig, ohne_kosten, bruchteile):
    """Kauf zu 100, Verkauf zu 150, danach Kasse: Am letzten Handelstag 2023 sinkt die Kasse um die Steuer."""
    e = _lauf({"2023-01-02": {"A": 1.0}, "2023-06-05": {"A": 0.0}}, konfig, ohne_kosten, bruchteile)
    w = e.werte
    vortag = TAGE[TAGE < ZAHLTAG_2023][-1]
    assert w.loc[vortag, "cash"] == pytest.approx(1500.0)
    assert w.loc[ZAHLTAG_2023, "cash"] == pytest.approx(1500.0 - STEUER)
    assert w.loc[ZAHLTAG_2023, "steuer"] == pytest.approx(STEUER) and w["steuer"].sum() == pytest.approx(STEUER)
    assert (w["steuerschuld"] == 0).all()
    assert w["wert_nach_steuern"].iloc[-1] == pytest.approx(1500.0 - STEUER)
    assert e.wert.iloc[-1] == pytest.approx(1500.0)                       # vor Steuern = nach Steuern + festgesetzte Steuern
    assert e.meta["steuern_gezahlt"] == pytest.approx(STEUER) and e.meta["steuerschuld_ende"] == 0.0
    assert e.meta["wert_nach_liquidation_und_steuern"] == pytest.approx(1500.0 - STEUER)
    assert list(e.meta["steuerzahlungen"]["datum"]) == [ZAHLTAG_2023]


WIEDER_VOLL = {"2023-01-02": {"A": 1.0}, "2023-06-05": {"A": 0.0}, "2023-07-03": {"A": 1.0},
               "2024-03-01": {"A": 0.0}, "2024-04-01": {"A": 1.0}}


def test_kasse_reicht_nicht_steuerschuld_ohne_zwangsverkauf_spaeterer_kauf_kleiner(konfig, ohne_kosten, bruchteile):
    """Gewinn realisiert und voll reinvestiert: Am Jahresende ist die Kasse leer. Die Steuer wird Schuld, nichts wird
    verkauft; der nächste Verkaufserlös tilgt sie, und der Rückkauf ist um die Steuer kleiner."""
    e = _lauf(WIEDER_VOLL, konfig, ohne_kosten, bruchteile)
    w = e.werte
    assert w.loc[ZAHLTAG_2023, "steuerschuld"] == pytest.approx(STEUER) and w.loc[ZAHLTAG_2023, "cash"] == pytest.approx(0.0)
    um_jahresende = e.trades[(e.trades.datum > "2023-07-04") & (e.trades.datum < "2024-03-04")]
    assert um_jahresende.empty                                             # kein Zwangsverkauf
    assert e.bestaende.loc[ZAHLTAG_2023, "A"] == pytest.approx(10.0)        # 1.500 € zu 150
    assert w.loc[ZAHLTAG_2023, "wert_nach_steuern"] == pytest.approx(1500.0 - STEUER)
    verkauf, rueckkauf = pd.Timestamp("2024-03-04"), pd.Timestamp("2024-04-02")
    assert w.loc[verkauf, "steuerschuld"] == 0.0 and w.loc[verkauf, "cash"] == pytest.approx(1500.0 - STEUER)
    assert list(e.meta["steuerzahlungen"]["datum"]) == [verkauf]
    kauf = e.trades[e.trades.datum == rueckkauf].iloc[0]
    assert kauf.kurswert == pytest.approx(1500.0 - STEUER)                 # späterer Kauf kleiner
    assert (w["cash"] > -1e-9).all()


def test_vergleichsmodus_rechnet_wie_bis_15_11(konfig, ohne_kosten, bruchteile):
    """`jahresende_nur_wertreihe`: Kasse unberührt, Rückkauf mit dem vollen Erlös. Bis zum ersten Zufluss nach dem
    Jahresende sind beide Modi gleich."""
    alt = _lauf(WIEDER_VOLL, konfig, ohne_kosten, bruchteile, zahlung="jahresende_nur_wertreihe")
    neu = _lauf(WIEDER_VOLL, konfig, ohne_kosten, bruchteile)
    assert alt.trades[alt.trades.datum == "2024-04-02"].iloc[0].kurswert == pytest.approx(1500.0)
    assert alt.werte["steuerschuld"].iloc[-1] == pytest.approx(STEUER) and alt.meta["steuerzahlungen"].empty
    assert alt.werte["wert_nach_steuern"].iloc[-1] == pytest.approx(1500.0 - STEUER)
    assert alt.meta["wert_nach_liquidation_und_steuern"] == pytest.approx(1500.0 - STEUER)
    bis = pd.Timestamp("2024-03-01")
    pd.testing.assert_series_equal(alt.wert_nach_steuern.loc[:bis], neu.wert_nach_steuern.loc[:bis])
    assert alt.meta["steuerzahlung"] == "jahresende_nur_wertreihe" and neu.meta["steuerzahlung"] == "jahresende_aus_kasse"
    with pytest.raises(ValueError):
        Steuerregeln(zahlung="jahresende_abfluss")


def test_einzahlung_tilgt_die_steuerschuld_zuerst(konfig, ohne_kosten, bruchteile):
    einz = pd.Series({pd.Timestamp("2024-01-10"): 50.0, pd.Timestamp("2024-02-12"): 100.0})
    plan = {"2023-01-02": {"A": 1.0}, "2023-06-05": {"A": 0.0}, "2023-07-03": {"A": 1.0}}
    e = _lauf(plan, konfig, ohne_kosten, bruchteile, einzahlungen=einz)
    w = e.werte
    assert w.loc["2024-01-10", "steuerschuld"] == pytest.approx(STEUER - 50.0) and w.loc["2024-01-10", "cash"] == pytest.approx(0.0)
    assert w.loc["2024-02-12", "steuerschuld"] == 0.0
    assert w.loc["2024-02-12", "cash"] == pytest.approx(150.0 - STEUER)     # nur der Rest der Einzahlungen bleibt Kasse
    assert len(e.trades) == 3                                              # kein Verkauf für die Steuer


def test_kaeufe_bei_offener_schuld_anteilig_kleiner(konfig, ohne_kosten, bruchteile):
    """Umschichtung von A in B und C je 50 % bei offener Schuld: Verkauf gegen den vollen Wert, beide Käufe gegen
    Wert minus Schuld, also gleich groß (nicht: B voll, C um die ganze Schuld gekürzt)."""
    plan = {"2023-01-02": {"A": 1.0}, "2023-06-05": {"A": 0.0}, "2023-07-03": {"A": 1.0},
            "2024-03-01": {"A": 0.0, "B": 0.5, "C": 0.5}}
    e = _lauf(plan, konfig, ohne_kosten, bruchteile, ticker=("A", "B", "C"))
    tag = pd.Timestamp("2024-03-04")
    t = e.trades[e.trades.datum == tag].set_index("ticker")
    assert t.loc["A", "stueck"] == pytest.approx(10.0) and t.loc["A", "richtung"] == -1
    assert t.loc["B", "kurswert"] == pytest.approx((1500.0 - STEUER) / 2)
    assert t.loc["C", "kurswert"] == pytest.approx((1500.0 - STEUER) / 2)
    assert e.werte.loc[tag, "steuerschuld"] == 0.0 and e.werte.loc[tag, "cash"] == pytest.approx(0.0)


def test_steuergruppe_zahlt_aus_beiden_kassen(konfig, ohne_kosten, bruchteile):
    """Zwei Teilportfolios einer Gruppe mit gleichem Gewinn teilen die Steuer hälftig; jede Kasse zahlt ihren Anteil."""
    plan = {"2023-01-02": {"A": 1.0}, "2023-06-05": {"A": 0.0}}
    d = [TeilportfolioDefinition(n, 1000.0, Plan(plan), [Instrument("A", "aktie")]) for n in ("a", "b")]
    erg = simuliere(d, _kurse(), TAGE[0], TAGE[-1], kosten=ohne_kosten, regeln=bruchteile, steuern=Steuerregeln(), konfig=konfig)
    gruppe = (2 * 500.0 - 1000.0) * SATZ                                  # ein Pauschbetrag für die Gruppe „depot“
    assert erg["a"].steuern_gruppe.loc[2023, "steuer"] == pytest.approx(gruppe)
    for n in ("a", "b"):
        assert erg[n].werte.loc[ZAHLTAG_2023, "cash"] == pytest.approx(1500.0 - gruppe / 2)


def test_fremdwaehrungskasse_wird_fuer_die_steuer_getauscht(konfig, mit_kosten, bruchteile):
    """US-Aktie: Der Verkaufserlös bleibt in USD. Am Zahltag wird für die Steuer zurückgetauscht, mit Tauschkosten."""
    schluss = np.where(TAGE < pd.Timestamp("2023-06-01"), 100.0, 150.0)
    m = Marktdaten({"US": kerzen(schluss, start="2023-01-02")}, {"US": "USD"}, {"USD": pd.Series(1.0, index=TAGE)})
    d = TeilportfolioDefinition("core", 1000.0, Plan({"2023-01-02": {"US": 0.9}, "2023-06-05": {"US": 0.0}}), [Instrument("US", "aktie")])
    e = simuliere([d], m, TAGE[0], TAGE[-1], kosten=mit_kosten, regeln=bruchteile, steuern=Steuerregeln(sparer_pauschbetrag=0.0),
                  konfig={**konfig, "steuern": {**konfig["steuern"], "pauschbetrag_anteil": {}}})["core"]
    steuer = float(e.steuern_gruppe.loc[2023, "steuer"])
    assert steuer > 50.0
    tausch = e.waehrungstausche[e.waehrungstausche.datum == ZAHLTAG_2023]
    assert len(tausch) == 1 and tausch.iloc[0]["von"] == "USD" and tausch.iloc[0]["kosten"] == pytest.approx(2.0)
    eur_vorher = e.werte.loc[TAGE[TAGE < ZAHLTAG_2023][-1], "cash"]       # EUR- plus USD-Kasse in EUR
    assert e.werte.loc[ZAHLTAG_2023, "cash"] == pytest.approx(eur_vorher - steuer - 2.0)
    assert e.werte.loc[ZAHLTAG_2023, "steuerschuld"] == 0.0


def test_twr_vor_steuern_zaehlt_steuer_als_auszahlung(konfig, ohne_kosten, bruchteile):
    werte = pd.Series([100.0, 110.0, 99.0, 108.9], index=pd.bdate_range("2024-01-01", periods=4))
    steuer = pd.Series([0.0, 0.0, 11.0, 0.0], index=werte.index)          # Tag 3: 11 € Steuer, sonst keine Bewegung
    twr = zeitgewichtete_rendite(werte, None, steuer)
    assert list(twr.round(10)) == [1.0, 1.1, 1.1, 1.21]
    e = _lauf({"2023-01-02": {"A": 1.0}, "2023-06-05": {"A": 0.0}}, konfig, ohne_kosten, bruchteile)
    assert e.twr_vor_steuern.iloc[-1] == pytest.approx(1.5)               # Abfluss der Steuer ist keine Rendite
