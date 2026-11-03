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
