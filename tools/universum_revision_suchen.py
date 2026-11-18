"""Befund 19, Schritt 1 (Plan Jakob 17.11.2026): früheste Wikipedia-Revision, die die Abnahme (a)–(c) besteht.

Kriterien und Verfahren stehen in docs/berichte/2026-11-18_universum_eingefroren.md und sind vor der Suche committet.
Das Werkzeug liest nur; es schreibt Revisionsseiten in einen eigenen Suchordner (Standard: daten/universum/suche/) und
legt mit --einfrieren die Seiten der gewählten Revision unter daten/universum/eingefroren/ ab.

Aufruf:
  .venv\\Scripts\\python tools\\universum_revision_suchen.py               Suche, Ergebnis als JSON auf stdout
  .venv\\Scripts\\python tools\\universum_revision_suchen.py --zeitpunkt 2026-11-09T07:31:00Z   nur einen Zeitpunkt prüfen
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
import sys
import time
from pathlib import Path

import pandas as pd
import requests

from tradingbot.daten import universum as u
from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration

API = "https://en.wikipedia.org/w/api.php"
INDEX = "https://en.wikipedia.org/w/index.php"
SEITEN = {"aktuell": "List of S&P 500 companies", "historie": "Historical components of the S&P 500"}
UA = {"User-Agent": "tradingbot-forschung/1.0 (privates Forschungsprojekt)"}   # bewusst ohne persönliche Angaben
FENSTER_START = pd.Timestamp("2026-10-01T00:00:00Z")
FENSTER_ENDE = pd.Timestamp("2026-11-16T21:18:00Z")       # 22:18 MEZ, Abruf der Probe (Befund 19)
SOLL_ZEILEN = 896
SUCHORDNER = PROJEKT_WURZEL / "daten" / "universum" / "suche"


def revisionen(titel: str, start: pd.Timestamp, ende: pd.Timestamp) -> pd.DataFrame:
    """Alle Revisionen (revid, zeit) einer Seite mit start ≤ zeit ≤ ende, plus die letzte vor start (Zustand am Start)."""
    zeilen, weiter = [], {}
    while True:
        p = {"action": "query", "prop": "revisions", "titles": titel, "rvprop": "ids|timestamp", "rvlimit": 500,
             "rvstart": ende.strftime("%Y-%m-%dT%H:%M:%SZ"), "rvend": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
             "format": "json", "formatversion": 2, **weiter}
        d = requests.get(API, params=p, headers=UA, timeout=60).json()
        zeilen += d["query"]["pages"][0].get("revisions", [])
        if "continue" not in d:
            break
        weiter = d["continue"]
    p = {"action": "query", "prop": "revisions", "titles": titel, "rvprop": "ids|timestamp", "rvlimit": 1,
         "rvstart": start.strftime("%Y-%m-%dT%H:%M:%SZ"), "format": "json", "formatversion": 2}
    zeilen += requests.get(API, params=p, headers=UA, timeout=60).json()["query"]["pages"][0].get("revisions", [])
    t = pd.DataFrame(zeilen).drop_duplicates("revid")
    t["zeit"] = pd.to_datetime(t["timestamp"], utc=True)
    return t[["revid", "zeit"]].sort_values("zeit").reset_index(drop=True)


def seite(name: str, revid: int, ordner: Path = SUCHORDNER) -> str:
    """HTML einer Revision (index.php?oldid=…), lokal gecacht als <name>_<revid>.html.gz."""
    datei = ordner / f"{name}_{revid}.html.gz"
    if datei.exists():
        with gzip.open(datei, "rt", encoding="utf-8") as f:
            return f.read()
    r = requests.get(INDEX, params={"title": SEITEN[name], "oldid": revid}, headers=UA, timeout=120)
    r.raise_for_status()
    r.encoding = r.encoding or "utf-8"
    ordner.mkdir(parents=True, exist_ok=True)
    with gzip.open(datei, "wt", encoding="utf-8") as f:
        f.write(r.text)
    time.sleep(1)   # höflich gegenüber Wikipedia
    return r.text


def intervalle_aus(html_akt: str, html_hist: str, sec_namen: pd.DataFrame) -> pd.DataFrame:
    """Wie lade_mitgliedschaften, aber aus gegebenen Seiten."""
    aktuell = u.aktuelle_mitglieder(pd.read_html(io.StringIO(html_akt))[0])
    aenderungen = u.aenderungen_normalisieren(pd.read_html(io.StringIO(html_hist))[0])
    korrekturen = lade_konfiguration("universum_korrekturen").get("korrekturen", [])
    return u.korrekturen_anwenden(u.mitgliedschaften(aktuell, aenderungen, sec_namen), korrekturen)


def _tag(v) -> str:
    return "" if v is None or v == "" or pd.isna(v) else pd.Timestamp(v).strftime("%Y-%m-%d")


def pruefe_a_b(t: pd.DataFrame, status: pd.DataFrame) -> dict:
    """(a) Zeilenzahl, (b) Zeilennummer und Schlüssel (ticker, von, bis) aller Statuszeilen."""
    t = t.reset_index(drop=True)
    falsch = []
    for r in status.itertuples():
        i = int(r.index)
        if i >= len(t) or (str(t.at[i, "ticker"]), _tag(t.at[i, "von"]), _tag(t.at[i, "bis"])) != (str(r.ticker), _tag(r.von), _tag(r.bis)):
            falsch.append(f"{i}:{r.ticker}")
    return {"zeilen": len(t), "a": len(t) == SOLL_ZEILEN, "b_falsch": len(falsch), "b_beispiele": falsch[:5], "b": not falsch}


def pruefe_c(t: pd.DataFrame, scores: pd.DataFrame) -> dict:
    """(c) jede (stichtag, firma) aus scores_eq_offer: CIK am Stichtag Mitglied."""
    fehlt = []
    for tag, gruppe in scores.groupby("stichtag"):
        mitglieder = set(u.mitglieder_am(t, tag)["cik"].dropna().astype(int))
        fehlt += [f"{pd.Timestamp(tag).date()}:{int(f)}" for f in set(gruppe["firma"].astype(int)) - mitglieder]
    return {"c_falsch": len(fehlt), "c_beispiele": sorted(fehlt)[:5], "c": not fehlt}


def kandidaten(start: pd.Timestamp, ende: pd.Timestamp) -> list[tuple[pd.Timestamp, int, int]]:
    """(T, revid aktuell, revid historie) je Revisionszeitpunkt im Fenster, chronologisch."""
    rev = {n: revisionen(t, start, ende) for n, t in SEITEN.items()}
    zeiten = sorted({z for r in rev.values() for z in r["zeit"] if z >= start} | {start})
    aus = []
    for z in zeiten:
        ids = [int(rev[n].loc[rev[n]["zeit"] <= z, "revid"].iloc[-1]) if (rev[n]["zeit"] <= z).any() else None for n in SEITEN]
        if None not in ids and (not aus or tuple(ids) != aus[-1][1:]):
            aus.append((z, *ids))
    return aus


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zeitpunkt", help="nur den Zustand zu diesem Zeitpunkt (UTC) prüfen")
    ap.add_argument("--start", default=str(FENSTER_START.date()), help="Fensterbeginn (Rand: monatsweise zurück)")
    ap.add_argument("--einfrieren", action="store_true", help="gewählte Revision unter daten/universum/eingefroren/ ablegen")
    args = ap.parse_args()

    from tradingbot.daten.cache import standard_cache
    from tradingbot.daten.sec import SecClient

    status = pd.read_csv(PROJEKT_WURZEL / "daten" / "universum" / "kursstatus.csv", keep_default_na=False)
    scores, _ = standard_cache().lesen("fundamental", "scores_eq_offer")
    sec_namen = u.lade_sec_namen()
    client = SecClient()

    if args.zeitpunkt:
        z = pd.Timestamp(args.zeitpunkt)
        liste = [k for k in kandidaten(z - pd.Timedelta(seconds=1), z)][-1:]
    else:
        liste = kandidaten(pd.Timestamp(args.start, tz="UTC"), FENSTER_ENDE)
    print(f"{len(liste)} Kandidaten", file=sys.stderr)

    ergebnisse = []
    for z, rev_akt, rev_hist in liste:
        e = {"zeit": z.isoformat(), "revid_aktuell": rev_akt, "revid_historie": rev_hist}
        try:
            iv = intervalle_aus(seite("aktuell", rev_akt), seite("historie", rev_hist), sec_namen)
        except ValueError as fehler:          # Aufbau scheitert (z. B. Korrektur passt nicht): kein Universum, nicht bestanden
            e |= {"aufbau_fehler": str(fehler), "bestanden": False}
            print(json.dumps(e, ensure_ascii=False), file=sys.stderr)
            ergebnisse.append(e)
            continue
        e |= pruefe_a_b(iv, status)
        if e["a"] and e["b"]:
            t = u.vorgaenger_suchen(u.cik_zuordnen(iv, sec_namen, client), sec_namen, client)
            t = u.cik_korrekturen_anwenden(t, lade_konfiguration("universum_korrekturen"), client)
            e |= pruefe_a_b(t, status) | pruefe_c(t, scores)
            e["bestanden"] = e["a"] and e["b"] and e["c"]
        else:
            e["bestanden"] = False
        print(json.dumps(e, ensure_ascii=False), file=sys.stderr)
        ergebnisse.append(e)
        if e["bestanden"] and not args.zeitpunkt:
            break
    print(json.dumps(ergebnisse, ensure_ascii=False, indent=1))
    if args.einfrieren:
        gewaehlt = next((e for e in ergebnisse if e["bestanden"]), None)
        if gewaehlt is None:
            print("Kein Kandidat besteht (a)–(c): nichts eingefroren. Anhalten und Jakob melden.", file=sys.stderr)
            return 1
        einfrieren(gewaehlt, sec_namen, client, status, scores)
    return 0


def _sha256(pfad: Path) -> str:
    import hashlib

    return hashlib.sha256(pfad.read_bytes()).hexdigest()


def einfrieren(gewaehlt: dict, sec_namen, client, status, scores) -> None:
    """Legt beide Seiten und das daraus berechnete Universum unter daten/universum/eingefroren/ ab, prüft die Abnahme
    am geschriebenen Universum noch einmal und gibt die Werte für config/universum_stand.yaml aus."""
    import shutil

    ziel = u.EINGEFROREN_ORDNER
    ziel.mkdir(parents=True, exist_ok=True)
    dateien = {}
    for name, schluessel in (("aktuell", "revid_aktuell"), ("historie", "revid_historie")):
        quelle = SUCHORDNER / f"{name}_{gewaehlt[schluessel]}.html.gz"
        datei = ziel / f"wikipedia_{name}_{gewaehlt[schluessel]}.html.gz"
        shutil.copyfile(quelle, datei)
        dateien[name] = datei
    with gzip.open(dateien["aktuell"], "rt", encoding="utf-8") as fa, gzip.open(dateien["historie"], "rt", encoding="utf-8") as fh:
        iv = intervalle_aus(fa.read(), fh.read(), sec_namen)
    t = u.vorgaenger_suchen(u.cik_zuordnen(iv, sec_namen, client), sec_namen, client)
    t = u.cik_korrekturen_anwenden(t, lade_konfiguration("universum_korrekturen"), client)
    datei_uni = ziel / "universum.parquet"
    t.to_parquet(datei_uni)
    zurueck = pd.read_parquet(datei_uni)
    pruefung = pruefe_a_b(zurueck, status) | pruefe_c(zurueck, scores)
    if not (pruefung["a"] and pruefung["b"] and pruefung["c"]):
        raise SystemExit(f"Geschriebenes Universum besteht die Abnahme nicht: {pruefung}")
    werte = {"zeitpunkt_utc": gewaehlt["zeit"],
             "aktuell": {"revid": gewaehlt["revid_aktuell"], "datei": dateien["aktuell"].name, "sha256": _sha256(dateien["aktuell"])},
             "historie": {"revid": gewaehlt["revid_historie"], "datei": dateien["historie"].name, "sha256": _sha256(dateien["historie"])},
             "universum": {"datei": datei_uni.name, "zeilen": len(zurueck), "sha256": _sha256(datei_uni)},
             "abnahme": pruefung}
    print(json.dumps(werte, ensure_ascii=False, indent=1, default=str), file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
