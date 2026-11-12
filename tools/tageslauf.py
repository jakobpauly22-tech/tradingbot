r"""Tageslauf und Freigabe des Paper Tradings (Bedienung per Doppelklick auf Tageslauf.bat, ohne Terminal).

Ablauf: Fenster öffnen → Tageslauf rechnen (Betriebsmodus, protokolliert) → Vorschläge je Buch mit These und Urteil des
Risk-Managers anzeigen → Freigabe (Realbuch einzeln je Order, Skalierungsbücher als Sammelfreigabe je Buch) → Senden
über das IB Gateway (nur wenn alle Riegel offen sind; `senden_freigeschaltet` steht bis zu Jakobs Freigabe auf aus).

Aufrufe:
  Tageslauf.bat                 Fenster (pythonw, ohne Konsole), echtes Journal, Freigabe 18–24 Uhr
  Tageslauf_Probe.bat           Fenster im Probe-Modus: Probe-Journal (daten/betrieb/probe), jederzeit bedienbar, sendet nie,
                                setzt nie einen Messbeginn
  .venv\Scripts\python tools\tageslauf.py --probe --ohne-fenster   Probelauf als Bericht auf der Konsole und in daten/betrieb/probe/
  Tageslauf_neu.bat             neue Oberfläche (--neu), echtes Journal; Tageslauf_Probe_neu.bat: neue Oberfläche auf einer
                                Kopie des echten Journals (--neu --kopie), sendet nie
  .venv\Scripts\python tools\tageslauf.py --kopie                   Probelauf aller Bücher auf einer Kopie des echten Journals
                                (Gateway nur lesend, sendet nie, keine Sicherung; Kopie und Bericht in daten/betrieb/probe/)
"""
import argparse
import logging
import sys
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from tradingbot.backtest.tresor import betriebsmodus
from tradingbot.betrieb import benachrichtigung
from tradingbot.betrieb.journal import Journal, konto_kurz
from tradingbot.betrieb.sperre import LaufGesperrt, laufsperre
from tradingbot.betrieb.speicher import betriebspfad
from tradingbot.betrieb.tageslauf import freigeben_und_senden, tageslauf
from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration

BERLIN = ZoneInfo("Europe/Berlin")


def broker_oder_none(meldungen: list[str], nur_lesen: bool = False):
    from tradingbot.broker.ibkr import IbkrBroker

    try:
        b = IbkrBroker(lade_konfiguration("betrieb"), PROJEKT_WURZEL, nur_lesen=nur_lesen, client_id=94 if nur_lesen else None)
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
    konto = journal.zustand("_konto")
    if konto.get("kassenbasis") is not None:
        zeilen += ["", "Kassenbasis (Kontokasse ohne Bot-Bewegungen): " + ", ".join(f"{w} {v:,.2f}" for w, v in konto["kassenbasis"].items())
                   + f", festgehalten {konto.get('festgehalten', '–')}"]
    for buch, bk in betrieb["buecher"].items():
        vs = [(bv, u) for bv, u in erg.vorschlaege if bv.vorschlag.buch == buch]
        zeilen += ["", f"== {buch} ({bk['art']}, Budget {bk['budget_eur']:,.0f} €, Kasse {journal.kasse(buch):,.2f} €, "
                       f"Freigabe {'einzeln' if bk['freigabe'] == 'einzeln' else 'als Sammelfreigabe'}) =="]
        bestand = journal.bestand(buch)
        zeilen.append("  Bestand: " + (", ".join(f"{t} {s:g}" for t, s in sorted(bestand.items())) if bestand else "–")
                      + "; Kasse je Währung: " + ", ".join(f"{w} {v:,.2f}" for w, v in journal.kasse_je_waehrung(buch).items()))
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


def sperrdatei(probe: bool):
    """Sperre gegen zwei gleichzeitige Läufe auf demselben Journal (echt und Probe getrennt), gilt für die ganze Sitzung."""
    with betriebsmodus("Laufsperre"):
        return betriebspfad("probe/tageslauf.sperre" if probe else "tageslauf.sperre")


def melden_nach_lauf(erg, journal, betrieb: dict, probe: bool) -> None:
    """Kurzfassung bzw. Stoppmeldung und Lebenszeichen nach einem echten Tageslauf (Jakob 12.11.2026); Probe meldet nie."""
    if probe:
        return
    erg.meldungen += benachrichtigung.nach_tageslauf(erg, journal, betrieb, benachrichtigung.melder_aus_env(betrieb))


