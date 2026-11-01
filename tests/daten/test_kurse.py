from datetime import date

import pandas as pd
import pytest

from conftest import HEUTE, SimulierteQuelle, yahoo_rohdaten
from tradingbot.daten.abruf import DatenFehler
from tradingbot.daten.kurse import SPALTEN, in_euro, lade_kurse, lade_kurse_eur, normalisieren


def test_normalisieren_yahoo_format():
    roh = yahoo_rohdaten("2024-03-01", "2024-03-08", tz="America/New_York")
    roh["Capital Gains"] = 0.0
    daten = normalisieren(roh)
    assert list(daten.columns) == SPALTEN  # ohne Adj Close und Capital Gains
    assert daten.index.tz is None and daten.index.name == "datum"
    assert daten.index[0] == pd.Timestamp("2024-03-01")  # Börsendatum bleibt erhalten


def test_erster_abruf_dann_aus_dem_cache(cache, quelle):
    erst = lade_kurse("TEST", "2024-02-01", "2024-03-29", cache=cache, abrufer=quelle, heute=HEUTE)
    zweit = lade_kurse("TEST", "2024-02-15", "2024-03-15", cache=cache, abrufer=quelle, heute=HEUTE)

    assert len(quelle.abrufe) == 1
    assert erst.index[0] == pd.Timestamp("2024-02-01") and erst.index[-1] == pd.Timestamp("2024-03-29")
    assert zweit.index[0] == pd.Timestamp("2024-02-15") and zweit.index[-1] == pd.Timestamp("2024-03-15")
    assert zweit.attrs["waehrung"] == "EUR"


def test_nur_fehlende_zeitraeume_mit_ueberlappung_nachladen(cache, quelle):
    lade_kurse("TEST", "2024-03-01", "2024-03-29", cache=cache, abrufer=quelle, heute=HEUTE)
    daten = lade_kurse("TEST", "2024-02-01", "2024-04-30", cache=cache, abrufer=quelle, heute=HEUTE)

    assert quelle.abrufe[1:] == [
        (date(2024, 2, 1), date(2024, 3, 8)),    # rückwärts, 7 Tage Überlappung
        (date(2024, 3, 22), date(2024, 4, 30)),  # vorwärts, 7 Tage Überlappung
    ]
    erwartet = pd.bdate_range("2024-02-01", "2024-04-30")
    assert list(daten.index) == list(erwartet)


def test_zeitraum_ohne_handelstage_wird_nicht_erneut_abgefragt(cache, quelle):
    # Gewünschter Start liegt vor dem ersten Handelstag (z.B. ETF erst später aufgelegt)
    lade_kurse("TEST", "2023-06-01", "2024-03-29", cache=cache, abrufer=quelle, heute=HEUTE)
    lade_kurse("TEST", "2023-06-01", "2024-03-29", cache=cache, abrufer=quelle, heute=HEUTE)
    assert len(quelle.abrufe) == 1


def test_heutige_kerze_wird_nie_gespeichert(cache):
    quelle = SimulierteQuelle(yahoo_rohdaten("2024-06-03", "2024-07-05"))
    daten = lade_kurse("TEST", "2024-06-03", None, cache=cache, abrufer=quelle, heute=HEUTE)
    assert daten.index[-1] == pd.Timestamp("2024-06-28")  # Freitag vor dem Montag „heute“
    assert quelle.abrufe[0][1] == date(2024, 6, 30)


