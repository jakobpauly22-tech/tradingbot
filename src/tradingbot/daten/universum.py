"""Historische Zusammensetzung des S&P 500 (point-in-time) und Zuordnung zur SEC-CIK.

Quellen:
- Wikipedia „List of S&P 500 companies“ (heutige Mitglieder mit CIK und Aufnahmedatum) und „Historical
  components of the S&P 500“ (Zu- und Abgänge seit 1976 mit Grund). Inhalte CC BY-SA; gespeichert wird nur
  lokal im Cache, nicht im Repository.
- SEC: cik-lookup-data.txt (alle Firmennamen inklusive früherer Namen mit CIK), Submissions (Einreichungen).

Rekonstruktion (Entscheidung Jakob 02.11.2026: historische Zusammensetzung statt heutiger Mitglieder):
- Zugang am Stichtag D: Mitglied ab D. Abgang am Stichtag D: Mitglied bis zum Tag vor D.
- Je Ticker werden Zu- und Abgänge zu Intervallen gepaart. Wechselt ein Unternehmen während der Mitgliedschaft den
  Ticker (z.B. FB → META), bleiben ein Zugang ohne Abgang und ein Abgang/heutiges Mitglied ohne Zugang übrig;
  diese werden über Datum und Namen zusammengeführt. Was sich nicht eindeutig zuordnen lässt, wird markiert
  (Spalte `hinweis`), nicht geraten.
"""
from __future__ import annotations

import gzip
import io
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

from tradingbot.daten.abruf import DatenFehler

log = logging.getLogger(__name__)

WIKI_AKTUELL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
WIKI_HISTORIE = "https://en.wikipedia.org/wiki/Historical_components_of_the_S%26P_500"
SEC_NAMEN = "https://www.sec.gov/Archives/edgar/cik-lookup-data.txt"

# Die rekonstruierte Zusammensetzung gilt erst ab 2012 als geprüft (Jakob, 03.11.2026): ab hier 500–506 Mitglieder je
# Quartal, Abgleich mit fja05680 bis 2019 und Korrekturen in config/universum_korrekturen.yaml. Für frühere Stichtage
# ist die Wikipedia-Änderungstabelle lückenhaft; Abfragen davor nur mit ausdrücklichem Schalter.
GEPRUEFT_AB = pd.Timestamp("2012-01-01")

_ZUSAETZE = r"\b(the|inc|incorporated|corp|corporation|co|company|ltd|limited|plc|llc|lp|l p|sa|nv|n v|ag|se|holdings?|group|cos)\b"


def name_normalisieren(name: str) -> str:
    """Vergleichbarer Firmenname: Kleinbuchstaben, ohne Satzzeichen und Rechtsform-Zusätze."""
    if not isinstance(name, str):
        return ""
    n = name.lower().replace("&", " and ").replace("'", "").replace("’", "")
    n = re.sub(r"/[a-z]{1,4}/?", " ", n)          # SEC-Zusätze wie /DE/, /NEW/, /NY
    n = re.sub(r"\(.*?\)", " ", n)                 # Klammerzusätze wie (Class A)
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    n = re.sub(_ZUSAETZE, " ", n)
    n = re.sub(r"\band\b", " ", n)
    return re.sub(r"\s+", " ", n).strip()


# --- Laden mit Cache ---------------------------------------------------------------------------
def _cache_pfad(name: str) -> Path:
    from tradingbot.konfiguration import PROJEKT_WURZEL

    return PROJEKT_WURZEL / "daten" / "cache" / "universum" / name


def _text_mit_cache(url: str, datei: Path, user_agent: str, max_alter: timedelta) -> tuple[str, datetime]:
    if datei.exists():
        abgerufen = datetime.fromtimestamp(datei.stat().st_mtime, tz=timezone.utc)
        if datetime.now(timezone.utc) - abgerufen < max_alter:
            with gzip.open(datei, "rt", encoding="utf-8") as f:
                return f.read(), abgerufen
    try:
        antwort = requests.get(url, headers={"User-Agent": user_agent}, timeout=120)
    except requests.RequestException as fehler:
        raise DatenFehler(f"{url} nicht erreichbar ({type(fehler).__name__})") from None
    if antwort.status_code != 200:
        raise DatenFehler(f"{url}: HTTP {antwort.status_code}")
    antwort.encoding = antwort.encoding or "utf-8"
    datei.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(datei, "wt", encoding="utf-8") as f:
        f.write(antwort.text)
    return antwort.text, datetime.now(timezone.utc)


