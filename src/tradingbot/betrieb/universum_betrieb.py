"""Eigenes Universum und eigener Kursstatus des Betriebs (Befund 19, Schritt 3; Plan Jakob 17.11.2026, Entscheidungen
18.11.2026).

Backtest und c3 lesen seit Schritt 1 einen eingefrorenen Stand (daten/universum/eingefroren/). Der Betrieb braucht den
laufenden Stand mit echten Indexwechseln (z. B. KVUE → OKTA am 30.10.2026) und hält ihn ganz in seinem eigenen Bereich
`daten/betrieb/cache/universum/`:

- **Wikipedia-Seiten:** eigener Cache, wöchentlich und am Quartalsstichtag erneuert (wie bisher). Beim ersten Zugriff
  einmalige Übernahme der Seiten aus daten/cache/universum, mit Zeitstempel, ohne Abruf (Marke UEBERNAHME.json).
- **Universum:** daraus berechnet wie bisher, zusätzlich mit den Betriebskorrekturen (`betrieb_korrekturen`), Ablage
  `sp500.parquet` im selben Ordner.
- **Kursstatus des Betriebs** (`kursstatus_betrieb`), je Statuszeile aus daten/universum/kursstatus.csv:
  1. gleicher Schlüssel (Ticker, von, bis) → übernommen;
  2. sonst Übernahme über Ticker und CIK (Jakob 18.11.2026): genau eine Betriebszeile mit gleichem Ticker, gleicher CIK
     und überlappendem Zeitraum; jede solche Übernahme steht mit altem und neuem Schlüssel in den Meldungen; kein oder
     mehr als ein Treffer → laut (UniversumVerschoben).
  Mitgliedschaften des Betriebs ab 2012 ohne Statuszeile sind neue Mitglieder (Variante a, Jakob 17.11.2026): Prüfung
  wie tools/kurse_universum.py (daten.kursquellen.pruefe_mitgliedschaft, inklusive Namensabgleich), Ergebnis in
  `kursstatus_neu.csv`; besteht sie nicht, bleibt der Titel mit Meldung außen vor.
- **Wächter** (`pruefe_betriebsstand`, Jakob 18.11.2026): eine CIK am Stichtag doppelt Mitglied → laut
  (UniversumVerschoben, die Fundamental-Bücher setzen aus); heutiges Mitglied ohne gültige Kursreihe → Meldung.
"""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from tradingbot.daten.kursstatus import UniversumVerschoben, lies_kursstatus, schluessel, tag_text

MARKE = "UEBERNAHME.json"
SEITEN = ("wikipedia_aktuell.html.gz", "wikipedia_historie.html.gz")
NEU_DATEI = "kursstatus_neu.csv"
AB_2012 = pd.Timestamp("2012-01-01")


def ordner() -> Path:
    """`daten/betrieb/cache/universum` (außerhalb des Betriebsmodus gesperrt, siehe betrieb/speicher.py)."""
    from tradingbot.betrieb.speicher import betriebspfad

    return betriebspfad("cache/universum/x").parent


def _quelle() -> Path:
    from tradingbot.konfiguration import PROJEKT_WURZEL

    return PROJEKT_WURZEL / "daten" / "cache" / "universum"


