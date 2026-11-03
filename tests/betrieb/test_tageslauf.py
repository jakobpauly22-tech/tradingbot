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


def betrieb_mit(global_an=True, buecher=("real", "crossover")):
    b = lade_konfiguration("betrieb")
    b["ibkr"] = {**b["ibkr"], "senden_freigeschaltet": global_an}
    b["buecher"] = {n: {**bk, "senden_freigeschaltet": n in buecher} for n, bk in b["buecher"].items()}
    return b


AUS, AN = betrieb_mit(False), betrieb_mit(True)


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
    assert sum(1 for bv, _ in e.vorschlaege if bv.vorschlag.buch == "fundamental_a" and bv.vorschlag.art != "fx") == 20
    tausch = [(bv, u) for bv, u in e.vorschlaege if bv.vorschlag.buch == "fundamental_a" and bv.vorschlag.art == "fx"]
    assert len(tausch) == 1 and tausch[0][1].frei
    kaeufe_usd = sum(bv.vorschlag.stueck * bv.limit_order for bv, _ in e.vorschlaege if bv.vorschlag.buch == "fundamental_a" and bv.vorschlag.art != "fx")
    assert tausch[0][0].vorschlag.stueck * 1.10 >= kaeufe_usd * 1.02                # deckt Käufe plus Puffer
    assert all(u.frei for bv, u in e.vorschlaege if bv.vorschlag.buch == "fundamental_a")   # USD-Käufe frei, weil der Tausch vorher geprüft wird
    assert not any(bv.vorschlag.art == "fx" for bv, _ in e.vorschlaege if bv.vorschlag.buch == "real")
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
    m = freigeben_und_senden(j, [real_id], BrokerAttrappe(), ABEND, risk=rm, kurse_laden=k, konfig_betrieb=AUS)
    assert any("nicht freigebbar" in x for x in m) and j.vorschlaege(buch="real")[0]["status"] == "vorgeschlagen"
    assert j.messbeginn("real") is None                     # Senden aus: nicht freigebbar, kein Messbeginn
    m = freigeben_und_senden(j, [real_id], BrokerAttrappe(verbunden=False), ABEND, risk=rm, kurse_laden=k, konfig_betrieb=AN)
    assert "Gateway nicht verbunden" in m[-1] and j.vorschlaege(buch="real")[0]["status"] == "freigegeben"
    assert j.messbeginn("real") is not None                 # Buch freigeschaltet: Freigabe ist Messbeginn
    m = freigeben_und_senden(j, [], BrokerAttrappe(sperre=True), ABEND, risk=rm, kurse_laden=k, konfig_betrieb=AN)
    assert any("nicht freigeschaltet" in x for x in m) and j.vorschlaege(buch="real")[0]["status"] == "freigegeben"
    b = BrokerAttrappe()
    m = freigeben_und_senden(j, [], b, ABEND, risk=rm, kurse_laden=k, konfig_betrieb=AN)
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


def test_probe_freigabe_jederzeit_ohne_senden_ohne_messbeginn(umgebung):
    j, rm = umgebung
    vormittag = ABEND.replace(hour=10)
    lauf(j, rm)
    rid = next(z["id"] for z in j.vorschlaege(buch="real"))
    m = freigeben_und_senden(j, [rid], None, vormittag.replace(hour=21), risk=rm, probe=True)
    assert "nichts gesendet" in m[-1] and j.vorschlaege(buch="real")[0]["status"] == "freigegeben"
    assert j.messbeginn("real") is None


def test_probe_ausserhalb_des_fensters(umgebung):
    j, rm = umgebung
    lauf(j, rm)
    rid = next(z["id"] for z in j.vorschlaege(buch="real"))
    früh = datetime(2026, 11, 2, 10, 0, tzinfo=ZoneInfo("Europe/Berlin"))
    m = freigeben_und_senden(j, [rid], None, früh, risk=rm, probe=True)
    assert "nichts gesendet" in m[-1] and j.messbeginn("real") is None


def test_messbeginn_nur_wenn_senden_freigeschaltet(umgebung):
    j, rm = umgebung
    lauf(j, rm)
    rid = next(z["id"] for z in j.vorschlaege(buch="real"))
    b = lade_konfiguration("betrieb")
    b["ibkr"] = {**b["ibkr"], "senden_freigeschaltet": False}
    m = freigeben_und_senden(j, [rid], BrokerAttrappe(sperre=True), ABEND, risk=rm, konfig_betrieb=b, kurse_laden=kurse_attrappe())
    assert any("nicht als Messbeginn" in x for x in m) and j.messbeginn("real") is None
    j2 = Journal(j.datei.parent / "zwei.sqlite")
    lauf(j2, rm)
    rid2 = next(z["id"] for z in j2.vorschlaege(buch="real"))
    b["ibkr"]["senden_freigeschaltet"] = True
    freigeben_und_senden(j2, [rid2], BrokerAttrappe(), ABEND, risk=rm, konfig_betrieb=b, kurse_laden=kurse_attrappe())
    assert j2.messbeginn("real") == "2026-11-02"
    j2.schliessen()



