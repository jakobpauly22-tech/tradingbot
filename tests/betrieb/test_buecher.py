"""Vorschläge je Buch: Realbuch, Technik mit gespeichertem Zustand, Fundamental Aufbau und Quartalsrhythmus."""
import numpy as np
import pandas as pd
import pytest

from tradingbot.betrieb.buecher import fundamentalbuch, quartalsstichtag, realbuch, stueck_fuer, technikbuch
from tradingbot.konfiguration import lade_konfiguration

GEB = lambda n, w: max(1.25, 0.0005 * w)   # noqa: E731


def test_realbuch_ganze_anteile_rest_bleibt_kasse():
    v = realbuch("2026-11-02", "SPYI.DE", 200.0, 500.0, 0.02, GEB)
    assert len(v) == 1 and v[0].vorschlag.stueck == 2 and v[0].limit_order == 204.0
    assert "Rest bleibt Kasse" in v[0].vorschlag.these
    assert realbuch("2026-11-02", "SPYI.DE", 200.0, 150.0, 0.02, GEB) == []
    assert stueck_fuer(1000, 300, 100.0, GEB) == 2           # 3 × 100 + 1,25 > 300


def _kerzen(schluss, start="2025-01-01"):
    tage = pd.bdate_range(start, periods=len(schluss))
    c = pd.Series(schluss, index=tage, dtype=float)
    o = c.shift(1).fillna(c.iloc[0])
    return pd.DataFrame({"open": o, "high": np.maximum(o, c) * 1.005, "low": np.minimum(o, c) * 0.995, "close": c,
                         "volume": 1.0, "dividende": 0.0, "split": 0.0})


def test_technikbuch_einstieg_und_zustand_ueber_tage():
    k = lade_konfiguration("technik")
    kurse = {"A.DE": _kerzen(np.linspace(100, 160, 300)), "B.DE": _kerzen(np.linspace(160, 100, 300))}
    tag = kurse["A.DE"].index[-2]
    teil = {t: d.loc[:tag] for t, d in kurse.items()}
    v, z = technikbuch("crossover", "crossover", tag, teil, {t: float(d["close"].iloc[-1]) for t, d in teil.items()},
                       {}, {}, 10_000.0, {}, {}, k, 0.02, GEB)
    assert [x.vorschlag.ticker for x in v] == ["A.DE"] and v[0].vorschlag.stop < v[0].vorschlag.letzter_kurs
    assert "A.DE" in z["positionen"] and z["positionen"]["A.DE"]["kauf_tag"] is None
    # nächster Tag: Kauf ausgeführt → Zustand übernimmt Kauftag und Stop, kein neuer Vorschlag
    tag2 = kurse["A.DE"].index[-1]
    v2, z2 = technikbuch("crossover", "crossover", tag2, kurse, {t: float(d["close"].iloc[-1]) for t, d in kurse.items()},
                         {}, {}, 10_000.0 - v[0].vorschlag.stueck * 160, {"A.DE": v[0].vorschlag.stueck}, z, k, 0.02, GEB)
    assert v2 == [] and z2["positionen"]["A.DE"]["kauf_tag"] == str(tag2.date()) and z2["positionen"]["A.DE"]["stop"] is not None


def test_fundamentalbuch_sofortaufbau_dann_quartal():
    kf = lade_konfiguration("fundamental")
    n = 30
    rl = pd.DataFrame({"ticker": [f"T{i}" for i in range(n)], "sic": [1000 + 100 * i for i in range(n)], "gesamt": np.linspace(0.9, 0.5, n),
                       "qualitaet": 0.8, "bewertung": 0.6, "ersetzt": ""})
    kurse = {f"T{i}": 50.0 for i in range(n)}
    v, z, grund = fundamentalbuch("fundamental_a", "A", "2026-11-02", rl, kurse, 1.10, 10_000.0, {}, {}, kf, 0.02, GEB)
    assert grund == "Aufbau" and len(v) == 20 and all(x.vorschlag.richtung == 1 and x.waehrung == "USD" for x in v)
    erster = v[0]
    assert erster.limit_order == 51.0 and erster.vorschlag.limit == pytest.approx(51.0 / 1.10)
    assert "Rang 1" in erster.vorschlag.these
    bestand = {x.vorschlag.ticker: x.vorschlag.stueck for x in v}
    v2, _, grund2 = fundamentalbuch("fundamental_a", "A", "2026-11-03", rl, kurse, 1.10, 500.0, bestand, z, kf, 0.02, GEB)
    assert v2 == [] and grund2 == "kein Quartalsstichtag"
    assert quartalsstichtag("2027-01-04") and not quartalsstichtag("2027-01-05") and not quartalsstichtag("2026-11-02")



def test_limit_abgerundet_nie_ueber_zwei_prozent():
    from tradingbot.betrieb.buecher import limit_preis
    assert limit_preis(11.67, 0.02) == 11.90 and 11.90 <= 11.67 * 1.02          # 11,9034 → 11,90
    assert limit_preis(67.87, 0.02) == 69.22 and 69.22 <= 67.87 * 1.02          # vorher gerundet 69,23 > 2 %



