"""Broker-Adapter: Sicherheitsriegel und Orderaufbau, ohne Gateway (Attrappe statt ib_async.IB)."""
from types import SimpleNamespace

import pytest

from tradingbot.broker.basis import Auftrag, SendenGesperrt, VerbindungGesperrt
from tradingbot.broker.ibkr import IbkrBroker
from tradingbot.konfiguration import lade_konfiguration


class IBAttrappe:
    """Verhält sich bei reqContractDetails wie IBKR am 03.11.2026: Xetra-ETFs über conId (Tabelle) oder ISIN auffindbar,
    über das Xetra-Kürzel als Symbol aber nicht, wenn IBKR ein anderes Symbol führt (EUNM = „IEMA“)."""

    def __init__(self, konto="DU1234567", offen=(), status="PreSubmitted", log=()):
        self.konto, self.offen, self.gesendet, self.verbunden = konto, list(offen), [], None
        self.status, self.log = status, list(log)

    def reqContractDetails(self, anfrage):
        from tradingbot.broker.ibkr import kontrakttabelle
        if getattr(anfrage, "secType", "") == "CASH":
            return [SimpleNamespace(contract=SimpleNamespace(conId=12087792, symbol="EUR", localSymbol="EUR.USD", exchange="IDEALPRO",
                                                             currency="USD"))]
        for t, e in kontrakttabelle().items():
            if anfrage.conId and int(e["con_id"]) == anfrage.conId or (not anfrage.conId and anfrage.symbol == e["symbol"]
                                                                        and anfrage.exchange in ("IBIS2", "SMART")):
                # wie IBKR: unter SMART ist localSymbol das IBKR-Symbol (IEMA), nur unter IBIS2 das Xetra-Kürzel (EUNM)
                lokal = e["lokal"] if anfrage.exchange == "SMART" else t.split(".")[0]
                return [SimpleNamespace(contract=SimpleNamespace(conId=int(e["con_id"]), symbol=e["symbol"], localSymbol=lokal,
                                                                 exchange=anfrage.exchange, primaryExchange="AEB", currency=e["waehrung"]),
                                        validExchanges="SMART,AEB,IBIS2", marketRuleIds=self.regel_ids.get(t, "1874,1874,1874"))]
        if anfrage.currency == "USD" and anfrage.exchange == "SMART":
            return [SimpleNamespace(contract=SimpleNamespace(conId=265598, symbol=anfrage.symbol, localSymbol=anfrage.symbol, exchange="SMART",
                                                             currency="USD"))]
        return []

    regel_ids = {"EUNM.DE": "2077,2077,1906"}
    REGELN = {1874: [(0.0, 0.0001), (1.0, 0.0002), (2.0, 0.0005), (5.0, 0.001), (10.0, 0.002), (20.0, 0.005), (50.0, 0.01), (100.0, 0.02),
                     (200.0, 0.05), (500.0, 0.1)],
              2077: [(0.0, 0.0001), (1.0, 0.0002), (2.0, 0.0005), (5.0, 0.001), (10.0, 0.002), (20.0, 0.005), (50.0, 0.01)],
              1906: [(0.0, 0.0001), (5.0, 0.0002), (10.0, 0.0005), (20.0, 0.001), (50.0, 0.002), (100.0, 0.005), (200.0, 0.01)]}

    def reqMarketRule(self, i):
        return [SimpleNamespace(lowEdge=a, increment=b) for a, b in self.REGELN[i]]

    def sleep(self, s):
        pass

    def connect(self, host, port, clientId, timeout, readonly, fetchFields=None):
        self.verbunden = dict(host=host, port=port, readonly=readonly, fetchFields=fetchFields)

    def managedAccounts(self):
        return [self.konto]

    def openTrades(self):
        return self.offen

    def placeOrder(self, kontrakt, order):
        self.gesendet.append((kontrakt, order))
        return SimpleNamespace(order=SimpleNamespace(orderId=len(self.gesendet) + 2), contract=kontrakt,
                               orderStatus=SimpleNamespace(status=self.status), log=list(self.log))


def betrieb(senden=True):
    b = lade_konfiguration("betrieb")
    b["ibkr"] = {**b["ibkr"], "senden_freigeschaltet": senden}
    return b


KAUF = Auftrag("real", "v1", "SPYI.DE", 1, 2, 204.0)
VERKAUF = Auftrag("real", "v2", "SPYI.DE", -1, 2, None)


def broker(tmp_path, *, senden=True, konto="DU1234567", modus="paper", port=4002, offen=(), **kw):
    return IbkrBroker(betrieb(senden), tmp_path, host="127.0.0.1", port=port, client_id=7, modus=modus, ib=IBAttrappe(konto, offen, **kw))


