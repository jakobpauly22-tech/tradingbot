r"""Ausführungen außerhalb des API-Zeitfensters nachtragen, ohne Tageslauf (Jakob 09.11.2026; Regeln in betrieb/nachtrag.py).

Verbindet nur lesend mit dem Gateway, erkennt Orders „unterwegs“, deren Handelstag vorbei ist, und trägt sie mit Beleg nach
(Flex-Abfrage, sonst Position mit Einstand). Danach Bestands- und Kassen-Abgleich. Ohne Beleg wird nichts gebucht.

  .venv\Scripts\python tools\ausfuehrungen_nachtragen.py            Trockenlauf auf einer Kopie des Journals
  .venv\Scripts\python tools\ausfuehrungen_nachtragen.py --buchen   echtes Journal (Sicherung vorher und nachher, Laufsperre)
"""
import argparse
import shutil
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from tradingbot.backtest.tresor import betriebsmodus
from tradingbot.betrieb import nachtrag
from tradingbot.betrieb.journal import Journal, konto_kurz
from tradingbot.betrieb.kalender import letzte_abgeschlossene_sitzung
from tradingbot.betrieb.speicher import betriebspfad
from tradingbot.betrieb.sperre import laufsperre
from tradingbot.betrieb.tageslauf import _eroeffnung_fn, _yahoo_kurse, abgleich, kassenabgleich
from tradingbot.broker.ibkr import IbkrBroker
from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration
from tradingbot.risiko.manager import RiskManager

BERLIN = ZoneInfo("Europe/Berlin")


def ausfuehren(journal, b, broker, jetzt) -> int:
    risk = RiskManager.aus_konfig()
    xetra = letzte_abgeschlossene_sitzung("xetra", jetzt)
    fx = {"USD": float(_yahoo_kurse("EURUSD=X", xetra, "fx")["close"].iloc[-1])}
    offen = broker.offene_orders()
    positionen = broker.positionen()
    kasse = broker.kasse_je_waehrung()
    print(f"Konto {konto_kurz(broker.konto_id())}, letzte Xetra-Sitzung {xetra:%d.%m.%Y}, EURUSD {fx['USD']:.4f}")
    print(f"API-Ausführungen (reqExecutions): {len(broker.ausfuehrungen())}; offene Orders: {len(offen)}")
    print("IBKR-Positionen: " + ", ".join(f"{p.ticker} {p.stueck:g} @ Einstand {p.einstand:.6f}" for p in positionen))
    print("IBKR-Kasse: " + ", ".join(f"{w} {v:,.2f}" for w, v in kasse.items()))
    buecher = list(b["buecher"])
    k = nachtrag.klaeren(journal, buecher, {o.order_ref for o in offen}, positionen, xetra, kasse_ibkr=kasse or None)
    print(f"Unterwegs und Handelstag vorbei: {len(k.verdacht)} Verdacht (Position weicht ab), {len(k.verfallen)} ohne Abweichung")
    if k.verfallen:
        print("  ohne Abweichung (würde der Tageslauf als verfallen markieren): " + ", ".join(z["id"] for z in k.verfallen))
    nachtrag.nachtragen(journal, buecher, k, positionen, fx, kosten=risk.kosten, kurse_laden=_yahoo_kurse, flex=nachtrag.flex_aus_env(),
                        gebuehrenplan=(b.get("nachtrag") or {}).get("gebuehr"), eroeffnung=_eroeffnung_fn(_yahoo_kurse))
    for h in k.hinweise:
        print(f"Hinweis: {h}")
    if k.ohne_beleg:
        print("OHNE BELEG – nichts gebucht:")
        for x in k.ohne_beleg:
            print(f"  {x}")
        return 1
    for x in k.gebucht:
        print(x)
    diff = abgleich(journal, buecher, positionen)
    print("Bestands-Abgleich: " + ("stimmt" if not diff else "WEICHT AB: " + "; ".join(diff)))
    if diff:
        return 1
    kdiff, text = kassenabgleich(journal, buecher, broker, b)
    print(text or "; ".join(kdiff))
    for n in buecher:
        print(f"  {n}: Bestand {journal.bestand(n) or '–'}, Kasse {journal.kasse(n):,.2f} € (je Währung "
              + ", ".join(f"{w} {v:,.2f}" for w, v in journal.kasse_je_waehrung(n).items()) + ")")
    return 1 if kdiff else 0


def main() -> int:
    load_dotenv(PROJEKT_WURZEL / ".env")
    a = argparse.ArgumentParser()
    a.add_argument("--buchen", action="store_true", help="ins echte Journal buchen (sonst Kopie)")
    arg = a.parse_args()
    b = lade_konfiguration("betrieb")
    jetzt = datetime.now(BERLIN)
    with betriebsmodus("Nachtrag Ausführungen" + (" (Buchung)" if arg.buchen else " (Trockenlauf, Kopie)")):
        with laufsperre(betriebspfad("tageslauf.sperre"), zweck="Nachtrag Ausführungen"):
            echt = betriebspfad("journal.sqlite")
            if arg.buchen:
                journal = Journal(echt)
                ziel = journal.sichern(None)
                if ziel is None:
                    print("ABBRUCH: keine Sicherung (JOURNAL_BACKUP_DIR fehlt)")
                    return 1
                print(f"gesichert vorher: {ziel.name}")
            else:
                kopie = betriebspfad(f"probe/nachtrag_kopie_{jetzt:%Y-%m-%d_%H%M%S}.sqlite")
                kopie.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(echt, kopie)
                print(f"Trockenlauf auf Kopie {kopie.relative_to(PROJEKT_WURZEL)}")
                journal = Journal(kopie)
            broker = IbkrBroker(b, PROJEKT_WURZEL, nur_lesen=True, client_id=93)
            broker.verbinden()
            try:
                rc = ausfuehren(journal, b, broker, jetzt)
            finally:
                broker.trennen()
            if arg.buchen:
                ziel = journal.sichern(None)
                print(f"gesichert nachher: {ziel.name if ziel else '–'}")
            journal.schliessen()
            return rc


if __name__ == "__main__":
    sys.exit(main())
