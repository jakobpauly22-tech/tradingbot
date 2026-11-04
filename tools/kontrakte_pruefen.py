r"""Zuordnungstabelle Ticker → IBKR-Kontrakt (nur lesend, Jakob 03./04.11.2026).

Geprüft werden das ganze Universum der Bücher und der Devisentausch:
- Core-ETF (config/betrieb.yaml) und Satellite-Universum (config/technik.yaml) über die ISIN: reqContractDetails mit
  ISIN und SMART; verlangt wird genau ein Kontrakt in der Handelswährung, der an Xetra (IBIS2 für ETFs, IBIS für ETCs
  und Aktien) handelbar ist (validExchanges).
- S&P-500-Aktien (aktuelle Mitglieder, Yahoo-Symbole aus daten/universum/kursstatus.csv) über Symbol, SMART und USD
  („BF-B“ → „BF B“); verlangt wird genau ein Treffer.
- EUR→USD-Tausch: Forex EUR.USD an IDEALPRO.
Ergebnis in config/kontrakte.yaml (conId, IBKR-Symbol, lokales Kürzel, Xetra-Platz bzw. Primärbörse, Währung, Name).
Nicht auflösbare Titel stehen im Bericht und in der Datei unter `nicht_aufloesbar`, ohne Eintrag in `kontrakte`; der
Bot vergibt für sie beim Senden ein Veto „Kontrakt unbekannt“.

Aufruf (Gateway läuft, Read-Only darf an sein):
  .venv\Scripts\python tools\kontrakte_pruefen.py            # ETFs, ETC, Tausch und S&P 500
  .venv\Scripts\python tools\kontrakte_pruefen.py --ohne-aktien
"""
import argparse
import sys
from datetime import date

import pandas as pd
from dotenv import load_dotenv
from ruamel.yaml import YAML

from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration

ZIEL = PROJEKT_WURZEL / "config" / "kontrakte.yaml"


def fonds() -> list[dict]:
    b, t = lade_konfiguration("betrieb"), lade_konfiguration("technik")
    liste = [{"ticker": b["core"]["etf"], "isin": b["core"]["isin"], "waehrung": "EUR", "art": "etf"}]
    for e in t["universum"]["etfs"]:
        liste.append({"ticker": e["ticker"], "isin": e["isin"], "waehrung": e.get("handelswaehrung", "EUR"),
                      "art": "etc" if e.get("steuerart") == "etc" else "etf"})
    return liste


def sp500_symbole() -> list[str]:
    """Yahoo-Symbole der heutigen S&P-500-Mitglieder (Betriebsmodus: Daten nach dem Tresor-Stichtag)."""
    from tradingbot.backtest.tresor import betriebsmodus
    from tradingbot.daten.universum import lade_universum, mitglieder_am

    with betriebsmodus("Kontraktprüfung S&P 500 (nur Mitgliederliste)"):
        universum, _ = lade_universum()
        aktiv = mitglieder_am(universum, pd.Timestamp(date.today()))
    status = pd.read_csv(PROJEKT_WURZEL / "daten" / "universum" / "kursstatus.csv").set_index("index")
    return sorted({str(status.loc[nr, "symbol"]) for nr in aktiv.index if nr in status.index and isinstance(status.loc[nr, "symbol"], str)})


def eintrag(cd, **extra) -> dict:
    k = cd.contract
    return {"con_id": int(k.conId), "symbol": k.symbol, "lokal": k.localSymbol, "primaer": k.primaryExchange or k.exchange,
            "waehrung": k.currency, "name": cd.longName, **extra}