def seiten_uebernehmen(quelle: Path, ziel: Path, *, jetzt: datetime | None = None) -> dict:
    """Einmalige Übernahme der Wikipedia-Seiten in den Bereich des Betriebs (Zeitstempel bleiben, also bleibt auch der
    Wochenrhythmus). Danach nie wieder; der Betrieb ruft Wikipedia nur noch in seinen eigenen Ordner ab."""
    from tradingbot.daten.schicht import lesepfad, schreibpfad

    if lesepfad(ziel / MARKE).exists():                      # Probe: Marke aus Schicht oder Betrieb (Befund 20)
        return {**json.loads(lesepfad(ziel / MARKE).read_text(encoding="utf-8")), "neu": False}
    vorhanden = {name for name in SEITEN if lesepfad(ziel / name).exists()}
    ziel = schreibpfad(ziel)                                 # Probe: Übernahme nur in die Schicht
    marke = ziel / MARKE
    ziel.mkdir(parents=True, exist_ok=True)
    kopiert = []
    for name in SEITEN:
        if (quelle / name).exists() and name not in vorhanden:
            temporaer = ziel / (name + ".kopie")
            shutil.copy2(quelle / name, temporaer)
            os.replace(temporaer, ziel / name)
            kopiert.append(name)
    inhalt = {"uebernommen_am": (jetzt or datetime.now()).isoformat(timespec="seconds"), "quelle": str(quelle),
              "dateien": kopiert, "grund": "Befund 19, Schritt 3: eigener Wikipedia-Cache des Betriebs, einmalige Übernahme ohne Abruf"}
    temporaer = marke.with_suffix(".tmp")
    temporaer.write_text(json.dumps(inhalt, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(temporaer, marke)
    return {**inhalt, "neu": True}


def _cache():
    from tradingbot.daten.cache import ParquetCache

    return ParquetCache(ordner().parent)                  # Bereich „universum“ → daten/betrieb/cache/universum/sp500.parquet


def lade_universum_betrieb(neu_berechnen: bool = False) -> tuple[pd.DataFrame, dict]:
    """Universum des Betriebs (siehe Moduldoku); Ergebnis gilt für den Kalendertag (UTC), wie bisher."""
    from tradingbot.daten import universum as u
    from tradingbot.daten.sec import SecClient
    from tradingbot.konfiguration import lade_konfiguration

    ziel = ordner()
    seiten_uebernehmen(_quelle(), ziel)
    cache = _cache()
    if not neu_berechnen:
        t, meta = cache.lesen("universum", "sp500")
        if t is not None and meta.get("berechnet_am", "")[:10] == datetime.now(timezone.utc).date().isoformat():
            return t, meta
    konfig = lade_konfiguration("universum_korrekturen")
    client, sec_namen = SecClient(), u.lade_sec_namen()
    intervalle, stand = u.lade_mitgliedschaften(ordner=ziel)
    intervalle, meldungen = u.betriebskorrekturen_anwenden(intervalle, konfig.get("betrieb_korrekturen", []) or [])
    t = u.vorgaenger_suchen(u.cik_zuordnen(intervalle, sec_namen, client), sec_namen, client)
    t = u.cik_korrekturen_anwenden(t, konfig, client)
    meta = {**stand, "stand": "betrieb", "meldungen": meldungen,
            "berechnet_am": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    cache.schreiben("universum", "sp500", t, meta)
    return t, meta


def aktualisieren(erzwingen: bool = False) -> dict:
    """Für den Tageslauf: Wikipedia im Betriebsordner erneuern (7 Tage; am Quartalsstichtag 12 Stunden), Universum und
    Kursstatus des Betriebs bilden (prüft dabei neue Mitglieder), Wächter am heutigen Tag."""
    from tradingbot.daten import universum as u

    seiten_uebernehmen(_quelle(), ordner())
    u.lade_wikipedia(max_alter=timedelta(hours=12) if erzwingen else timedelta(days=7), ordner=ordner())
    t, meta = lade_universum_betrieb(neu_berechnen=erzwingen)
    status, meldungen = kursstatus_betrieb(t)
    uebernommen = [m.split(": ", 1)[1].split(" ", 1)[0] for m in meldungen if m.startswith("Kursstatus übernommen")]
    meldungen = [m for m in meldungen if not m.startswith("Kursstatus übernommen")]
    if uebernommen:                                        # täglich gleich, deshalb eine Zeile statt fünf
        meldungen.insert(0, f"Kursstatus über Ticker und CIK übernommen (Schlüssel im Betriebsstand anders): {', '.join(uebernommen)}")
    meldungen = list(meta.get("meldungen", [])) + meldungen + pruefe_betriebsstand(t, status, pd.Timestamp.today().normalize())
    letzte = max(d for d in (t["von"].max(), t["bis"].max()) if pd.notna(d))
    zugang = ", ".join(t.loc[t["von"] == letzte, "ticker"].astype(str))
    abgang = ", ".join(t.loc[t["bis"] == letzte, "ticker"].astype(str))
    return {**meta, "meldungen": meldungen, "letzte_aenderung": str(pd.Timestamp(letzte).date()), "zugang": zugang, "abgang": abgang}


# --- Kursstatus des Betriebs -------------------------------------------------------------------------------------------
def _ueberlappt(von_a, bis_a, von_b, bis_b) -> bool:
    """[von, bis) überlappen sich; fehlendes von = seit jeher, fehlendes bis = bis heute."""
    a0 = pd.Timestamp(von_a) if pd.notna(von_a) else pd.Timestamp.min
    a1 = pd.Timestamp(bis_a) if pd.notna(bis_a) else pd.Timestamp.max
    b0 = pd.Timestamp(von_b) if pd.notna(von_b) else pd.Timestamp.min
    b1 = pd.Timestamp(bis_b) if pd.notna(bis_b) else pd.Timestamp.max
    return a0 < b1 and b0 < a1


def ordne_basis_zu(universum: pd.DataFrame, basis: pd.DataFrame, cik_je_basiszeile: dict) -> tuple[pd.DataFrame, list[str]]:
    """Statuszeilen der Basis (kursstatus.csv) den Zeilen des Betriebsuniversums zuordnen: Schlüssel, sonst Ticker und CIK
    (siehe Moduldoku). `cik_je_basiszeile`: Spalte `index` der Basis → CIK (aus dem eingefrorenen Stand)."""
    s_uni, s_basis = schluessel(universum), schluessel(basis)
    if s_uni.duplicated().any():
        raise UniversumVerschoben(f"Schlüssel doppelt im Universum des Betriebs: {sorted(set(s_uni[s_uni.duplicated()]))[:3]}")
    nr_je_schluessel = {k: nr for nr, k in s_uni.items()}
    exakt = {i: nr_je_schluessel[k] for i, k in s_basis.items() if k in nr_je_schluessel}
    belegt = set(exakt.values())
    zuordnung, meldungen = dict(exakt), []
    for i, k in s_basis.items():
        if i in exakt:
            continue
        r = basis.loc[i]
        cik = cik_je_basiszeile.get(int(r["index"]))
        kandidaten = [nr for nr, z in universum.iterrows()
                      if nr not in belegt and str(z["ticker"]) == str(r["ticker"]) and cik is not None and pd.notna(z["cik"])
                      and int(z["cik"]) == int(cik) and _ueberlappt(r["von"], r["bis"], z["von"], z["bis"])]
        if len(kandidaten) != 1:
            raise UniversumVerschoben(f"Statuszeile {k} (CIK {cik}): {len(kandidaten)} passende Mitgliedschaften im Betriebsstand "
                                      "statt 1 (Übernahme über Ticker und CIK) – keine Kurse zugeordnet")
        nr = kandidaten[0]
        zuordnung[i] = nr
        belegt.add(nr)
        meldungen.append(f"Kursstatus übernommen über Ticker und CIK: {k[0]} {k[1] or '–'}…{k[2] or 'heute'} → "
                         f"{s_uni[nr][1] or '–'}…{s_uni[nr][2] or 'heute'}")
    aus = basis.rename(columns={"index": "index_csv"}).copy()
    aus["herkunft"] = ["basis" if i in exakt else "uebernommen" for i in aus.index]
    for spalte in ("von", "bis"):                          # Schlüssel des Betriebsstands, damit der Wächter passt
        aus[spalte] = [tag_text(universum.at[zuordnung[i], spalte]) or float("nan") for i in aus.index]
    aus.index = pd.Index([zuordnung[i] for i in aus.index], name="index").astype(universum.index.dtype)
    return aus, meldungen


def neue_mitglieder(universum: pd.DataFrame, zugeordnet) -> pd.DataFrame:
    """Mitgliedschaften des Betriebs ab 2012 ohne Statuszeile (die Basis führt genau die Mitgliedschaften ab 2012)."""
    rest = universum[~universum.index.isin(list(zugeordnet))]
    return rest[rest["bis"].isna() | (rest["bis"] >= AB_2012)]


def _pruefe_neu(neu: pd.DataFrame) -> list[dict]:
    """Prüfung wie tools/kurse_universum.py für neue Mitglieder; Yahoo-Namen im Betriebsordner, keine Tiingo-Liste
    (ein neues Mitglied ist heute gelistet; ohne heutigen SEC-Ticker bleibt es außen vor)."""
    from tradingbot.daten.kursquellen import kursquelle, pruefe_mitgliedschaft
    from tradingbot.daten.sec import SecClient
    from tradingbot.daten.tiingo import TiingoClient

    sec_client = SecClient()
    sec = sec_client.ticker_tabelle().groupby("cik").ticker.apply(list).to_dict()
    datenende = pd.Timestamp.today().normalize() - pd.Timedelta(days=7)
    eintraege = []
    for nr, z in neu.iterrows():
        r = pd.concat([z, pd.Series(kursquelle(z, sec, None))])
        e = pruefe_mitgliedschaft(nr, r, sec_client=sec_client, tiingo=TiingoClient(), datenende=datenende,
                                  yahoo_namen_datei=ordner() / "yahoo_namen.json")
        e.update({"von": tag_text(z["von"]), "bis": tag_text(z["bis"]), "cik": int(z["cik"]) if pd.notna(z["cik"]) else None,
                  "geprueft_am": datetime.now().isoformat(timespec="seconds")})
        eintraege.append(e)
    return eintraege


def kursstatus_betrieb(universum: pd.DataFrame, *, pruefen: bool = True) -> tuple[pd.DataFrame, list[str]]:
    """Kursstatus des Betriebs, Form wie daten.kursstatus.lade_kursstatus (Index = Zeile im Betriebsuniversum), plus
    Spalte `herkunft` (basis, uebernommen, neu). Gibt (Status, Meldungen) zurück. Neue Mitglieder werden einmal geprüft
    und in kursstatus_neu.csv festgehalten; mit `pruefen=False` gelten ungeprüfte neue Mitglieder als ungültig."""
    from tradingbot.daten.universum import lade_eingefrorenen_stand

    eingefroren, _ = lade_eingefrorenen_stand()
    basis = lies_kursstatus()
    cik_je_basiszeile = {int(nr): (int(c) if pd.notna(c) else None) for nr, c in eingefroren["cik"].items()}
    status, meldungen = ordne_basis_zu(universum, basis, cik_je_basiszeile)

    neu = neue_mitglieder(universum, status.index)
    datei = ordner() / NEU_DATEI
    from tradingbot.daten.schicht import lesepfad, schreibpfad

    lesen = lesepfad(datei)                                  # Probe: Schicht zuerst, schreiben nur dort (Befund 20)
    bekannt = pd.read_csv(lesen, dtype={"ticker": str}, keep_default_na=False) if lesen.exists() else pd.DataFrame()
    bekannt_schl = {(str(r["ticker"]), str(r["von"]), str(r["bis"])): r for _, r in bekannt.iterrows()} if len(bekannt) else {}
    s_neu = schluessel(neu)
    offen = neu[[k not in bekannt_schl for k in s_neu]]
    if len(offen) and pruefen:
        frisch = _pruefe_neu(offen)
        alle = pd.concat([bekannt, pd.DataFrame(frisch)], ignore_index=True) if len(bekannt) else pd.DataFrame(frisch)
        datei = schreibpfad(datei)
        temporaer = datei.with_suffix(".tmp")
        alle.to_csv(temporaer, index=False)
        os.replace(temporaer, datei)
        bekannt_schl.update({(str(e["ticker"]), e["von"], e["bis"]): pd.Series(e) for e in frisch})
    zeilen = []
    for nr, k in s_neu.items():
        e = bekannt_schl.get(k)
        if e is None:
            e = {"ticker": k[0], "name": neu.at[nr, "name"], "quelle": None, "symbol": None, "gueltig": False,
                 "grund": "neues Mitglied, noch nicht geprüft"}
        gueltig = str(e.get("gueltig")).lower() == "true"
        zeilen.append({"index": nr, "ticker": k[0], "name": e.get("name"), "von": k[1] or float("nan"), "bis": k[2] or float("nan"),
                       "quelle": e.get("quelle") or None, "symbol": e.get("symbol") or None, "gueltig": gueltig,
                       "grund": e.get("grund") or None, "herkunft": "neu"})
        meldungen.append(f"Neues Mitglied {k[0]} ({neu.at[nr, 'name']}, ab {k[1] or '–'}): "
                         + ("Kursreihe geprüft, gültig" if gueltig else f"ohne gültige Kursreihe ({e.get('grund') or 'unbekannt'}) – außen vor"))
    if zeilen:
        status = pd.concat([status, pd.DataFrame(zeilen).set_index("index")])
        status.index = status.index.astype(universum.index.dtype)
    status["gueltig"] = status["gueltig"].astype(bool)
    return status, meldungen


def bekannte_gattungen() -> dict[int, frozenset]:
    """CIK → Tickermenge der Firmen, die im eingefrorenen, abgenommenen Stand an dessen letztem Tag mit mehreren
    Aktiengattungen Mitglied sind (z. B. GOOG/GOOGL, FOX/FOXA, NWSA/NWS)."""
    from tradingbot.daten.universum import lade_eingefrorenen_stand, mitglieder_am

    eingefroren, meta = lade_eingefrorenen_stand()
    tag = pd.Timestamp(meta["zeitpunkt_utc"]).tz_localize(None).normalize()
    aktiv = mitglieder_am(eingefroren, tag).dropna(subset=["cik"])
    gruppen = aktiv.groupby(aktiv["cik"].astype(int))["ticker"].apply(lambda s: frozenset(s.astype(str)))
    return {int(c): g for c, g in gruppen.items() if len(g) > 1}


def pruefe_betriebsstand(universum: pd.DataFrame, status: pd.DataFrame, tag, gattungen: dict | None = None) -> list[str]:
    """Wächter (Jakob 18.11.2026): eine CIK am Tag doppelt Mitglied → UniversumVerschoben; heutiges Mitglied ohne gültige
    Kursreihe → Meldung (je Titel).

    „Doppelt“ heißt: dieselbe CIK mehrfach Mitglied, und ihre Tickermenge ist keine bekannte Aktiengattung
    (bekannte_gattungen, aus dem eingefrorenen Stand), oder derselbe Ticker mehrfach. Echte Gattungen wie GOOG/GOOGL sind
    so erlaubt, eine Umbenennung mit überlappenden Zeiträumen (CDAY/DAY im Betriebsstand vom 16.11.2026) nicht."""
    from tradingbot.daten.universum import mitglieder_am

    gattungen = bekannte_gattungen() if gattungen is None else gattungen
    aktiv = mitglieder_am(universum, pd.Timestamp(tag))
    mit_cik = aktiv.dropna(subset=["cik"])
    doppelt = []
    for cik, gruppe in mit_cik.groupby(mit_cik["cik"].astype(int)):
        ticker = list(gruppe["ticker"].astype(str))
        if len(ticker) > 1 and (len(set(ticker)) < len(ticker) or frozenset(ticker) != gattungen.get(int(cik))):
            doppelt.append(f"{cik} ({', '.join(ticker)})")
    if doppelt:
        raise UniversumVerschoben(f"Betriebsstand: CIK am {pd.Timestamp(tag).date()} doppelt Mitglied: " + "; ".join(doppelt))
    gueltig = set(status.index[status["gueltig"].astype(bool)])
    return [f"Heutiges Mitglied {z['ticker']} ({z['name']}) ohne gültige Kursreihe – keine Bewertung, keine Vorschläge"
            for nr, z in aktiv.iterrows() if nr not in gueltig]