def lade_wikipedia(max_alter: timedelta = timedelta(days=7)) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """(heutige Mitglieder, Änderungen, Stand) aus Wikipedia, im Cache höchstens `max_alter` alt."""
    from tradingbot.konfiguration import geheimnis

    ua = "tradingbot-forschung " + geheimnis("SEC_USER_AGENT")
    html_akt, stand_akt = _text_mit_cache(WIKI_AKTUELL, _cache_pfad("wikipedia_aktuell.html.gz"), ua, max_alter)
    html_hist, stand_hist = _text_mit_cache(WIKI_HISTORIE, _cache_pfad("wikipedia_historie.html.gz"), ua, max_alter)
    aktuell = aktuelle_mitglieder(pd.read_html(io.StringIO(html_akt))[0])
    aenderungen = aenderungen_normalisieren(pd.read_html(io.StringIO(html_hist))[0])
    return aktuell, aenderungen, {"wikipedia_aktuell": stand_akt.isoformat(timespec="seconds"),
                                  "wikipedia_historie": stand_hist.isoformat(timespec="seconds")}


def aktuelle_mitglieder(tabelle: pd.DataFrame) -> pd.DataFrame:
    t = tabelle.rename(columns={"Symbol": "ticker", "Security": "name", "Date added": "aufgenommen", "CIK": "cik",
                                "GICS Sector": "sektor"})
    t["aufgenommen"] = pd.to_datetime(t["aufgenommen"], errors="coerce")
    t["cik"] = pd.to_numeric(t["cik"], errors="coerce").astype("Int64")
    return t[["ticker", "name", "sektor", "aufgenommen", "cik"]]


def aenderungen_normalisieren(tabelle: pd.DataFrame) -> pd.DataFrame:
    """Wikipedia-Tabelle (zweizeiliger Kopf) → datum, zugang_ticker, zugang_name, abgang_ticker, abgang_name, grund."""
    t = tabelle.copy()
    t.columns = ["datum", "zugang_ticker", "zugang_name", "abgang_ticker", "abgang_name", "grund", "refs"][: len(t.columns)]
    t["datum"] = pd.to_datetime(t["datum"], format="mixed", errors="coerce")
    for spalte in ("zugang_ticker", "abgang_ticker"):
        t[spalte] = t[spalte].where(t[spalte].notna(), None)
    return t.drop(columns=[c for c in ["refs"] if c in t.columns]).dropna(subset=["datum"]).sort_values("datum").reset_index(drop=True)


