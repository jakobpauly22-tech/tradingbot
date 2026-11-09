"""Verpasste Abende (Jakob 09.11.2026): Ausführungen außerhalb des API-Zeitfensters werden erkannt und mit Beleg
nachgetragen (Flex, sonst Position mit Einstand); ohne Beleg stoppt der Tageslauf, nichts wird gebucht oder verfallen."""
import copy
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from test_tageslauf import ABEND, AN, BrokerAttrappe, KontoAttrappe, kurse_attrappe, lauf, umgebung  # noqa: F401
from tradingbot.betrieb.nachtrag import flex_ausfuehrungen, naechste_sitzung
from tradingbot.betrieb.tageslauf import freigeben_und_senden
from tradingbot.broker.basis import Position
from tradingbot.konfiguration import lade_konfiguration

SPAETER = datetime(2026, 11, 5, 19, 30, tzinfo=ZoneInfo("Europe/Berlin"))   # Abende 03. und 04.11. verpasst
HANDELSTAG = date(2026, 11, 3)                                                # Order vom 02.11. abends gilt am 03.11.


def _konfig(gebuehr=3.0):
    k = {n: lade_konfiguration(n) for n in ("betrieb", "technik", "fundamental", "backtest")}
    k["betrieb"] = copy.deepcopy(k["betrieb"])
    k["betrieb"]["nachtrag"] = {"gebuehr_je_order": gebuehr}
    return k


def _gesendet(j, rm):
    """Realbuch: Tageslauf am 02.11., Freigabe und Senden; die Order steht danach als „gesendet“ im Journal."""
    lauf(j, rm)
    z = next(x for x in j.vorschlaege(buch="real") if x["status"] == "vorgeschlagen")
    freigeben_und_senden(j, [z["id"]], BrokerAttrappe(), ABEND, risk=rm, kurse_laden=kurse_attrappe(), konfig_betrieb=AN)
    z = j.vorschlaege(buch="real")[0]
    assert z["status"] == "gesendet"
    return z


def _tagespreis():
    k = kurse_attrappe()("SPYI.DE", HANDELSTAG, "etf")
    return float(k.loc[str(HANDELSTAG), "open"])


def test_naechste_sitzung():
    assert naechste_sitzung("xetra", "2026-11-03") == date(2026, 11, 4)
    assert naechste_sitzung("xetra", "2026-11-06") == date(2026, 11, 9)          # Freitag → Montag
    assert naechste_sitzung("xetra", "2026-12-23") == date(2026, 12, 28)         # Heiligabend und Feiertage


def test_verpasster_abend_nachtrag_aus_position(umgebung):
    j, rm = umgebung
    z = _gesendet(j, rm)
    preis = _tagespreis()
    einstand = (preis * z["stueck"] + 3.0) / z["stueck"]                          # IBKR: Einstand inklusive Gebühr
    broker = KontoAttrappe({"EUR": 1_000_000.0 - preis * z["stueck"] - 3.0},
                           positionen=[Position("DU1", "SPYI.DE", z["stueck"], einstand)])   # keine Fills mehr über die API
    e = lauf(j, rm, jetzt=SPAETER, broker=broker, konfig=_konfig(), flex=None)
    assert e.gestoppt is None, e.gestoppt
    assert any("außerhalb des API-Zeitfensters vermutet" in m for m in e.meldungen)
    assert any(m.startswith("Nachtrag real:") and "IBKR Position (Einstand)" in m for m in e.meldungen)
    a = j.db.execute("SELECT * FROM ausfuehrungen WHERE buch='real'").fetchone()
    assert a["stueck"] == z["stueck"] and abs(a["preis"] - preis) < 1e-9 and a["gebuehr_eur"] == 3.0
    assert a["quelle"].startswith("IBKR Position (Einstand)") and a["zeit"] == "2026-11-03" and a["boerse"] is None
    assert j.vorschlaege(buch="real")[0]["status"] == "ausgefuehrt"
    assert j.db.execute("SELECT COUNT(*) FROM ereignisse WHERE art='nachtrag' AND buch='real'").fetchone()[0] == 1
    assert any("Abgleich: Bestände aller Bücher stimmen" in m for m in e.meldungen)
    assert abs(j.kasse("real") - (500 - preis * z["stueck"] - 3.0)) < 1e-6
    # Kassenbasis ohne den nachgetragenen Kauf: Paper-Startguthaben
    assert abs(j.zustand("_konto")["kassenbasis"]["EUR"] - 1_000_000.0) < 1e-6
    # nächster Lauf: kein zweiter Nachtrag, Kasse stimmt weiter
    e2 = lauf(j, rm, jetzt=SPAETER.replace(day=6), broker=broker, konfig=_konfig(), flex=None)
    assert e2.gestoppt is None and len(j.db.execute("SELECT * FROM ausfuehrungen").fetchall()) == 1
    assert any("Kasse je Währung stimmt" in m for m in e2.meldungen)


