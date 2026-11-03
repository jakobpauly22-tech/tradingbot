"""Phase 2: TWR, XIRR, echte Anteilspreise, Sparplan, Einzahlungen, Limit-Modell, Risk-Manager-Hook."""
import pandas as pd
import pytest

from conftest import kerzen
from tradingbot.backtest.marktdaten import Instrument, Marktdaten
from tradingbot.backtest.simulation import Ausfuehrungsregeln, TeilportfolioDefinition, simuliere
from tradingbot.backtest.strategie import SparplanKern
from tradingbot.daten.kurse import echte_anteilspreise
from tradingbot.kennzahlen.performance import xirr, zeitgewichtete_rendite
from tradingbot.risiko.manager import Urteil

GEB = lambda n, w: max(1.25, 0.0005 * w)   # noqa: E731


def test_twr_ignoriert_einzahlungen():
    tage = pd.bdate_range("2024-01-01", periods=3)
    werte = pd.Series([100.0, 110.0, 220.0], index=tage)          # Tag 3: Einzahlung 100, danach 10 € Gewinn
    twr = zeitgewichtete_rendite(werte, pd.Series({tage[2]: 100.0}))
    assert twr.iloc[1] == pytest.approx(1.10) and twr.iloc[2] == pytest.approx(1.10 * (120 / 110))


def test_xirr_von_hand():
    z = pd.Series({pd.Timestamp("2024-01-01"): -100.0, pd.Timestamp("2025-01-01"): 110.0})
    assert xirr(z) == pytest.approx(1.10 ** (365.25 / 366) - 1, abs=1e-6)      # 366 Tage (Schaltjahr)


def test_echte_anteilspreise_nach_split():
    k = kerzen([10.0, 10.0, 11.0], start="2026-02-19")
    echt = echte_anteilspreise(k, "SPYI.DE", [{"ticker": "SPYI.DE", "art": "split", "datum": "2026-02-23", "verhaeltnis": 25}])
    assert echt["close"].tolist() == [250.0, 250.0, 11.0] and echt["volume"].iloc[0] == pytest.approx(1000.0 / 25)


def _def(strategie, einz=None, limit=None, risk=None):
    return TeilportfolioDefinition("real", 500.0, strategie, [Instrument("A", "etf")], einzahlungen=einz, kauf_limit_aufschlag=limit,
                                   risk_pruefung=risk)


def test_einzahlung_und_sparplan_mit_restkasse(konfig, mit_kosten):
    m = Marktdaten({"A": kerzen([200.0] * 30)})
    t = m.kalender
    einz = pd.Series({t[10]: 100.0, t[20]: 100.0})
    e = simuliere([_def(SparplanKern("A", GEB), einz, limit=0.02)], m, t[0], t[-1], kosten=mit_kosten, regeln=Ausfuehrungsregeln(),
                  konfig=konfig)["real"]
    assert e.werte["einzahlung"].sum() == 200.0
    # 500 € → 2 Stück (400 € plus Kosten); +100 → knapp 200 € Kasse, reicht nicht für Stück plus Gebühr; +100 → 1 Stück
    assert e.trades.stueck.tolist() == [2, 1] and (e.werte["cash"] >= 0).all()


def test_limit_verfaellt_wenn_eroeffnung_darueber(konfig, ohne_kosten):
    eroeffnung = [100.0, 103.0, 101.0, 100.0, 100.0]             # Tag 2: 103 > Limit 102 → verfallen; Tag 3: 101 ≤ 102
    m = Marktdaten({"A": kerzen([100.0] * 5, eroeffnung=eroeffnung)})
    t = m.kalender
    e = simuliere([_def(SparplanKern("A", lambda n, w: 0.0), limit=0.02)], m, t[0], t[-1], kosten=ohne_kosten,
                  regeln=Ausfuehrungsregeln(), konfig=konfig)["real"]
    assert len(e.meta["verfallen"]) == 1 and e.meta["verfallen"].iloc[0]["limit"] == 102.0
    assert e.trades.iloc[0]["datum"] == t[2] and e.trades.iloc[0]["ausfuehrungspreis"] <= 102.0


def test_risk_hook_veto_verhindert_ausfuehrung(konfig, ohne_kosten):
    aufrufe = []

    def veto(lauf, tag, ticker, richtung, stueck, letzter_kurs, limit):
        aufrufe.append((ticker, richtung, stueck, letzter_kurs, limit))
        return Urteil(False, ["Test-Veto"])
    m = Marktdaten({"A": kerzen([100.0] * 5)})
    t = m.kalender
    e = simuliere([_def(SparplanKern("A", lambda n, w: 0.0), limit=0.02, risk=veto)], m, t[0], t[-1], kosten=ohne_kosten,
                  regeln=Ausfuehrungsregeln(), konfig=konfig)["real"]
    assert e.trades.empty and len(e.meta["vetos"]) >= 1 and aufrufe[0][4] == 102.0 and e.meta["risk_geprueft"] == len(aufrufe)
