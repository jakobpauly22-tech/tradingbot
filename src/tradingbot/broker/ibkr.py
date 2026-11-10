"""Interactive Brokers über das lokale IB Gateway (ib_async). Zugangsdaten nie im Code; Host, Port und Client-ID aus .env
(IB_HOST, IB_PORT, IB_CLIENT_ID), Modus aus TRADING_MODE. Verbindung nur zu 127.0.0.1:4002 (Paper), Live-Port 4001
gesperrt. Lesen geht immer; Senden nur, wenn alle Riegel aus broker/basis.py offen sind.

Orders: Kauf als Limit-Order (Vortagesschluss + 2 %), Verkauf als Market-Order, beide mit Gültigkeit DAY. Nach
Börsenschluss gesendet gelten sie für den nächsten Handelstag und gehen in die Xetra-Eröffnungsauktion. Kennung je Order:
orderRef = „<Buch>:<Vorschlag-ID>“ (Zuordnung zu Buch und Journal, Doppel-Order-Schutz).
"""
from __future__ import annotations

import math
import os
import time
from functools import lru_cache
from pathlib import Path

from tradingbot.broker.basis import (Auftrag, KontraktUnbekannt, OffeneOrder, Position, SendeErgebnis, SendenGesperrt, pruefe_senden,
                                     pruefe_verbindung)

ANGENOMMEN = {"PreSubmitted", "Submitted", "Filled"}
ROUTING = "SMART"            # Jakob 03.11.2026: Direktrouting an IBIS2 sperren die API-Vorsichtseinstellungen (Fehler 10311)


def stufe_fuer(regel: list, preis: float) -> float:
    """Preisstufe einer IBKR-Marktregel (Liste von (lowEdge, increment)) für ein Preisniveau: größte Untergrenze ≤ Preis."""
    passend = [s for s in regel if s[0] <= preis + 1e-12]
    return float(max(passend, key=lambda s: s[0])[1]) if passend else float(regel[0][1])


def gemeinsame_stufe(stufen: list[float]) -> float:
    """Kleinste Stufe, die ein Vielfaches aller Stufen ist (kgV in 1e-6-Einheiten): gilt für SMART und IBIS2 zugleich."""
    einheiten = [max(int(round(s * 1_000_000)), 1) for s in stufen]
    k = einheiten[0]
    for e in einheiten[1:]:
        k = k * e // math.gcd(k, e)
    return k / 1_000_000


def auf_stufe(preis: float, stufe: float, richtung: int) -> float:
    """Kauflimit auf die gültige Kursstufe abrunden, Verkaufslimit aufrunden (nie über die 2-%-Grenze hinaus)."""
    n = preis / stufe
    n = math.floor(n + 1e-9) if richtung > 0 else math.ceil(n - 1e-9)
    return round(n * stufe, 6)
ABGELEHNT = {"Cancelled", "ApiCancelled", "Inactive", "ValidationError"}   # ValidationError: z. B. 321 Read-Only (09.11.2026)
READ_ONLY_CODE = 321                 # „Die API befindet sich im schreibgeschützten Modus“


@lru_cache(maxsize=1)
def kontrakttabelle() -> dict[str, dict]:
    """Zuordnung Ticker → IBKR-Kontrakt aus config/kontrakte.yaml (tools/kontrakte_pruefen.py); leer, wenn die Datei fehlt."""
    from tradingbot.konfiguration import PROJEKT_WURZEL

    pfad = PROJEKT_WURZEL / "config" / "kontrakte.yaml"
    if not pfad.exists():
        return {}
    from ruamel.yaml import YAML

    daten = YAML(typ="safe").load(pfad.read_text(encoding="utf-8")) or {}
    return dict(daten.get("kontrakte") or {})


@lru_cache(maxsize=1)
def nicht_aufloesbar() -> dict[str, str]:
    """Titel, die tools/kontrakte_pruefen.py nicht eindeutig zuordnen konnte (mit Grund)."""
    from tradingbot.konfiguration import PROJEKT_WURZEL

    pfad = PROJEKT_WURZEL / "config" / "kontrakte.yaml"
    if not pfad.exists():
        return {}
    from ruamel.yaml import YAML

    return dict((YAML(typ="safe").load(pfad.read_text(encoding="utf-8")) or {}).get("nicht_aufloesbar") or {})


def _ticker_je_conid() -> dict[int, str]:
    return {int(e["con_id"]): t for t, e in kontrakttabelle().items()}


