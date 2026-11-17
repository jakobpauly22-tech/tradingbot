"""Befund 17 (Plan freigegeben von Jakob 16.11.2026): Realbuch und regime haben am selben Abend je eine Order in SPYI.DE
gesendet, der Folgeabend wird verpasst, nur eine Order wird ausgeführt. Deckt der Flex-Bericht den Handelstag ab und erklären
die belegten Ausführungen die Abweichung genau, wird die belegte gebucht und die andere gilt als verfallen; sonst Stopp wie
bisher."""
from datetime import date

from test_regimebuch import MIT_REGIME, Makro, abend, daten, kursreihe  # noqa: F401
from test_tageslauf import BrokerAttrappe, kurse_attrappe, lauf, umgebung  # noqa: F401
from tradingbot.betrieb.nachtrag import flex_datum
from tradingbot.betrieb.tageslauf import freigeben_und_senden
from tradingbot.broker.basis import Position


def _zwei_orders(j, rm):
    """16.11.: real und regime kaufen SPYI.DE, beide gesendet (gelten für den 17.11.)."""
    c, m = kursreihe("2026-12-02"), Makro()
    e = lauf(j, rm, jetzt=abend(2026, 11, 16), regime_daten=daten(c, m))
    ids = [bv.vorschlag.id for bv, u in e.vorschlaege if bv.vorschlag.buch in ("real", "regime") and u.frei]
    freigeben_und_senden(j, ids, BrokerAttrappe(), abend(2026, 11, 16), risk=rm, kurse_laden=kurse_attrappe(), konfig_betrieb=MIT_REGIME)
    real, reg = j.vorschlaege(buch="real")[0], j.vorschlaege(buch="regime")[0]
    assert real["status"] == reg["status"] == "gesendet"
    return real, reg, (c, m)


def _flex(real, von="20261101", bis="20261117"):
    zeilen = [{"orderReference": f"real:{real['id']}", "ibExecID": "0001f.flex.01", "assetCategory": "STK", "symbol": "SPYI", "conid": "0",
               "currency": "EUR", "buySell": "BUY", "quantity": str(real["stueck"]), "tradePrice": "11.70", "ibCommission": "-3",
               "ibCommissionCurrency": "EUR", "dateTime": "20261117;090007", "exchange": "IBIS2"}]

    def laden():
        return zeilen, "IBKR Flex-Abfrage 1, erstellt 18.11."
    laden.zeitraum = lambda: (flex_datum(von), flex_datum(bis))
    return laden


def test_nur_eine_ausgefuehrt_flex_deckt_den_tag_belegte_gebucht_andere_verfallen(umgebung):
    j, rm = umgebung
    real, reg, (c, m) = _zwei_orders(j, rm)
    pos = [Position("DU1", "SPYI.DE", real["stueck"], 11.70)]
    e = lauf(j, rm, jetzt=abend(2026, 11, 18), regime_daten=daten(c, m), broker=BrokerAttrappe(positionen=pos), flex=_flex(real))
    assert e.gestoppt is None, e.gestoppt
    assert j.bestand("real") == {"SPYI.DE": real["stueck"]} and j.bestand("regime") == {}
    status = {z["id"]: z["status"] for z in j.vorschlaege()}
    assert status[real["id"]] == "ausgefuehrt" and status[reg["id"]] == "verfallen"
    assert any("laut Flex-Bericht 01.11.2026–17.11.2026 am 17.11.2026 nicht ausgeführt" in x for x in e.meldungen)
    assert j.db.execute("SELECT COUNT(*) FROM ereignisse WHERE art='verfallen' AND text LIKE '%Befund 17%'").fetchone()[0] == 1


def test_flex_deckt_den_tag_nicht_stopp_wie_bisher(umgebung):
    j, rm = umgebung
    real, reg, (c, m) = _zwei_orders(j, rm)
    pos = [Position("DU1", "SPYI.DE", real["stueck"], 11.70)]
    e = lauf(j, rm, jetzt=abend(2026, 11, 18), regime_daten=daten(c, m), broker=BrokerAttrappe(positionen=pos),
             flex=_flex(real, bis="20261116"))
    assert e.gestoppt and "ohne Beleg" in e.gestoppt and "mehrere Orders unterwegs" in e.gestoppt
    assert j.bestand("real") == {} and {z["status"] for z in j.vorschlaege(buch="regime")} == {"gesendet"}


def test_abweichung_nicht_erklaert_stopp_wie_bisher(umgebung):
    j, rm = umgebung
    real, reg, (c, m) = _zwei_orders(j, rm)
    pos = [Position("DU1", "SPYI.DE", real["stueck"] + 1, 11.70)]                 # ein Stück mehr, als Flex belegt
    e = lauf(j, rm, jetzt=abend(2026, 11, 18), regime_daten=daten(c, m), broker=BrokerAttrappe(positionen=pos), flex=_flex(real))
    assert e.gestoppt and "ohne Beleg" in e.gestoppt
    assert j.bestand("real") == {} and {z["status"] for z in j.vorschlaege(buch="regime")} == {"gesendet"}


def test_flex_datum():
    assert flex_datum("20261116") == date(2026, 11, 16) == flex_datum("2026-11-16")
    assert flex_datum(None) is None and flex_datum("2026") is None and flex_datum("20261332") is None