# --- Mitgliedschaften --------------------------------------------------------------------------
def mitgliedschaften(aktuell: pd.DataFrame, aenderungen: pd.DataFrame, sec_namen: pd.DataFrame | None = None) -> pd.DataFrame:
    """Mitgliedschaftsintervalle [von, bis) je Unternehmen; bis = NaT heißt heute noch Mitglied.

    Zusammenführung in drei Stufen: (1) gleicher Ticker; (2) heutige Mitglieder: Zugang am Aufnahmedatum der
    heutigen Liste; (3) gleiche CIK laut SEC-Namensverzeichnis (enthält frühere Namen, z.B. Tesoro → Andeavor),
    sonst ähnlicher Name. Ohne `sec_namen` entfällt die CIK-Stufe.

    Spalten: ticker (zuletzt), ticker_frueher, name, von, bis, cik (falls aus der heutigen Liste), grund_abgang, hinweis.
    """
    cache_cik: dict[str, set[int]] = {}

    def ciks(name) -> set[int]:
        if sec_namen is None or not isinstance(name, str):
            return set()
        if name not in cache_cik:
            cache_cik[name] = set(cik_kandidaten(name, sec_namen))
        return cache_cik[name]

    def gleiche_firma(name_a, name_b=None, cik_b=None) -> bool:
        if name_b is not None and _aehnlich(name_a, name_b):
            return True
        ziel = {int(cik_b)} if cik_b is not None and pd.notna(cik_b) else ciks(name_b)
        return bool(ziel & ciks(name_a))

    zugaenge = [(r.datum, r.zugang_ticker, r.zugang_name) for r in aenderungen.itertuples() if isinstance(r.zugang_ticker, str)]
    abgaenge = [(r.datum, r.abgang_ticker, r.abgang_name, r.grund) for r in aenderungen.itertuples() if isinstance(r.abgang_ticker, str)]
    offen: dict[str, list] = {}       # ticker -> offene Zugänge (datum, name)
    intervalle = []

    ereignisse = sorted([(d, 1, t, n, None) for d, t, n in zugaenge] + [(d, 0, t, n, g) for d, t, n, g in abgaenge],
                        key=lambda e: (e[0], e[1]))   # am selben Tag erst Abgang, dann Zugang
    abgang_ohne_zugang = []
    for datum, ist_zugang, ticker, name, grund in ereignisse:
        if ist_zugang:
            offen.setdefault(ticker, []).append((datum, name))
        elif offen.get(ticker):
            von, name_zugang = offen[ticker].pop()
            intervalle.append({"ticker": ticker, "ticker_frueher": None, "name": name or name_zugang, "von": von,
                               "bis": datum, "grund_abgang": grund, "hinweis": None})
        else:
            abgang_ohne_zugang.append((datum, ticker, name, grund))

    zugang_ohne_abgang = [(d, t, n) for t, liste in offen.items() for d, n in liste]
    zugangstage = {d for d, _, _ in zugaenge}
    # Heute noch Mitglied: Zugang unter demselben Ticker, sonst (Ticker gewechselt) am Aufnahmedatum, sonst gleiche CIK
    for r in aktuell.itertuples():
        treffer = [z for z in zugang_ohne_abgang if z[1] == r.ticker]
        hinweis, frueher = None, None
        if not treffer and pd.notna(r.aufgenommen):
            am_tag = [z for z in zugang_ohne_abgang if z[0] == r.aufgenommen]
            treffer = am_tag if len(am_tag) == 1 else [z for z in am_tag if gleiche_firma(z[2], r.name, r.cik)]
        if not treffer:
            treffer = [z for z in zugang_ohne_abgang if gleiche_firma(z[2], cik_b=r.cik)]
        if treffer:
            frueher = max(treffer, key=lambda x: x[0])[1] if max(treffer, key=lambda x: x[0])[1] != r.ticker else None
        if treffer:
            z = max(treffer, key=lambda x: x[0])
            zugang_ohne_abgang.remove(z)
            von = z[0]
        elif pd.notna(r.aufgenommen) and r.aufgenommen in zugangstage:
            von = r.aufgenommen
            hinweis = "Zugang nur aus dem Aufnahmedatum der heutigen Liste"
        else:
            # Aufnahmedatum ohne jeden Zugang in der Änderungstabelle ist unzuverlässig (z.B. Dominion „2016“, seit
            # Jahrzehnten Mitglied): als Mitglied vor Beginn der Historie behandeln und markieren.
            von = pd.NaT
            hinweis = (f"Aufnahmedatum {r.aufgenommen.date()} nicht durch Änderungstabelle belegt; Mitglied seit vor Beginn angenommen"
                       if pd.notna(r.aufgenommen) else "Zugangsdatum unbekannt")
        intervalle.append({"ticker": r.ticker, "ticker_frueher": frueher, "name": r.name, "von": von, "bis": pd.NaT,
                           "cik": r.cik, "grund_abgang": None, "hinweis": hinweis})

    # Abgänge ohne Zugang: Tickerwechsel während der Mitgliedschaft (Zugang unter anderem Ticker, ähnlicher Name)
    for datum, ticker, name, grund in abgang_ohne_zugang:
        kandidaten = [z for z in zugang_ohne_abgang if z[0] < datum and gleiche_firma(z[2], name)]
        if kandidaten:
            z = max(kandidaten, key=lambda x: x[0])
            zugang_ohne_abgang.remove(z)
            intervalle.append({"ticker": ticker, "ticker_frueher": z[1], "name": name, "von": z[0], "bis": datum,
                               "grund_abgang": grund, "hinweis": None})
        else:
            intervalle.append({"ticker": ticker, "ticker_frueher": None, "name": name, "von": pd.NaT, "bis": datum,
                               "grund_abgang": grund, "hinweis": "Zugangsdatum unbekannt (vor Beginn der Historie oder Tickerwechsel)"})
    for datum, ticker, name in zugang_ohne_abgang:
        intervalle.append({"ticker": ticker, "ticker_frueher": None, "name": name, "von": datum, "bis": pd.NaT,
                           "grund_abgang": None, "hinweis": "Zugang ohne Abgang, aber nicht in der heutigen Liste"})

    tabelle = pd.DataFrame(intervalle)
    if "cik" not in tabelle:
        tabelle["cik"] = pd.NA
    tabelle["cik"] = tabelle["cik"].astype("Int64")
    return tabelle[["ticker", "ticker_frueher", "name", "von", "bis", "cik", "grund_abgang", "hinweis"]].sort_values(
        ["von", "ticker"], na_position="first").reset_index(drop=True)


