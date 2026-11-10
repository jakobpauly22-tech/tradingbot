"""Lage vom 09./10.11.2026 (Jakob 10.11.2026): Fundamental A und B haben ihre US-Käufe (NYSE-Signaltag 06.11.) am 09.11.
um 22:07 gesendet, die Tausche sind ausgeführt, die Orders liegen bis zur US-Eröffnung am 10.11. bei IBKR. Ein Lauf am
10.11. vormittags, dessen Verbindung die Orders nicht sieht (andere Client-ID), darf sie weder als verfallen markieren noch
neu vorschlagen: Bücher mit Orders unterwegs gelten als aufgebaut. Keine doppelten Käufe, kein zweiter Tausch."""
from datetime import datetime
from zoneinfo import ZoneInfo

from test_tageslauf import AN, BrokerAttrappe, kurse_attrappe, lauf, umgebung  # noqa: F401
from tradingbot.betrieb.tageslauf import freigeben_und_senden

B = ZoneInfo("Europe/Berlin")
LAUF_0911 = datetime(2026, 11, 9, 21, 53, tzinfo=B)                  # Xetra 09.11., NYSE 06.11. (NYSE noch offen)
SENDEN_0911 = datetime(2026, 11, 9, 22, 7, tzinfo=B)
PROBE_1011 = datetime(2026, 11, 10, 10, 4, tzinfo=B)                  # vor der US-Eröffnung
ABEND_1011 = datetime(2026, 11, 10, 23, 30, tzinfo=B)                 # nach dem NYSE-Schluss
ALLE_AN = {**AN, "buecher": {n: {**bk, "senden_freigeschaltet": True} for n, bk in AN["buecher"].items()}}
FUNDAMENTAL = ("fundamental_a", "fundamental_b")


def _lage_09_11(j, rm):
    e = lauf(j, rm, jetzt=LAUF_0911)
    ids = [bv.vorschlag.id for bv, u in e.vorschlaege if bv.vorschlag.buch in FUNDAMENTAL and u.frei]
    assert sum(1 for i in ids if not i.endswith("EUR.USD-V")) >= 30 and any(i.endswith("EUR.USD-V") for i in ids)
    freigeben_und_senden(j, ids, BrokerAttrappe(), SENDEN_0911, risk=rm, kurse_laden=kurse_attrappe(), konfig_betrieb=ALLE_AN)
    for n in FUNDAMENTAL:                                             # Tausch sofort ausgeführt (IDEALPRO)
        fx = next(z for z in j.vorschlaege(buch=n) if z["art"] == "fx")
        j.tausch(f"t-{n}", f"{n}:{fx['id']}", "EUR", "USD", fx["stueck"], fx["stueck"] * 1.10, 1.79, "2026-11-09T21:07:21+00:00")
    gesendet = {n: [z["id"] for z in j.vorschlaege(buch=n) if z["status"] == "gesendet"] for n in FUNDAMENTAL}
    assert all(len(v) >= 15 for v in gesendet.values())
    assert all(z["signaltag"] == "2026-11-06" for n in FUNDAMENTAL for z in j.vorschlaege(buch=n) if z["status"] == "gesendet")
    return gesendet


def test_orders_unterwegs_keine_doppelten_kaeufe(umgebung):
    j, rm = umgebung
    gesendet = _lage_09_11(j, rm)
    # Probe am 10.11. vormittags: Verbindung sieht die offenen Orders nicht (offene_orders leer), keine Positionen
    e = lauf(j, rm, jetzt=PROBE_1011, broker=BrokerAttrappe())
    assert e.gestoppt is None, e.gestoppt
    assert not [bv for bv, _ in e.vorschlaege if bv.vorschlag.buch in FUNDAMENTAL]          # weder Käufe noch Tausch
    for n in FUNDAMENTAL:
        assert {z["id"] for z in j.vorschlaege(buch=n) if z["status"] == "gesendet"} == set(gesendet[n])   # nicht verfallen
        assert any(m.startswith(f"{n}: {len(gesendet[n])} Order(s) unterwegs – Buch gilt als aufgebaut") for m in e.meldungen)
    assert not any("verfallen" in m for m in e.meldungen)
    # Abend 10.11. nach dem NYSE-Schluss, Orders nicht ausgeführt und nicht mehr offen (OPG verfallen): jetzt verfallen
    e = lauf(j, rm, jetzt=ABEND_1011, broker=BrokerAttrappe())
    assert all(z["status"] == "verfallen" for n in FUNDAMENTAL for z in j.vorschlaege(buch=n) if z["id"] in gesendet[n])


def test_orders_unterwegs_auch_ohne_gateway_keine_neuen_kaeufe(umgebung):
    j, rm = umgebung
    _lage_09_11(j, rm)
    e = lauf(j, rm, jetzt=PROBE_1011)                                  # ohne Gateway
    assert not [bv for bv, _ in e.vorschlaege if bv.vorschlag.buch in FUNDAMENTAL]
