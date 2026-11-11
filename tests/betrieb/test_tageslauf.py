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
    def __init__(self, verbunden=True, positionen=(), sperre=False, fills=(), antwort=None, unbekannt=()):
        self._verbunden, self._positionen, self.sperre, self._fills, self.gesendet = verbunden, list(positionen), sperre, list(fills), []
        self.antwort, self.unbekannt = antwort, set(unbekannt)

    def verbunden(self):
        return self._verbunden and not self._getrennt

    def verbinden(self):
        if self._getrennt:
            self._getrennt = False
            return
        if not self._verbunden:
            raise ConnectionRefusedError("Gateway aus")

    _getrennt = False

    def trennen(self):
        self._getrennt = True

    def ausfuehrungen(self):
        return self._fills

    def offene_orders(self):
        return []

    def positionen(self):
        return self._positionen

    def sende(self, auftrag, refs):
        if self.sperre:
            raise SendenGesperrt("Senden ist in config/betrieb.yaml nicht freigeschaltet")
        from tradingbot.broker.basis import KontraktUnbekannt, SendeErgebnis
        if auftrag.ticker in self.unbekannt:
            raise KontraktUnbekannt(f"Kontrakt unbekannt: {auftrag.ticker} – 0 Treffer bei IBKR")
        refs.add(auftrag.order_ref)
        self.gesendet.append(auftrag)
        if self.antwort:
            return SendeErgebnis(str(len(self.gesendet) + 2), self.antwort, "200: Es wurde keine Wertpapierdefinition gefunden"
                                 if self.antwort == "abgelehnt" else "Status PendingSubmit nach 8 s")
        return str(len(self.gesendet))

    def kontrakt_aufloesen(self, ticker, art="etf", waehrung=None):
        from tradingbot.broker.basis import KontraktUnbekannt
        if ticker in self.unbekannt:
            raise KontraktUnbekannt(f"Kontrakt unbekannt: {ticker} – 0 Treffer bei IBKR")
        from types import SimpleNamespace
        return SimpleNamespace(conId=1000 + len(ticker), symbol=ticker[:-3], localSymbol=ticker[:-3], exchange="SMART", primaryExchange="IBIS2",
                               currency="EUR")

    def limit_runden(self, ticker, preis, richtung):
        from tradingbot.broker.ibkr import auf_stufe
        return auf_stufe(preis, 0.05, richtung), 0.05


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
    assert any("Gateway nicht verbunden" in x for x in m) and j.vorschlaege(buch="real")[0]["status"] == "freigegeben"
    assert j.messbeginn("real") is None                     # Messbeginn erst mit der ersten von IBKR angenommenen Order
    m = freigeben_und_senden(j, [], BrokerAttrappe(sperre=True), ABEND, risk=rm, kurse_laden=k, konfig_betrieb=AN)
    assert any("nicht freigeschaltet" in x for x in m) and j.vorschlaege(buch="real")[0]["status"] == "freigegeben"
    b = BrokerAttrappe()
    m = freigeben_und_senden(j, [], b, ABEND, risk=rm, kurse_laden=k, konfig_betrieb=AN)
    assert any("von IBKR angenommen" in x for x in m) and b.gesendet[0].order_ref == f"real:{real_id}" and b.gesendet[0].limit is not None
    assert j.vorschlaege(buch="real")[0]["status"] == "gesendet" and j.messbeginn("real") == "2026-11-02"
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
    # Abweichung zum Eröffnungskurs als Paper-Simulation gekennzeichnet (Jakob 11.11.2026)
    assert any("Eröffnung" in m and "Abweichung" in m and "Paper-Simulation" in m for m in e.meldungen)


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


