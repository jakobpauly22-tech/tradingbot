r"""Tageslauf und Freigabe des Paper Tradings (Bedienung per Doppelklick auf Tageslauf.bat, ohne Terminal).

Ablauf: Fenster öffnen → Tageslauf rechnen (Betriebsmodus, protokolliert) → Vorschläge je Buch mit These und Urteil des
Risk-Managers anzeigen → Freigabe (Realbuch einzeln je Order, Skalierungsbücher als Sammelfreigabe je Buch) → Senden
über das IB Gateway (nur wenn alle Riegel offen sind; `senden_freigeschaltet` steht bis zu Jakobs Freigabe auf aus).

Aufrufe:
  Tageslauf.bat                                              Fenster (pythonw, ohne Konsole)
  .venv\Scripts\python tools\tageslauf.py --probe --ohne-fenster   Probelauf mit eigenem Journal (daten/betrieb/probe),
                                                             Bericht auf der Konsole und in daten/betrieb/probe/, sendet nie
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
            zeilen.append(f"  {'KAUF' if v.richtung > 0 else 'VERKAUF'} {v.stueck} × {v.ticker} ({limit}, Wert ≈ {v.orderwert:,.2f} €) "
                          f"→ {'frei' if u.frei else 'VETO: ' + '; '.join(u.gruende)}")
            if u.hinweise:
                zeilen.append("     Hinweise: " + "; ".join(u.hinweise))
            zeilen.append(f"     These: {v.these}")
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


def fenster() -> int:
    import tkinter as tk
    from tkinter import messagebox, scrolledtext

    betrieb = lade_konfiguration("betrieb")
    wurzel = tk.Tk()
    wurzel.title("Trading-Bot – Tageslauf (Paper)")
    wurzel.geometry("1100x800")
    try:
        erg, journal, broker = rechnen(probe=False)
    except Exception:  # noqa: BLE001
        messagebox.showerror("Tageslauf fehlgeschlagen", traceback.format_exc()[-1500:])
        return 1
    kopf = tk.Label(wurzel, text=f"Tageslauf {erg.jetzt:%d.%m.%Y %H:%M} – Senden {'AN' if betrieb['ibkr'].get('senden_freigeschaltet') else 'AUS (nur Freigabe)'}",
                    font=("Segoe UI", 12, "bold"))
    kopf.pack(anchor="w", padx=8, pady=4)
    if erg.gestoppt:
        tk.Label(wurzel, text=erg.gestoppt, fg="red", wraplength=1050, justify="left").pack(anchor="w", padx=8)
    auswahl: dict[str, tk.BooleanVar] = {}
    rahmen = tk.Frame(wurzel)
    rahmen.pack(fill="both", expand=True, padx=8)
    for buch, bk in betrieb["buecher"].items():
        vs = [(bv, u) for bv, u in erg.vorschlaege if bv.vorschlag.buch == buch]
        gruppe = tk.LabelFrame(rahmen, text=f"{buch} – Kasse {journal.kasse(buch):,.2f} € – Messbeginn {journal.messbeginn(buch) or 'noch nicht'}")
        gruppe.pack(fill="x", pady=3)
        if buch in erg.befunde:
            tk.Label(gruppe, text="Datenprüfung: " + "; ".join(erg.befunde[buch][:3]), fg="red").pack(anchor="w")
        frei = [(bv, u) for bv, u in vs if u.frei]
        if bk["freigabe"] == "sammel" and frei:
            var = tk.BooleanVar(value=False)
            tk.Checkbutton(gruppe, text=f"Sammelfreigabe: alle {len(frei)} freien Vorschläge", variable=var).pack(anchor="w")
            for bv, _ in frei:
                auswahl[bv.vorschlag.id] = var
        for bv, u in vs:
            v = bv.vorschlag
            text = (f"{'KAUF' if v.richtung > 0 else 'VERKAUF'} {v.stueck} × {v.ticker}  "
                    f"{('Limit %.2f %s' % (bv.limit_order, bv.waehrung)) if bv.limit_order else 'ohne Limit'}  ≈ {v.orderwert:,.2f} €  "
                    f"{'' if u.frei else 'VETO: ' + '; '.join(u.gruende)}")
            if bk["freigabe"] == "einzeln" and u.frei:
                var = tk.BooleanVar(value=False)
                auswahl[v.id] = var
                tk.Checkbutton(gruppe, text=text, variable=var, anchor="w", justify="left").pack(anchor="w")
            else:
                tk.Label(gruppe, text=text, anchor="w", justify="left", fg="black" if u.frei else "gray").pack(anchor="w")
            tk.Label(gruppe, text="   These: " + v.these + ("   Hinweise: " + "; ".join(u.hinweise) if u.hinweise else ""),
                     wraplength=1040, justify="left", fg="#444").pack(anchor="w")
    protokoll = scrolledtext.ScrolledText(wurzel, height=8)
    protokoll.pack(fill="x", padx=8, pady=4)
    protokoll.insert("end", "\n".join(erg.meldungen) + "\n")

    def senden():
        ids = sorted({i for i, var in auswahl.items() if var.get()})
        if not ids:
            messagebox.showinfo("Freigabe", "Nichts ausgewählt.")
            return
        if not messagebox.askyesno("Freigabe bestätigen", f"{len(ids)} Vorschläge freigeben und senden?"):
            return
        from tradingbot.broker.ibkr import IbkrBroker
        with betriebsmodus("Freigabe"):
            b = broker or IbkrBroker(betrieb, PROJEKT_WURZEL)
            m = freigeben_und_senden(journal, ids, b, datetime.now(BERLIN))
        protokoll.insert("end", "\n".join(m) + "\n")
        protokoll.see("end")

    leiste = tk.Frame(wurzel)
    leiste.pack(fill="x", padx=8, pady=6)
    tk.Button(leiste, text="Freigeben und senden", command=senden, state="disabled" if erg.gestoppt else "normal").pack(side="left")
    tk.Button(leiste, text="Schließen", command=wurzel.destroy).pack(side="right")
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
    if arg.ohne_fenster or arg.probe:
        return ohne_fenster(arg.probe)
    return fenster()


if __name__ == "__main__":
    sys.exit(main())