def main() -> int:
    from ib_async import IB, Contract, Forex, Stock
    from ib_async.ib import StartupFetch

    arg = argparse.ArgumentParser()
    arg.add_argument("--ohne-aktien", action="store_true")
    a = arg.parse_args()
    load_dotenv(PROJEKT_WURZEL / ".env")
    ib = IB()
    ib.connect("127.0.0.1", 4002, clientId=95, timeout=15, readonly=True, fetchFields=StartupFetch(0))
    eintraege, fehler = {}, {}
    for w in fonds():
        platz = "IBIS" if w["art"] == "etc" else "IBIS2"
        treffer = [cd for cd in ib.reqContractDetails(Contract(secType="STK", secIdType="ISIN", secId=w["isin"], exchange="SMART"))
                   if cd.contract.currency == w["waehrung"] and platz in str(cd.validExchanges).split(",")]
        if len(treffer) != 1 or not treffer[0].contract.conId:
            fehler[w["ticker"]] = f"ISIN {w['isin']}: kein eindeutiger Kontrakt in {w['waehrung']} mit Xetra-Platz {platz} ({len(treffer)} Treffer)"
            continue
        eintraege[w["ticker"]] = eintrag(treffer[0], isin=w["isin"], boerse=platz, art=w["art"])
    fx = ib.reqContractDetails(Forex("EURUSD"))
    if len(fx) == 1:
        eintraege["EUR.USD"] = eintrag(fx[0], boerse="IDEALPRO", art="fx")
    else:
        fehler["EUR.USD"] = f"{len(fx)} Treffer"
    if not a.ohne_aktien:
        symbole = sp500_symbole()
        print(f"S&P 500: {len(symbole)} Symbole")
        for i, sym in enumerate(symbole, 1):
            treffer = ib.reqContractDetails(Stock(sym.replace("-", " "), "SMART", "USD"))
            if len(treffer) != 1 or not treffer[0].contract.conId:
                fehler[sym] = f"{len(treffer)} Treffer (Symbol {sym.replace('-', ' ')}, SMART, USD)"
            else:
                eintraege[sym] = eintrag(treffer[0], boerse="SMART", art="aktie")
            if i % 100 == 0:
                print(f"  {i} geprüft")
    ib.disconnect()
    if a.ohne_aktien and ZIEL.exists():                    # bestehende Aktien-Einträge (und ihre Fehler) behalten
        alt = YAML(typ="safe").load(ZIEL.read_text(encoding="utf-8")) or {}
        for t, e in (alt.get("kontrakte") or {}).items():
            if e.get("art") == "aktie":
                eintraege.setdefault(t, e)
        for t, x in (alt.get("nicht_aufloesbar") or {}).items():
            if not t.endswith(".DE") and t != "EUR.USD":
                fehler.setdefault(t, x)
    for t, e in eintraege.items():
        if e["art"] != "aktie":
            print(f"{t:9} conId {e['con_id']:>10}  Symbol {e['symbol']:6} lokal {e['lokal']:8} primär {e['primaer']:8} {e['waehrung']}  {e['name']}")
    yaml = YAML()
    yaml.width = 4096
    with ZIEL.open("w", encoding="utf-8") as f:
        f.write("# Zuordnung Ticker → IBKR-Kontrakt, erzeugt von tools/kontrakte_pruefen.py (nur lesend). Nicht von Hand ändern;\n"
                "# neu erzeugen. Gesendet wird der von IBKR unter SMART qualifizierte Kontrakt (conId); `boerse` = Xetra-Platz bzw.\n"
                "# IDEALPRO/SMART. Titel unter `nicht_aufloesbar` bekommen beim Senden ein Veto „Kontrakt unbekannt“.\n")
        yaml.dump({"stand": date.today().isoformat(), "kontrakte": eintraege, "nicht_aufloesbar": fehler}, f)
    for t, x in fehler.items():
        print(f"NICHT AUFLÖSBAR: {t}: {x}")
    print(f"{len(eintraege)} Kontrakte nach {ZIEL.relative_to(PROJEKT_WURZEL)}; {len(fehler)} nicht auflösbar")
    return 0


if __name__ == "__main__":
    sys.exit(main())
