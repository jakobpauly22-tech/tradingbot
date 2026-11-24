r"""Einordnung der „Split“-Ereignisse der Kursreihen: echter Split, Abspaltung, kombiniert oder unklar (Teil a der
Datenkorrektur Marktwert, Jakob 13.11.2026; c3 Schritt 1b, Jakob 24.11.2026, docs/FUNDAMENTAL.md).

Aufrufe:
  .venv\Scripts\python tools\split_ereignisse_einordnen.py
      Einordnung bis zur Tresorgrenze. Schreibt NICHT nach config/, sondern nach daten/fundamental/einordnung/:
      <Zeit>_kandidat.yaml (Kandidatenliste), <Zeit>_vergleich.md (Unterschied zur geltenden Liste, Messung Gleichstand,
      Versiegelung) und <Zeit>_split_ereignisse.md (Bericht). Netz gesperrt, daten/cache/ versiegelt.
  .venv\Scripts\python tools\split_ereignisse_einordnen.py --belege-holen <kandidat>
      Nur nach Jakobs Freigabe (24.11.2026): 8-K mit filed ≤ Tresorgrenze rund um die „unklar“-Ereignisse der Kandidatenliste
      von der SEC holen, in die eigene Belegablage daten/fundamental/einordnung/belege/ (nicht in den Entwicklungs-Cache).
  .venv\Scripts\python tools\split_ereignisse_einordnen.py --uebernehmen <kandidat>
      Nur nach Jakobs Okay: geltende Liste nach daten/fundamental/sicherung/ sichern, Kandidat nach
      config/kapitalmassnahmen_historie.yaml übernehmen, Bericht nach docs/berichte/ kopieren.

Methode: Yahoo (und Tiingo) führen in der Spalte `split` echte Splits, aber auch Abspaltungen (Kursbereinigung). Den
echten Split-Faktor zeigt die SEC: Dieselbe Periode (gewichtete Aktienzahl eines Geschäftsjahrs) steht vor dem Ereignis
in der alten und danach in der ersten Einreichung neu auf der neuen Basis (ASC 260, rückwirkend). Verhältnis r = neu/alt.
- r ≈ Faktor der Kursreihe → Split (auch Aktiendividende); r ≈ 1 → Abspaltung (Split-Faktor 1);
- r weder noch → kombiniert (z. B. Reverse-Split und Abspaltung am selben Tag), Vorschlag Split-Faktor = r, zu prüfen;
- kein r (keine Einreichung davor/danach, Skalierungsfehler, Faktor nahe 1) → unklar, zu prüfen. Geraten wird nichts.
Liegen mehrere Ereignisse zwischen den beiden Einreichungen, wird gegen ihr Produkt geprüft.

Tresorgrenze (Befund 8 der unabhängigen Prüfung, Jakob 16.11.2026): kein Betriebsmodus. Kurse gelten nur bis zur
Datumsgrenze des Tresors (`begrenze` in lade_firmendaten), SEC-Einreichungen nur mit `filed` bis zur Grenze. Ein Ereignis
kurz vor der Grenze ohne Einreichung danach bleibt deshalb „unklar“. Einträge der Liste nach der Grenze werden
unverändert übernommen, nicht neu eingeordnet und im Bericht nicht genannt.

Regel für „unklar“ (Variante b, Jakob 24.11.2026): Ein Ereignis bis zur Grenze, das hier „unklar“ wird, darf als geprüfter
Split übernommen werden, wenn ein Beleg (8-K oder Anlage zum 8-K) mit filed ≤ Grenze Verhältnis und Wirksamkeitsdatum
nennt. Jakob gibt jeden Fall einzeln frei; die Freigaben stehen in daten/fundamental/einordnung/belege/freigaben.yaml und
werden beim nächsten Lauf angewendet (nur auf „unklar“, nur mit filed ≤ Grenze und vorhandenem Beleg in der Ablage).
"""
import argparse
import gzip
import hashlib
import json
import shutil
import socket
import sys
import warnings
from contextlib import contextmanager
from datetime import datetime
from io import StringIO
from pathlib import Path

import pandas as pd

from tradingbot.backtest.tresor import begrenze, datengrenze, pruefe_kein_betriebsmodus
from tradingbot.daten.index_nachbau import ABNAHME_ZEITRAUM
from tradingbot.daten.sp500_nachbau import ciks_der_zeile, lade_firmendaten
from tradingbot.daten.universum import lade_sic_historien, lade_universum
from tradingbot.daten.kursstatus import lade_kursstatus
from tradingbot.daten.kapitalmassnahmen_historie import PERIODENBERICHTE, einordnen, sec_verhaeltnis
from tradingbot.engines.fundamental.aktienzahl import aktienfakten
from tradingbot.konfiguration import PROJEKT_WURZEL

