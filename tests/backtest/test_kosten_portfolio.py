import pandas as pd
import pytest

from conftest import kerzen
from tradingbot.backtest.portfolio import Teilportfolio


def test_eur_gebuehr_minimum_satz_maximum(mit_kosten):
    assert mit_kosten.gebuehren_eur("EUR", 1, 100.0, 1.0) == 1.25       # Minimum
    assert mit_kosten.gebuehren_eur("EUR", 1, 10_000.0, 1.0) == 5.0     # 0,05 %
    assert mit_kosten.gebuehren_eur("EUR", 1, 100_000.0, 1.0) == 29.0   # Maximum


def test_usd_gebuehr_und_waehrungstausch(mit_kosten):
    # 10 Stück für 1.000 € bei 1,25 USD je EUR = 1.250 USD: Gebühr 1 USD (Minimum); Tausch eigener Vorgang, 2 USD Minimum
    assert mit_kosten.gebuehren_eur("USD", 10, 1000.0, 1.25) == pytest.approx(1.0 / 1.25)
    assert mit_kosten.tauschkosten_eur("USD", 1250.0, 1.25) == pytest.approx(2.0 / 1.25)
    assert mit_kosten.tauschkosten_eur("USD", 500_000.0, 1.25) == pytest.approx(10.0 / 1.25)   # 0,002 % über dem Minimum


def test_ausfuehrungspreis_halber_spread_plus_slippage(mit_kosten):
    assert mit_kosten.ausfuehrungspreis(100.0, +1, "etf") == pytest.approx(100.10)
    assert mit_kosten.ausfuehrungspreis(100.0, -1, "aktie") == pytest.approx(99.85)


def test_fifo_verkauf():
    p = Teilportfolio("core", 1000.0)
    p.kaufen("2024-01-02", "A", 2, 100.0, 2.0)   # Einstand 101 je Stück
    p.kaufen("2024-02-01", "A", 2, 120.0, 0.0)   # Einstand 120 je Stück
    ergebnis = p.verkaufen("2024-03-01", "A", 3, 130.0, 1.0)
    assert ergebnis.einstand == pytest.approx(2 * 101 + 120)
    assert ergebnis.erloes == pytest.approx(389.0)
    assert ergebnis.gewinn == pytest.approx(389.0 - 322.0)
    assert [(q.datum, q.stueck) for q in ergebnis.verbrauchte_posten] == [(pd.Timestamp("2024-01-02"), 2), (pd.Timestamp("2024-02-01"), 1)]
    assert p.stueck("A") == 1 and p.cash == pytest.approx(1000 - 202 - 240 + 389)


def test_keine_margin_und_kein_leerverkauf():
    p = Teilportfolio("satellite", 100.0)
    with pytest.raises(ValueError, match="keine Margin"):
        p.kaufen("2024-01-02", "A", 2, 60.0, 0.0)
    with pytest.raises(ValueError, match="nur long"):
        p.verkaufen("2024-01-02", "A", 1, 60.0, 0.0)


def test_fremdwaehrungskasse_netto_tausch(konfig, mit_kosten):
    """Zwei US-Käufe am selben Tag → ein Tausch; beim Umschichten deckt der Verkaufserlös (bleibt in USD) den Kauf,
    getauscht wird nur der Netto-Fehlbetrag; Rücktausch erst beim fiktiven Verkauf am Ende (Auszahlung)."""
    from tradingbot.backtest.marktdaten import Instrument, Marktdaten
    from tradingbot.backtest.simulation import Ausfuehrungsregeln, TeilportfolioDefinition, simuliere

    class Plan:
        name = "plan"
        def __init__(self):
            self.n = 0
        def zielgewichte(self, tag, sicht):
            self.n += 1
            return {1: pd.Series({"A": 0.5, "B": 0.5}), 5: pd.Series({"A": 0.0, "B": 0.5, "C": 0.5})}.get(self.n)
    tage = pd.bdate_range("2024-01-01", periods=10)
    fx = pd.Series(1.25, index=tage)
    m = Marktdaten({t: kerzen([100.0] * 10) for t in "ABC"}, {t: "USD" for t in "ABC"}, {"USD": fx})
    d = TeilportfolioDefinition("core", 10_000.0, Plan(), [Instrument(t, "aktie") for t in "ABC"])
    e = simuliere([d], m, tage[0], tage[-1], kosten=mit_kosten, regeln=Ausfuehrungsregeln(), konfig=konfig)["core"]
    t = e.waehrungstausche
    assert list(t["datum"]) == [tage[1], tage[5]] and (t["von"] == "EUR").all()   # je Ausführungstag höchstens ein Tausch
    kauf_c = e.trades[(e.trades.datum == tage[5]) & (e.trades.ticker == "C")].kurswert.iloc[0]
    assert t.iloc[1]["betrag_eur"] < 0.05 * kauf_c                                  # nur der Fehlbetrag, nicht die Order
    assert e.kosten_gesamt == pytest.approx(e.trades.gebuehr.sum() + e.trades.spread_slippage.sum() + 2 * 2.0 / 1.25)
    # Wert = EUR-Kasse + USD-Kasse/1,25 + Positionen; am Ende Rücktausch mit Kosten im Liquidationswert
    assert e.meta["liquidationswert"] < e.wert.iloc[-1]


def test_stueckpreis_ueber_zielwert_wird_protokolliert(konfig, ohne_kosten):
    from tradingbot.backtest.marktdaten import Instrument, Marktdaten
    from tradingbot.backtest.simulation import Ausfuehrungsregeln, TeilportfolioDefinition, simuliere
    from tradingbot.backtest.strategie import BuyAndHold
    m = Marktdaten({"A": kerzen([500.0] * 5)})
    d = TeilportfolioDefinition("core", 1000.0, BuyAndHold({"A": 0.25}), [Instrument("A", "etf")])
    e = simuliere([d], m, m.kalender[0], m.kalender[-1], kosten=ohne_kosten, regeln=Ausfuehrungsregeln(), konfig=konfig)["core"]
    assert e.trades.empty and e.verworfen.iloc[0]["grund"].startswith("Stückpreis 500.00")


def test_gebuehrenplan_xetra_fuer_usd_notierten_etf(konfig, mit_kosten):
    """SXRM: Xetra-Handel in USD → Gebühr nach Xetra-Plan (0,05 %, min. 1,25 €), Abrechnung über die USD-Kasse."""
    from tradingbot.backtest.marktdaten import Instrument, Marktdaten
    from tradingbot.backtest.simulation import Ausfuehrungsregeln, TeilportfolioDefinition, simuliere
    from tradingbot.backtest.strategie import BuyAndHold
    tage = pd.bdate_range("2024-01-01", periods=5)
    m = Marktdaten({"T": kerzen([100.0] * 5)}, {"T": "USD"}, {"USD": pd.Series(1.25, index=tage)})
    d = TeilportfolioDefinition("core", 1000.0, BuyAndHold({"T": 0.5}), [Instrument("T", "etf", "sonstiger_fonds", gebuehrenplan="EUR")])
    e = simuliere([d], m, tage[0], tage[-1], kosten=mit_kosten, regeln=Ausfuehrungsregeln(), konfig=konfig)["core"]
    assert e.trades.iloc[0]["gebuehr"] == pytest.approx(1.25)
    assert len(e.waehrungstausche) == 1 and e.waehrungstausche.iloc[0]["nach"] == "USD"