def korrekturen_anwenden(intervalle: pd.DataFrame, korrekturen: list[dict]) -> pd.DataFrame:
    """Wendet die Einträge aus config/universum_korrekturen.yaml an; jede Korrektur wird in `hinweis` vermerkt."""
    t = intervalle.copy()
    for k in korrekturen:
        vermerk = f"korrigiert: {k['quelle']}"
        datum = lambda feld: pd.Timestamp(str(k[feld])) if k.get(feld) else pd.NaT  # noqa: E731
        if k["aktion"] == "beenden":
            maske = (t["ticker"] == k["ticker"]) & t["bis"].isna() & t["name"].eq(k["name"])
            if maske.sum() != 1:
                raise ValueError(f"Korrektur beenden {k['ticker']}/{k['name']}: {int(maske.sum())} Treffer statt 1")
            t.loc[maske, ["bis", "hinweis"]] = [datum("bis"), vermerk]
        elif k["aktion"] == "von_setzen":
            maske = (t["ticker"] == k["ticker"]) & t["name"].eq(k["name"])
            if maske.sum() != 1:
                raise ValueError(f"Korrektur von_setzen {k['ticker']}/{k['name']}: {int(maske.sum())} Treffer statt 1")
            t.loc[maske, ["von", "hinweis"]] = [datum("von"), vermerk]
        elif k["aktion"] == "ergaenzen":
            neu = {"ticker": k["ticker"], "ticker_frueher": None, "name": k["name"], "von": datum("von"), "bis": datum("bis"),
                   "cik": pd.NA, "grund_abgang": k.get("grund_abgang"), "hinweis": vermerk}
            t = pd.concat([t, pd.DataFrame([neu])], ignore_index=True)
        else:
            raise ValueError(f"Unbekannte Korrektur-Aktion {k['aktion']!r}")
    t["cik"] = t["cik"].astype("Int64")
    return t.sort_values(["von", "ticker"], na_position="first").reset_index(drop=True)


def lade_mitgliedschaften() -> tuple[pd.DataFrame, dict]:
    """Rekonstruktion aus Wikipedia plus SEC-Namensabgleich plus Korrekturen. Gibt (Intervalle, Stand) zurück."""
    from tradingbot.konfiguration import lade_konfiguration

    aktuell, aenderungen, stand = lade_wikipedia()
    intervalle = mitgliedschaften(aktuell, aenderungen, lade_sec_namen())
    korrekturen = lade_konfiguration("universum_korrekturen").get("korrekturen", [])
    return korrekturen_anwenden(intervalle, korrekturen), {**stand, "korrekturen": len(korrekturen)}


def _aehnlich(a, b) -> bool:
    na, nb = name_normalisieren(a), name_normalisieren(b)
    if not na or not nb:
        return False
    return na == nb or na.startswith(nb) or nb.startswith(na) or na.split()[0] == nb.split()[0]


def mitglieder_am(intervalle: pd.DataFrame, stichtag, *, vor_pruefzeitraum_erlaubt: bool = False) -> pd.DataFrame:
    """Mitglieder am Stichtag (von <= Stichtag < bis; unbekanntes von gilt als „schon vorher Mitglied“).

    Stichtage vor `GEPRUEFT_AB` (2012) sind nicht geprüft und werden ohne `vor_pruefzeitraum_erlaubt=True` abgelehnt.
    """
    tag = pd.Timestamp(stichtag)
    if tag < GEPRUEFT_AB and not vor_pruefzeitraum_erlaubt:
        raise ValueError(f"Zusammensetzung vor {GEPRUEFT_AB.date()} ist nicht geprüft (Stichtag {tag.date()}); "
                         "nur mit vor_pruefzeitraum_erlaubt=True abfragen")
    von_ok = intervalle["von"].isna() | (intervalle["von"] <= tag)
    bis_ok = intervalle["bis"].isna() | (intervalle["bis"] > tag)
    return intervalle[von_ok & bis_ok]


def anzahl_je_stichtag(intervalle: pd.DataFrame, stichtage, *, vor_pruefzeitraum_erlaubt: bool = False) -> pd.Series:
    return pd.Series({pd.Timestamp(s): len(mitglieder_am(intervalle, s, vor_pruefzeitraum_erlaubt=vor_pruefzeitraum_erlaubt))
                      for s in stichtage}, name="mitglieder")


# --- CIK-Zuordnung -----------------------------------------------------------------------------
def lade_sec_namen(max_alter: timedelta = timedelta(days=30)) -> pd.DataFrame:
    """SEC-Namensverzeichnis (Name, CIK), inklusive früherer Namen, normalisiert."""
    from tradingbot.konfiguration import geheimnis

    text, _ = _text_mit_cache(SEC_NAMEN, _cache_pfad("sec_cik_lookup.txt.gz"), geheimnis("SEC_USER_AGENT"), max_alter)
    zeilen = []
    for zeile in text.splitlines():
        teile = zeile.rstrip(":").rsplit(":", 1)
        if len(teile) == 2 and teile[1].strip().isdigit():
            zeilen.append((teile[0], int(teile[1])))
    namen = pd.DataFrame(zeilen, columns=["name", "cik"])
    namen["norm"] = namen["name"].map(name_normalisieren)
    return namen