def test_thesen_kern_und_details():
    v = realbuch("2026-11-02", "SPYI.DE", 200.0, 500.0, 0.02, GEB)[0]
    assert v.kern and "Widerlegt, wenn" in v.details and "Was dagegen spricht" in v.details
    k = lade_konfiguration("technik")
    kurse = {"A.DE": _kerzen(np.linspace(100, 160, 300))}
    tag = kurse["A.DE"].index[-1]
    tv, _ = technikbuch("crossover", "crossover", tag, kurse, {"A.DE": 160.0}, {}, {}, 10_000.0, {}, {}, k, 0.02, GEB)
    d = tv[0].details
    assert "SMA50" in d and "Stop" in d and "Maximaler Verlust bis Stop" in d and "des Buchs" in d


def test_technikbuch_risiko_vom_limit_begrenzt_stueck():
    """Stückzahl so, dass Stück · (Limit − Stop) ≤ 1 % des Buchwerts (Jakob 03.11.2026)."""
    k = lade_konfiguration("technik")
    kurse = {"A.DE": _kerzen(np.linspace(100, 160, 300) + np.tile([0.0, 6.0], 150))}      # hohe ATR → Risiko bindet
    tag = kurse["A.DE"].index[-1]
    schluss = float(kurse["A.DE"]["close"].iloc[-1])
    tv, _ = technikbuch("crossover", "crossover", tag, kurse, {"A.DE": schluss}, {}, {}, 10_000.0, {}, {}, k, 0.02, GEB)
    kaeufe = [b for b in tv if b.vorschlag.richtung > 0]
    assert kaeufe
    for b in kaeufe:
        v = b.vorschlag
        assert v.stueck * (b.limit_order - v.stop) <= 0.01 * 10_000.0 + 1e-6
        assert (v.stueck + 1) * (b.limit_order - v.stop) > 0.01 * 10_000.0          # das Risiko bindet hier


def test_technikbuch_titel_unterwegs_gesperrt():
    k = lade_konfiguration("technik")
    kurse = {"A.DE": _kerzen(np.linspace(100, 160, 300))}
    tag = kurse["A.DE"].index[-1]
    tv, _ = technikbuch("crossover", "crossover", tag, kurse, {"A.DE": 160.0}, {}, {}, 10_000.0, {}, {}, k, 0.02, GEB, gesperrt_titel={"A.DE"})
    assert not [b for b in tv if b.vorschlag.ticker == "A.DE"]


def test_verkauf_begruendung_stop_nachgeholt_und_signalende():
    """Jakob 11.11.2026: Grund-Kennzahlen des Verkaufs und „Was dagegen spricht“ automatisch."""
    from tradingbot.betrieb.buecher import verkauf_begruendung
    from tradingbot.engines.technik.strategien import berechne_indikatoren
    k = lade_konfiguration("technik")
    schluss = np.linspace(50, 80, 300)
    schluss[-3] = 60.0                                              # Einbruch unter den Stop am drittletzten Tag
    ind = berechne_indikatoren(_kerzen(schluss), k)
    tag, aus = ind.index[-1], ind.index[-3]
    daten, zahlen, dagegen = verkauf_begruendung("crossover", ind, tag, aus, "Stop 69.04", 69.04)
    assert daten["aktion"] == "verkauf" and daten["ausstieg"] == "stop" and daten["nachgeholt"]
    assert daten["schluss_ausloese"] == 60.0 and daten["stop_kurs"] == 69.04 and daten["ausloese_tag"] == str(aus.date())
    assert any(f"am {aus:%d.%m.%Y} (nachgeholt)" in z for z in zahlen)
    assert dagegen[0] == "Kurs liegt inzwischen wieder über dem Stop (80,00 > 69,04 €); Verkauf folgt der Regel 'verpasste Stops nachholen'"
    assert dagegen[1].startswith("Trend intakt (SMA50 > SMA200")
    # Stop ohne gespeicherten Stop-Kurs: aus dem Grund gelesen
    assert verkauf_begruendung("crossover", ind, tag, aus, "Stop 69.04", None)[0]["stop_kurs"] == 69.04
    # Signalende am selben Tag (fallender Kurs): nichts dagegen
    ind2 = berechne_indikatoren(_kerzen(np.linspace(80, 50, 300)), k)
    d2, _, dagegen2 = verkauf_begruendung("momentum", ind2, ind2.index[-1], ind2.index[-1], "12−1 ≤ 0", None)
    assert d2["ausstieg"] == "signal" and not d2["nachgeholt"] and d2["mom"] < 0 and dagegen2 == []


def test_technikbuch_verkauf_traegt_verkaufsdaten():
    k = lade_konfiguration("technik")
    kurse = {"A.DE": _kerzen(np.r_[np.linspace(100, 160, 280), np.linspace(160, 90, 40)])}
    tag = kurse["A.DE"].index[-1]
    zustand = {"positionen": {"A.DE": {"regel": "crossover", "signal_tag": str(kurse["A.DE"].index[200].date()),
                                       "kauf_tag": str(kurse["A.DE"].index[201].date()), "stop": 150.0, "atr_signal": 2.0}}}
    v, _ = technikbuch("crossover", "crossover", tag, kurse, {"A.DE": 90.0}, {}, {}, 0.0, {"A.DE": 10}, zustand, k, 0.02, GEB)
    assert len(v) == 1 and v[0].vorschlag.richtung < 0
    d = v[0].daten
    assert d["aktion"] == "verkauf" and d["stop_kurs"] == 150.0 and d["bestand_wert"] == pytest.approx(900.0)
    assert "Auslöser:" in v[0].details