warnings.simplefilter("ignore")
LISTE = PROJEKT_WURZEL / "config" / "kapitalmassnahmen_historie.yaml"
ABLAGE = PROJEKT_WURZEL / "daten" / "fundamental" / "einordnung"
BELEGE = ABLAGE / "belege"
FREIGABEN = BELEGE / "freigaben.yaml"
SICHERUNG = PROJEKT_WURZEL / "daten" / "fundamental" / "sicherung"
CACHE = PROJEKT_WURZEL / "daten" / "cache"
BERICHTE = PROJEKT_WURZEL / "docs" / "berichte"
REGEL_UNKLAR = "Regel c3 Schritt 1b, Variante b (Jakob 24.11.2026)"
BELEG_TAGE_DAVOR, BELEG_TAGE_DANACH = 120, 15           # Fenster der 8-K um das Ereignis (Ankündigung bis Vollzug)
# Bekannte Bestätigungen aus Primärquellen (nicht aus dem Gedächtnis): Ticker, Datum → Bemerkung. Seit 16.11.2026 nur noch
# für Ereignisse bis zur Grenze wirksam; der Eintrag für 2026 bleibt als Beleg des übernommenen Betriebseintrags stehen.
BESTAETIGT = {("CMCSA", "2026-01-05"): ("abspaltung", "SEC 8-K vom 05.01.2026 (accn 0000950103-26-000079): Abspaltung Versant Media "
                                                     "(VSNT), 1 Versant je 25 Comcast, wirksam 02.01.2026 23:59 ET")}
KOPF = ("# Einordnung der „Split“-Ereignisse der Kursreihen (tools/split_ereignisse_einordnen.py, Jakob 13.11.2026).\n"
        "# art: split (auch Reverse-Split, Aktiendividende) | abspaltung | kombiniert | unklar | nicht_zugehoerig; "
        "split_faktor gilt für die Aktienzahl (Abspaltung: 1).\n"
        "# Einträge mit geprueft: true hat Jakob bestätigt; sie bleiben bei neuen Läufen unverändert.\n"
        "# Datumsfilter (korrigiert 16.11.2026, Befund 8 der unabhängigen Prüfung): lade_ereignisse liest ALLE Einträge, ohne\n"
        "# Datumsfilter. In Backtests wirken nur Ereignisse, die in der vom Tresor begrenzten Kursreihe stehen\n"
        "# (kapitalmassnahmen_historie.korrektur geht von den Ereignissen der Kursreihe aus). Einträge ab 2025 stammen aus\n"
        "# Läufen im Betriebsmodus bis 13.11.2026 und dienen dem Betrieb; seit 16.11.2026 ordnet das Werkzeug nur bis zur\n"
        "# Tresorgrenze ein und übernimmt sie unverändert (docs/TRESOR_BEKANNT.md).\n")
VERGLICHENE_FELDER = ("ticker", "faktor_kursreihe", "sec_verhaeltnis", "sec_einreichungen", "art", "split_faktor", "quelle",
                      "geprueft", "bemerkung")


class Abbruch(SystemExit):
    pass


class NetzGesperrt(BaseException):
    """Netzzugriff im Einordnungslauf. BaseException, damit kein `except Exception` (z. B. die Fehlerschwelle in
    lade_firmendaten) den Versuch still als Ladefehler zählt: Eine fehlende Datei bricht den Lauf ab, statt nachzuladen."""


# --- Netzsperre und Versiegelung (Jakob 24.11.2026) -----------------------------------------------------------------
@contextmanager
def netzsperre():
    """Sperrt Verbindungen und Namensauflösung; jeder Versuch wird protokolliert und bricht mit NetzGesperrt ab."""
    versuche: list[str] = []
    alt = socket.getaddrinfo, socket.socket.connect, socket.socket.connect_ex

    def gesperrt(*args, **kwargs):
        ziel = next((repr(a) for a in args if not isinstance(a, socket.socket)), "?")
        versuche.append(ziel)
        raise NetzGesperrt(f"Netzzugriff gesperrt ({ziel}): eine Datei fehlt im Cache und würde nachgeladen")
    socket.getaddrinfo, socket.socket.connect, socket.socket.connect_ex = gesperrt, gesperrt, gesperrt
    try:
        yield versuche
    finally:
        socket.getaddrinfo, socket.socket.connect, socket.socket.connect_ex = alt