def test_live_port_und_fremder_host_gesperrt(tmp_path):
    with pytest.raises(VerbindungGesperrt, match="Live-Port"):
        broker(tmp_path, port=4001)
    with pytest.raises(VerbindungGesperrt):
        IbkrBroker(betrieb(), tmp_path, host="192.168.0.5", port=4002, modus="paper", ib=IBAttrappe())


def test_verbindung_nur_lesend_solange_senden_aus(tmp_path):
    b = broker(tmp_path, senden=False)
    b.verbinden()
    v = b.ib.verbunden
    assert (v["host"], v["port"], v["readonly"]) == ("127.0.0.1", 4002, True)


def test_senden_aus_in_der_konfiguration(tmp_path):
    with pytest.raises(SendenGesperrt, match="nicht freigeschaltet"):
        broker(tmp_path, senden=False).sende(KAUF, set())


def test_nur_paper_konto_und_paper_modus(tmp_path):
    with pytest.raises(SendenGesperrt, match="kein Paper-Konto"):
        broker(tmp_path, konto="U7654321").sende(KAUF, set())
    with pytest.raises(SendenGesperrt, match="TRADING_MODE"):
        broker(tmp_path, modus="live").sende(KAUF, set())


def test_not_aus_datei(tmp_path):
    (tmp_path / "STOP").write_text("")
    with pytest.raises(SendenGesperrt, match="Not-Aus"):
        broker(tmp_path).sende(VERKAUF, set())


def test_doppel_orders(tmp_path):
    b = broker(tmp_path)
    gesendet = set()
    b.sende(KAUF, gesendet)
    with pytest.raises(SendenGesperrt, match="schon gesendet"):
        b.sende(KAUF, gesendet)
    offen = [SimpleNamespace(order=SimpleNamespace(orderRef="real:alt", action="BUY", totalQuantity=1, orderType="LMT", lmtPrice=200.0),
                             contract=SimpleNamespace(symbol="SPYI", exchange="IBIS", currency="EUR"), orderStatus=SimpleNamespace(status="Submitted"))]
    with pytest.raises(SendenGesperrt, match="derselben Richtung"):
        broker(tmp_path, offen=offen).sende(Auftrag("real", "v9", "SPYI.DE", 1, 1, 204.0), set())
    # anderes Buch darf denselben Ticker kaufen
    broker(tmp_path, offen=offen).sende(Auftrag("crossover", "v9", "SPYI.DE", 1, 1, 204.0), set())


def test_orderaufbau(tmp_path):
    b = broker(tmp_path)
    b.sende(KAUF, set())
    b.sende(Auftrag("real", "v3", "SPYI.DE", -1, 1, None), set())
    (k1, o1), (k2, o2) = b.ib.gesendet
    assert (k1.symbol, k1.exchange, k1.currency) == ("SPYI", "SMART", "EUR")                     # SMART, Kontrakt wie von IBKR
    assert (o1.action, o1.orderType, o1.lmtPrice, o1.tif, o1.orderRef) == ("BUY", "LMT", 204.0, "DAY", "real:v1")
    assert (o2.action, o2.orderType, o2.tif, o2.orderRef) == ("SELL", "MKT", "DAY", "real:v3")
    with pytest.raises(SendenGesperrt, match="Kauf ohne Limit"):
        b.sende(Auftrag("real", "v4", "SPYI.DE", 1, 1, None), set())


def test_kontrakte_xetra_aktie_und_us():
    from tradingbot.broker.ibkr import kontrakt
    assert kontrakt("SAP.DE", "aktie").exchange == "IBIS"
    assert kontrakt("BF-B", "aktie").symbol == "BF B"
    us = kontrakt("AAPL", "aktie")
    assert (us.exchange, us.currency) == ("SMART", "USD")


def test_senden_je_buch_freigeschaltet(tmp_path):
    """Freischaltung je Buch (03.11.2026): real und crossover an, Fundamental A/B und Momentum gesperrt."""
    b = broker(tmp_path)
    for buch in ("fundamental_a", "fundamental_b", "momentum"):
        with pytest.raises(SendenGesperrt, match=f"Buch {buch} ist zum Senden nicht freigeschaltet"):
            b.sende(Auftrag(buch, "v5", "SPYI.DE", 1, 1, 204.0), set())
    b.sende(Auftrag("crossover", "v6", "SPYI.DE", 1, 1, 204.0), set())
    with pytest.raises(SendenGesperrt, match="nicht freigeschaltet"):          # global aus sperrt alle Bücher
        broker(tmp_path, senden=False).sende(Auftrag("real", "v7", "SPYI.DE", 1, 1, 204.0), set())