def test_abgleichzeile_und_sicherung_nach_senden(umgebung, tmp_path, monkeypatch):
    """Abgleichzeile in jedem Lauf im Protokoll, auch bei leerem Bestand; Sicherung direkt nach Freigabe/Senden (03.11.2026)."""
    j, rm = umgebung
    e = lauf(j, rm, broker=BrokerAttrappe())
    assert any(m.startswith("Abgleich: Bestände aller Bücher stimmen") and "ohne Bestand" in m for m in e.meldungen)
    e = lauf(j, rm)
    assert any(m.startswith("Abgleich: nicht möglich") for m in e.meldungen)
    monkeypatch.setenv("JOURNAL_BACKUP_DIR", str(tmp_path / "sicherung"))
    rid = next(z["id"] for z in j.vorschlaege(buch="real") if z["status"] == "vorgeschlagen")
    b = BrokerAttrappe()
    m = freigeben_und_senden(j, [rid], b, ABEND, risk=rm, kurse_laden=kurse_attrappe(), konfig_betrieb=AN)
    assert b.gesendet and any(x.startswith("Abgleich vor dem Senden") for x in m)
    assert m[-1].startswith("Journal gesichert nach Freigabe/Senden")
    kopie = list((tmp_path / "sicherung").glob("*.sqlite"))
    assert len(kopie) == 1
    import sqlite3
    with sqlite3.connect(kopie[0]) as k:                     # die Kopie enthält den Status „gesendet“
        assert k.execute("SELECT status FROM vorschlaege WHERE id=?", (rid,)).fetchone()[0] == "gesendet"


def test_ablehnung_durch_ibkr(umgebung):
    """IBKR lehnt ab (03.11.2026, Fehler 200): Status „abgelehnt“ mit Text, keine Reservierung, kein Messbeginn; der
    nächste Lauf darf denselben Kauf neu vorschlagen."""
    from tradingbot.betrieb.tageslauf import kasse_frei

    j, rm = umgebung
    lauf(j, rm)
    rid = next(z["id"] for z in j.vorschlaege(buch="real") if z["status"] == "vorgeschlagen")
    m = freigeben_und_senden(j, [rid], BrokerAttrappe(antwort="abgelehnt"), ABEND, risk=rm, kurse_laden=kurse_attrappe(), konfig_betrieb=AN)
    z = j.vorschlaege(buch="real")[0]
    assert z["status"] == "abgelehnt" and "Wertpapierdefinition" in z["meldung"]
    assert any("ABGELEHNT" in x for x in m) and not any("angenommen" in x for x in m)
    assert j.unterwegs("real") == [] and kasse_frei(j, "real")[0] == j.kasse("real")
    assert j.messbeginn("real") is None
    e2 = lauf(j, rm)
    assert any(bv.vorschlag.id == rid for bv, _ in e2.vorschlaege) and j.vorschlaege(buch="real")[0]["status"] == "vorgeschlagen"


def test_unbestaetigt_reserviert_und_angenommen_setzt_messbeginn(umgebung):
    j, rm = umgebung
    lauf(j, rm)
    cross = [z["id"] for z in j.vorschlaege(buch="crossover") if z["status"] == "vorgeschlagen" and z["richtung"] > 0]
    freigeben_und_senden(j, cross[:1], BrokerAttrappe(antwort="unbestaetigt"), ABEND, risk=rm, kurse_laden=kurse_attrappe(), konfig_betrieb=AN)
    assert j.vorschlaege(buch="crossover")[0]["status"] in ("unbestaetigt",) or any(z["status"] == "unbestaetigt" for z in j.vorschlaege(buch="crossover"))
    assert len(j.unterwegs("crossover")) == 1 and j.messbeginn("crossover") is None
    rid = next(z["id"] for z in j.vorschlaege(buch="real") if z["status"] == "vorgeschlagen")
    freigeben_und_senden(j, [rid], BrokerAttrappe(), ABEND, risk=rm, kurse_laden=kurse_attrappe(), konfig_betrieb=AN)
    assert j.messbeginn("real") == "2026-11-02"                 # erst mit der angenommenen Order


