"""Vorfall 09.11.2026 (Read-Only im Gateway, Fenster eingefroren und von Windows geschlossen): Schreibzugriff vor jedem
Senden prüfen, bei Read-Only nichts an IBKR übergeben (auch keinen Tausch), klare Meldung; keine Ausnahme bis zum Fenster."""

import pytest

from test_oberflaeche import JournalAttrappe, _erg, wurzel  # noqa: F401
from test_tageslauf import ABEND, AN, BrokerAttrappe, kurse_attrappe, lauf, umgebung  # noqa: F401
from tradingbot.betrieb.tageslauf import READ_ONLY_MELDUNG, freigeben_und_senden, ist_read_only_ablehnung
from tradingbot.broker.basis import SendeErgebnis
from tradingbot.konfiguration import lade_konfiguration

ALLE_AN = {**AN, "buecher": {n: {**bk, "senden_freigeschaltet": True} for n, bk in AN["buecher"].items()}}
TEXT_321 = ("321: Warning 321, reqId 49: Bei der Validierung der Anfrage ist ein Fehler aufgetreten.-'PlaceOrder(3)' : cause - "
            "Die API befindet sich im schreibgesch\\u00fctzten Modus.")


class ReadOnlyBroker(BrokerAttrappe):
    def __init__(self, schreiben=False, **kw):
        super().__init__(**kw)
        self.schreiben, self.geprueft = schreiben, 0

    def schreibzugriff(self):
        self.geprueft += 1
        return (True, "Schreibzugriff im Gateway geprüft") if self.schreiben else (False, "Read-Only im Gateway ist aktiv (Fehler 321 auf eine reine Abfrage)")


def _freigebbar(j, rm):
    lauf(j, rm)
    ids = [z["id"] for z in j.vorschlaege() if z["status"] == "vorgeschlagen" and z["buch"] in ("real", "fundamental_a")]
    assert any(z["art"] == "fx" for z in j.vorschlaege(buch="fundamental_a"))         # mit Tausch
    return ids


def test_read_only_nichts_uebergeben(umgebung):
    j, rm = umgebung
    ids = _freigebbar(j, rm)
    b = ReadOnlyBroker()
    m = freigeben_und_senden(j, ids, b, ABEND, risk=rm, kurse_laden=kurse_attrappe(), konfig_betrieb=ALLE_AN)
    assert b.geprueft == 1 and b.gesendet == []                                       # kein placeOrder, auch kein Tausch
    assert any(x.startswith(READ_ONLY_MELDUNG) for x in m)
    assert {z["status"] for z in j.vorschlaege() if z["id"] in ids} == {"freigegeben"}  # bleiben bis 24 Uhr freigegeben
    assert j.db.execute("SELECT COUNT(*) FROM ereignisse WHERE art='read_only'").fetchone()[0] == 1
    # nach dem Ausschalten: dieselben Freigaben werden gesendet
    b2 = ReadOnlyBroker(schreiben=True)
    m = freigeben_und_senden(j, [], b2, ABEND, risk=rm, kurse_laden=kurse_attrappe(), konfig_betrieb=ALLE_AN)
    assert len(b2.gesendet) == len(ids) and "Schreibzugriff im Gateway geprüft" in m


class AblehnungsBroker(ReadOnlyBroker):
    def sende(self, auftrag, refs):
        refs.add(auftrag.order_ref)
        self.gesendet.append(auftrag)
        return SendeErgebnis("49", "abgelehnt", f"Status ValidationError nach 8 s: {TEXT_321}")


def test_read_only_waehrend_des_sendens_bricht_ab(umgebung):
    j, rm = umgebung
    ids = _freigebbar(j, rm)
    b = AblehnungsBroker(schreiben=True)
    m = freigeben_und_senden(j, ids, b, ABEND, risk=rm, kurse_laden=kurse_attrappe(), konfig_betrieb=ALLE_AN)
    assert len(b.gesendet) == 1                                                       # danach nichts mehr übergeben
    assert any(READ_ONLY_MELDUNG in x and "abgebrochen" in x for x in m)
    status = [z["status"] for z in j.vorschlaege() if z["id"] in ids]
    assert status.count("abgelehnt") == 1 and status.count("freigegeben") == len(ids) - 1


