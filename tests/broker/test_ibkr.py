"""Broker-Adapter: Sicherheitsriegel und Orderaufbau, ohne Gateway (Attrappe statt ib_async.IB)."""
from types import SimpleNamespace

import pytest

from tradingbot.broker.basis import Auftrag, SendenGesperrt, VerbindungGesperrt
from tradingbot.broker.ibkr import IbkrBroker
from tradingbot.konfiguration import lade_konfiguration


class IBAttrappe:
    def __init__(self, konto="DU1234567", offen=()):
        self.konto, self.offen, self.gesendet, self.verbunden = konto, list(offen), [], None

    def connect(self, host, port, clientId, timeout, readonly):
        self.verbunden = dict(host=host, port=port, readonly=readonly)

    def managedAccounts(self):
        return [self.konto]

    def openTrades(self):
        return self.offen

    def placeOrder(self, kontrakt, order):
        self.gesendet.append((kontrakt, order))
        return SimpleNamespace(order=SimpleNamespace(orderId=len(self.gesendet)))


def betrieb(senden=True):
    b = lade_konfiguration("betrieb")
    b["ibkr"] = {**b["ibkr"], "senden_freigeschaltet": senden}
    return b


KAUF = Auftrag("real", "v1", "SPYI.DE", 1, 2, 204.0)
VERKAUF = Auftrag("real", "v2", "SPYI.DE", -1, 2, None)


def broker(tmp_path, *, senden=True, konto="DU1234567", modus="paper", port=4002, offen=()):
    return IbkrBroker(betrieb(senden), tmp_path, host="127.0.0.1", port=port, client_id=7, modus=modus, ib=IBAttrappe(konto, offen))


def test_live_port_und_fremder_host_gesperrt(tmp_path):
    with pytest.raises(VerbindungGesperrt, match="Live-Port"):
        broker(tmp_path, port=4001)
    with pytest.raises(VerbindungGesperrt):
        IbkrBroker(betrieb(), tmp_path, host="192.168.0.5", port=4002, modus="paper", ib=IBAttrappe())


def test_verbindung_nur_lesend_solange_senden_aus(tmp_path):
    b = broker(tmp_path, senden=False)
    b.verbinden()
    assert b.ib.verbunden == {"host": "127.0.0.1", "port": 4002, "readonly": True}


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
    broker(tmp_path, offen=offen).sende(Auftrag("fundamental_a", "v9", "SPYI.DE", 1, 1, 204.0), set())


def test_orderaufbau(tmp_path):
    b = broker(tmp_path)
    b.sende(KAUF, set())
    b.sende(Auftrag("real", "v3", "SPYI.DE", -1, 1, None), set())
    (k1, o1), (k2, o2) = b.ib.gesendet
    assert (k1.symbol, k1.exchange, k1.currency) == ("SPYI", "IBIS", "EUR")
    assert (o1.action, o1.orderType, o1.lmtPrice, o1.tif, o1.orderRef) == ("BUY", "LMT", 204.0, "DAY", "real:v1")
    assert (o2.action, o2.orderType, o2.tif, o2.orderRef) == ("SELL", "MKT", "DAY", "real:v3")
    with pytest.raises(SendenGesperrt, match="Kauf ohne Limit"):
        b.sende(Auftrag("real", "v4", "SPYI.DE", 1, 1, None), set())
