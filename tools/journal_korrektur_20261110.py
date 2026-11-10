r"""Journal-Korrektur nach dem Read-Only-Vorfall vom 09.11.2026 (Jakob 10.11.2026). Nichts wird storniert.

Befund (lesend geprüft): Alle 41 offenen Bot-Orders bei IBKR stehen im Journal als „gesendet“ mit Order-ID
(fundamental_a 20, fundamental_b 19, momentum 2; momentum IUSA und SXR1 heute ausgeführt). Die beiden Crossover-Orders
(Verkauf EUNN.DE als nachgeholter Stop, Kauf EUNK.DE) bekamen Fehler 321 (Read-Only) und stehen als „unbestaetigt“; bei
IBKR gibt es sie nicht (weder offen noch ausgeführt, Client Portal laut Jakob).

Korrektur:
1. Crossover 49/51: „unbestaetigt“ → „abgelehnt“ (nie bei IBKR angekommen; Reservierung und Titelsperre entfallen).
2. Crossover-Strategiezustand auf den Stand vor dem Lauf vom 09.11. zurück (dessen Orders sind nie angekommen): Der Lauf
   heute Abend prüft damit die Tage seit dem 03.11. und schlägt den Verkauf EUNN (Stop gerissen am 06.11., nachgeholt)
   und den Kauf EUNK (falls das Signal am aktuellen Tag gilt) neu vor.
3. Ereignis „korrektur“ mit Befund; Sicherung vorher und nachher.

  .venv\Scripts\python tools\journal_korrektur_20261110.py            Prüfung, Trockenlauf (ändert nichts)
  .venv\Scripts\python tools\journal_korrektur_20261110.py --buchen   Korrektur im echten Journal
"""
import argparse
import sys

from dotenv import load_dotenv

from tradingbot.backtest.tresor import betriebsmodus
from tradingbot.betrieb.journal import Journal
from tradingbot.betrieb.speicher import betriebspfad
from tradingbot.betrieb.sperre import laufsperre
from tradingbot.konfiguration import PROJEKT_WURZEL

CROSSOVER = ["crossover-20261109-EUNN.DE-V", "crossover-20261109-EUNK.DE-K"]
TEXT = ("321 Read-Only im Gateway (ValidationError) beim Senden am 09.11.2026 22:07 – bei IBKR nicht vorhanden (offene Orders "
        "und Ausführungen am 10.11.2026 lesend geprüft, Client Portal laut Jakob); Korrektur 10.11.2026, neu vorschlagen")


def ibkr_lesen() -> tuple[dict, dict]:
    """Alle offenen Orders (auch anderer Client-IDs) und die heutigen Ausführungen je orderRef, nur lesend."""
    from ib_async import IB
    from ib_async.ib import StartupFetch, StartupFetchALL

    ib = IB()
    ib.connect("127.0.0.1", 4002, clientId=98, timeout=15, readonly=True, fetchFields=StartupFetchALL & ~StartupFetch.ORDERS_COMPLETE)
    try:
        ib.reqAllOpenOrders()
        ib.sleep(3)
        offen = {t.order.orderRef: (t.order.orderId, t.order.permId, t.orderStatus.status) for t in ib.openTrades()}
        fills: dict[str, float] = {}
        for f in ib.fills():
            fills[f.execution.orderRef] = fills.get(f.execution.orderRef, 0.0) + float(f.execution.shares)
        return offen, fills
    finally:
        ib.disconnect()


def main() -> int:
    load_dotenv(PROJEKT_WURZEL / ".env")
    a = argparse.ArgumentParser()
    a.add_argument("--buchen", action="store_true")
    arg = a.parse_args()
    with betriebsmodus("Journal-Korrektur 10.11.2026 (Read-Only-Vorfall)" + ("" if arg.buchen else ", Trockenlauf")):
        with laufsperre(betriebspfad("tageslauf.sperre"), zweck="Journal-Korrektur"):
            offen, fills = ibkr_lesen()
            j = Journal(betriebspfad("journal.sqlite"))
            unterwegs = {f"{z['buch']}:{z['id']}": z for z in j.unterwegs()}
            fehler = []
            for ref, z in sorted(unterwegs.items()):
                bei_ibkr = "offen" if ref in offen else (f"ausgeführt {fills[ref]:g} Stück (heute)" if ref in fills else "NICHT bei IBKR")
                print(f"{ref:48} Journal {z['status']:12} Order {z['order_id']:>4} | IBKR {bei_ibkr}")
                if z["status"] == "gesendet" and ref not in offen and ref not in fills:
                    fehler.append(f"{ref}: im Journal gesendet, bei IBKR weder offen noch heute ausgeführt")
            fremd = sorted(r for r in offen if r not in unterwegs)
            if fremd:
                fehler.append(f"offen bei IBKR, im Journal nicht unterwegs: {fremd}")
            for i in CROSSOVER:
                ref = f"crossover:{i}"
                if ref in offen or ref in fills:
                    fehler.append(f"{ref} ist bei IBKR vorhanden – keine Korrektur")
                if ref not in unterwegs or unterwegs[ref]["status"] != "unbestaetigt":
                    fehler.append(f"{ref}: nicht als unbestaetigt im Journal")
            zustand = j.zustand("crossover")
            if zustand.get("signaltag") != "2026-11-09" or zustand.get("vor_signaltag") != "2026-11-03":
                fehler.append(f"Crossover-Zustand unerwartet: Signaltag {zustand.get('signaltag')}, Vorlauf {zustand.get('vor_signaltag')}")
            if fehler:
                print("ABBRUCH, nichts geändert:\n  " + "\n  ".join(fehler))
                return 1
            print(f"Befund passt: {len(offen)} offene Bot-Orders, alle im Journal; Crossover 49/51 nicht bei IBKR.")
            if not arg.buchen:
                print("Trockenlauf – mit --buchen korrigieren.")
                return 0
            print(f"gesichert vorher: {j.sichern(None).name}")
            j.nachtraeglich_abgelehnt(CROSSOVER, TEXT)
            j.zustand_speichern("crossover", {"signaltag": "2026-11-03", "vor": zustand["vor"], "nach": zustand["vor"], "vor_signaltag": None,
                                              "korrektur": "10.11.2026: Lauf vom 09.11. zurückgenommen (Orders nie bei IBKR)"})
            j.ereignis("korrektur", "Read-Only-Vorfall 09.11.2026: " + TEXT + f". Offene Bot-Orders bei IBKR: {len(offen)}, alle im Journal "
                       "als gesendet mit Order-ID. Crossover-Zustand auf den Stand nach dem Lauf vom 03.11. zurückgesetzt; verpasste Tage "
                       "ab 04.11. werden heute Abend geprüft (Stop EUNN 06.11. nachgeholt).", "crossover")
            for i in CROSSOVER:
                z = next(x for x in j.vorschlaege(buch="crossover") if x["id"] == i)
                print(f"{i}: {z['status']}")
            print(f"Crossover unterwegs: {len(j.unterwegs('crossover'))}; Vorlauf-Signaltag für heute: {j.vorlauf_signaltag('crossover', '2026-11-10')}")
            print(f"gesichert nachher: {j.sichern(None).name}")
            j.schliessen()
    return 0


if __name__ == "__main__":
    sys.exit(main())
