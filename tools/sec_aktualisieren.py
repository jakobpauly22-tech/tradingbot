r"""SEC-Aktualisierung des Betriebs (Schritt 2; Festlegung Jakob 23.11.2026, docs/BETRIEB.md).

Lädt companyfacts und submissions der heutigen Mitglieder des Betriebsuniversums plus Vorgänger in den SEC-Cache des
Betriebs (daten/betrieb/cache), mit Prüfregel je CIK und STAND.json (betrieb/secaktualisierung.py). Getrennt vom
Abendlauf; nimmt die Laufsperre des Tageslaufs (Probe: die der Probe), läuft also nie neben ihm.

  .venv\Scripts\python tools\sec_aktualisieren.py --probe   komplett in der Probe-Schicht (Betriebs- und Entwicklungsdaten
                                                             bleiben byteweise unverändert), keine Sofortmeldung
  .venv\Scripts\python tools\sec_aktualisieren.py           echter Lauf (Zeitplan: Samstag 10:00)

SEC-Regeln: höchstens 8 Anfragen je Sekunde (eine gemeinsame Drossel, config/fundamental.yaml), User-Agent aus
SEC_USER_AGENT in .env, HTTP 429/5xx mit Pause wiederholt, HTTP 403 bricht sofort ab. Ausgang 0 nur bei Erfolg.
"""
import argparse
import subprocess
import sys
import time
import warnings
from collections import Counter
from contextlib import nullcontext
from datetime import date, datetime, timedelta, timezone

from dotenv import load_dotenv

from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration

warnings.simplefilter("ignore")


def git_stand() -> str:
    r = subprocess.run(["git", "describe", "--always", "--dirty"], cwd=PROJEKT_WURZEL, capture_output=True, text=True)
    return r.stdout.strip()


def mb(b: int) -> str:
    return f"{b / 1e6:,.1f} MB".replace(",", "X").replace(".", ",").replace("X", ".")