def test_geaenderte_bereinigung_fuehrt_zu_neuladen(cache):
    vorher = SimulierteQuelle(yahoo_rohdaten())
    lade_kurse("TEST", "2024-01-02", "2024-03-29", cache=cache, abrufer=vorher, heute=HEUTE)

    # Neuer Split 2:1 im Juni: Yahoo halbiert rückwirkend alle älteren Kurse
    nachher_roh = yahoo_rohdaten()
    nachher_roh[["Open", "High", "Low", "Close"]] /= 2
    nachher = SimulierteQuelle(nachher_roh)
    daten = lade_kurse("TEST", "2024-01-02", "2024-06-28", cache=cache, abrufer=nachher, heute=HEUTE)

    assert nachher.abrufe == [(date(2024, 3, 22), date(2024, 6, 28)), (date(2024, 1, 2), date(2024, 6, 28))]
    erwartet = normalisieren(nachher_roh).loc["2024-01-02":"2024-06-28", "close"]
    pd.testing.assert_series_equal(daten["close"], erwartet, check_freq=False)


def test_unbekannter_ticker_meldet_fehler(cache):
    leer = SimulierteQuelle(yahoo_rohdaten().iloc[:0], waehrung=None)
    with pytest.raises(DatenFehler, match="Keine Kurse für FALSCH"):
        lade_kurse("FALSCH", "2024-01-01", "2024-06-28", cache=cache, abrufer=leer, heute=HEUTE)


def _kurse(werte, tage, waehrung):
    daten = pd.DataFrame(
        {s: werte for s in ["open", "high", "low", "close"]} | {"volume": 1.0, "dividende": 0.0, "split": 0.0},
        index=pd.DatetimeIndex(pd.to_datetime(tage), name="datum"),
    )
    daten.attrs["waehrung"] = waehrung
    return daten


def test_in_euro_usd_mit_auffuellen_an_feiertagen():
    kurse = _kurse([110.0, 120.0, 130.0], ["2024-07-03", "2024-07-04", "2024-07-05"], "USD")
    eurusd = pd.Series([1.10, 1.20], index=pd.to_datetime(["2024-07-03", "2024-07-05"]))  # 04.07. fehlt
    euro = in_euro(kurse, "USD", eurusd)
    assert euro["close"].tolist() == pytest.approx([100.0, 120.0 / 1.10, 130.0 / 1.20])
    assert euro.attrs["waehrung"] == "EUR" and euro.attrs["originalwaehrung"] == "USD"


def test_in_euro_ohne_wechselkurs_aus_der_vergangenheit_meldet_fehler():
    kurse = _kurse([110.0], ["2024-07-03"], "USD")
    eurusd = pd.Series([1.10], index=pd.to_datetime(["2024-07-04"]))  # nur ein späterer Kurs: kein Look-ahead
    with pytest.raises(DatenFehler, match="fehlt für 1 Tage"):
        in_euro(kurse, "USD", eurusd)


def test_in_euro_pence_und_euro():
    pence = in_euro(_kurse([250.0], ["2024-07-03"], "GBp"), "GBp", pd.Series([0.85], index=pd.to_datetime(["2024-07-03"])))
    assert pence["close"].iloc[0] == pytest.approx(2.5 / 0.85)
    euro = in_euro(_kurse([10.0], ["2024-07-03"], "EUR"), "EUR")
    assert euro["close"].iloc[0] == 10.0


def test_lade_kurse_eur_nutzt_wechselkurs_aus_konfiguration(cache):
    aktie = SimulierteQuelle(yahoo_rohdaten("2024-06-03", "2024-06-28"), waehrung="USD")
    fx_roh = yahoo_rohdaten("2024-05-20", "2024-06-28", tz="Europe/London", basis=1.25)
    fx_roh[["Open", "High", "Low", "Close"]] = 1.25

    def abrufer(ticker, start, ende):
        return (SimulierteQuelle(fx_roh) if ticker == "EURUSD=X" else aktie)(ticker, start, ende)

    konfig = {"kurse": {"wechselkurse": {"USD": "EURUSD=X"}}}
    euro = lade_kurse_eur("AAPL", "2024-06-03", "2024-06-28", konfig=konfig, cache=cache, abrufer=abrufer, heute=HEUTE)
    usd = normalisieren(aktie.rohdaten)["close"]
    assert euro["close"].tolist() == pytest.approx((usd / 1.25).tolist())