def cik_kandidaten(name: str, sec_namen: pd.DataFrame, *, erweitert: bool = False) -> list[int]:
    """CIKs mit gleichem normalisiertem Namen. Mehrere Treffer sind möglich (Tochter- oder Mantelgesellschaften).

    `erweitert`: zusätzlich gleich ohne Leerzeichen („C R Bard“ = „CR Bard“) und Namensanfang in beide Richtungen
    („Family Dollar“ ↔ „Family Dollar Stores“). Treffer müssen danach gegen die 10-K im Zeitraum geprüft werden.
    """
    norm = name_normalisieren(name)
    if not norm:
        return []
    treffer = set(sec_namen.loc[sec_namen["norm"] == norm, "cik"])
    if erweitert and not treffer:
        if "_kompakt" not in sec_namen:
            sec_namen["_kompakt"] = sec_namen["norm"].str.replace(" ", "", regex=False)
        treffer = set(sec_namen.loc[sec_namen["_kompakt"] == norm.replace(" ", ""), "cik"])
        if not treffer and len(norm) >= 5:
            anfang = sec_namen["norm"].str.startswith(norm + " ")
            umgekehrt = sec_namen["norm"].map(lambda n: len(n) >= 5 and norm.startswith(n + " "))
            treffer = set(sec_namen.loc[anfang | umgekehrt, "cik"])
    return sorted(treffer)


def zehn_k_daten(submissions: dict) -> pd.DatetimeIndex:
    """Einreichungsdaten aller 10-K (inklusive älterer Einreichungen, soweit in `recent` enthalten)."""
    r = submissions.get("filings", {}).get("recent", {})
    daten = [d for d, f in zip(r.get("filingDate", []), r.get("form", [])) if f in ("10-K", "10-K405", "10-KT")]
    return pd.DatetimeIndex(sorted(pd.to_datetime(daten)))


def alle_zehn_k(cik: int, client, bis_mindestens=pd.Timestamp("2010-01-01")) -> tuple[pd.DatetimeIndex, dict]:
    """10-K-Einreichungsdaten einer CIK, inklusive älterer Zusatzseiten, solange `recent` nicht weit genug zurückreicht."""
    subs, _ = client.submissions(cik)
    daten = list(zehn_k_daten(subs))
    erste = pd.to_datetime(subs.get("filings", {}).get("recent", {}).get("filingDate", [None])[-1:] or [None])[0]
    for seite in subs.get("filings", {}).get("files", []):
        if pd.notna(erste) and erste <= bis_mindestens:
            break
        zusatz, _ = client.submissions_seite(seite["name"])
        daten += list(zehn_k_daten({"filings": {"recent": zusatz}}))
        erste = pd.to_datetime(seite.get("filingFrom")) if seite.get("filingFrom") else erste
    return pd.DatetimeIndex(sorted(set(daten))), subs


def cik_zuordnen(intervalle: pd.DataFrame, sec_namen: pd.DataFrame, client, ab=pd.Timestamp("2011-01-01")) -> pd.DataFrame:
    """Ergänzt CIK, Prüfstatus und Vorgänger-Hinweis für alle Mitgliedschaften, die ab `ab` relevant sind.

    Spalten neu: cik_quelle (heutige_liste | namensverzeichnis | sec_suche), cik_status (ok | mehrdeutig | nicht_gefunden |
    keine_10k_im_zeitraum), vorgaenger_pruefen (bool: erstes 10-K deutlich nach Beginn des relevanten Zeitraums).
    """
    t = intervalle.copy()
    for spalte, wert in (("cik_quelle", None), ("cik_status", None), ("vorgaenger_pruefen", False)):
        t[spalte] = wert
    relevant = t["bis"].isna() | (t["bis"] >= ab)
    zehn_k_cache: dict[int, pd.DatetimeIndex] = {}

    def zk(cik):
        if cik not in zehn_k_cache:
            try:
                zehn_k_cache[cik] = alle_zehn_k(cik, client)[0]
            except DatenFehler:
                zehn_k_cache[cik] = pd.DatetimeIndex([])
        return zehn_k_cache[cik]

    for i in t.index[relevant]:
        r = t.loc[i]
        if pd.notna(r["cik"]):
            kandidaten, quelle = [int(r["cik"])], "heutige_liste"
        else:
            kandidaten, quelle = cik_kandidaten(r["name"], sec_namen), "namensverzeichnis"
            passend = [c for c in kandidaten if passt_zum_intervall(zk(c), r["von"], r["bis"], ab)]
            if not passend:
                weitere = [c for c in cik_kandidaten(r["name"], sec_namen, erweitert=True) if c not in kandidaten][:15]
                if weitere:
                    kandidaten, quelle = weitere, "namensverzeichnis_erweitert"
            passend = [c for c in kandidaten if passt_zum_intervall(zk(c), r["von"], r["bis"], ab)]
            if not passend and isinstance(r["name"], str):
                kandidaten, quelle = [c for c, _ in client.entity_suche(r["name"])[:8]], "sec_suche"
        passend = [c for c in kandidaten if passt_zum_intervall(zk(c), r["von"], r["bis"], ab)]
        if not kandidaten:
            status, cik = "nicht_gefunden", pd.NA
        elif not passend:
            status, cik = "keine_10k_im_zeitraum", (kandidaten[0] if quelle == "heutige_liste" else pd.NA)
        else:
            # mehrere passende: die CIK, deren 10-K-Zeitraum die Mitgliedschaft am stärksten überdeckt
            cik = max(passend, key=lambda c: ueberdeckung_tage(zk(c), r["von"], r["bis"], ab))
            status = "ok" if len(passend) == 1 else "mehrdeutig"
        t.loc[i, ["cik", "cik_quelle", "cik_status"]] = [cik, quelle, status]
        if pd.notna(cik):
            t.loc[i, "vorgaenger_pruefen"] = vorgaenger_fehlt(zk(int(cik)), r["von"], ab)
    t["cik"] = t["cik"].astype("Int64")
    return t