def test_kontrakt_unbekannt_veto_beim_senden_und_im_lauf(umgebung):
    j, rm = umgebung
    lauf(j, rm)
    rid = next(z["id"] for z in j.vorschlaege(buch="real") if z["status"] == "vorgeschlagen")
    b = BrokerAttrappe(unbekannt={"SPYI.DE"})
    m = freigeben_und_senden(j, [rid], b, ABEND, risk=rm, kurse_laden=kurse_attrappe(), konfig_betrieb=AN)
    assert b.gesendet == [] and any("Kontrakt unbekannt" in x for x in m)
    assert j.vorschlaege(buch="real")[0]["status"] == "veto" and j.messbeginn("real") is None
    # im Tageslauf mit Gateway: conId in den Details, unbekannte Kontrakte als Veto
    e = lauf(j, rm, broker=BrokerAttrappe(unbekannt={"SPYI.DE"}))
    real = [(bv, u) for bv, u in e.vorschlaege if bv.vorschlag.buch == "real"]
    assert real and not real[0][1].frei and any("Kontrakt unbekannt" in g for g in real[0][1].gruende)
    cross = [(bv, u) for bv, u in e.vorschlaege if bv.vorschlag.buch == "crossover" and u.frei]
    assert cross and all("IBKR-Kontrakt: conId" in bv.details for bv, _ in cross)


def test_nachtraeglich_abgelehnt_loest_reservierung_und_messbeginn(umgebung):
    """Korrektur vom 03.11.2026: als gesendet verbuchte, nie angenommene Orders → abgelehnt; Reservierung und Messbeginn weg."""
    from tradingbot.betrieb.tageslauf import kasse_frei

    j, rm = umgebung
    lauf(j, rm)
    ids = [z["id"] for z in j.vorschlaege() if z["status"] == "vorgeschlagen" and z["buch"] in ("real", "crossover") and z["richtung"] > 0]
    freigeben_und_senden(j, ids, BrokerAttrappe(), ABEND, risk=rm, kurse_laden=kurse_attrappe(), konfig_betrieb=AN)
    assert j.messbeginn("real") and j.messbeginn("crossover") and j.unterwegs("crossover")
    with pytest.raises(ValueError):
        j.nachtraeglich_abgelehnt(["gibt-es-nicht"], "x")
    assert j.nachtraeglich_abgelehnt(ids, "Fehler 200: keine Wertpapierdefinition (conId 0)") == ["crossover", "real"]
    assert j.unterwegs() == [] and kasse_frei(j, "crossover")[0] == j.kasse("crossover")
    assert j.messbeginn("real") is None and j.messbeginn("crossover") is None
    assert all(z["status"] == "abgelehnt" and "conId 0" in z["meldung"] for z in j.vorschlaege() if z["id"] in ids)


def test_tageslauf_rundet_limit_auf_kursstufe_und_zeigt_routing(umgebung):
    j, rm = umgebung
    e = lauf(j, rm, broker=BrokerAttrappe())
    frei = [(bv, u) for bv, u in e.vorschlaege if bv.vorschlag.buch in ("real", "crossover") and u.frei and bv.vorschlag.richtung > 0]
    assert frei
    for bv, _ in frei:
        assert "Routing SMART/IBIS2" in bv.details and "Kursstufe 0.05" in bv.details
        assert abs(bv.limit_order / 0.05 - round(bv.limit_order / 0.05)) < 1e-6 and bv.vorschlag.limit == bv.limit_order
        z = next(x for x in j.vorschlaege() if x["id"] == bv.vorschlag.id)
        assert z["limit_preis"] == bv.limit_order and z["limit_preis"] <= z["letzter_kurs_eur"] * 1.02 + 1e-9


def test_ausfuehrungsplatz_im_journal(umgebung):
    j, rm = umgebung
    lauf(j, rm)
    z = j.vorschlaege(buch="real")[0]
    assert j.ausfuehrung("x9", f"real:{z['id']}", "SPYI.DE", 1, 2, 11.8, 1.25, "2026-11-04T09:00", boerse="IBIS2")
    assert j.db.execute("SELECT boerse FROM ausfuehrungen WHERE exec_id='x9'").fetchone()[0] == "IBIS2"