def sha256(pfad: Path) -> str:
    h = hashlib.sha256()
    with open(pfad, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def inventar(wurzel: Path) -> dict[str, tuple[int, str]]:
    """Versiegelung: je Datei unter `wurzel` (relativer Pfad) Größe und SHA-256."""
    wurzel = Path(wurzel)
    if not wurzel.exists():
        return {}
    return {p.relative_to(wurzel).as_posix(): (p.stat().st_size, sha256(p)) for p in sorted(wurzel.rglob("*")) if p.is_file()}


def inventar_vergleichen(vorher: dict, nachher: dict) -> dict[str, list[str]]:
    return {"neu": sorted(set(nachher) - set(vorher)), "entfernt": sorted(set(vorher) - set(nachher)),
            "geaendert": sorted(k for k in set(vorher) & set(nachher) if vorher[k] != nachher[k])}


# --- Liste lesen, teilen, schreiben ------------------------------------------------------------------------------------
def lies_liste(pfad: Path) -> dict:
    from ruamel.yaml import YAML

    return YAML(typ="safe").load(Path(pfad).read_text(encoding="utf-8")) or {}


def eintraege_nach_schluessel(eintraege) -> dict:
    return {(int(e["cik"]), str(e["datum"])): dict(e) for e in eintraege or []}


def teile_nach_grenze(alt: dict, grenze: pd.Timestamp) -> tuple[dict, list[dict]]:
    """Trennt die bisherige Liste: Einträge bis zur Grenze (werden neu eingeordnet, außer geprüfte) und Einträge danach
    (unverändert übernommen, Befund 8)."""
    bis, nach = {}, []
    for schluessel, e in alt.items():
        if pd.Timestamp(str(e["datum"])) > grenze:
            nach.append(e)
        else:
            bis[schluessel] = e
    return bis, nach


def listentext(eintraege: list[dict], stand: str, grundlage: str | None = None) -> str:
    """Text im Format von config/kapitalmassnahmen_historie.yaml; `grundlage` = SHA-256 der Liste, auf der der Kandidat
    beruht (nur im Kandidaten; --uebernehmen prüft ihn und entfernt ihn)."""
    from ruamel.yaml import YAML

    puffer = StringIO()
    YAML().dump({"stand": stand, "ereignisse": eintraege}, puffer)
    text = puffer.getvalue()
    if grundlage:                                    # eigene Zeile, damit der YAML-Umbruch den Wert nicht teilt
        text = text.replace("\nereignisse:", f"\ngrundlage_sha256: {grundlage}\nereignisse:", 1)
    return KOPF + text


# --- Einordnung ------------------------------------------------------------------------------------------------------
def aktienfakten_mit_quartalen(ciks) -> pd.DataFrame:
    """Gewichtete Aktienzahl für Quartale und Geschäftsjahre (80–380 Tage) aus den gecachten companyfacts, ohne Netzabruf.
    Quartale lassen Ereignisse schon mit dem nächsten 10-Q einordnen (Vorjahresquartal neu dargestellt). Nur Einreichungen
    bis zur Tresorgrenze (`filed`, Befund 8). Fehlt eine companyfacts-Datei, bricht der Lauf ab (c3 1b)."""
    from tradingbot.daten.sec import SecClient
    from tradingbot.konfiguration import lade_konfiguration

    definition = lade_konfiguration("fundamental")["kennzahlen"]["gewichtete_aktien"]
    client, teile = SecClient(user_agent="offline"), []
    for cik in ciks:
        roh, _ = client.companyfacts_aus_cache(cik)
        if roh is None:
            raise Abbruch(f"companyfacts für CIK {cik} fehlen im Entwicklungs-Cache – kein Nachladen (c3 1b), Lauf abgebrochen")
        teile.append(aktienfakten(roh, definition, (80, 380)))
    fakten = pd.concat(teile, ignore_index=True) if teile else pd.DataFrame()
    return begrenze(fakten, "filed") if len(fakten) else fakten


def gleichstand(fakten: pd.DataFrame, tag: pd.Timestamp) -> dict:
    """Messung (c3 1b, nur messen): Gibt es auf dem Weg von `sec_verhaeltnis` Kandidaten mit gleichem Sortierschlüssel und
    verschiedenem Wert? Geprüft wird, (1) ob in der ersten Einreichung danach mehrere Werte dieselbe (ende, rang) haben
    und (2) ob es zu einer Periode davor mehrere Werte mit gleichem `filed` gibt; dazu r bei umgekehrter Zeilenfolge.
    Ändert nichts an der Einordnung."""
    ergebnis = {"gleichstand": False, "r_umgekehrt": None}
    if fakten is None or fakten.empty:
        return ergebnis
    f = fakten[fakten["form"].fillna("").isin(PERIODENBERICHTE)]
    vor, nach = f[f["filed"] < tag], f[f["filed"] > tag]
    if vor.empty or nach.empty:
        return ergebnis
    neu = nach[nach["filed"] == nach["filed"].min()]
    if (neu.groupby(["ende", "rang"])["wert"].nunique() > 1).any():
        ergebnis["gleichstand"] = True
    for _, z in neu.iterrows():
        alt = vor[(vor["ende"] == z["ende"]) & (vor["start"] == z["start"]) & (vor["konzept"] == z["konzept"])]
        if len(alt) and alt[alt["filed"] == alt["filed"].max()]["wert"].nunique() > 1:
            ergebnis["gleichstand"] = True
    ergebnis["r_umgekehrt"] = sec_verhaeltnis(fakten.iloc[::-1].reset_index(drop=True), tag)[0]
    return ergebnis


def lade_freigaben(pfad: Path = FREIGABEN) -> dict:
    """Jakobs Einzelfreigaben nach Variante b: (cik, datum) → {split_faktor, accn, filed, beleg, freigegeben}."""
    if not Path(pfad).exists():
        return {}
    return eintraege_nach_schluessel((lies_liste(pfad) or {}).get("freigaben", []))


def freigabe_anwenden(eintrag: dict, freigabe: dict, grenze: pd.Timestamp, belege: Path = BELEGE) -> dict:
    """Variante b: nur auf „unklar“, nur mit filed ≤ Grenze und Beleg in der Ablage; sonst Abbruch (nie still)."""
    schluessel = f"{eintrag['ticker']} {eintrag['datum']}"
    if eintrag["art"] != "unklar":
        raise Abbruch(f"Freigabe {schluessel}: Ereignis ist nicht „unklar“ ({eintrag['art']}) – Freigabe nicht anwendbar")
    if pd.Timestamp(str(freigabe["filed"])) > grenze:
        raise Abbruch(f"Freigabe {schluessel}: Beleg mit filed {freigabe['filed']} liegt nach der Tresorgrenze")
    accn = str(freigabe["accn"])
    if not list(Path(belege).glob(f"*/{accn}.txt.gz")):
        raise Abbruch(f"Freigabe {schluessel}: Beleg {accn} fehlt in der Belegablage {belege}")
    neu = dict(eintrag)
    neu.update(art="split", split_faktor=round(float(freigabe["split_faktor"]), 6), geprueft=True,
               quelle=f"SEC 8-K {freigabe['filed']} ({accn}): {freigabe['beleg']}; {REGEL_UNKLAR}, freigegeben {freigabe['freigegeben']}")
    return neu


def einordnung(grenze: pd.Timestamp, alt: dict, freigaben: dict) -> tuple[list[dict], dict]:
    """Ordnet alle Ereignisse bis zur Grenze ein (ohne Schreiben). Gibt (Einträge bis zur Grenze, Messung) zurück."""
    universum, _ = lade_universum()
    status = lade_kursstatus(universum)                 # über den Schlüssel (Befund 19, Schritt 2)
    daten = lade_firmendaten(universum, status, lade_sic_historien(universum), mitglied_ab=ABNAHME_ZEITRAUM[0], bis=grenze)
    namen = {int(z["cik"]): z["ticker"] for _, z in daten.relevant.sort_values("von", na_position="first").iterrows() if pd.notna(z["cik"])}
    eintraege, messung = [], {"ereignisse_mit_r": 0, "gleichstand": [], "r_anders": [], "art_anders": []}
    for firma, kurse in sorted(daten.kurse.items(), key=lambda x: str(x[0])):
        if isinstance(firma, str) or kurse is None or "split" not in kurse.columns:
            continue
        s = kurse["split"].fillna(0)
        s = s[(s > 0) & (s.index >= pd.Timestamp("2012-01-01")) & (s.index <= grenze)]
        if s.empty:
            continue
        zeile = daten.relevant[daten.relevant["cik"] == firma].iloc[0]
        fakten = aktienfakten_mit_quartalen(ciks_der_zeile(zeile))
        for tag, f in s.items():
            schluessel = (int(firma), str(tag.date()))
            if alt.get(schluessel, {}).get("geprueft"):
                eintraege.append(alt[schluessel])
                continue
            r, vor_f, nach_f, grund = sec_verhaeltnis(fakten, tag)
            fenster = s[(s.index > vor_f) & (s.index < nach_f)] if r is not None else s[s.index == tag]
            art, faktor, bemerkung = einordnen(float(f), r, float(fenster.prod()), len(fenster), grund)
            ticker = namen.get(int(firma), f"CIK{firma}")
            if r is not None:                            # Messung Gleichstand (nur messen, Jakob 24.11.2026)
                messung["ereignisse_mit_r"] += 1
                g = gleichstand(fakten, tag)
                if g["gleichstand"]:
                    messung["gleichstand"].append(f"{ticker} {tag.date()}")
                ru = g["r_umgekehrt"]
                if ru is None or abs(ru - r) > 1e-12:
                    messung["r_anders"].append(f"{ticker} {tag.date()} (r {r:.6f} / umgekehrt {ru})")
                    art_u = einordnen(float(f), ru, float(fenster.prod()), len(fenster), grund)[0]
                    if art_u != art:
                        messung["art_anders"].append(f"{ticker} {tag.date()} ({art} / umgekehrt {art_u})")
            bestaetigt = BESTAETIGT.get((ticker, str(tag.date())))
            if bestaetigt and bestaetigt[0] == art:
                bemerkung += "; bestätigt: " + bestaetigt[1]
            elif bestaetigt:
                bemerkung += f"; ABWEICHUNG zur Primärquelle ({bestaetigt[0]}): " + bestaetigt[1]
                art, faktor = "unklar", None
            eintrag = {"cik": int(firma), "ticker": ticker, "datum": str(tag.date()), "faktor_kursreihe": round(float(f), 6),
                       "sec_verhaeltnis": None if r is None else round(r, 6),
                       "sec_einreichungen": None if r is None else f"{vor_f.date()} → {nach_f.date()}",
                       "art": art, "split_faktor": None if faktor is None else round(float(faktor), 6),
                       "quelle": "SEC-Vergleich automatisch", "geprueft": False, "bemerkung": bemerkung}
            if schluessel in freigaben:
                eintrag = freigabe_anwenden(eintrag, freigaben[schluessel], grenze)
            eintraege.append(eintrag)
    unbenutzt = set(freigaben) - {(int(e["cik"]), str(e["datum"])) for e in eintraege}
    if unbenutzt:
        raise Abbruch(f"Freigaben ohne Ereignis bis zur Grenze: {sorted(unbenutzt)}")
    return eintraege, messung


# --- Vergleich und Bericht -------------------------------------------------------------------------------------------
def _gleich(a, b) -> bool:
    if isinstance(a, float) and isinstance(b, float):
        return abs(a - b) < 1e-9
    return a == b or (a in (None, "") and b in (None, ""))


def vergleich(alt: dict, neu: dict, grenze: pd.Timestamp) -> dict:
    """Unterschied Kandidat ↔ geltende Liste je Schlüssel (cik, datum)."""
    geaendert = []
    for k in sorted(set(alt) & set(neu), key=lambda k: (k[1], k[0])):
        felder = [(f, alt[k].get(f), neu[k].get(f)) for f in VERGLICHENE_FELDER if not _gleich(alt[k].get(f), neu[k].get(f))]
        if felder:
            geaendert.append((k, felder))

    def nach(k):
        return pd.Timestamp(k[1]) > grenze
    return {"neu": sorted((k for k in set(neu) - set(alt)), key=lambda k: (k[1], k[0])),
            "entfernt": sorted((k for k in set(alt) - set(neu)), key=lambda k: (k[1], k[0])),
            "geaendert": geaendert,
            "geaendert_nach_grenze": [k for k, _ in geaendert if nach(k)],
            "geaendert_geprueft": [k for k, _ in geaendert if alt[k].get("geprueft")]}


def vergleich_text(alt: dict, neu: dict, v: dict, messung: dict, siegel: dict, grenze, netz: list, zeit: str) -> str:
    def name(k, quelle):
        return f"{quelle[k].get('ticker', '?')} ({k[0]}) {k[1]}"
    unklar = [k for k, e in neu.items() if e.get("art") == "unklar" and pd.Timestamp(k[1]) <= grenze]
    z = [f"# Einordnung c3 Schritt 1b: Vergleich Kandidat ↔ geltende Liste ({zeit})", "",
         f"Tresorgrenze {grenze.date()}. Geltende Liste {len(alt)} Einträge, Kandidat {len(neu)}.", "",
         "## Abnahme", "",
         f"- Versiegelung daten/cache/: {sum(len(x) for x in siegel.values())} Dateien verändert "
         f"(neu {len(siegel['neu'])}, geändert {len(siegel['geaendert'])}, entfernt {len(siegel['entfernt'])}); erwartet 0.",
         f"- Netzversuche: {len(netz)}; erwartet 0.",
         f"- Geänderte Einträge nach der Grenze: {len(v['geaendert_nach_grenze'])}; erwartet 0.",
         f"- Geänderte geprüfte Einträge: {len(v['geaendert_geprueft'])}; erwartet 0.",
         f"- Neu: {len(v['neu'])}, entfernt: {len(v['entfernt'])}, geändert: {len(v['geaendert'])}.", ""]
    for titel, schl in (("Versiegelung: veränderte Dateien", [f"{a}: {p}" for a, ps in siegel.items() for p in ps]),
                        ("Neu im Kandidaten", [name(k, neu) for k in v["neu"]]),
                        ("Nicht mehr im Kandidaten", [name(k, alt) for k in v["entfernt"]])):
        if schl:
            z += [f"## {titel}", ""] + [f"- {s}" for s in schl] + [""]
    z += ["## Geänderte Einträge", "", "| Ereignis | Feld | geltend | Kandidat |", "| --- | --- | --- | --- |"]
    for k, felder in v["geaendert"]:
        for f, a, b in felder:
            z.append(f"| {name(k, neu)} | {f} | {a} | {b} |")
    z += ["", f"## „unklar“ bis zur Grenze im Kandidaten ({len(unklar)})", ""]
    z += [f"- {name(k, neu)}: Faktor Kursreihe {neu[k].get('faktor_kursreihe')}; {neu[k].get('bemerkung')}" for k in sorted(unklar, key=lambda k: (k[1], k[0]))]
    z += ["", "## Messung Gleichstand in sec_verhaeltnis (nur gemessen, nichts geändert)", "",
          f"- Ereignisse mit SEC-Verhältnis: {messung['ereignisse_mit_r']}",
          f"- mit Gleichstand (gleicher Sortierschlüssel, verschiedene Werte): {len(messung['gleichstand'])}"
          + (": " + ", ".join(messung["gleichstand"]) if messung["gleichstand"] else ""),
          f"- r anders bei umgekehrter Zeilenfolge: {len(messung['r_anders'])}"
          + (": " + "; ".join(messung["r_anders"]) if messung["r_anders"] else ""),
          f"- Art anders bei umgekehrter Zeilenfolge: {len(messung['art_anders'])}"
          + (": " + "; ".join(messung["art_anders"]) if messung["art_anders"] else ""), ""]
    return "\n".join(z) + "\n"


def bericht_text(eintraege: list[dict], grenze, neu_bis_grenze: int, nach_grenze: int, zeit: datetime) -> str:
    df = pd.DataFrame(eintraege)
    df = df[pd.to_datetime(df["datum"].astype(str)) <= grenze]           # Bericht nur bis zur Grenze
    zaehl = df.pivot_table(index="art", values="cik", aggfunc="count", fill_value=0)
    offen = df["art"].isin(["kombiniert", "unklar"]) & ~df["geprueft"].astype(bool)
    pruef = df[offen]
    geprueft = df[df["geprueft"].astype(bool)]
    text = ["# Split-Ereignisse der Kursreihen: Einordnung und Prüfliste", "",
            f"Erstellt {zeit:%d.%m.%Y %H:%M} mit `tools/split_ereignisse_einordnen.py`; Liste `config/kapitalmassnahmen_historie.yaml`. "
            f"{neu_bis_grenze} Ereignisse von 2012 bis zur Tresorgrenze ({grenze.date()}) in den Kursreihen des Universums, "
            f"Kurse und SEC-Einreichungen nur bis zur Grenze (Befund 8). {nach_grenze} Einträge nach der Grenze "
            "unverändert übernommen (hier nicht genannt).", "",
            "| Art | Ereignisse |", "| --- | --- |"]
    for art, z in zaehl.iterrows():
        text.append(f"| {art} | {int(z.iloc[0])} |")
    text += ["", f"## Prüfliste ({len(pruef)} Fälle: kombiniert oder unklar)", "",
             "Bitte je Fall: Art (split, abspaltung, kombiniert) und Split-Faktor für die Aktienzahl bestätigen oder korrigieren.", "",
             "| Ticker (CIK) | Datum | Faktor Kursreihe | SEC-Verhältnis | Einreichungen | Vorschlag | Bemerkung |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for z in pruef.itertuples():
        vorschlag = f"{z.art}, Split-Faktor {z.split_faktor:g}" if z.split_faktor is not None and not pd.isna(z.split_faktor) else z.art
        sec = "–" if z.sec_verhaeltnis is None or pd.isna(z.sec_verhaeltnis) else f"{z.sec_verhaeltnis:.4f}"
        text.append(f"| {z.ticker} ({z.cik}) | {z.datum} | {z.faktor_kursreihe:g} | {sec} | {z.sec_einreichungen or '–'} | {vorschlag} | {z.bemerkung} |")
    text += ["", f"## Von Jakob geprüft, mit Beleg ({len(geprueft)})", "",
             "| Ticker (CIK) | Datum | Faktor Kursreihe | Art | Split-Faktor | Beleg |", "| --- | --- | --- | --- | --- | --- |"]
    for z in geprueft.itertuples():
        f = "–" if z.split_faktor is None or pd.isna(z.split_faktor) else f"{z.split_faktor:g}"
        text.append(f"| {z.ticker} ({z.cik}) | {z.datum} | {z.faktor_kursreihe:g} | {z.art} | {f} | {z.quelle} |")
    abs_ = df[(df["art"] == "abspaltung") & ~df["geprueft"].astype(bool)]
    text += ["", f"## Automatisch als Abspaltung eingeordnet, ungeprüft ({len(abs_)})", "",
             ", ".join(f"{z.ticker} {z.datum} ({z.faktor_kursreihe:g})" for z in abs_.itertuples()) or "–", ""]
    einfach_aber_abs = abs_[abs_["faktor_kursreihe"].map(lambda v: abs(v - round(v)) < 1e-6 or abs(1 / v - round(1 / v)) < 1e-6)]
    if len(einfach_aber_abs):
        text += [f"Achtung: {len(einfach_aber_abs)} davon haben ein glattes Verhältnis: "
                 + ", ".join(f"{z.ticker} {z.datum}" for z in einfach_aber_abs.itertuples()), ""]
    return "\n".join(text) + "\n"


# --- Abläufe ---------------------------------------------------------------------------------------------------------
def grenze_pruefen(zweck: str) -> pd.Timestamp:
    pruefe_kein_betriebsmodus(zweck)
    grenze = datengrenze()
    if grenze is None:
        raise Abbruch("Einordnung nur mit Tresorgrenze (keine Tresor-Öffnung, kein Betriebsmodus)")
    return grenze


def lauf(ablage: Path = ABLAGE, liste: Path = LISTE, cache: Path = CACHE, freigaben_pfad: Path = FREIGABEN) -> Path:
    """Einordnung mit Netzsperre und Versiegelung; schreibt nur in `ablage`. Gibt den Pfad des Kandidaten zurück."""
    grenze = grenze_pruefen("Einordnung der Split-Ereignisse")
    zeit = datetime.now()
    grundlage = sha256(liste)
    geltend = eintraege_nach_schluessel(lies_liste(liste).get("ereignisse"))
    bis, nach_grenze = teile_nach_grenze(geltend, grenze)
    freigaben = lade_freigaben(freigaben_pfad)
    print(f"Versiegelung daten/cache/ (vorher) …", flush=True)
    vorher = inventar(cache)
    with netzsperre() as netz:
        try:
            eintraege, messung = einordnung(grenze, bis, freigaben)
        except NetzGesperrt as fehler:
            raise Abbruch(f"Abbruch: {fehler}") from None
    print(f"Versiegelung daten/cache/ (nachher) …", flush=True)
    siegel = inventar_vergleichen(vorher, inventar(cache))
    if netz:
        raise Abbruch(f"Abbruch: {len(netz)} Netzversuche ({netz[:3]}) – Kandidat wird nicht geschrieben")
    neu_bis_grenze = len(eintraege)
    alle = sorted(eintraege + nach_grenze, key=lambda e: (str(e["datum"]), e["ticker"]))
    if sha256(liste) != grundlage:
        raise Abbruch("Die geltende Liste wurde während des Laufs geändert – Kandidat wird nicht geschrieben")
    ablage.mkdir(parents=True, exist_ok=True)
    stempel = f"{zeit:%Y-%m-%d_%H%M}"
    kandidat = ablage / f"{stempel}_kandidat.yaml"
    kandidat.write_text(listentext(alle, zeit.isoformat(timespec="seconds"), grundlage), encoding="utf-8")
    v = vergleich(geltend, eintraege_nach_schluessel(alle), grenze)
    text = vergleich_text(geltend, eintraege_nach_schluessel(alle), v, messung, siegel, grenze, netz, f"{zeit:%d.%m.%Y %H:%M}")
    (ablage / f"{stempel}_vergleich.md").write_text(text, encoding="utf-8")
    (ablage / f"{stempel}_split_ereignisse.md").write_text(
        bericht_text(alle, grenze, neu_bis_grenze, len(nach_grenze), zeit), encoding="utf-8")
    print(text)
    print(f"Kandidat: {kandidat}")
    return kandidat


def belege_holen(kandidat: Path, belege: Path = BELEGE, client=None, lesen=None) -> list[Path]:
    """8-K (filed im Fenster um das Ereignis, höchstens bis zur Grenze) für alle „unklar“-Ereignisse bis zur Grenze holen.
    Einreichungsliste aus dem Entwicklungs-Cache (nur lesen); Dokumente nur in die Belegablage."""
    from tradingbot.daten.sec import SecClient, cik10

    grenze = grenze_pruefen("Belege der Split-Ereignisse")
    eintraege = lies_liste(kandidat).get("ereignisse") or []
    offen = [e for e in eintraege if e["art"] == "unklar" and pd.Timestamp(str(e["datum"])) <= grenze and not e.get("geprueft")]
    lesen = lesen or SecClient(user_agent="offline")
    client = client or SecClient(cache_wurzel=belege / "_kein_cache")
    geschrieben = []
    for e in offen:
        subs, _ = lesen._cache_lesen(lesen.cache_wurzel / "submissions" / f"CIK{cik10(e['cik'])}.json.gz")
        if subs is None:
            raise Abbruch(f"Einreichungsliste für {e['ticker']} fehlt im Entwicklungs-Cache – kein Nachladen")
        r = subs.get("filings", {}).get("recent", {})
        tag = pd.Timestamp(str(e["datum"]))
        von, bis = tag - pd.Timedelta(days=BELEG_TAGE_DAVOR), min(tag + pd.Timedelta(days=BELEG_TAGE_DANACH), grenze)
        ordner = belege / f"{e['ticker']}_{e['datum']}"
        ordner.mkdir(parents=True, exist_ok=True)
        index = []
        for form, filed, accn, items in zip(r.get("form", []), r.get("filingDate", []), r.get("accessionNumber", []),
                                            r.get("items", [""] * len(r.get("form", [])))):
            if not str(form).startswith("8-K") or not (von <= pd.Timestamp(filed) <= bis):
                continue
            datei = ordner / f"{accn}.txt.gz"
            if not datei.exists():
                url = f"https://www.sec.gov/Archives/edgar/data/{int(e['cik'])}/{accn.replace('-', '')}/{accn}.txt"
                text = client.text_holen(url)
                with gzip.open(datei, "wt", encoding="utf-8") as f:
                    f.write(text)
            index.append({"accn": accn, "form": form, "filed": filed, "items": items})
            geschrieben.append(datei)
        (ordner / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
        print(f"{e['ticker']} {e['datum']}: {len(index)} 8-K ({von.date()} bis {bis.date()})")
    return geschrieben


def uebernehmen(kandidat: Path, liste: Path = LISTE, sicherung: Path = SICHERUNG, berichte: Path = BERICHTE) -> Path:
    """Nur nach Jakobs Okay: geltende Liste sichern, Kandidat übernehmen (ohne `grundlage_sha256`), Bericht kopieren."""
    kandidat = Path(kandidat)
    daten = lies_liste(kandidat)
    if daten.get("grundlage_sha256") != sha256(liste):
        raise Abbruch("Die geltende Liste ist nicht mehr die Grundlage des Kandidaten – neu einordnen, nicht übernehmen")
    zeit = datetime.now()
    sicherung.mkdir(parents=True, exist_ok=True)
    ziel = sicherung / f"kapitalmassnahmen_historie_{zeit:%Y-%m-%d_%H%M%S}.yaml"
    shutil.copy2(liste, ziel)
    zeilen = kandidat.read_text(encoding="utf-8").splitlines(keepends=True)
    liste.write_text("".join(z for z in zeilen if not z.startswith("grundlage_sha256:")), encoding="utf-8")
    bericht = kandidat.with_name(kandidat.name.replace("_kandidat.yaml", "_split_ereignisse.md"))
    if bericht.exists():
        berichte.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bericht, berichte / bericht.name)
    print(f"Gesichert: {ziel}\nÜbernommen: {kandidat} → {liste}")
    return ziel


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    gruppe = p.add_mutually_exclusive_group()
    gruppe.add_argument("--uebernehmen", type=Path, metavar="KANDIDAT", help="nur nach Jakobs Okay")
    gruppe.add_argument("--belege-holen", type=Path, metavar="KANDIDAT", help="8-K-Belege der „unklar“-Fälle holen")
    a = p.parse_args(argv)
    if a.uebernehmen:
        uebernehmen(a.uebernehmen)
    elif a.belege_holen:
        belege_holen(a.belege_holen)
    else:
        lauf()
    return 0


if __name__ == "__main__":
    sys.exit(main())