def _technik(e):
    return sorted((bv.vorschlag.buch, bv.vorschlag.ticker, bv.vorschlag.stueck) for bv, _ in e.vorschlaege if bv.vorschlag.buch in ("crossover", "momentum"))


def test_zweiter_lauf_am_selben_tag_gleiche_vorschlaege_alte_ersetzt(umgebung):
    j, rm = umgebung
    erst = lauf(j, rm, jetzt=ABEND.replace(hour=11))
    zweit = lauf(j, rm, jetzt=ABEND.replace(hour=19))
    assert _technik(erst) == _technik(zweit) and len(_technik(erst)) > 0
    offen = j.vorschlaege(status=("vorgeschlagen",))
    assert len(offen) == sum(1 for _, u in zweit.vorschlaege if u.frei)        # nur die des letzten Laufs sind freigebbar


def test_probe_und_echtes_journal_teilen_keinen_zustand(tmp_path):
    rm = RiskManager(lade_konfiguration("risiko"), lade_konfiguration("betrieb"), KOSTEN, tmp_path)
    probe = Journal(tmp_path / "probe" / "journal.sqlite")
    echt = Journal(tmp_path / "journal.sqlite")
    e_probe = lauf(probe, rm)
    lauf(probe, rm)                                                            # Probe mehrfach
    e_echt = lauf(echt, rm)
    assert _technik(e_probe) == _technik(e_echt)
    probe.schliessen()
    echt.schliessen()


def test_momentum_baut_beim_ersten_lauf_mitten_im_monat_auf(umgebung):
    j, rm = umgebung
    mitte = datetime(2026, 11, 17, 23, 30, tzinfo=ZoneInfo("Europe/Berlin"))
    e = lauf(j, rm, jetzt=mitte)
    assert any(bv.vorschlag.buch == "momentum" for bv, _ in e.vorschlaege)


def test_gesperrte_buecher_nicht_freigebbar(umgebung):
    """Fundamental A/B und Momentum heute gesperrt (03.11.2026): Vorschläge erscheinen, Freigabe wird abgelehnt."""
    j, rm = umgebung
    lauf(j, rm)
    fa = [z["id"] for z in j.vorschlaege(buch="fundamental_a") if z["status"] == "vorgeschlagen"]
    assert fa
    m = freigeben_und_senden(j, fa[:2], BrokerAttrappe(), ABEND, risk=rm, kurse_laden=kurse_attrappe(), konfig_betrieb=AN)
    assert sum("nicht freigebbar" in x for x in m) == 2
    assert {z["status"] for z in j.vorschlaege(buch="fundamental_a")} <= {"vorgeschlagen", "veto"}
    assert j.messbeginn("fundamental_a") is None


def test_orders_unterwegs_keine_doppelten_kaeufe(umgebung):
    """Lauf, Freigabe, Senden mit Fake-Broker, zweiter Lauf am selben Tag → keine doppelten Vorschläge; die Kasse ist
    um die Orders unterwegs reserviert (Jakob 03.11.2026)."""
    from tradingbot.betrieb.tageslauf import kasse_frei

    j, rm = umgebung
    lauf(j, rm)
    k = kurse_attrappe()
    real = [z["id"] for z in j.vorschlaege(buch="real") if z["status"] == "vorgeschlagen"]
    cross = [z["id"] for z in j.vorschlaege(buch="crossover") if z["status"] == "vorgeschlagen" and z["richtung"] > 0]
    assert real and cross, "Testdaten müssen Käufe in real und crossover erzeugen"
    b = BrokerAttrappe()
    m = freigeben_und_senden(j, real + cross, b, ABEND, risk=rm, kurse_laden=k, konfig_betrieb=AN)
    gesendet = {(a.buch, a.ticker) for a in b.gesendet}
    assert len(b.gesendet) == len(real) + len(cross), m
    kasse_vorher = {n: j.kasse(n) for n in ("real", "crossover")}
    reserve = sum(z["stueck"] * z["letzter_kurs_eur"] for z in j.unterwegs("crossover"))
    assert kasse_frei(j, "real")[0] < kasse_vorher["real"]
    assert kasse_frei(j, "crossover")[0] <= kasse_vorher["crossover"] - reserve

    e2 = lauf(j, rm, broker=BrokerAttrappe())                       # zweiter Lauf, Orders noch nicht ausgeführt
    assert e2.gestoppt is None
    neu = {(bv.vorschlag.buch, bv.vorschlag.ticker) for bv, _ in e2.vorschlaege if bv.vorschlag.richtung > 0 and bv.vorschlag.art != "fx"}
    assert not (neu & gesendet), f"doppelte Käufe: {neu & gesendet}"
    assert not any(bv.vorschlag.buch == "real" for bv, _ in e2.vorschlaege)
    assert sum(1 for z in j.vorschlaege(buch="real") if z["status"] == "gesendet") == 1
    assert sum(1 for z in j.vorschlaege(buch="crossover") if z["status"] == "gesendet") == len(cross)
    b2 = BrokerAttrappe()                                            # erneutes Senden ohne neue Freigabe sendet nichts
    freigeben_und_senden(j, [], b2, ABEND, risk=rm, kurse_laden=k, konfig_betrieb=AN)
    assert b2.gesendet == []
