"""Interactive Brokers über das lokale IB Gateway (ib_async). Zugangsdaten nie im Code; Host, Port und Client-ID aus .env
(IB_HOST, IB_PORT, IB_CLIENT_ID), Modus aus TRADING_MODE. Verbindung nur zu 127.0.0.1:4002 (Paper), Live-Port 4001
gesperrt. Lesen geht immer; Senden nur, wenn alle Riegel aus broker/basis.py offen sind.

Orders: Kauf als Limit-Order (Vortagesschluss + 2 %), Verkauf als Market-Order, beide mit Gültigkeit DAY. Nach
Börsenschluss gesendet gelten sie für den nächsten Handelstag und gehen in die Xetra-Eröffnungsauktion. Kennung je Order:
orderRef = „<Buch>:<Vorschlag-ID>“ (Zuordnung zu Buch und Journal, Doppel-Order-Schutz).
"""
from __future__ import annotations

import os
from pathlib import Path

from tradingbot.broker.basis import Auftrag, OffeneOrder, Position, pruefe_senden, pruefe_verbindung


XETRA_ETF, XETRA_AKTIE = "IBIS2", "IBIS"    # IBKR-Börsenkennungen: Xetra-ETFs/ETCs und Xetra-Aktien (geprüft 02.11.2026)


def kontrakt(ticker: str, art: str = "etf", waehrung: str | None = None):
    """Yahoo-Ticker → IBKR-Kontrakt. „XYZ.DE“ = Xetra direkt (ETF/ETC: IBIS2, Aktie: IBIS; EUR), damit die Order in
    die Xetra-Eröffnungsauktion geht; sonst US-Aktie (SMART, USD)."""
    from ib_async import Stock

    if ticker.endswith(".DE"):
        return Stock(ticker[:-3], XETRA_ETF if art in ("etf", "etc") else XETRA_AKTIE, waehrung or "EUR")
    return Stock(ticker.replace("-", " "), "SMART", "USD")      # Yahoo „BF-B“ = IBKR „BF B“


def ticker_aus(kontrakt_) -> str:
    boerse = getattr(kontrakt_, "primaryExchange", "") or getattr(kontrakt_, "exchange", "")
    return f"{kontrakt_.symbol}.DE" if boerse in (XETRA_ETF, XETRA_AKTIE) or kontrakt_.currency == "EUR" else kontrakt_.symbol