def test_verbinden_ohne_abruf_abgeschlossener_orders(tmp_path):
    """ReqCompletedOrders wird im Read-Only-Modus abgelehnt (03.11.2026) und nie gebraucht: beim Start weglassen,
    Ausführungen (reqExecutions), Positionen und offene Orders bleiben."""
    pytest.importorskip("ib_async")
    from ib_async.ib import StartupFetch

    b = broker(tmp_path)
    b.verbinden()
    f = b.ib.verbunden["fetchFields"]
    assert not (f & StartupFetch.ORDERS_COMPLETE)
    assert f & StartupFetch.EXECUTIONS and f & StartupFetch.POSITIONS and f & StartupFetch.ORDERS_OPEN


def test_gateway_fehler_landen_im_protokoll(tmp_path):
    b = broker(tmp_path)
    b._gateway_fehler(-1, 321, "Die API befindet sich im schreibgeschützten Modus")
    b._gateway_fehler(-1, 2104, "Market data farm connection is OK")
    assert b.gateway_meldungen == ["Gateway-Meldung 321: Die API befindet sich im schreibgeschützten Modus"]


def test_kontrakt_qualifiziert_ueber_tabelle(tmp_path):
    """EUNM heißt bei IBKR „IEMA“ (03.11.2026): Auflösung über die conId der Tabelle, Order direkt an IBIS2 mit conId ≠ 0."""
    from tradingbot.broker.ibkr import kontrakttabelle
    assert int(kontrakttabelle()["EUNM.DE"]["con_id"]) == 100292766
    b = broker(tmp_path)
    k = b.kontrakt_aufloesen("EUNM.DE", "etf")
    assert (k.conId, k.symbol, k.localSymbol, k.exchange, k.primaryExchange, k.currency) == (100292766, "IEMA", "IEMA", "SMART", "AEB", "EUR")
    e = b.sende(Auftrag("crossover", "x1", "EUNM.DE", 1, 35, 53.61), set())
    kontrakt_gesendet, order = b.ib.gesendet[-1]
    assert kontrakt_gesendet.conId == 100292766 and kontrakt_gesendet.exchange == "SMART" and order.orderRef == "crossover:x1"
    assert e.status == "angenommen" and e.con_id == 100292766


def test_kontrakt_unbekannt_wird_nicht_gesendet(tmp_path):
    from tradingbot.broker.basis import KontraktUnbekannt
    b = broker(tmp_path)
    with pytest.raises(KontraktUnbekannt, match="Kontrakt unbekannt: XYZQ.DE"):
        b.sende(Auftrag("crossover", "x2", "XYZQ.DE", 1, 1, 10.0), set())
    assert b.ib.gesendet == []


def test_ablehnung_und_unbestaetigt(tmp_path):
    log = [SimpleNamespace(message="Es wurde keine Wertpapierdefinition zu der Anfrage gefunden", errorCode=200)]
    e = broker(tmp_path, status="Cancelled", log=log).sende(KAUF, set())
    assert e.status == "abgelehnt" and "200" in e.text and "Wertpapierdefinition" in e.text
    e = broker(tmp_path, status="PendingSubmit").sende(KAUF, set(), wartezeit=0.0)
    assert e.status == "unbestaetigt" and "PendingSubmit" in e.text
    assert broker(tmp_path, status="Submitted").sende(KAUF, set()).status == "angenommen"


def test_ticker_aus_conid():
    from tradingbot.broker.ibkr import ticker_aus
    assert ticker_aus(SimpleNamespace(conId=100292766, symbol="IEMA", primaryExchange="AEB", exchange="", currency="EUR")) == "EUNM.DE"
    assert ticker_aus(SimpleNamespace(conId=80268543, symbol="IJPA", primaryExchange="AEB", exchange="", currency="EUR")) == "EUNN.DE"


def test_kursstufe_runden():
    """Fehler 110 am 03.11.2026: SXR1 221,34 € verletzt die Stufe 0,05 (Regel 1874 ab 200 €) → Kauf 221,30, Verkauf 221,35."""
    from tradingbot.broker.ibkr import auf_stufe, gemeinsame_stufe, stufe_fuer
    r1874 = IBAttrappe.REGELN[1874]
    assert stufe_fuer(r1874, 221.34) == 0.05 and stufe_fuer(r1874, 11.81) == 0.002 and stufe_fuer(r1874, 200.0) == 0.05
    assert auf_stufe(221.34, 0.05, 1) == 221.30 and auf_stufe(221.34, 0.05, -1) == 221.35
    assert auf_stufe(221.30, 0.05, 1) == 221.30                       # schon gültig: unverändert
    assert gemeinsame_stufe([0.002, 0.005]) == 0.01 and gemeinsame_stufe([0.01, 0.002]) == 0.01