def fehler_melden(was: str, ausnahme: BaseException, betrieb: dict, probe: bool) -> None:
    """Sofortmeldung bei einer Ausnahme (nur der Typ) und Lebenszeichen „fehlgeschlagen“; wirft nie."""
    if probe:
        return
    try:
        melder = benachrichtigung.melder_aus_env(betrieb)
        melder.melden(benachrichtigung.fehlermeldung(was, ausnahme, datetime.now(BERLIN)))
        melder.lebenszeichen(fehler=True)
    except Exception:  # noqa: BLE001
        pass


def senden_melden(journal, ids, start: datetime, meldungen: list[str], betrieb: dict) -> list[str]:
    """Sofortmeldung, wenn beim Senden etwas abgelehnt, unbestätigt oder abgebrochen wurde (Jakob 12.11.2026)."""
    try:
        text = benachrichtigung.sendeprobleme(journal, list(ids), start.isoformat(timespec="seconds"), meldungen, datetime.now(BERLIN))
        if text:
            return meldungen + [benachrichtigung.melder_aus_env(betrieb).melden(text)]
    except Exception as f:  # noqa: BLE001
        return meldungen + [f"Benachrichtigung nach dem Senden fehlgeschlagen ({type(f).__name__})"]
    return meldungen


def rechnen(probe: bool, kopie: bool = False):
    meldungen = []
    with betriebsmodus("Probelauf (Kopie des echten Journals)" if kopie else "Probelauf" if probe else "Tageslauf"):
        if kopie:                                     # nur lesend: echtes Journal kopieren, Gateway readonly (09.11.2026)
            import shutil
            ziel = betriebspfad(f"probe/kopie_{datetime.now():%Y-%m-%d_%H%M%S}.sqlite")
            ziel.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(betriebspfad("journal.sqlite"), ziel)
            meldungen.append(f"Probelauf auf Kopie des echten Journals ({ziel.name}); Gateway nur lesend, nichts gesendet")
            journal = Journal(ziel)
        else:
            journal = Journal(betriebspfad("probe/journal.sqlite" if probe else "journal.sqlite"))
        broker = broker_oder_none(meldungen, nur_lesen=probe or kopie)
        erg = tageslauf(datetime.now(BERLIN), journal, broker=broker, sichern=not probe)
        gateway = getattr(broker, "gateway_meldungen", [])
        erg.meldungen = meldungen + erg.meldungen + [f"(kein Abbruch) {m}" for m in gateway]
        return erg, journal, broker


def ohne_fenster(probe: bool, kopie: bool = False) -> int:
    try:
        with laufsperre(sperrdatei(probe), zweck="Probelauf" if probe else "Tageslauf"):
            return _ohne_fenster(probe, kopie)
    except LaufGesperrt as f:
        print(f"ABGEBROCHEN: {f}")
        return 2


def _ohne_fenster(probe: bool, kopie: bool = False) -> int:
    betrieb = lade_konfiguration("betrieb")
    try:
        erg, journal, broker = rechnen(probe, kopie)
    except Exception as f:
        fehler_melden("Tageslauf", f, betrieb, probe or kopie)
        raise
    melden_nach_lauf(erg, journal, betrieb, probe or kopie)
    text = bericht(erg, journal, betrieb)
    print(text)
    with betriebsmodus("Probelauf-Bericht" if probe else "Tageslauf-Bericht"):
        ziel = betriebspfad(f"{'probe/' if probe else ''}bericht_{datetime.now():%Y-%m-%d_%H%M}.txt")
        ziel.write_text(text, encoding="utf-8")
    if broker:
        broker.trennen()
    journal.schliessen()
    return 0


def fenster(probe: bool = False, neu: bool = False, kopie: bool = False) -> int:
    """`neu`: neue Oberfläche (betrieb/oberflaeche_neu.py, 10.11.2026); die alte bleibt Reserve, bis Jakob umstellt.
    `kopie`: Probe-Fenster auf einer Kopie des echten Journals (Gateway nur lesend, sendet nie)."""
    import tkinter as tk
    from tkinter import messagebox

    from tradingbot.betrieb.oberflaeche import Freigabefenster

    betrieb = lade_konfiguration("betrieb")
    wurzel = tk.Tk()
    hinweise: list[str] = []
    try:
        with laufsperre(sperrdatei(probe), zweck="Probefenster" if probe else "Tageslauf-Fenster", meldungen=hinweise):
            if neu:
                return _fenster_neu(tk, messagebox, betrieb, wurzel, probe, kopie, hinweise)
            return _fenster(tk, messagebox, Freigabefenster, betrieb, wurzel, probe, hinweise)
    except LaufGesperrt as f:
        messagebox.showerror("Tageslauf läuft schon", str(f))
        return 2