def main() -> int:
    load_dotenv(PROJEKT_WURZEL / ".env")
    a = argparse.ArgumentParser()
    a.add_argument("--probe", action="store_true", help="nur in der Probe-Schicht, ohne Sofortmeldung")
    arg = a.parse_args()
    probe = arg.probe

    from tradingbot.backtest.tresor import betriebsmodus
    from tradingbot.betrieb import seccache
    from tradingbot.betrieb.secaktualisierung import ZaehlendeSitzung, aktualisieren, ciks_betrieb, hoechste_rate, stand_schreiben
    from tradingbot.betrieb.speicher import betriebspfad
    from tradingbot.betrieb.sperre import LaufGesperrt, laufsperre
    from tradingbot.daten.abruf import Drossel
    from tradingbot.daten.schicht import probe_schicht
    from tradingbot.daten.sec import SecClient, sec_cache, sec_rohwurzel
    from tradingbot.daten.universum import lade_universum

    zweck = "Probe: SEC-Aktualisierung (nur Schicht)" if probe else "SEC-Aktualisierung"
    with betriebsmodus(zweck):
        sperre = betriebspfad("probe/tageslauf.sperre" if probe else "tageslauf.sperre")
        try:
            with laufsperre(sperre, zweck=zweck), (probe_schicht(leeren=True) if probe else nullcontext()):
                beginn = time.perf_counter()
                info = seccache.sicherstellen()
                print(seccache.protokollzeile(info), flush=True)
                t_uebernahme = time.perf_counter() - beginn
                universum, _ = lade_universum(stand="betrieb")
                ciks = ciks_betrieb(universum, date.today())
                print(f"{len(ciks)} CIKs (heutige Mitglieder des Betriebsuniversums plus Vorgänger)", flush=True)
                sitzung = ZaehlendeSitzung()
                drossel = Drossel(min_abstand_s=1.0 / float(lade_konfiguration("fundamental")["sec"]["max_anfragen_pro_sekunde"]))
                client = SecClient(sitzung=sitzung, drossel=drossel)
                client_frisch = SecClient(sitzung=sitzung, drossel=drossel, max_alter=timedelta(0))

                def fortschritt(nr, gesamt, cik, eintrag):
                    if nr % 50 == 0 or nr == gesamt or eintrag["stand"] not in ("übernommen", "ohne Daten"):
                        print(f"  {nr}/{gesamt} CIK {cik}: {eintrag['stand']} – {eintrag.get('text', '')[:160]}", flush=True)

                t_lauf = time.perf_counter()
                quittiert = lade_konfiguration("betrieb").get("sec_quittiert") or []
                erg = aktualisieren(ciks, client=client, client_frisch=client_frisch, sec_tabellen=sec_cache(), fortschritt=fortschritt,
                                    quittiert=quittiert)
                dauer_lauf = time.perf_counter() - t_lauf
                anfr = sitzung.anfragen
                zusatz = {
                    "probe": probe, "git": git_stand(), "user_agent_gesetzt": bool(client.user_agent),
                    "anfragen": dict(Counter(x[1] for x in anfr)), "anfragen_gesamt": len(anfr),
                    "status": dict(Counter(str(x[2]) for x in anfr)),
                    "bytes_entpackt": sum(x[3] for x in anfr), "bytes_uebertragen": sum(x[4] for x in anfr),
                    "hoechste_rate_je_s": hoechste_rate([x[0] for x in anfr]),
                    "dauer_s": round(dauer_lauf, 1), "dauer_uebernahme_s": round(t_uebernahme, 1),
                }
                stand = stand_schreiben(sec_rohwurzel(), erg, ende=datetime.now(timezone.utc), zusatz=zusatz)
        except LaufGesperrt as f:
            print(f"GESPERRT – {f}")
            return 3

    z = stand["zusammenfassung"]
    neu_je_cik = [e for e in erg.je_cik.values() if e.get("neue_zeilen")]
    filed = sorted(e["neueste_filed"] for e in neu_je_cik if e.get("neueste_filed"))
    print("\n=== Ergebnis" + (" (Probe, nur Schicht)" if probe else "") + " ===")
    print(f"erfolgreich: {stand['erfolgreich']}" + (f" – {stand['abbruch']}" if stand["abbruch"] else ""))
    print(f"CIKs: {z['ciks']} (übernommen {z['übernommen']}, alter Stand {z['alter Stand']}, Fehler {z['Fehler']}, ohne Daten {z['ohne Daten']})")
    print(f"neue Erstmeldungen: {z['neue_zeilen']} in {len(neu_je_cik)} CIKs" + (f", neueste filed {filed[-1]}" if filed else ""))
    print(f"SIC: {sum(1 for e in erg.je_cik.values() if e.get('sic_neu', 0) > 0)} CIKs mit neuen Einträgen")
    print(f"Anfragen: {zusatz['anfragen_gesamt']} {zusatz['anfragen']}, Status {zusatz['status']}, höchste Rate {zusatz['hoechste_rate_je_s']}/s")
    print(f"Daten: {mb(zusatz['bytes_uebertragen'])} übertragen, {mb(zusatz['bytes_entpackt'])} entpackt")
    print(f"Dauer: Abruf {zusatz['dauer_s']} s, Übernahme vorher {zusatz['dauer_uebernahme_s']} s")
    print(f"Hinweise (nachgelieferte Einreichungen vor der Grenze): {len(erg.hinweise)}")
    for h in erg.hinweise:
        print(f"  HINWEIS: {h['firma']} (CIK {h['cik']}), {h['accn']}, {h['form']}, filed {h['filed']}, {h['zeilen']} Erstmeldungen")
    for m in erg.quittiert:                      # quittierte Verletzungen: nur Protokoll, kein Telegram (Jakob 24.11.2026)
        print("QUITTIERT:", m)
    for m in erg.meldungen:
        print("MELDUNG:", m)
    if erg.meldungen and not probe:
        from tradingbot.betrieb.benachrichtigung import melder_aus_env

        print(melder_aus_env(lade_konfiguration("betrieb")).melden("\n".join(erg.meldungen[:10])))
    return 0 if stand["erfolgreich"] else 1


if __name__ == "__main__":
    sys.exit(main())