def test_orders_unterwegs_halbieren_nicht_die_stueckzahl(umgebung):
    """Korrektur 03.11.2026: Reservierte Kasse gehört zum Buchwert. Nach Ablehnung einzelner Orders erscheinen die
    abgelehnten Käufe im nächsten Lauf mit derselben Stückzahl wie zuvor, die angenommenen bleiben gesperrt."""
    j, rm = umgebung
    e1 = lauf(j, rm)
    kaeufe = {bv.vorschlag.ticker: bv.vorschlag.stueck for bv, u in e1.vorschlaege if bv.vorschlag.buch == "crossover" and u.frei
              and bv.vorschlag.richtung > 0}
    assert len(kaeufe) >= 2
    ids = [z["id"] for z in j.vorschlaege(buch="crossover") if z["status"] == "vorgeschlagen" and z["richtung"] > 0]
    angenommen, abgelehnt = ids[:1], ids[1:]
    freigeben_und_senden(j, angenommen, BrokerAttrappe(), ABEND, risk=rm, kurse_laden=kurse_attrappe(), konfig_betrieb=AN)
    freigeben_und_senden(j, abgelehnt, BrokerAttrappe(antwort="abgelehnt"), ABEND, risk=rm, kurse_laden=kurse_attrappe(), konfig_betrieb=AN)
    e2 = lauf(j, rm)
    neu = {bv.vorschlag.ticker: bv.vorschlag.stueck for bv, u in e2.vorschlaege if bv.vorschlag.buch == "crossover" and bv.vorschlag.richtung > 0}
    gesperrt = {z["ticker"] for z in j.unterwegs("crossover")}
    assert gesperrt and not (gesperrt & set(neu))
    abgelehnte_titel = {z["ticker"] for z in j.vorschlaege(buch="crossover") if z["id"] in abgelehnt} | {
        t for t in kaeufe if t not in gesperrt}
    verglichen = [t for t in abgelehnte_titel if t in neu]
    assert verglichen
    for t in verglichen:
        assert neu[t] == kaeufe[t], (t, neu[t], kaeufe[t])


def test_gebuehr_ibkr_gebucht_modell_daneben_und_trennen(umgebung):
    """Entscheidung 04.11.2026: Kasse bucht die IBKR-Gebühr (Paper Festpreis 3 €), Modellgebühr (Tiered 1,25 €) daneben,
    Minimum einmal je Order; Buchwert zweifach im Protokoll; Verbindung nach Freigabe/Senden getrennt."""
    j, rm = umgebung
    lauf(j, rm)
    z = next(x for x in j.vorschlaege(buch="real") if x["status"] == "vorgeschlagen")
    b = BrokerAttrappe()
    m = freigeben_und_senden(j, [z["id"]], b, ABEND, risk=rm, kurse_laden=kurse_attrappe(), konfig_betrieb=AN)
    assert "Verbindung zum Gateway getrennt" in m and not b.verbunden()
    fills = [{"exec_id": "e1", "order_ref": f"real:{z['id']}", "ticker": "SPYI.DE", "richtung": 1, "stueck": 20, "preis": 11.62,
              "waehrung": "EUR", "gebuehr": 3.0, "gebuehr_waehrung": "EUR", "zeit": "2026-11-04 08:00:05+00:00", "boerse": "GETTEX2"},
             {"exec_id": "e2", "order_ref": f"real:{z['id']}", "ticker": "SPYI.DE", "richtung": 1, "stueck": 22, "preis": 11.62,
              "waehrung": "EUR", "gebuehr": None, "gebuehr_waehrung": "EUR", "zeit": "2026-11-04 08:00:05+00:00", "boerse": "GETTEX2"}]
    naechster = datetime(2026, 11, 4, 19, 0, tzinfo=ZoneInfo("Europe/Berlin"))
    e = lauf(j, rm, jetzt=naechster, broker=BrokerAttrappe(fills=fills, positionen=[Position("DU1", "SPYI.DE", 42, 11.62)]))
    zeilen = [x for x in e.meldungen if x.startswith("Ausführung real")]
    assert len(zeilen) == 2 and "Gebühr IBKR 3.00 EUR (gebucht), Modell 1.25 €, Abweichung IBKR − Modell +1.75 €" in zeilen[0]
    assert "am GETTEX2 um 2026-11-04 08:00:05+00:00" in zeilen[0] and "Eröffnung" in zeilen[0]
    assert "nicht gemeldet – vorläufig Modell 0.00 € gebucht" in zeilen[1]           # Minimum nur einmal je Order
    assert abs(j.kasse("real") - (500 - 42 * 11.62 - 3.0)) < 1e-6
    assert abs(j.kasse_modell("real") - (500 - 42 * 11.62 - 1.25)) < 1e-6
    assert any(x.startswith("real: Buchwert wie gebucht (Paper, Festpreis)") and "mit Modellgebühr (Tiered" in x for x in e.meldungen)
    w = j.db.execute("SELECT wert, wert_modell FROM buchwerte WHERE buch='real' AND tag='2026-11-04'").fetchone()
    assert abs((w["wert_modell"] - w["wert"]) - 1.75) < 1e-6
    r = j.db.execute("SELECT eroeffnung, boerse FROM ausfuehrungen WHERE exec_id='e1'").fetchone()
    assert r["eroeffnung"] is not None and r["boerse"] == "GETTEX2"