XETRA_ETF, XETRA_AKTIE = "IBIS2", "IBIS"    # IBKR-Börsenkennungen: Xetra-ETFs/ETCs und Xetra-Aktien (geprüft 02.11.2026)


def kontrakt(ticker: str, art: str = "etf", waehrung: str | None = None):
    """Yahoo-Ticker → IBKR-Kontrakt. „XYZ.DE“ = Xetra direkt (ETF/ETC: IBIS2, Aktie: IBIS; EUR), damit die Order in
    die Xetra-Eröffnungsauktion geht; sonst US-Aktie (SMART, USD)."""
    from ib_async import Stock

    if ticker.endswith(".DE"):
        return Stock(ticker[:-3], XETRA_ETF if art in ("etf", "etc") else XETRA_AKTIE, waehrung or "EUR")
    return Stock(ticker.replace("-", " "), "SMART", "USD")      # Yahoo „BF-B“ = IBKR „BF B“


def us_aktie(auftrag) -> bool:
    return auftrag.art == "aktie" and not auftrag.ticker.endswith(".DE")


def ibkr_gebuehr(fill) -> float | None:
    """Gebühr aus dem CommissionReport; None, wenn keiner vorliegt oder IBKR den Leerwert (UNSET_DOUBLE) meldet."""
    bericht = getattr(fill, "commissionReport", None)
    wert = getattr(bericht, "commission", None) if bericht else None
    if wert is None or not math.isfinite(float(wert)) or abs(float(wert)) > 1e100:
        return None
    return float(wert)


def ticker_aus(kontrakt_) -> str:
    """IBKR-Kontrakt → Yahoo-Ticker; zuerst über die conId aus der Zuordnungstabelle (IBKR-Symbol „IEMA“ = EUNM.DE)."""
    cid = int(getattr(kontrakt_, "conId", 0) or 0)
    if cid and cid in _ticker_je_conid():
        return _ticker_je_conid()[cid]
    boerse = getattr(kontrakt_, "primaryExchange", "") or getattr(kontrakt_, "exchange", "")
    return f"{kontrakt_.symbol}.DE" if boerse in (XETRA_ETF, XETRA_AKTIE) or kontrakt_.currency == "EUR" else kontrakt_.symbol


