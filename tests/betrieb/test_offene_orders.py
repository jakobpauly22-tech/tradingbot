"""Abgleich der offenen Orders bei IBKR mit dem Journal nach dem Senden (Jakob 13.11.2026).

Nachgestellter Fall BF-B (Order 211, 12.11.2026): IBKR schickte nur Warnung 399, die Order war PreSubmitted (aktiv), der Bot
buchte sie als abgelehnt. Eine bei IBKR offene Order, die im Journal fehlt oder nicht unterwegs ist, ergibt eine
Sofortmeldung und einen Protokolleintrag; nichts wird storniert."""
from datetime import datetime

from test_oberflaeche import JournalAttrappe, _erg, wurzel  # noqa: F401
from test_read_only import ALLE_AN, ReadOnlyBroker, _freigebbar
from test_tageslauf import ABEND, kurse_attrappe, lauf, umgebung  # noqa: F401
from tradingbot.betrieb import benachrichtigung as bn
from tradingbot.betrieb.tageslauf import ORDER_OFFEN_MELDUNG, freigeben_und_senden, offene_orders_abgleichen
from tradingbot.broker.basis import OffeneOrder, SendeErgebnis

TEXT_399 = ("399: Warning 399, reqId 211: Order-Mitteilung: KAUFEN 17 BF B NYSE Warnung: Ihre Order wird nicht vor "
            "2026-11-13 09:30:00 US/Eastern an der Börse platziert.")


class BfbBroker(ReadOnlyBroker):
    """Erste Order wird (wie vor der Korrektur) als abgelehnt gemeldet, bleibt bei IBKR aber offen (PreSubmitted).
    Dazu eine von Hand im Client Portal angelegte Order ohne orderRef. Stornieren gibt es nicht."""

    def __init__(self, **kw):
        super().__init__(schreiben=True, **kw)
        self.offen, self.abfragen = [], 0

    def sende(self, auftrag, refs):
        refs.add(auftrag.order_ref)
        self.gesendet.append(auftrag)
        if len(self.gesendet) == 1:
            self.offen.append(OffeneOrder(auftrag.order_ref, auftrag.ticker, auftrag.richtung, auftrag.stueck, auftrag.limit, "PreSubmitted"))
            return SendeErgebnis("211", "abgelehnt", TEXT_399)
        self.offen.append(OffeneOrder(auftrag.order_ref, auftrag.ticker, auftrag.richtung, auftrag.stueck, auftrag.limit, "PreSubmitted"))
        return SendeErgebnis(str(211 + len(self.gesendet)), "angenommen", "PreSubmitted")

    def offene_orders(self):
        self.abfragen += 1
        return list(self.offen) + ([OffeneOrder("", "HAND", 1, 3, 10.0, "Submitted")] if self.abfragen > 1 else [])


def test_bfb_fall_offen_aber_abgelehnt_wird_gemeldet(umgebung):
    j, rm = umgebung
    ids = _freigebbar(j, rm)
    b = BfbBroker()
    start = datetime.now().isoformat(timespec="seconds")
    m = freigeben_und_senden(j, ids, b, ABEND, risk=rm, kurse_laden=kurse_attrappe(), konfig_betrieb=ALLE_AN)
    erste = b.gesendet[0]
    treffer = [x for x in m if x.startswith(ORDER_OFFEN_MELDUNG)]
    assert len(treffer) == 1 and treffer[0].startswith(f"{ORDER_OFFEN_MELDUNG}: {erste.ticker}, HAND – nichts storniert")
    assert "Journal: abgelehnt" in treffer[0] and "im Journal nicht vorhanden" in treffer[0]
    # die übrigen, korrekt als gesendet gebuchten Orders lösen nichts aus
    assert not any(a.ticker in treffer[0].split(" – ")[0] for a in b.gesendet[1:] if a.ticker != erste.ticker)
    ereignisse = j.db.execute("SELECT buch, text FROM ereignisse WHERE art='order_offen_nicht_unterwegs' ORDER BY text").fetchall()
    assert len(ereignisse) == 2 and all("nichts storniert" in e["text"] for e in ereignisse)
    assert {e["buch"] for e in ereignisse} == {erste.buch, None}
    assert j.vorschlaege(buch=erste.buch) and next(z for z in j.vorschlaege() if z["id"] == erste.vorschlag_id)["status"] == "abgelehnt"
    # Sofortmeldung per Telegram: nur die Kürzel, keine Freitexte
    text = bn.sendeprobleme(j, ids, start, m, ABEND)
    assert f"{ORDER_OFFEN_MELDUNG}: {erste.ticker}, HAND (nichts storniert)" in text
    assert "Journal: " not in text and "orderRef" not in text and "Client Portal prüfen" not in text


class Leer:
    def offene_orders(self):
        return []


def test_ohne_offene_orders_keine_meldung(umgebung):
    j, _ = umgebung
    assert offene_orders_abgleichen(j, Leer()) == []
    assert j.db.execute("SELECT COUNT(*) FROM ereignisse WHERE art='order_offen_nicht_unterwegs'").fetchone()[0] == 0


class AbfrageKaputt(BfbBroker):
    def offene_orders(self):
        self.abfragen += 1
        if self.abfragen > 1:
            raise ConnectionError("weg")
        return []


def test_fehler_im_abgleich_bricht_senden_nicht_ab(umgebung):
    j, rm = umgebung
    ids = _freigebbar(j, rm)
    m = freigeben_und_senden(j, ids, AbfrageKaputt(), ABEND, risk=rm, kurse_laden=kurse_attrappe(), konfig_betrieb=ALLE_AN)
    assert any(x.startswith("Abgleich der offenen Orders nach dem Senden fehlgeschlagen (ConnectionError)") for x in m)
    assert not any(x.startswith("Senden abgebrochen") for x in m)
    assert "Abgleich der offenen Orders fehlgeschlagen" in bn.sendeprobleme(j, [], "2026-01-01", m, ABEND)


def test_unterwegs_ist_still_und_unbekannter_vorschlag_meldet(umgebung):
    j, rm = umgebung
    lauf(j, rm)
    z = j.vorschlaege()[0]
    j.status_setzen(z["id"], "gesendet", order_id="5")

    class Broker:
        def offene_orders(self):
            return [OffeneOrder(f"{z['buch']}:{z['id']}", z["ticker"], z["richtung"], z["stueck"], None, "Submitted"),
                    OffeneOrder("real:gibt-es-nicht", "XYZ", -1, 1, None, "PreSubmitted")]

    m = offene_orders_abgleichen(j, Broker())
    assert m == [f"{ORDER_OFFEN_MELDUNG}: XYZ – nichts storniert, bitte im Client Portal prüfen (XYZ: real, im Journal nicht vorhanden)"]