class KontoAttrappe(BrokerAttrappe):
    def __init__(self, kasse, **kw):
        super().__init__(**kw)
        self._kasse = kasse

    def kasse_je_waehrung(self):
        return dict(self._kasse)


def test_kassenabgleich(umgebung):
    from tradingbot.betrieb.tageslauf import kassenabgleich
    j, rm = umgebung
    lauf(j, rm)
    b = lade_konfiguration("betrieb")
    diff, text = kassenabgleich(j, list(b["buecher"]), KontoAttrappe({"EUR": 1_000_000.0}), b)
    assert diff == [] and "erstmals festgehalten" in text and j.zustand("_konto")["kassenbasis"]["EUR"] == 1_000_000.0
    diff, text = kassenabgleich(j, list(b["buecher"]), KontoAttrappe({"EUR": 1_000_000.03}), b)
    assert diff == [] and "stimmt" in text                                         # innerhalb der Toleranz
    diff, _ = kassenabgleich(j, list(b["buecher"]), KontoAttrappe({"EUR": 999_970.0}), b)
    assert diff and "Kasse EUR" in diff[0] and "-30.00" in diff[0]
    # im Tageslauf stoppt eine Kassenabweichung über 10 € wie eine Bestandsabweichung
    e = lauf(j, rm, broker=KontoAttrappe({"EUR": 999_970.0}))
    assert e.gestoppt and "Kasse EUR" in e.gestoppt


def test_nachkauf_technik_momentum_nach_ablehnung(umgebung):
    """Restfall (04.11.2026): Momentum-Käufe, teils angenommen, teils abgelehnt → am nächsten Abend werden die abgelehnten
    neu vorgeschlagen, solange 12−1 > 0 (auch ohne Monatsprüfung)."""
    j, rm = umgebung
    lauf(j, rm)
    ids = [z["id"] for z in j.vorschlaege(buch="momentum") if z["status"] == "vorgeschlagen" and z["richtung"] > 0]
    assert len(ids) >= 2
    alle = dict(AN["buecher"])
    an = {**AN, "buecher": {n: {**bk, "senden_freigeschaltet": True} for n, bk in alle.items()}}
    freigeben_und_senden(j, ids[:1], BrokerAttrappe(), ABEND, risk=rm, kurse_laden=kurse_attrappe(), konfig_betrieb=an)
    freigeben_und_senden(j, ids[1:], BrokerAttrappe(antwort="abgelehnt"), ABEND, risk=rm, kurse_laden=kurse_attrappe(), konfig_betrieb=an)
    abgelehnt = {z["ticker"] for z in j.vorschlaege(buch="momentum") if z["status"] == "abgelehnt"}
    naechster = datetime(2026, 11, 3, 23, 30, tzinfo=ZoneInfo("Europe/Berlin"))
    e = lauf(j, rm, jetzt=naechster)
    neu = {bv.vorschlag.ticker for bv, _ in e.vorschlaege if bv.vorschlag.buch == "momentum" and bv.vorschlag.richtung > 0}
    assert abgelehnt and abgelehnt <= neu
    assert not (neu & {z["ticker"] for z in j.unterwegs("momentum")})