def vorgaenger_suchen(t: pd.DataFrame, sec_namen: pd.DataFrame, client, ab=pd.Timestamp("2011-01-01")) -> pd.DataFrame:
    """Schlägt für Zeilen mit `vorgaenger_pruefen` eine Vorgänger-CIK vor (z.B. Umgründung in eine neue Holding).

    Kandidaten: andere CIKs unter einem der Namen der aktuellen CIK (inklusive früherer Namen) oder unter dem
    Indexnamen. Ein Kandidat passt, wenn er im relevanten Zeitraum vor dem ersten 10-K der aktuellen CIK 10-K
    eingereicht hat und sein letztes 10-K höchstens 15 Monate vor diesem ersten 10-K liegt (lückenlose Kette).
    Spalten neu: vorgaenger_cik (Int64), vorgaenger_status (vorgeschlagen | mehrdeutig | nicht_gefunden).
    """
    t = t.copy()
    t["vorgaenger_cik"] = pd.Series(pd.NA, index=t.index, dtype="Int64")
    t["vorgaenger_status"] = None
    for i in t.index[t["vorgaenger_pruefen"].fillna(False).astype(bool)]:
        r = t.loc[i]
        cik = int(r["cik"])
        erstes = alle_zehn_k(cik, client)[0]
        if len(erstes) == 0:
            t.loc[i, "vorgaenger_status"] = "neue_gesellschaft_ohne_10k"
            continue
        erstes = erstes[0]
        namen = set(sec_namen.loc[sec_namen["cik"] == cik, "norm"]) | {name_normalisieren(r["name"])}
        kandidaten = set(sec_namen.loc[sec_namen["norm"].isin(namen - {""}), "cik"]) - {cik}
        start = max(pd.Timestamp(r["von"]) if pd.notna(r["von"]) else ab, ab)
        passend = []
        for k in sorted(kandidaten):
            zk = alle_zehn_k(k, client)[0]
            vorher = zk[(zk >= start - pd.Timedelta(days=400)) & (zk < erstes)]
            if len(vorher) and (erstes - vorher[-1]).days <= 460:
                passend.append(k)
        if len(passend) == 1:
            t.loc[i, ["vorgaenger_cik", "vorgaenger_status"]] = [passend[0], "vorgeschlagen"]
        else:
            t.loc[i, "vorgaenger_status"] = "mehrdeutig" if passend else "nicht_gefunden"
    return t


def ueberdeckung_tage(zehn_k: pd.DatetimeIndex, von, bis, ab=pd.Timestamp("2011-01-01")) -> int:
    """Tage, in denen der 10-K-Zeitraum einer CIK (erstes 10-K − 1 Jahr bis letztes 10-K + 1 Jahr) die Mitgliedschaft überdeckt."""
    if len(zehn_k) == 0:
        return 0
    start = max(pd.Timestamp(von) if pd.notna(von) else ab, ab)
    ende = pd.Timestamp(bis) if pd.notna(bis) else pd.Timestamp.today().normalize()
    a, b = max(start, zehn_k[0] - pd.Timedelta(days=365)), min(ende, zehn_k[-1] + pd.Timedelta(days=365))
    return max((b - a).days, 0)


def sec_namen_einer_cik(cik: int, client) -> list[str]:
    """Heutiger und alle früheren SEC-Namen einer CIK."""
    s, _ = client.submissions(cik)
    return [s.get("name") or ""] + [f.get("name") or "" for f in s.get("formerNames", [])]


def _namen_pruefen(cik: int, erwartet: str, client, wo: str) -> None:
    namen = sec_namen_einer_cik(cik, client)
    if not any(erwartet.upper() in n.upper() for n in namen):
        raise ValueError(f"{wo}: CIK {cik} heißt bei der SEC {namen}, erwartet war „{erwartet}“")


