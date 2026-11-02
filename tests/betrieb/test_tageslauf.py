"""Tageslauf und Freigabe mit Attrappen (Broker, Kurse, Fundamentalbewertung)."""
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

from tradingbot.backtest.kosten import Kostenmodell
from tradingbot.betrieb.journal import Journal
from tradingbot.betrieb.tageslauf import freigeben_und_senden, tageslauf
from tradingbot.broker.basis import Position, SendenGesperrt
from tradingbot.konfiguration import lade_konfiguration
from tradingbot.risiko.manager import RiskManager

ABEND = datetime(2026, 11, 2, 23, 30, tzinfo=ZoneInfo("Europe/Berlin"))
KOSTEN = Kostenmodell(gebuehren={"EUR": {"satz": 0.0005, "minimum": 1.25, "maximum": 29.0},
                                 "USD": {"je_stueck": 0.005, "minimum": 1.0, "max_anteil": 0.01}})


def kurse_attrappe(stale=frozenset()):
    def laden(ticker, bis, art):
        ende = pd.Timestamp(bis) - (pd.Timedelta(days=1) if ticker in stale else pd.Timedelta(0))
        tage = pd.bdate_range(end=ende, periods=320)
        if ticker == "EURUSD=X":
            c = np.full(len(tage), 1.10)
        else:
            basis = 50 + (sum(map(ord, ticker)) % 100)
            steigung = 0.5 if sum(map(ord, ticker)) % 2 else -0.2
            c = basis + steigung * np.arange(len(tage)) / 10
        return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99, "close": c, "volume": 1.0, "dividende": 0.0, "split": 0.0}, index=tage)
    return laden


def bewertung_attrappe(tag):
    n = 30
    return (pd.DataFrame({"firma": range(n), "symbol": [f"US{i}" for i in range(n)], "sic": [1000 + 100 * i for i in range(n)],
                          "schluss_usd": 80.0, "kursdatum": tag, "piotroski_filter": np.linspace(9, 4, n), "accruals": np.linspace(-0.1, 0.1, n),
                          "ep": np.linspace(0.1, 0.01, n), "ebit_ev": np.linspace(0.1, 0.01, n), "ausgeschlossen": False,
                          "gruende": [[] for _ in range(n)], "hinweise": [[] for _ in range(n)], "piotroski_hoch": False}), {}, [])


class BrokerAttrappe:
    def __init__(self, verbunden=True, positionen=(), sperre=False, fills=()):
        self._verbunden, self._positionen, self.sperre, self._fills, self.gesendet = verbunden, list(positionen), sperre, list(fills), []

    def verbunden(self):
        return self._verbunden

    def verbinden(self):
        if not self._verbunden:
            raise ConnectionRefusedError("Gateway aus")

    def ausfuehrungen(self):
        return self._fills

    def offene_orders(self):
        return []

    def positionen(self):
        return self._positionen

    def sende(self, auftrag, refs):
        if self.sperre:
            raise SendenGesperrt("Senden ist in config/betrieb.yaml nicht freigeschaltet")
        refs.add(auftrag.order_ref)
        self.gesendet.append(auftrag)
        return str(len(self.gesendet))


@pytest.fixture
def umgebung(tmp_path):
    j = Journal(tmp_path / "journal.sqlite")
    rm = RiskManager(lade_konfiguration("risiko"), lade_konfiguration("betrieb"), KOSTEN, tmp_path)
    yield j, rm
    j.schliessen()


def lauf(j, rm, jetzt=ABEND, **kw):
    kurse = kw.pop("kurse", kurse_attrappe())
    return tageslauf(jetzt, j, kurse_laden=kurse, fundamental_bewertung=bewertung_attrappe, risk=rm, sichern=False, **kw)


