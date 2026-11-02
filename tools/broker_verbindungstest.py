r"""Verbindungstest mit dem lokalen IB Gateway (Paper-Konto), NUR LESEND.

Voraussetzung: IB Gateway läuft, eingeloggt ins Paper-Konto; API aktiviert, Port 4002, „Read-Only API“ an, vertrauenswürdige
IP nur 127.0.0.1. In .env: IB_HOST=127.0.0.1, IB_PORT=4002, IB_CLIENT_ID=1, TRADING_MODE=paper.
Aufruf:  .venv\Scripts\python tools\broker_verbindungstest.py
Prüft: Verbindung, Konto ist Paper (DU…), Nettowert, Positionen, offene Orders, Marktdaten für SPYI (Xetra).
Sendet nichts (die Verbindung wird schreibgeschützt geöffnet, Senden ist in config/betrieb.yaml abgeschaltet).
"""
import sys

from dotenv import load_dotenv

from tradingbot.broker.ibkr import IbkrBroker, kontrakt
from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration


def main() -> int:
    load_dotenv(PROJEKT_WURZEL / ".env")
    betrieb = lade_konfiguration("betrieb")
    b = IbkrBroker(betrieb, PROJEKT_WURZEL)
    print(f"Verbinde mit {b.host}:{b.port} (Client-ID {b.client_id}, Modus {b.modus}) …")
    b.verbinden()
    try:
        konto = b.konto_id()
        paper = konto.startswith(betrieb["ibkr"]["konto_praefix_paper"])
        print(f"Konto: {konto[:4]}… → {'Paper-Konto' if paper else 'KEIN Paper-Konto – abbrechen!'}")
        if not paper:
            return 2
        print(f"Nettowert: {b.nettowert():,.2f} EUR")
        pos = b.positionen()
        print(f"Positionen: {len(pos)}" + "".join(f"\n  {p.ticker}: {p.stueck:g}" for p in pos))
        offen = b.offene_orders()
        print(f"Offene Orders: {len(offen)}" + "".join(f"\n  {o.order_ref} {o.ticker} {o.richtung:+d} {o.stueck:g} {o.status}" for o in offen))
        k = kontrakt(betrieb["core"]["etf"])
        b.ib.qualifyContracts(k)
        balken = b.ib.reqHistoricalData(k, endDateTime="", durationStr="5 D", barSizeSetting="1 day", whatToShow="TRADES", useRTH=True)
        if balken:
            print(f"Marktdaten {betrieb['core']['etf']}: letzter Tagesschluss {balken[-1].close} am {balken[-1].date} (historische Daten verfügbar)")
        else:
            print(f"Marktdaten {betrieb['core']['etf']}: keine Daten – Marktdaten-Freigabe im Paper-Konto prüfen")
    finally:
        b.trennen()
    return 0


if __name__ == "__main__":
    sys.exit(main())