def cik_korrekturen_anwenden(t: pd.DataFrame, korrekturen: dict, client) -> pd.DataFrame:
    """Manuelle CIK- und Vorgänger-Korrekturen (config/universum_korrekturen.yaml), mit Namensprüfung gegen die SEC."""
    t = t.copy()
    if "vorgaenger_ciks" not in t:
        t["vorgaenger_ciks"] = [[int(v)] if pd.notna(v) else [] for v in t.get("vorgaenger_cik", pd.Series(pd.NA, index=t.index))]
    for k in korrekturen.get("cik", []):
        maske = (t["ticker"] == k["ticker"]) & (t["name"] == k["name"])
        if maske.sum() < 1:
            raise ValueError(f"CIK-Korrektur {k['ticker']}/{k['name']}: keine Mitgliedschaft gefunden")
        _namen_pruefen(int(k["cik"]), k["erwartet"], client, f"CIK-Korrektur {k['ticker']}")
        t.loc[maske, ["cik", "cik_quelle", "cik_status"]] = [int(k["cik"]), "korrektur", "ok"]
        t.loc[maske, "vorgaenger_pruefen"] = False
    for k in korrekturen.get("vorgaenger", []):
        maske = (t["ticker"] == k["ticker"]) & (t["name"] == k["name"])
        if "cik_aktuell" in k:
            maske &= t["cik"] == int(k["cik_aktuell"])
        if maske.sum() != 1:
            raise ValueError(f"Vorgänger-Korrektur {k['ticker']}/{k['name']}: {int(maske.sum())} Treffer statt 1 (cik_aktuell angeben)")
        for cik, erwartet in zip(k["ciks"], k["erwartet"]):
            _namen_pruefen(int(cik), erwartet, client, f"Vorgänger-Korrektur {k['ticker']}")
        i = t.index[maske][0]
        t.at[i, "vorgaenger_ciks"] = [int(c) for c in k["ciks"]]
        t.at[i, "vorgaenger_status"] = "korrektur"
        t.at[i, "vorgaenger_pruefen"] = False
        if t.at[i, "cik_status"] == "keine_10k_im_zeitraum":   # 10-K kommen über den Vorgänger (z.B. neue Holding)
            t.at[i, "cik_status"] = "ok_ueber_vorgaenger"
    t["cik"] = t["cik"].astype("Int64")
    return t