def test_verpasster_abend_ohne_beleg_stoppt(umgebung):
    j, rm = umgebung
    z = _gesendet(j, rm)
    broker = KontoAttrappe({"EUR": 999_000.0}, positionen=[Position("DU1", "SPYI.DE", z["stueck"], 11.0)])
    e = lauf(j, rm, jetzt=SPAETER, broker=broker, konfig=_konfig(gebuehr=None), flex=None)
    assert e.gestoppt and "ohne Beleg" in e.gestoppt and "Flex" in e.gestoppt and e.vorschlaege == []
    assert j.vorschlaege(buch="real")[0]["status"] == "gesendet"                 # weder verfallen noch gebucht
    assert j.bestand("real") == {} and "kassenbasis" not in j.zustand("_konto")


def test_preis_ausserhalb_der_tagesspanne_stoppt(umgebung):
    j, rm = umgebung
    z = _gesendet(j, rm)
    broker = KontoAttrappe({"EUR": 999_000.0}, positionen=[Position("DU1", "SPYI.DE", z["stueck"], _tagespreis() * 0.8)])
    e = lauf(j, rm, jetzt=SPAETER, broker=broker, konfig=_konfig(), flex=None)
    assert e.gestoppt and "außerhalb Tief/Hoch" in e.gestoppt
    assert j.vorschlaege(buch="real")[0]["status"] == "gesendet"


def test_teilausfuehrung_ohne_flex_stoppt(umgebung):
    j, rm = umgebung
    z = _gesendet(j, rm)
    broker = KontoAttrappe({"EUR": 999_000.0}, positionen=[Position("DU1", "SPYI.DE", z["stueck"] - 1, _tagespreis())])
    e = lauf(j, rm, jetzt=SPAETER, broker=broker, konfig=_konfig(), flex=None)
    assert e.gestoppt and "Teilausführung" in e.gestoppt


def test_verpasster_abend_nachtrag_aus_flex(umgebung):
    j, rm = umgebung
    z = _gesendet(j, rm)
    preis = _tagespreis()
    flex_zeilen = [{"orderReference": f"real:{z['id']}", "ibExecID": "0000e0d5.6729a1b2.01.01", "assetCategory": "STK", "symbol": "SPYI",
                    "conid": "0", "currency": "EUR", "buySell": "BUY", "quantity": str(z["stueck"]), "tradePrice": str(preis),
                    "ibCommission": "-3", "ibCommissionCurrency": "EUR", "dateTime": "20261103;090007", "exchange": "IBIS2"},
                   {"orderReference": "fremd:x", "ibExecID": "y", "assetCategory": "STK", "symbol": "ABC", "conid": "0", "currency": "USD",
                    "buySell": "BUY", "quantity": "1", "tradePrice": "1", "ibCommission": "-1", "dateTime": "20261103;150000"}]
    broker = KontoAttrappe({"EUR": 1_000_000.0 - preis * z["stueck"] - 3.0},
                           positionen=[Position("DU1", "SPYI.DE", z["stueck"], preis + 3.0 / z["stueck"])])
    e = lauf(j, rm, jetzt=SPAETER, broker=broker, konfig=_konfig(gebuehr=None), flex=lambda: (flex_zeilen, "IBKR Flex-Abfrage 123, erstellt x"))
    assert e.gestoppt is None, e.gestoppt
    a = j.db.execute("SELECT * FROM ausfuehrungen").fetchall()
    assert len(a) == 1 and a[0]["exec_id"] == "0000e0d5.6729a1b2.01.01" and a[0]["boerse"] == "IBIS2"
    assert a[0]["quelle"] == "IBKR Flex-Abfrage 123, erstellt x" and a[0]["zeit"] == "2026-11-03T09:00:07"


def test_ohne_abweichung_verfallen_wie_bisher(umgebung):
    j, rm = umgebung
    _gesendet(j, rm)
    e = lauf(j, rm, jetzt=SPAETER, broker=KontoAttrappe({"EUR": 1_000_000.0}), konfig=_konfig(), flex=None)
    assert e.gestoppt is None and j.vorschlaege(buch="real")[0]["status"] in ("verfallen",)
    assert any("verfallen" in m for m in e.meldungen)


def test_flex_tausch():
    zeilen = [{"orderReference": "fundamental_a:t", "ibExecID": "f1", "assetCategory": "CASH", "symbol": "EUR.USD", "currency": "USD",
               "buySell": "SELL", "quantity": "-9000", "tradePrice": "1.1", "ibCommission": "-2", "ibCommissionCurrency": "USD",
               "dateTime": "2026-11-03;22:10:00"}]
    a = flex_ausfuehrungen(zeilen, {"fundamental_a:t"})[0]
    assert a["art"] == "fx" and a["von"] == "EUR" and a["nach"] == "USD" and a["betrag_von"] == 9000
    assert a["betrag_nach"] == pytest.approx(9900) and a["gebuehr"] == 2 and a["zeit"] == "2026-11-03T22:10:00"