def _fenster(tk, messagebox, Freigabefenster, betrieb, wurzel, probe, hinweise) -> int:
    try:
        erg, journal, broker = rechnen(probe=probe)
        erg.meldungen = hinweise + erg.meldungen
        melden_nach_lauf(erg, journal, betrieb, probe)
    except Exception as f:  # noqa: BLE001
        fehler_melden("Tageslauf", f, betrieb, probe)
        messagebox.showerror("Tageslauf fehlgeschlagen", traceback.format_exc()[-1500:])
        return 1

    def senden_fn(ids):
        with betriebsmodus("Probe-Freigabe" if probe else "Freigabe"):
            if probe:
                return freigeben_und_senden(journal, ids, None, datetime.now(BERLIN), probe=True)
            from tradingbot.broker.ibkr import IbkrBroker
            start = datetime.now()
            m = freigeben_und_senden(journal, ids, broker or IbkrBroker(betrieb, PROJEKT_WURZEL), datetime.now(BERLIN),
                                     fortschritt=wurzel.update)             # Fenster bleibt während des Sendens bedienbar
            return senden_melden(journal, ids, start, m, betrieb)

    Freigabefenster(wurzel, erg, journal, betrieb, probe=probe, senden_fn=senden_fn)
    wurzel.mainloop()
    if broker:
        broker.trennen()
    journal.schliessen()
    return 0


def _fenster_neu(tk, messagebox, betrieb, wurzel, probe, kopie, hinweise) -> int:
    from tradingbot.betrieb import ansicht
    from tradingbot.betrieb.oberflaeche_neu import Tagesfenster
    from tradingbot.broker.ibkr import IbkrBroker

    try:
        erg, journal, broker = rechnen(probe=probe, kopie=kopie)
        erg.meldungen = hinweise + erg.meldungen
        melden_nach_lauf(erg, journal, betrieb, probe)
    except Exception as f:  # noqa: BLE001
        fehler_melden("Tageslauf", f, betrieb, probe)
        messagebox.showerror("Tageslauf fehlgeschlagen", traceback.format_exc()[-1500:])
        return 1
    zustand = {"broker": broker}

    def status_fn():
        """Gateway und Schreibzugriff prüfen (beim Start und per Knopf); in Probe und Kopie nur lesend verbunden."""
        if zustand["broker"] is None:
            try:
                zustand["broker"] = IbkrBroker(betrieb, PROJEKT_WURZEL, nur_lesen=probe, client_id=94 if probe else None)
            except Exception:  # noqa: BLE001
                return ansicht.gateway_status(None)
        return ansicht.gateway_status(zustand["broker"])

    def senden_fn(ids):
        with betriebsmodus("Probe-Freigabe" if probe else "Freigabe"):
            if probe:
                return freigeben_und_senden(journal, ids, None, datetime.now(BERLIN), probe=True)
            b = zustand["broker"] or IbkrBroker(betrieb, PROJEKT_WURZEL)
            zustand["broker"] = b
            start = datetime.now()
            m = freigeben_und_senden(journal, ids, b, datetime.now(BERLIN), fortschritt=wurzel.update)
            return senden_melden(journal, ids, start, m, betrieb)

    gateway = status_fn() if broker is not None else ansicht.gateway_status(None)
    Tagesfenster(wurzel, erg, journal, betrieb, probe=probe, senden_fn=senden_fn, status_fn=status_fn, gateway=gateway,
                 jetzt_fn=lambda: datetime.now(BERLIN).replace(tzinfo=None))
    wurzel.mainloop()
    if zustand["broker"]:
        try:
            zustand["broker"].trennen()
        except Exception:  # noqa: BLE001
            pass
    journal.schliessen()
    return 0


def main() -> int:
    load_dotenv(PROJEKT_WURZEL / ".env")
    a = argparse.ArgumentParser()
    a.add_argument("--probe", action="store_true", help="eigenes Probe-Journal, keine Sicherung, sendet nie")
    a.add_argument("--ohne-fenster", action="store_true")
    a.add_argument("--kopie", action="store_true", help="Probelauf auf einer Kopie des echten Journals (nur lesend, ohne Fenster)")
    a.add_argument("--neu", action="store_true", help="neue Oberfläche (10.11.2026); mit --kopie als Probe-Fenster auf einer Kopie")
    arg = a.parse_args()
    logging.basicConfig(level=logging.WARNING)
    if arg.neu:
        return fenster(probe=arg.probe or arg.kopie, neu=True, kopie=arg.kopie)
    if arg.kopie:
        return ohne_fenster(True, kopie=True)
    if arg.ohne_fenster:
        return ohne_fenster(arg.probe)
    return fenster(probe=arg.probe)


if __name__ == "__main__":
    sys.exit(main())