def test_nachkauf_fundamental_bis_zum_stichtag(umgebung):
    j, rm = umgebung
    lauf(j, rm)
    ids = [z["id"] for z in j.vorschlaege(buch="fundamental_a") if z["status"] == "vorgeschlagen" and z["richtung"] > 0 and z["art"] != "fx"]
    an = {**AN, "buecher": {n: {**bk, "senden_freigeschaltet": True} for n, bk in AN["buecher"].items()}}
    fx = [z["id"] for z in j.vorschlaege(buch="fundamental_a") if z["art"] == "fx" and z["status"] == "vorgeschlagen"]
    m = freigeben_und_senden(j, fx + ids[:5], BrokerAttrappe(), ABEND, risk=rm, kurse_laden=kurse_attrappe(), konfig_betrieb=an)
    j.tausch("t1", f"fundamental_a:{fx[0]}", "EUR", "USD", 9000.0, 9900.0, 2.0, "2026-11-02T23:00")   # Tausch ausgeführt
    freigeben_und_senden(j, ids[5:7], BrokerAttrappe(antwort="abgelehnt"), ABEND, risk=rm, kurse_laden=kurse_attrappe(), konfig_betrieb=an)
    abgelehnt = {z["ticker"] for z in j.vorschlaege(buch="fundamental_a") if z["status"] == "abgelehnt"}
    assert len(abgelehnt) == 2 and "ziel" in j.zustand("fundamental_a")
    naechster = datetime(2026, 11, 3, 23, 30, tzinfo=ZoneInfo("Europe/Berlin"))       # kein Quartalsstichtag
    # solange Orders unterwegs sind, gilt das Buch als aufgebaut (Jakob 10.11.2026): kein Nachkauf
    e = lauf(j, rm, jetzt=naechster)
    assert not any(bv.vorschlag.buch == "fundamental_a" for bv, _ in e.vorschlaege)
    # die 5 angenommenen Käufe sind ausgeführt und werden eingelesen → Nachkauf der 2 abgelehnten
    gesendet = [z for z in j.vorschlaege(buch="fundamental_a") if z["status"] == "gesendet"]
    fills = [{"exec_id": f"f{i}", "order_ref": f"fundamental_a:{z['id']}", "ticker": z["ticker"], "richtung": 1, "stueck": z["stueck"],
              "preis": 80.0, "waehrung": "USD", "gebuehr": 1.0, "gebuehr_waehrung": "USD", "zeit": "2026-11-03T14:30:00+00:00"}
             for i, z in enumerate(gesendet)]
    positionen = [Position("DU1", z["ticker"], z["stueck"], 80.2) for z in gesendet]
    e = lauf(j, rm, jetzt=naechster, broker=BrokerAttrappe(fills=fills, positionen=positionen))
    assert e.gestoppt is None, e.gestoppt
    neu = {bv.vorschlag.ticker for bv, _ in e.vorschlaege if bv.vorschlag.buch == "fundamental_a" and bv.vorschlag.art != "fx"}
    assert neu == abgelehnt
    assert any("fundamental_a: Nachkauf 2 Titel" in m for m in e.meldungen)

def test_technikbuch_ohne_kauf_baut_am_naechsten_tag_wieder_auf(umgebung):
    """Momentum war am 03.11. gesperrt, der Zustand galt trotzdem als aufgebaut → am 04.11. keine Vorschläge bis zur
    Monatsprüfung. Korrektur 04.11.2026: ohne Bestand und ohne Order unterwegs Aufbau wie beim ersten Lauf."""
    j, rm = umgebung
    e1 = lauf(j, rm)
    erst = {bv.vorschlag.ticker for bv, _ in e1.vorschlaege if bv.vorschlag.buch == "momentum" and bv.vorschlag.richtung > 0}
    assert erst
    naechster = datetime(2026, 11, 3, 23, 30, tzinfo=ZoneInfo("Europe/Berlin"))      # kein erster Handelstag des Monats
    e2 = lauf(j, rm, jetzt=naechster)
    zweit = {bv.vorschlag.ticker for bv, _ in e2.vorschlaege if bv.vorschlag.buch == "momentum" and bv.vorschlag.richtung > 0}
    assert zweit == erst and any("Aufbau wie beim ersten Lauf" in m for m in e2.meldungen)