def lade_universum(neu_berechnen: bool = False) -> tuple[pd.DataFrame, dict]:
    """Komplettes Universum: Mitgliedschaften, CIK, Vorgänger, Korrekturen. Ergebnis im Parquet-Cache mit Stand."""
    from tradingbot.daten.cache import standard_cache
    from tradingbot.daten.sec import SecClient
    from tradingbot.konfiguration import lade_konfiguration

    cache = standard_cache()
    if not neu_berechnen:
        t, meta = cache.lesen("universum", "sp500")
        if t is not None and meta.get("berechnet_am", "")[:10] == datetime.now(timezone.utc).date().isoformat():
            return t, meta
    client = SecClient()
    sec_namen = lade_sec_namen()
    intervalle, stand = lade_mitgliedschaften()
    t = vorgaenger_suchen(cik_zuordnen(intervalle, sec_namen, client), sec_namen, client)
    t = cik_korrekturen_anwenden(t, lade_konfiguration("universum_korrekturen"), client)
    meta = {**stand, "berechnet_am": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    cache.schreiben("universum", "sp500", t, meta)
    return t, meta


# --- SIC point-in-time (Entscheidung 02.11.2026: Finanzwerte SIC 6000–6999 nach dem damaligen Code) -----------
_SIC_MUSTER = re.compile(r"STANDARD INDUSTRIAL CLASSIFICATION:[^\[\n]*\[(\d{4})\]|<ASSIGNED-SIC>\s*(\d{4})")


def sic_aus_kopf(kopf: str) -> int | None:
    """SIC-Code aus dem Kopf einer Einreichung (Text- oder SGML-Format; erster Treffer = Hauptanmelder)."""
    treffer = _SIC_MUSTER.search(kopf)
    return int(treffer.group(1) or treffer.group(2)) if treffer else None


def zehn_k_liste(cik: int, client, ab=pd.Timestamp("2010-01-01")) -> pd.DataFrame:
    """10-K-Einreichungen (datum, accn) einer CIK ab `ab`, inklusive Zusatzseiten, aufsteigend sortiert."""
    subs, _ = client.submissions(cik)
    seiten = [subs.get("filings", {}).get("recent", {})]
    for seite in subs.get("filings", {}).get("files", []):
        if seite.get("filingTo") and pd.Timestamp(seite["filingTo"]) < ab:
            continue
        seiten.append(client.submissions_seite(seite["name"])[0])
    zeilen = [(d, a) for s in seiten for d, a, f in zip(s.get("filingDate", []), s.get("accessionNumber", []), s.get("form", []))
              if f in ("10-K", "10-K405", "10-KT")]
    t = pd.DataFrame(zeilen, columns=["datum", "accn"]).assign(datum=lambda d: pd.to_datetime(d["datum"]))
    return t[t["datum"] >= ab].drop_duplicates("accn").sort_values("datum").reset_index(drop=True)


def sic_historie(cik: int, client, ab=pd.Timestamp("2010-01-01")) -> list[tuple[pd.Timestamp, int]]:
    """Wechselpunkte (gültig ab Einreichungsdatum, SIC) aus den Köpfen der 10-K.

    Liest erstes und letztes 10-K; nur wenn die Codes abweichen, wird per Halbierung der Wechsel gesucht. So reichen
    meist zwei Abrufe je Unternehmen. Annahme: höchstens wenige Wechsel, zwischen gleichen Codes kein Hin und Zurück.
    """
    liste = zehn_k_liste(cik, client, ab)
    if liste.empty:
        return []
    cache: dict[int, int | None] = {}

    def sic(i):
        if i not in cache:
            cache[i] = sic_aus_kopf(client.einreichungskopf(cik, liste.loc[i, "accn"]))
        return cache[i]

    punkte = [(liste.loc[0, "datum"], sic(0))]

    def suche(links, rechts):
        if sic(links) == sic(rechts):
            return
        if rechts - links == 1:
            punkte.append((liste.loc[rechts, "datum"], sic(rechts)))
            return
        mitte = (links + rechts) // 2
        suche(links, mitte)
        suche(mitte, rechts)

    suche(0, len(liste) - 1)
    return sorted(punkte)


def sic_am(historie: list[tuple[pd.Timestamp, int]], stichtag) -> int | None:
    """SIC am Stichtag: letzter Wechselpunkt bis zum Stichtag; vor dem ersten 10-K gilt der erste bekannte Code."""
    if not historie:
        return None
    tag = pd.Timestamp(stichtag)
    gueltig = [s for d, s in historie if d <= tag]
    return gueltig[-1] if gueltig else historie[0][1]


def ist_finanzwert(sic: int | None, bereich=(6000, 6999)) -> bool | None:
    return None if sic is None else bereich[0] <= sic <= bereich[1]


def lade_sic_historien(universum: pd.DataFrame, client=None) -> dict[int, list]:
    """SIC-Historie für alle CIKs (inklusive Vorgänger) der ab 2012 relevanten Mitgliedschaften; im Cache."""
    from tradingbot.daten.cache import standard_cache
    from tradingbot.daten.sec import SecClient

    client = client or SecClient()
    cache = standard_cache()
    relevant = universum[universum["bis"].isna() | (universum["bis"] >= "2012-01-01")]
    ciks = {int(c) for c in relevant["cik"].dropna()} | {int(c) for liste in relevant["vorgaenger_ciks"] if liste is not None for c in list(liste)}
    tabelle, _ = cache.lesen("universum", "sic_historie")
    bekannt = {} if tabelle is None else {int(c): [(d, int(s)) for d, s in zip(g["gueltig_ab"], g["sic"])] for c, g in tabelle.groupby("cik")}
    neu = False
    for cik in sorted(ciks - set(bekannt)):
        try:
            bekannt[cik] = [(d, s) for d, s in sic_historie(cik, client) if s is not None]
        except DatenFehler as fehler:
            log.warning("SIC-Historie für CIK %s fehlt: %s", cik, fehler)
            bekannt[cik] = []
        neu = True
    if neu:
        zeilen = [{"cik": c, "gueltig_ab": d, "sic": s} for c, h in bekannt.items() for d, s in h]
        cache.schreiben("universum", "sic_historie", pd.DataFrame(zeilen, columns=["cik", "gueltig_ab", "sic"]),
                        {"quelle": "SEC-Einreichungsköpfe (10-K)", "ciks": len(bekannt)})
    return bekannt


def passt_zum_intervall(zehn_k: pd.DatetimeIndex, von, bis, ab=pd.Timestamp("2011-01-01")) -> bool:
    """Hat die CIK im (relevanten Teil des) Mitgliedszeitraums 10-K eingereicht?"""
    start = max(pd.Timestamp(von) if pd.notna(von) else ab, ab)
    ende = (pd.Timestamp(bis) if pd.notna(bis) else pd.Timestamp.today()) + pd.Timedelta(days=400)
    return bool(((zehn_k >= start - pd.Timedelta(days=400)) & (zehn_k <= ende)).any())


def vorgaenger_fehlt(zehn_k: pd.DatetimeIndex, von, ab=pd.Timestamp("2011-01-01")) -> bool:
    """Erstes 10-K der CIK liegt deutlich nach Beginn des relevanten Mitgliedszeitraums (z.B. Alphabet ab 2016)."""
    if len(zehn_k) == 0:
        return True
    start = max(pd.Timestamp(von) if pd.notna(von) else ab, ab)
    return zehn_k[0] > start + pd.Timedelta(days=460)
