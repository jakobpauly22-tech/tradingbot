import pandas as pd
import pytest

from tradingbot.backtest.portfolio import Teilportfolio


def test_eur_gebuehr_minimum_satz_maximum(mit_kosten):
    assert mit_kosten.gebuehren_eur("EUR", 1, 100.0, 1.0) == (1.25, 0.0)       # Minimum
    assert mit_kosten.gebuehren_eur("EUR", 1, 10_000.0, 1.0) == (5.0, 0.0)     # 0,05 %
    assert mit_kosten.gebuehren_eur("EUR", 1, 100_000.0, 1.0) == (29.0, 0.0)   # Maximum


def test_usd_gebuehr_und_waehrungstausch(mit_kosten):
    # 10 Stück für 1.000 € bei 1,25 USD je EUR = 1.250 USD: Gebühr 1 USD (Minimum), Tausch 2 USD (Minimum)
    gebuehr, tausch = mit_kosten.gebuehren_eur("USD", 10, 1000.0, 1.25)
    assert gebuehr == pytest.approx(1.0 / 1.25) and tausch == pytest.approx(2.0 / 1.25)


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