def test_nicht_notierte_titel_werden_nicht_vorgeschlagen(umgebung):
    """KVUE-Fall (04.11.2026): Titel mit veraltetem Kurs oder ohne IBKR-Kontrakt fallen vor der Rangliste heraus."""
    from tradingbot.betrieb.tageslauf import nicht_handelbare_entfernen
    j, rm = umgebung
    bew, _, _ = bewertung_attrappe(pd.Timestamp("2026-11-02"))
    bew.loc[0, "kursdatum"] = pd.Timestamp("2026-10-30")
    bew.loc[1, "symbol"] = "KVUE"                                    # steht in config/kontrakte.yaml unter nicht_aufloesbar
    rest, meld = nicht_handelbare_entfernen(bew, pd.Timestamp("2026-11-09"))
    assert "US0" not in set(rest["symbol"]) and "KVUE" not in set(rest["symbol"]) and len(rest) == len(bew) - 2
    assert any("US0" in m and "letzter Kurs 30.10.2026" in m for m in meld) and any("KVUE" in m and "IBKR" in m for m in meld)

    def bewertung_mit_alt(tag):
        b, s, m = bewertung_attrappe(tag)
        b.loc[0, "kursdatum"] = pd.Timestamp(tag) - pd.Timedelta(days=20)
        return b, s, m
    e = tageslauf(ABEND, j, kurse_laden=kurse_attrappe(), fundamental_bewertung=bewertung_mit_alt, risk=rm, sichern=False)
    assert not any(bv.vorschlag.ticker == "US0" for bv, _ in e.vorschlaege)


def test_kassenbasis_buchung_ohne_buchbezug(umgebung):
    """Zinsen/Kontogebühren bis 10 € gehen in die Kassenbasis (protokolliert), darüber stoppt der Abgleich (04.11.2026)."""
    from tradingbot.betrieb.tageslauf import kassenabgleich
    j, rm = umgebung
    lauf(j, rm)
    b = lade_konfiguration("betrieb")
    kassenabgleich(j, list(b["buecher"]), KontoAttrappe({"EUR": 1_000_000.0}), b)
    diff, text = kassenabgleich(j, list(b["buecher"]), KontoAttrappe({"EUR": 1_000_004.20}), b)       # Zinsgutschrift
    assert diff == [] and "Buchung ohne Buchbezug" in text and "+4.20" in text
    assert abs(j.zustand("_konto")["kassenbasis"]["EUR"] - 1_000_004.20) < 1e-9
    assert j.zustand("_konto")["buchungen_ohne_buchbezug"][0]["betraege"] == ["EUR +4.20"]
    diff, _ = kassenabgleich(j, list(b["buecher"]), KontoAttrappe({"EUR": 1_000_004.20 - 12.0}), b)  # 12 € unerklärt
    assert diff and "unerklärte Buchung" in diff[0]


def test_zeitfenster_hinweis():
    from types import SimpleNamespace as N
    from tradingbot.betrieb.tageslauf import zeitfenster_hinweis
    us = N(art="aktie", ticker="DPZ", richtung=1)
    fx = N(art="fx", ticker="EUR.USD", richtung=-1)
    etf = N(art="etf", ticker="EUNM.DE", richtung=1)
    assert len(zeitfenster_hinweis(datetime(2026, 11, 4, 21, 30), [us, fx])) == 1             # US-Handel offen
    assert zeitfenster_hinweis(datetime(2026, 11, 4, 22, 5), [us, fx]) == []
    assert zeitfenster_hinweis(datetime(2026, 11, 4, 22, 50), [us, fx]) == []
    assert "FX-Tagesschluss" in zeitfenster_hinweis(datetime(2026, 11, 4, 23, 0), [fx])[0]
    assert zeitfenster_hinweis(datetime(2026, 11, 4, 21, 0), [etf]) == []                      # Xetra-ETFs ohne Hinweis