def test_erster_tageslauf_ohne_gateway(umgebung):
    j, rm = umgebung
    e = lauf(j, rm)
    buecher = {bv.vorschlag.buch for bv, _ in e.vorschlaege}
    assert {"real", "fundamental_a", "fundamental_b"} <= buecher
    real = [bv for bv, u in e.vorschlaege if bv.vorschlag.buch == "real"]
    assert len(real) == 1 and real[0].vorschlag.ticker == "SPYI.DE"
    assert sum(1 for bv, _ in e.vorschlaege if bv.vorschlag.buch == "fundamental_a") == 20
    assert any("ohne Gateway" in m for m in e.meldungen)
    assert all(z["status"] in ("vorgeschlagen", "veto") for z in j.vorschlaege())


def test_datenbefund_sperrt_nur_das_betroffene_buch(umgebung):
    j, rm = umgebung
    e = lauf(j, rm, kurse=kurse_attrappe(stale={"SPYI.DE"}))
    assert "real" in e.befunde and "erwartet" in e.befunde["real"][0]
    assert not any(bv.vorschlag.buch == "real" for bv, _ in e.vorschlaege)
    assert any(bv.vorschlag.buch == "fundamental_a" for bv, _ in e.vorschlaege)


def test_abgleich_weicht_ab_stoppt(umgebung):
    j, rm = umgebung
    e = lauf(j, rm, broker=BrokerAttrappe(positionen=[Position("DU1", "SPYI.DE", 3, 200.0)]))
    assert e.gestoppt and "SPYI.DE" in e.gestoppt and e.vorschlaege == []


def test_freigabe_und_senden(umgebung):
    j, rm = umgebung
    lauf(j, rm)
    real_id = next(z["id"] for z in j.vorschlaege(buch="real"))
    k = kurse_attrappe()
    assert "18 und 24 Uhr" in freigeben_und_senden(j, [real_id], BrokerAttrappe(), ABEND.replace(hour=17), risk=rm, kurse_laden=k)[0]
    m = freigeben_und_senden(j, [real_id], BrokerAttrappe(verbunden=False), ABEND, risk=rm, kurse_laden=k)
    assert "Gateway nicht verbunden" in m[-1] and j.vorschlaege(buch="real")[0]["status"] == "freigegeben"
    assert j.messbeginn("real") == "2026-11-02"
    m = freigeben_und_senden(j, [], BrokerAttrappe(sperre=True), ABEND, risk=rm, kurse_laden=k)
    assert any("nicht freigeschaltet" in x for x in m) and j.vorschlaege(buch="real")[0]["status"] == "freigegeben"
    b = BrokerAttrappe()
    m = freigeben_und_senden(j, [], b, ABEND, risk=rm, kurse_laden=k)
    assert any("gesendet" in x for x in m) and b.gesendet[0].order_ref == f"real:{real_id}" and b.gesendet[0].limit is not None
    assert j.vorschlaege(buch="real")[0]["status"] == "gesendet"
    lauf(j, rm)                                            # zweiter Tageslauf am selben Abend
    assert j.vorschlaege(buch="real")[0]["status"] == "gesendet"


def test_ausfuehrung_einlesen_und_abgleich_ok(umgebung):
    j, rm = umgebung
    lauf(j, rm)
    z = j.vorschlaege(buch="real")[0]
    fill = {"exec_id": "x1", "order_ref": f"real:{z['id']}", "ticker": "SPYI.DE", "richtung": 1, "stueck": z["stueck"], "preis": 150.0,
            "waehrung": "EUR", "gebuehr": 1.25, "gebuehr_waehrung": "EUR", "zeit": "2026-11-03T09:00"}
    naechster = datetime(2026, 11, 3, 23, 30, tzinfo=ZoneInfo("Europe/Berlin"))
    e = lauf(j, rm, jetzt=naechster, broker=BrokerAttrappe(fills=[fill], positionen=[Position("DU1", "SPYI.DE", z["stueck"], 150.0)]))
    assert e.gestoppt is None and any("Neue Ausführungen" in m for m in e.meldungen)
    assert j.bestand("real") == {"SPYI.DE": z["stueck"]}