def test_limit_im_auftrag_auf_kursstufe(tmp_path):
    b = broker(tmp_path)
    b.sende(Auftrag("crossover", "s1", "SXR1.DE", 1, 11, 221.34), set())
    k, o = b.ib.gesendet[-1]
    assert o.lmtPrice == 221.30 and o.lmtPrice <= 221.34 and k.exchange == "SMART"
    # EUNM: SMART-Regel 2077 (0,01 ab 50 €) und IBIS2-Regel 1906 (0,002) → gemeinsame Stufe 0,01
    b.kontrakt_aufloesen("EUNM.DE")
    assert b.limit_runden("EUNM.DE", 53.617, 1) == (53.61, 0.01)


def test_ausfuehrungsplatz(tmp_path):
    b = broker(tmp_path)
    b.ib.fills = lambda: [SimpleNamespace(execution=SimpleNamespace(orderRef="real:v1", execId="e1", side="BOT", shares=2.0, price=11.8,
                                                                    time="t", exchange="GETTEX2"),
                                          contract=SimpleNamespace(conId=89384965, symbol="SPYI", secType="STK", currency="EUR",
                                                                   primaryExchange="IBIS2", exchange=""),
                                          commissionReport=None)]
    a = b.ausfuehrungen()[0]
    assert a["ticker"] == "SPYI.DE" and a["boerse"] == "GETTEX2"


def test_kontrakt_unveraendert_wie_von_ibkr(tmp_path):
    """Fehler 478 (03.11.2026): Symbol ≠ Xetra-Kürzel (EUNM/IEMA, EUNN/IJPA). Gesendet wird genau der von IBKR unter SMART
    qualifizierte Kontrakt – kein eigenes symbol/localSymbol/primaryExchange."""
    b = broker(tmp_path)
    anfragen = []
    original = b.ib.reqContractDetails
    b.ib.reqContractDetails = lambda a: (anfragen.append(a), original(a))[1]
    for ticker, symbol in (("EUNM.DE", "IEMA"), ("EUNN.DE", "IJPA")):
        geliefert = b.kontrakt_aufloesen(ticker)
        b.sende(Auftrag("crossover", f"x-{ticker}", ticker, 1, 10, 50.0), set())
        gesendet, _ = b.ib.gesendet[-1]
        assert gesendet is not None and (gesendet.conId, gesendet.symbol, gesendet.localSymbol) == (geliefert.conId, symbol, symbol)
        assert gesendet.exchange == "SMART" and gesendet.primaryExchange == "AEB" and gesendet.localSymbol != ticker[:-3]
    a = anfragen[-1]
    assert a.conId and a.exchange == "SMART" and not a.symbol and not a.localSymbol and not a.primaryExchange


def test_ibkr_gebuehr_leerwert():
    from tradingbot.broker.ibkr import ibkr_gebuehr
    assert ibkr_gebuehr(SimpleNamespace(commissionReport=SimpleNamespace(commission=1.7976931348623157e308))) is None
    assert ibkr_gebuehr(SimpleNamespace(commissionReport=None)) is None
    assert ibkr_gebuehr(SimpleNamespace(commissionReport=SimpleNamespace(commission=0.0))) == 0.0
    assert ibkr_gebuehr(SimpleNamespace(commissionReport=SimpleNamespace(commission=1.25))) == 1.25


def test_tabelle_deckt_universum_ab():
    """Zuordnungstabelle 04.11.2026: Core, Satellite (außer SXRM), Xetra-Gold, EUR.USD und S&P-500-Aktien."""
    from tradingbot.broker.ibkr import kontrakttabelle, nicht_aufloesbar
    tab = kontrakttabelle()
    assert int(tab["4GLD.DE"]["con_id"]) == 50784405 and tab["4GLD.DE"]["boerse"] == "IBIS"
    assert int(tab["EUR.USD"]["con_id"]) == 12087792 and tab["EUR.USD"]["boerse"] == "IDEALPRO"
    assert sum(1 for e in tab.values() if e["art"] == "aktie") > 450 and "SXRM.DE" in nicht_aufloesbar()


def test_nicht_aufloesbar_veto(tmp_path):
    from tradingbot.broker.basis import KontraktUnbekannt
    b = broker(tmp_path)
    with pytest.raises(KontraktUnbekannt, match="SXRM.DE"):
        b.kontrakt_aufloesen("SXRM.DE", "etf", "USD")
    k = b.kontrakt_aufloesen("EUR.USD", "fx", "USD")
    assert k.conId == 12087792
