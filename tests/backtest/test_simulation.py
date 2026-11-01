import numpy as np
import pandas as pd
import pytest

from conftest import kerzen
from tradingbot.backtest.marktdaten import Instrument, LookAheadFehler, Marktdaten
from tradingbot.backtest.simulation import Ausfuehrungsregeln, TeilportfolioDefinition, simuliere
from tradingbot.backtest.strategie import BuyAndHold, FesteGewichte
from tradingbot.backtest.tresor import TresorGesperrt
from tradingbot.kennzahlen.rendite import total_return_index


def _definition(strategie, ticker=("A",), kapital=1000.0, name="core", klasse="etf"):
    return TeilportfolioDefinition(name, kapital, strategie, [Instrument(t, klasse) for t in ticker])


def test_gegenprobe_buy_and_hold_ohne_kosten_entspricht_total_return(konfig, ohne_kosten, bruchteile):
    rng = np.random.default_rng(1)
    schluss = 100 * np.cumprod(1 + rng.normal(0.0004, 0.01, 250))
    m = Marktdaten({"A": kerzen(schluss)})
    e = simuliere([_definition(BuyAndHold({"A": 1.0}))], m, "2024-01-01", "2024-12-31",
                  kosten=ohne_kosten, regeln=bruchteile, konfig=konfig)["core"]
    # Kauf am 2. Tag zur Eröffnung, danach Wert = Stück · Schluss = Startkapital · Schluss_t / Eröffnung_2
    kauftag = m.kalender[1]
    tri = total_return_index(m.kurse["A"]).loc[kauftag:]
    erwartet = 1000.0 * tri / tri.iloc[0] * m.kurse["A"].loc[kauftag, "close"] / m.kurse["A"].loc[kauftag, "open"]
    pd.testing.assert_series_equal(e.wert.loc[kauftag:], erwartet, check_names=False, check_freq=False)
    assert e.wert.iloc[0] == 1000.0


def test_kosten_exakt_nachgerechnet(konfig, mit_kosten):
    m = Marktdaten({"A": kerzen([100.0] * 5)})
    e = simuliere([_definition(BuyAndHold({"A": 1.0}))], m, "2024-01-01", "2024-01-05",
                  kosten=mit_kosten, regeln=Ausfuehrungsregeln(), konfig=konfig)["core"]
    t = e.trades.iloc[0]
    preis = 100.0 * (1 + 0.0005 + 0.0005)                 # halber Spread ETF + Slippage
    assert t.ausfuehrungspreis == pytest.approx(preis)
    assert t.stueck == 9                                   # 1.000 / 100,10 = 9,99 → 9 ganze Stück
    assert t.gebuehr == pytest.approx(1.25)                # 0,05 % von 900,90 < Minimum
    assert e.werte["cash"].iloc[-1] == pytest.approx(1000 - 9 * preis - 1.25)
    assert e.wert.iloc[-1] == pytest.approx(1000 - 9 * preis - 1.25 + 9 * 100.0)


def test_mindestorder_regel_verwirft_kleine_order(konfig, mit_kosten):
    # 150 € Satellite, Position 10 % = 15 €: Gebühr 1,25 € wären 8 % → Order verworfen
    m = Marktdaten({"A": kerzen([5.0] * 5)})
    e = simuliere([_definition(BuyAndHold({"A": 0.10}), kapital=150.0, name="satellite")], m, "2024-01-01", "2024-01-05",
                  kosten=mit_kosten, regeln=Ausfuehrungsregeln(), konfig=konfig)["satellite"]
    assert e.trades.empty
    assert e.verworfen.iloc[0].grund.startswith("Gebühren 1.25 € > 1%")
    assert e.wert.iloc[-1] == 150.0


def test_rebalancing_verkauft_zuerst_und_bleibt_long(konfig, ohne_kosten):
    # A verdoppelt sich im Januar; zum Quartalswechsel wird zurück auf 50/50 gebracht
    tage = pd.bdate_range("2024-01-01", "2024-04-30")
    a = np.where(tage < "2024-02-01", 100.0, 200.0)
    m = Marktdaten({"A": kerzen(a), "B": kerzen([100.0] * len(tage))})
    e = simuliere([_definition(FesteGewichte({"A": 0.5, "B": 0.5}, "Q"), ticker=("A", "B"))], m, "2024-01-01", "2024-04-30",
                  kosten=ohne_kosten, regeln=Ausfuehrungsregeln(), konfig=konfig)["core"]
    april = e.trades[e.trades.datum >= "2024-04-01"]
    assert list(april.richtung) == [-1, +1]                # erst verkaufen, dann kaufen
    assert april.iloc[0].ticker == "A" and april.iloc[1].ticker == "B"
    assert (e.bestaende >= 0).all().all() and (e.werte["cash"] >= -1e-9).all()
    # Nach dem Rebalancing etwa 50/50 (Rundung auf ganze Stück)
    nach = e.bestaende.loc["2024-04-03"]
    assert abs(nach["A"] * 200 - nach["B"] * 100) <= 200


