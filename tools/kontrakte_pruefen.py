r"""Zuordnungstabelle Ticker → IBKR-Kontrakt (nur lesend, Jakob 03.11.2026).

Für jeden Wert mit ISIN (Core-ETF aus config/betrieb.yaml, Satellite-Universum aus config/technik.yaml) wird der Kontrakt
per reqContractDetails über ISIN, Xetra-Börse (IBIS2) und Handelswährung gesucht. Genau ein Treffer → Eintrag in
config/kontrakte.yaml (conId, IBKR-Symbol, Xetra-Kürzel, Börse, Währung, Name). Kein oder mehrere Treffer → Fehler im
Bericht, kein Eintrag. Anlass: IBKR führt EUNM als „IEMA“ und EUNN als „IJPA“; Orders mit dem Xetra-Kürzel als Symbol
wurden am 03.11.2026 mit Fehler 200 abgelehnt.

Aufruf (Gateway läuft, Read-Only darf an sein):
  .venv\Scripts\python tools\kontrakte_pruefen.py
"""
import sys
from datetime import date

from dotenv import load_dotenv
from ruamel.yaml import YAML

from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration

ZIEL = PROJEKT_WURZEL / "config" / "kontrakte.yaml"


def werte() -> list[dict]:
    b, t = lade_konfiguration("betrieb"), lade_konfiguration("technik")
    liste = [{"ticker": b["core"]["etf"], "isin": b["core"]["isin"], "waehrung": "EUR", "art": "etf"}]
    for e in t["universum"]["etfs"]:
        liste.append({"ticker": e["ticker"], "isin": e["isin"], "waehrung": e.get("handelswaehrung", "EUR"),
                      "art": "etc" if e.get("steuerart") == "etc" else "etf"})
    return liste


def main() -> int:
    from ib_async import IB, Contract
    from ib_async.ib import StartupFetch

    load_dotenv(PROJEKT_WURZEL / ".env")
    ib = IB()
    ib.connect("127.0.0.1", 4002, clientId=95, timeout=15, readonly=True, fetchFields=StartupFetch(0))
    eintraege, fehler = {}, []
    for w in werte():
        treffer = ib.reqContractDetails(Contract(secType="STK", secIdType="ISIN", secId=w["isin"], exchange="IBIS2", currency=w["waehrung"]))
        if len(treffer) != 1 or not treffer[0].contract.conId:
            fehler.append(f"{w['ticker']} ({w['isin']}, IBIS2, {w['waehrung']}): {len(treffer)} Treffer")
            continue
        cd, k = treffer[0], treffer[0].contract
        eintraege[w["ticker"]] = {"isin": w["isin"], "con_id": int(k.conId), "symbol": k.symbol, "xetra_kuerzel": k.localSymbol,
                                  "boerse": "IBIS2", "waehrung": k.currency, "art": w["art"], "name": cd.longName}
        print(f"{w['ticker']:9} conId {k.conId:>10}  Symbol {k.symbol:6} Xetra {k.localSymbol:6} {k.currency}  {cd.longName}")
    ib.disconnect()
    yaml = YAML()
    yaml.default_flow_style = None
    with ZIEL.open("w", encoding="utf-8") as f:
        f.write("# Zuordnung Ticker → IBKR-Kontrakt, erzeugt von tools/kontrakte_pruefen.py (nur lesend, reqContractDetails über\n"
                "# ISIN, IBIS2, Handelswährung). Nicht von Hand ändern; neu erzeugen. Senden nur mit Kontrakt aus dieser Tabelle\n"
                "# oder eindeutiger Auflösung über das Symbol (US-Aktien), conId ≠ 0 (Jakob 03.11.2026).\n")
        yaml.dump({"stand": date.today().isoformat(), "kontrakte": eintraege}, f)
    for x in fehler:
        print("FEHLER:", x)
    print(f"{len(eintraege)} Kontrakte nach {ZIEL.relative_to(PROJEKT_WURZEL)}; {len(fehler)} Fehler")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
