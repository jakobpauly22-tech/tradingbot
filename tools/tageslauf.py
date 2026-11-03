r"""Tageslauf und Freigabe des Paper Tradings (Bedienung per Doppelklick auf Tageslauf.bat, ohne Terminal).

Ablauf: Fenster öffnen → Tageslauf rechnen (Betriebsmodus, protokolliert) → Vorschläge je Buch mit These und Urteil des
Risk-Managers anzeigen → Freigabe (Realbuch einzeln je Order, Skalierungsbücher als Sammelfreigabe je Buch) → Senden
über das IB Gateway (nur wenn alle Riegel offen sind; `senden_freigeschaltet` steht bis zu Jakobs Freigabe auf aus).

Aufrufe:
  Tageslauf.bat                 Fenster (pythonw, ohne Konsole), echtes Journal, Freigabe 18–24 Uhr
  Tageslauf_Probe.bat           Fenster im Probe-Modus: Probe-Journal (daten/betrieb/probe), jederzeit bedienbar, sendet nie,
                                setzt nie einen Messbeginn
  .venv\Scripts\python tools\tageslauf.py --probe --ohne-fenster   Probelauf als Bericht auf der Konsole und in daten/betrieb/probe/
"""
import argparse
import logging
import sys
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from tradingbot.backtest.tresor import betriebsmodus
from tradingbot.betrieb.journal import Journal, konto_kurz
from tradingbot.betrieb.speicher import betriebspfad
from tradingbot.betrieb.tageslauf import freigeben_und_senden, tageslauf
from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration

BERLIN = ZoneInfo("Europe/Berlin")


def broker_oder_none(meldungen: list[str]):
    from tradingbot.broker.ibkr import IbkrBroker

    try:
        b = IbkrBroker(lade_konfiguration("betrieb"), PROJEKT_WURZEL)
        b.verbinden()
        meldungen.append(f"Gateway verbunden, Konto {konto_kurz(b.konto_id())} (Paper: {b.konto_id().startswith('DU')})")
        return b
    except Exception as f:  # noqa: BLE001
        meldungen.append(f"Gateway nicht verbunden ({type(f).__name__}) – Vorschläge aus dem Journal, Abgleich vor dem Senden")
        return None


def bericht(erg, journal, betrieb: dict) -> str:
    zeilen = [f"Tageslauf {erg.jetzt:%d.%m.%Y %H:%M}", ""]
    zeilen += [f"- {m}" for m in erg.meldungen]
    if erg.gestoppt:
        zeilen += ["", f"GESTOPPT: {erg.gestoppt}"]
    for buch, bk in betrieb["buecher"].items():
        vs = [(bv, u) for bv, u in erg.vorschlaege if bv.vorschlag.buch == buch]
        zeilen += ["", f"== {buch} ({bk['art']}, Budget {bk['budget_eur']:,.0f} €, Kasse {journal.kasse(buch):,.2f} €, "
                       f"Freigabe {'einzeln' if bk['freigabe'] == 'einzeln' else 'als Sammelfreigabe'}) =="]
        if buch in erg.befunde:
            zeilen.append("  Datenprüfung – keine Vorschläge: " + "; ".join(erg.befunde[buch][:5]))
        if not vs:
            zeilen.append("  keine Vorschläge")
        for bv, u in vs:
            v = bv.vorschlag
            limit = f"Limit {bv.limit_order:.2f} {bv.waehrung}" if bv.limit_order else "ohne Limit"
            art = "TAUSCH" if v.art == "fx" else ("KAUF" if v.richtung > 0 else "VERKAUF")
            zeilen.append(f"  {art} {v.stueck} × {v.ticker} ({limit}, Wert ≈ {v.orderwert:,.2f} €) → {'frei' if u.frei else 'VETO: ' + '; '.join(u.gruende)}")
            zeilen.append(f"     Kern: {bv.kern or v.these}")
            if u.hinweise:
                zeilen.append("     Hinweise: " + "; ".join(u.hinweise))
            zeilen += ["     " + x for x in (bv.details or "").splitlines()]
    return "\n".join(zeilen)


def rechnen(probe: bool):
    meldungen = []
    with betriebsmodus("Probelauf" if probe else "Tageslauf"):
        journal = Journal(betriebspfad("probe/journal.sqlite" if probe else "journal.sqlite"))
        broker = broker_oder_none(meldungen)
        erg = tageslauf(datetime.now(BERLIN), journal, broker=broker, sichern=not probe)
        erg.meldungen = meldungen + erg.meldungen
        return erg, journal, broker


def ohne_fenster(probe: bool) -> int:
    erg, journal, broker = rechnen(probe)
    text = bericht(erg, journal, lade_konfiguration("betrieb"))
    print(text)
    with betriebsmodus("Probelauf-Bericht" if probe else "Tageslauf-Bericht"):
        ziel = betriebspfad(f"{'probe/' if probe else ''}bericht_{datetime.now():%Y-%m-%d_%H%M}.txt")
        ziel.write_text(text, encoding="utf-8")
    if broker:
        broker.trennen()
    journal.schliessen()
    return 0


def fenster(probe: bool = False) -> int:
    import tkinter as tk
    from tkinter import messagebox

    from tradingbot.betrieb.oberflaeche import Freigabefenster

    betrieb = lade_konfiguration("betrieb")
    wurzel = tk.Tk()
    try:
        erg, journal, broker = rechnen(probe=probe)
    except Exception:  # noqa: BLE001
        messagebox.showerror("Tageslauf fehlgeschlagen", traceback.format_exc()[-1500:])
        return 1

    def senden_fn(ids):
        with betriebsmodus("Probe-Freigabe" if probe else "Freigabe"):
            if probe:
                return freigeben_und_senden(journal, ids, None, datetime.now(BERLIN), probe=True)
            from tradingbot.broker.ibkr import IbkrBroker
            return freigeben_und_senden(journal, ids, broker or IbkrBroker(betrieb, PROJEKT_WURZEL), datetime.now(BERLIN))

    Freigabefenster(wurzel, erg, journal, betrieb, probe=probe, senden_fn=senden_fn)
    wurzel.mainloop()
    if broker:
        broker.trennen()
    journal.schliessen()
    return 0


def main() -> int:
    load_dotenv(PROJEKT_WURZEL / ".env")
    a = argparse.ArgumentParser()
    a.add_argument("--probe", action="store_true", help="eigenes Probe-Journal, keine Sicherung, sendet nie")
    a.add_argument("--ohne-fenster", action="store_true")
    arg = a.parse_args()
    logging.basicConfig(level=logging.WARNING)
    if arg.ohne_fenster:
        return ohne_fenster(arg.probe)
    return fenster(probe=arg.probe)


if __name__ == "__main__":
    sys.exit(main())