def test_hinweis_bei_freigabe_und_im_lauf(umgebung):
    j, rm = umgebung
    e = lauf(j, rm)
    assert any(m.startswith("Zeitpunkt: US-Käufe (Limit-On-Open)") for m in e.meldungen)
    fx = [z["id"] for z in j.vorschlaege(buch="fundamental_a") if z["art"] == "fx" and z["status"] == "vorgeschlagen"]
    an = {**AN, "buecher": {n: {**bk, "senden_freigeschaltet": True} for n, bk in AN["buecher"].items()}}
    m = freigeben_und_senden(j, fx, BrokerAttrappe(), ABEND.replace(hour=23, minute=0), risk=rm, kurse_laden=kurse_attrappe(), konfig_betrieb=an)
    assert any("FX-Tagesschluss" in x for x in m)


def test_wiederholter_signaltag_nach_ausfuehrung_keine_restkasse_momentum(umgebung):
    """Probelauf 10.11.2026 11:06 (Signaltag noch 09.11.): nach Senden und Ausführung der Aufbau-Käufe startete der erneute
    Lauf vom Stand VOR dem Signaltag und legte Restkasse an („KAUF 15 × EUNK“). Im Backtest bleibt Restkasse bis zur nächsten
    Monatsprüfung Kasse. Korrektur 11.11.2026: nach dem Senden startet ein erneuter Lauf vom Stand nach dem Tag."""
    j, rm = umgebung
    mitte = datetime(2026, 11, 17, 23, 30, tzinfo=ZoneInfo("Europe/Berlin"))       # Aufbau mitten im Monat
    lauf(j, rm, jetzt=mitte)
    ids = [z["id"] for z in j.vorschlaege(buch="momentum") if z["status"] == "vorgeschlagen" and z["richtung"] > 0]
    assert ids
    an = {**AN, "buecher": {n: {**bk, "senden_freigeschaltet": True} for n, bk in AN["buecher"].items()}}
    freigeben_und_senden(j, ids, BrokerAttrappe(), mitte, risk=rm, kurse_laden=kurse_attrappe(), konfig_betrieb=an)
    gesendet = [z for z in j.vorschlaege(buch="momentum") if z["status"] == "gesendet"]
    assert gesendet and j.signaltag_gesendet("momentum", "2026-11-17")
    fills = [{"exec_id": f"m{i}", "order_ref": f"momentum:{z['id']}", "ticker": z["ticker"], "richtung": 1, "stueck": z["stueck"],
              "preis": z["limit_preis"] * 0.98, "waehrung": "EUR", "gebuehr": 3.0, "gebuehr_waehrung": "EUR", "zeit": "2026-11-18T09:00"}
             for i, z in enumerate(gesendet)]
    positionen = [Position("DU1", z["ticker"], z["stueck"], 1.0) for z in gesendet]
    vormittag = datetime(2026, 11, 18, 11, 6, tzinfo=ZoneInfo("Europe/Berlin"))   # Xetra noch offen: Signaltag 17.11.
    e = lauf(j, rm, jetzt=vormittag, broker=BrokerAttrappe(fills=fills, positionen=positionen))
    assert e.gestoppt is None, e.gestoppt
    assert j.bestand("momentum") and j.kasse("momentum") > 0.2 * 10_000          # Restkasse vorhanden (1-%-Regel, ganze Stücke)
    assert not [bv for bv, _ in e.vorschlaege if bv.vorschlag.buch == "momentum" and bv.vorschlag.richtung > 0]
    # vor dem Senden bleibt der erneute Lauf am selben Signaltag wiederholbar (Stand vor dem Tag)
    j2 = Journal(j.datei.parent / "zwei.sqlite")
    e1 = lauf(j2, rm, jetzt=mitte)
    e2 = lauf(j2, rm, jetzt=mitte)
    erst = sorted(bv.vorschlag.ticker for bv, _ in e1.vorschlaege if bv.vorschlag.buch == "momentum")
    assert erst and erst == sorted(bv.vorschlag.ticker for bv, _ in e2.vorschlaege if bv.vorschlag.buch == "momentum")
    j2.schliessen()