class KaputterBroker(ReadOnlyBroker):
    def sende(self, auftrag, refs):
        raise RuntimeError("Socket getrennt")


def test_fehler_beim_senden_wird_meldung(umgebung):
    j, rm = umgebung
    ids = _freigebbar(j, rm)
    zaehler = []
    m = freigeben_und_senden(j, ids, KaputterBroker(schreiben=True), ABEND, risk=rm, kurse_laden=kurse_attrappe(),
                             konfig_betrieb=ALLE_AN, fortschritt=lambda: zaehler.append(1))
    assert any(x.startswith("Senden abgebrochen (RuntimeError: Socket getrennt)") for x in m)
    assert zaehler                                                                     # Fenster wurde zwischendurch bedient


def test_ist_read_only_ablehnung():
    assert ist_read_only_ablehnung(TEXT_321)
    assert not ist_read_only_ablehnung("200: Es wurde keine Wertpapierdefinition gefunden")


# --- Adapter: Schreibprüfung ohne Order ----------------------------------------------------------------------------------
class IbProbe:
    def __init__(self, verhalten, broker_ref):
        self.verhalten, self.broker_ref, self.RequestTimeout, self.orders = verhalten, broker_ref, 0, []

    def reqCompletedOrders(self, apiOnly):
        assert self.RequestTimeout == 3.0
        if self.verhalten == "read_only":
            self.broker_ref[0]._gateway_fehler(-1, 321, "Bei der Validierung der Anfrage ist ein Fehler aufgetreten.-'ReqCompletedOrders(99)' "
                                                        ": cause - Die API befindet sich im schreibgeschützten Modus.")
            raise TimeoutError
        if self.verhalten == "stumm":
            raise TimeoutError
        return []

    def placeOrder(self, *a):                                       # darf nie aufgerufen werden
        self.orders.append(a)


@pytest.mark.parametrize("verhalten, ok, text", [("read_only", False, "Read-Only im Gateway ist aktiv"),
                                                ("stumm", False, "nicht in 3 s beantwortet"), ("frei", True, "geprüft")])
def test_schreibzugriff_ohne_order(tmp_path, verhalten, ok, text):
    from tradingbot.broker.ibkr import IbkrBroker
    ref = [None]
    ib = IbProbe(verhalten, ref)
    b = IbkrBroker(lade_konfiguration("betrieb"), tmp_path, modus="paper", ib=ib)
    ref[0] = b
    erg = b.schreibzugriff()
    assert erg[0] is ok and text in erg[1] and ib.orders == [] and ib.RequestTimeout == 0


# --- Fenster: Ablehnung oder Fehler beendet es nie -----------------------------------------------------------------------
def test_fenster_ueberlebt_fehler_beim_senden(wurzel, monkeypatch):  # noqa: F811
    from tradingbot.betrieb import oberflaeche
    from tradingbot.betrieb.oberflaeche import Freigabefenster
    meldungen = []
    monkeypatch.setattr(oberflaeche.messagebox, "askyesno", lambda *a, **k: True)
    monkeypatch.setattr(oberflaeche.messagebox, "showerror", lambda *a, **k: meldungen.append(("fehler", a)))
    monkeypatch.setattr(oberflaeche.messagebox, "showwarning", lambda *a, **k: meldungen.append(("warnung", a)))

    def kaputt(ids):
        raise RuntimeError("Gateway weg")
    erg = _erg(10)
    f = Freigabefenster(wurzel, erg, JournalAttrappe(), lade_konfiguration("betrieb"), probe=True, senden_fn=kaputt)
    next(var for vid, var in f.auswahl.items()).set(True)
    f.senden()                                                                         # keine Ausnahme
    assert meldungen and meldungen[0][0] == "fehler" and "Gateway weg" in f.protokoll.get("1.0", "end")
    f.senden_fn = lambda ids: [f"{READ_ONLY_MELDUNG} (Fehler 321). Nichts gesendet."]
    f.senden()
    assert meldungen[-1][0] == "warnung"