class IbkrBroker:
    def __init__(self, betrieb: dict, projekt_wurzel: Path, *, host: str | None = None, port: int | None = None,
                 client_id: int | None = None, modus: str | None = None, ib=None, nur_lesen: bool = False):
        self.betrieb, self.wurzel = betrieb, Path(projekt_wurzel)
        self.nur_lesen = nur_lesen                       # Probeläufe und Werkzeuge (09.11.2026): readonly, Senden gesperrt
        self.host = host or os.getenv("IB_HOST", betrieb["ibkr"]["host"])
        self.port = int(port or os.getenv("IB_PORT", betrieb["ibkr"]["port_paper"]))
        self.client_id = int(client_id or os.getenv("IB_CLIENT_ID", "1"))
        self.modus = modus if modus is not None else os.getenv(betrieb["ibkr"]["modus_variable"])
        pruefe_verbindung(self.host, self.port, betrieb)          # schon beim Anlegen: kein Objekt für Port 4001
        if ib is None:
            from ib_async import IB

            ib = IB()
        self.ib = ib
        self.gateway_meldungen: list[str] = []          # Fehlermeldungen des Gateways (z. B. Read-Only-Ablehnungen) fürs Protokoll
        self.waehrend_warten = None                       # Rückruf beim Warten auf IBKR (Fenster bedienbar halten, 10.11.2026)
        ereignis = getattr(ib, "errorEvent", None)
        if ereignis is not None:
            ereignis += self._gateway_fehler

    def _gateway_fehler(self, req_id, code, text, *rest) -> None:
        if code in (2104, 2106, 2107, 2108, 2158):        # reine Statusmeldungen der Datenfarmen
            return
        self.gateway_meldungen.append(f"Gateway-Meldung {code}: {text}")

    def verbinden(self) -> None:
        """Verbindet mit dem lokalen Gateway.

        readonly, solange Senden nicht freigeschaltet ist (zusätzlich zur Read-Only-Einstellung im Gateway). Beim Start
        ruft ib_async Positionen, offene Orders, Kontodaten und Ausführungen (reqExecutions) ab; den Abruf abgeschlossener
        Orders (ReqCompletedOrders) lassen wir bewusst weg: der Bot braucht ihn nicht (Ausführungen kommen aus
        reqExecutions, der Abgleich aus den Positionen), und IBKR wertet ihn im Read-Only-Modus als Schreibzugriff
        (Hinweis vom Gateway, 03.11.2026)."""
        from ib_async.ib import StartupFetch, StartupFetchALL

        pruefe_verbindung(self.host, self.port, self.betrieb)
        readonly = self.nur_lesen or not self.betrieb["ibkr"].get("senden_freigeschaltet", False)
        self.ib.connect(self.host, self.port, clientId=self.client_id, timeout=10, readonly=readonly,
                        fetchFields=StartupFetchALL & ~StartupFetch.ORDERS_COMPLETE)

    def schreibzugriff(self, wartezeit: float = 3.0) -> tuple[bool, str]:
        """Prüft vor dem Senden, ob das Gateway Schreibzugriffe annimmt, ohne eine Order zu übergeben (Jakob 10.11.2026).

        Probe ist `reqCompletedOrders` (reine Abfrage, keine Order): Im Read-Only-Modus antwortet das Gateway sofort mit
        Fehler 321 („Die API befindet sich im schreibgeschützten Modus“) und nie mit dem Listenende (geprüft 10.11.2026).
        Ergebnis: (True, …) nur bei vollständiger Antwort; Fehler 321 oder keine Antwort → (False, Grund)."""
        vorher = len(self.gateway_meldungen)
        alt = getattr(self.ib, "RequestTimeout", 0)
        self.ib.RequestTimeout = wartezeit
        try:
            self.ib.reqCompletedOrders(apiOnly=True)
            antwort = True
        except Exception:  # noqa: BLE001 – TimeoutError (keine Antwort) oder Abbruch
            antwort = False
        finally:
            self.ib.RequestTimeout = alt
        neu = self.gateway_meldungen[vorher:]
        if any(m.startswith(f"Gateway-Meldung {READ_ONLY_CODE}:") for m in neu):
            return False, "Read-Only im Gateway ist aktiv (Fehler 321 auf eine reine Abfrage)"
        if not antwort:
            return False, f"Gateway hat die Schreibprüfung nicht in {wartezeit:.0f} s beantwortet – nicht gesendet"
        return True, "Schreibzugriff im Gateway geprüft"

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

    def kasse_je_waehrung(self) -> dict[str, float]:
        """Kontokasse je Währung laut IBKR (accountValues, ohne die Summenzeile BASE). Das Paper-Konto meldet die Kasse als
        „$LEDGER-CashBalance“ (geprüft 09.11.2026), nicht als „CashBalance“; bis dahin blieb der Kassen-Abgleich ungeprüft.
        Aufgelaufene, noch nicht gebuchte Zinsen (AccruedCash) zählen nicht."""
        kassen: dict[str, dict[str, float]] = {"CashBalance": {}, "$LEDGER-CashBalance": {}}
        for w in self.ib.accountValues():
            if w.tag in kassen and w.currency and w.currency != "BASE":
                kassen[w.tag][w.currency] = kassen[w.tag].get(w.currency, 0.0) + float(w.value)
        return kassen["CashBalance"] or kassen["$LEDGER-CashBalance"]

    def aufgelaufene_zinsen(self) -> dict[str, float]:
        """Aufgelaufene, noch nicht gebuchte Zinsen je Währung (accountValues „AccruedCash“, sonst „$LEDGER-AccruedCash“,
        ohne BASE). Für den Beleg von Zinsbuchungen im Kassen-Abgleich (Jakob 09.11.2026)."""
        werte: dict[str, dict[str, float]] = {"AccruedCash": {}, "$LEDGER-AccruedCash": {}}
        for w in self.ib.accountValues():
            if w.tag in werte and w.currency and w.currency != "BASE":
                werte[w.tag][w.currency] = werte[w.tag].get(w.currency, 0.0) + float(w.value)
        return werte["AccruedCash"] or werte["$LEDGER-AccruedCash"]

    def offene_orders(self) -> list[OffeneOrder]:
        """Alle offenen Orders des Kontos, auch die anderer Client-IDs (reqAllOpenOrders, reine Abfrage; Korrektur 10.11.2026:
        die Probe mit Client-ID 94 sah die Orders von Client 1 nicht und hielt sie für verfallen)."""
        if hasattr(self.ib, "reqAllOpenOrders"):
            try:
                self.ib.reqAllOpenOrders()
            except Exception:  # noqa: BLE001 – Abfrage fehlgeschlagen: wenigstens die eigenen Orders
                pass
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
            gebuehr = ibkr_gebuehr(f)                     # None = (noch) kein CommissionReport
            if getattr(f.contract, "secType", "") == "CASH":
                ergebnis.append({"art": "fx", "exec_id": e.execId, "order_ref": e.orderRef, "von": f.contract.symbol, "nach": f.contract.currency,
                                 "betrag_von": float(e.shares), "betrag_nach": float(e.shares) * float(e.price), "kurs": float(e.price),
                                 "gebuehr": gebuehr, "gebuehr_waehrung": (f.commissionReport.currency if f.commissionReport else None) or f.contract.currency,
                                 "zeit": str(e.time)})
                continue
            ergebnis.append({"exec_id": e.execId, "order_ref": e.orderRef, "ticker": ticker_aus(f.contract), "boerse": e.exchange,
                             "richtung": 1 if e.side == "BOT" else -1, "stueck": float(e.shares), "preis": float(e.price),
                             "waehrung": f.contract.currency, "gebuehr": gebuehr,
                             "gebuehr_waehrung": (f.commissionReport.currency if f.commissionReport else None) or f.contract.currency,
                             "zeit": str(e.time)})
        return ergebnis

    def kontrakt_aufloesen(self, ticker: str, art: str = "etf", waehrung: str | None = None):
        """Qualifiziert den Kontrakt vor dem Senden (Jakob 03.11.2026): Werte aus config/kontrakte.yaml über ihre conId,
        sonst über Symbol/Börse/Währung (US-Aktien) bzw. EUR.USD als Forex. Verlangt genau einen Treffer mit conId ≠ 0,
        passender Währung und – bei Tabellenwerten – derselben conId; sonst `KontraktUnbekannt`."""
        from ib_async import Contract, Forex

        eintrag = kontrakttabelle().get("EUR.USD" if art == "fx" else ticker)
        if art != "fx" and ticker in nicht_aufloesbar():
            raise KontraktUnbekannt(f"Kontrakt unbekannt: {ticker} – {nicht_aufloesbar()[ticker]} (config/kontrakte.yaml)")
        if art == "fx":
            anfrage, erwartet = Forex(f"EUR{waehrung or 'USD'}"), waehrung or "USD"
        elif eintrag:
            # nur conId plus SMART; IBKR liefert Symbol, localSymbol und primaryExchange (Fehler 478 am 03.11.2026, als das
            # Xetra-Kürzel EUNM gegen das SMART-Symbol IEMA stand)
            anfrage, erwartet = Contract(conId=int(eintrag["con_id"]), exchange=ROUTING), eintrag["waehrung"]
        else:
            anfrage = kontrakt(ticker, art, waehrung)
            erwartet = anfrage.currency
        try:
            treffer = self.ib.reqContractDetails(anfrage)
        except Exception as f:  # noqa: BLE001
            raise KontraktUnbekannt(f"Kontrakt unbekannt: {ticker} ({type(f).__name__}: {f})") from f
        if len(treffer) != 1:
            raise KontraktUnbekannt(f"Kontrakt unbekannt: {ticker} – {len(treffer)} Treffer bei IBKR")
        k = treffer[0].contract
        if not k.conId:
            raise KontraktUnbekannt(f"Kontrakt unbekannt: {ticker} – conId 0")
        if k.currency != erwartet:
            raise KontraktUnbekannt(f"Kontrakt unbekannt: {ticker} – Währung {k.currency} statt {erwartet}")
        if eintrag and int(k.conId) != int(eintrag["con_id"]):
            raise KontraktUnbekannt(f"Kontrakt unbekannt: {ticker} – conId {k.conId} statt {eintrag['con_id']}")
        # Kursregeln für SMART und den Xetra-Platz merken (marketRuleIds passen der Reihe nach zu validExchanges)
        cd = treffer[0]
        plaetze = dict(zip(str(getattr(cd, "validExchanges", "") or "").split(","), str(getattr(cd, "marketRuleIds", "") or "").split(",")))
        self._regel_ids = getattr(self, "_regel_ids", {})
        platz = (eintrag or {}).get("boerse") or (XETRA_ETF if art != "aktie" else XETRA_AKTIE)
        self._regel_ids[ticker] = sorted({int(plaetze[p]) for p in ("SMART", platz) if plaetze.get(p)})
        if eintrag and art != "fx" and k.exchange != ROUTING:
            raise KontraktUnbekannt(f"Kontrakt unbekannt: {ticker} – Routing {k.exchange} statt {ROUTING}")
        return k                                                   # unverändert, wie von IBKR qualifiziert

    def kursstufe(self, ticker: str, preis: float) -> float:
        """Gültige Kursstufe für einen Preis (reqMarketRule, Regeln von SMART und Xetra; Ergebnis gilt für beide)."""
        ids = getattr(self, "_regel_ids", {}).get(ticker)
        if not ids:
            raise KontraktUnbekannt(f"Kursregel für {ticker} unbekannt – erst Kontrakt qualifizieren")
        self._regeln = getattr(self, "_regeln", {})
        stufen = []
        for i in ids:
            if i not in self._regeln:
                self._regeln[i] = [(float(s.lowEdge), float(s.increment)) for s in self.ib.reqMarketRule(i)]
            stufen.append(stufe_fuer(self._regeln[i], preis))
        return gemeinsame_stufe(stufen)

    def limit_runden(self, ticker: str, preis: float, richtung: int) -> tuple[float, float]:
        """Limit auf die gültige Kursstufe: Kauf abrunden, Verkauf aufrunden. Gibt (Limit, Stufe) zurück."""
        stufe = self.kursstufe(ticker, preis)
        return auf_stufe(preis, stufe, richtung), stufe

    def _warte_auf_antwort(self, trade, sekunden: float) -> SendeErgebnis:
        """Wartet kurz auf die Antwort von IBKR: angenommen, abgelehnt (mit Fehlertext) oder unbestätigt."""
        ende = time.monotonic() + sekunden
        while True:
            status = trade.orderStatus.status
            if status in ANGENOMMEN or status in ABGELEHNT or time.monotonic() >= ende:
                break
            self.ib.sleep(0.2)
            if self.waehrend_warten is not None:
                self.waehrend_warten()
        texte = [f"{e.errorCode}: {e.message}" if getattr(e, "errorCode", 0) else e.message for e in getattr(trade, "log", []) if e.message]
        oid = str(trade.order.orderId)
        cid = int(getattr(trade.contract, "conId", 0) or 0)
        if status in ANGENOMMEN:
            return SendeErgebnis(oid, "angenommen", status, cid)
        if status in ABGELEHNT:
            return SendeErgebnis(oid, "abgelehnt", "; ".join(texte) or status, cid)
        return SendeErgebnis(oid, "unbestaetigt", f"Status {status} nach {sekunden:.0f} s" + (": " + "; ".join(texte) if texte else ""), cid)

    def sende(self, auftrag: Auftrag, gesendete_refs: set[str], *, wartezeit: float = 8.0) -> SendeErgebnis:
        """Sendet einen freigegebenen Auftrag; vorher alle Riegel (inkl. offener Orders beim Broker) prüfen und den
        Kontrakt qualifizieren. Ergebnis erst nach der Antwort von IBKR (angenommen/abgelehnt/unbestätigt)."""
        from ib_async import LimitOrder, MarketOrder

        if self.nur_lesen:
            raise SendenGesperrt("Verbindung nur lesend (Probelauf/Werkzeug) – Senden gesperrt")
        pruefe_senden(konto_id=self.konto_id(), port=self.port, modus=self.modus, betrieb=self.betrieb, projekt_wurzel=self.wurzel,
                      auftrag=auftrag, offene=self.offene_orders(), gesendete_refs=gesendete_refs)
        k = self.kontrakt_aufloesen(auftrag.ticker, auftrag.art, auftrag.waehrung)
        aktion = "BUY" if auftrag.richtung > 0 else "SELL"
        if auftrag.art == "fx":
            order = MarketOrder("SELL", auftrag.stueck, tif="DAY", orderRef=auftrag.order_ref)
        elif auftrag.richtung > 0:
            limit, _ = self.limit_runden(auftrag.ticker, auftrag.limit, auftrag.richtung)     # Kursstufe (Fehler 110 am 03.11.2026)
            # US-Käufe als Limit-On-Open (Jakob 04.11.2026): Ausführung zur Eröffnung, unabhängig von der Freigabezeit.
            # Nimmt IBKR OPG nicht an, wird die Order abgelehnt gemeldet – kein Ersatz-Ordertyp ohne Jakobs Zustimmung.
            tif = "OPG" if us_aktie(auftrag) else "DAY"
            order = LimitOrder(aktion, auftrag.stueck, limit, tif=tif, orderRef=auftrag.order_ref)
        else:
            order = MarketOrder(aktion, auftrag.stueck, tif="DAY", orderRef=auftrag.order_ref)
        trade = self.ib.placeOrder(k, order)
        gesendete_refs.add(auftrag.order_ref)
        return self._warte_auf_antwort(trade, wartezeit)