class IbkrBroker:
    def __init__(self, betrieb: dict, projekt_wurzel: Path, *, host: str | None = None, port: int | None = None,
                 client_id: int | None = None, modus: str | None = None, ib=None):
        self.betrieb, self.wurzel = betrieb, Path(projekt_wurzel)
        self.host = host or os.getenv("IB_HOST", betrieb["ibkr"]["host"])
        self.port = int(port or os.getenv("IB_PORT", betrieb["ibkr"]["port_paper"]))
        self.client_id = int(client_id or os.getenv("IB_CLIENT_ID", "1"))
        self.modus = modus if modus is not None else os.getenv(betrieb["ibkr"]["modus_variable"])
        pruefe_verbindung(self.host, self.port, betrieb)          # schon beim Anlegen: kein Objekt für Port 4001
        if ib is None:
            from ib_async import IB

            ib = IB()
        self.ib = ib

    def verbinden(self) -> None:
        pruefe_verbindung(self.host, self.port, self.betrieb)
        # readonly, solange Senden nicht freigeschaltet ist (zusätzlich zur Read-Only-Einstellung im Gateway)
        readonly = not self.betrieb["ibkr"].get("senden_freigeschaltet", False)
        self.ib.connect(self.host, self.port, clientId=self.client_id, timeout=10, readonly=readonly)

    def trennen(self) -> None:
        self.ib.disconnect()

    def konto_id(self) -> str:
        konten = self.ib.managedAccounts()
        if len(konten) != 1:
            raise RuntimeError(f"genau ein Konto erwartet, gefunden: {konten}")
        return konten[0]

    def nettowert(self) -> float:
        for w in self.ib.accountSummary(self.konto_id()):
            if w.tag == "NetLiquidation" and w.currency == "EUR":
                return float(w.value)
        raise RuntimeError("NetLiquidation in EUR nicht gefunden")

    def positionen(self) -> list[Position]:
        return [Position(p.account, ticker_aus(p.contract), float(p.position), float(p.avgCost)) for p in self.ib.positions()
                if getattr(p.contract, "secType", "STK") != "CASH"]              # Devisenbestände sind Kasse, keine Position

    def offene_orders(self) -> list[OffeneOrder]:
        ergebnis = []
        for t in self.ib.openTrades():
            o = t.order
            ergebnis.append(OffeneOrder(o.orderRef or "", ticker_aus(t.contract), 1 if o.action == "BUY" else -1, float(o.totalQuantity),
                                        float(o.lmtPrice) if o.orderType == "LMT" else None, t.orderStatus.status))
        return ergebnis

    def verbunden(self) -> bool:
        return bool(self.ib.isConnected())

    def ausfuehrungen(self) -> list[dict]:
        """Ausführungen der Bot-Orders (orderRef „<Buch>:<ID>“) mit Preis und Gebühr in der Handelswährung.
        Devisentausch (secType CASH): art „fx“, Stück = verkaufte EUR, Preis = USD je EUR."""
        ergebnis = []
        for f in self.ib.fills():
            e = f.execution
            if not e.orderRef or ":" not in e.orderRef:
                continue
            gebuehr = float(f.commissionReport.commission or 0.0) if f.commissionReport else 0.0
            if getattr(f.contract, "secType", "") == "CASH":
                ergebnis.append({"art": "fx", "exec_id": e.execId, "order_ref": e.orderRef, "von": f.contract.symbol, "nach": f.contract.currency,
                                 "betrag_von": float(e.shares), "betrag_nach": float(e.shares) * float(e.price), "kurs": float(e.price),
                                 "gebuehr": gebuehr, "gebuehr_waehrung": (f.commissionReport.currency if f.commissionReport else None) or f.contract.currency,
                                 "zeit": str(e.time)})
                continue
            ergebnis.append({"exec_id": e.execId, "order_ref": e.orderRef, "ticker": ticker_aus(f.contract),
                             "richtung": 1 if e.side == "BOT" else -1, "stueck": float(e.shares), "preis": float(e.price),
                             "waehrung": f.contract.currency, "gebuehr": gebuehr,
                             "gebuehr_waehrung": (f.commissionReport.currency if f.commissionReport else None) or f.contract.currency,
                             "zeit": str(e.time)})
        return ergebnis

    def sende(self, auftrag: Auftrag, gesendete_refs: set[str]) -> str:
        """Sendet einen freigegebenen Auftrag; vorher alle Riegel (inkl. offener Orders beim Broker) prüfen."""
        from ib_async import LimitOrder, MarketOrder

        pruefe_senden(konto_id=self.konto_id(), port=self.port, modus=self.modus, betrieb=self.betrieb, projekt_wurzel=self.wurzel,
                      auftrag=auftrag, offene=self.offene_orders(), gesendete_refs=gesendete_refs)
        aktion = "BUY" if auftrag.richtung > 0 else "SELL"
        if auftrag.art == "fx":
            from ib_async import Forex

            trade = self.ib.placeOrder(Forex(f"EUR{auftrag.waehrung or 'USD'}"), MarketOrder("SELL", auftrag.stueck, tif="DAY", orderRef=auftrag.order_ref))
            gesendete_refs.add(auftrag.order_ref)
            return str(trade.order.orderId)
        if auftrag.richtung > 0:
            order = LimitOrder(aktion, auftrag.stueck, round(auftrag.limit, 2), tif="DAY", orderRef=auftrag.order_ref)
        else:
            order = MarketOrder(aktion, auftrag.stueck, tif="DAY", orderRef=auftrag.order_ref)
        trade = self.ib.placeOrder(kontrakt(auftrag.ticker, auftrag.art, auftrag.waehrung), order)
        gesendete_refs.add(auftrag.order_ref)
        return str(trade.order.orderId)