def test_abweichung_unter_einem_stueck_ist_keine_verworfene_order(konfig, ohne_kosten):
    m = Marktdaten({"A": kerzen([300.0] * 40)})
    e = simuliere([_definition(FesteGewichte({"A": 1.0}, "M"))], m, "2024-01-01", "2024-02-26",
                  kosten=ohne_kosten, regeln=Ausfuehrungsregeln(), konfig=konfig)["core"]
    assert len(e.trades) == 1 and e.verworfen.empty      # 3 Stück, Rest 100 € Cash reicht nie für ein weiteres


def test_zu_wenig_cash_wird_protokolliert(konfig, mit_kosten):
    # Ziel 100 % bei 1.000 € und Kurs 999 €: Kurswert plus Kosten passen nicht ins Cash
    m = Marktdaten({"A": kerzen([999.0] * 5)})
    e = simuliere([_definition(BuyAndHold({"A": 1.0}))], m, "2024-01-01", "2024-01-05",
                  kosten=mit_kosten, regeln=Ausfuehrungsregeln(), konfig=konfig)["core"]
    assert e.trades.empty and e.verworfen.grund.tolist() == ["zu wenig Cash für ein Stück"]


def test_dividende_am_ex_tag(konfig, ohne_kosten, bruchteile):
    dividende = [0.0] * 10
    dividende[5] = 2.0
    m = Marktdaten({"A": kerzen([100.0] * 10, dividende=dividende)})
    e = simuliere([_definition(BuyAndHold({"A": 1.0}))], m, "2024-01-01", "2024-01-31",
                  kosten=ohne_kosten, regeln=bruchteile, konfig=konfig)["core"]
    assert e.dividenden.betrag.tolist() == [pytest.approx(20.0)]  # 10 Stück · 2 €


def test_look_ahead_falle(konfig, ohne_kosten):
    class Hellseher:
        name = "Hellseher"

        def zielgewichte(self, stichtag, sicht):
            sicht.kurs_am("A", stichtag + pd.Timedelta(days=1))

    m = Marktdaten({"A": kerzen([100.0] * 5)})
    with pytest.raises(LookAheadFehler):
        simuliere([_definition(Hellseher())], m, "2024-01-01", "2024-01-05", kosten=ohne_kosten, konfig=konfig)

    class Vorsichtig:
        name = "Vorsichtig"

        def zielgewichte(self, stichtag, sicht):
            assert sicht.kurse("A").index.max() == stichtag
            assert sicht.schlusskurse().index.max() == stichtag

    simuliere([_definition(Vorsichtig())], m, "2024-01-01", "2024-01-05", kosten=ohne_kosten, konfig=konfig)


def test_unzulaessige_gewichte(konfig, ohne_kosten):
    m = Marktdaten({"A": kerzen([100.0] * 5)})
    for gewichte, fehler in [({"A": -0.5}, "nur long"), ({"A": 1.5}, "kein Hebel"), ({"X": 0.5}, "außerhalb")]:
        with pytest.raises(ValueError, match=fehler):
            simuliere([_definition(BuyAndHold(gewichte))], m, "2024-01-01", "2024-01-05", kosten=ohne_kosten, konfig=konfig)


def test_simulation_respektiert_tresor(konfig, ohne_kosten):
    m = Marktdaten({"A": kerzen([100.0] * 5, start="2025-01-01")})
    with pytest.raises(TresorGesperrt):
        simuliere([_definition(BuyAndHold({"A": 1.0}))], m, "2025-01-01", "2025-01-07", kosten=ohne_kosten, konfig=konfig)


def test_core_und_satellite_getrennt(konfig, ohne_kosten):
    a = kerzen([100.0, 100.0, 50.0, 50.0, 50.0])
    m = Marktdaten({"A": a, "B": kerzen([100.0] * 5)})
    ergebnisse = simuliere(
        [_definition(BuyAndHold({"B": 1.0}), ticker=("B",), kapital=350.0, name="core"),
         _definition(BuyAndHold({"A": 1.0}), ticker=("A",), kapital=150.0, name="satellite")],
        m, "2024-01-01", "2024-01-05", kosten=ohne_kosten, konfig=konfig,
    )
    assert ergebnisse["core"].wert.iloc[-1] == 350.0       # Verlust im Satellite berührt den Core nicht
    assert ergebnisse["satellite"].wert.iloc[-1] == pytest.approx(150.0 - 1 * 50.0)
