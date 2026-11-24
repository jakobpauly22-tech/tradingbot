r"""Nachweis „gleiche Bewertung vorher/nachher“ für die Laufzeit-Arbeit an der Fundamental-Bewertung (Jakob 19.11.2026).

Rechnet `engines/fundamental/aktuell.bewertung_am(stichtag, aktualisieren=False)` – ohne Kursabruf – und vergleicht die
Bewertungstabelle sowie die Ranglisten A und B exakt (Spalten, Datentypen, jeder Wert, Gründe und Signale) mit einer
zuvor festgehaltenen Referenz.

Eingefrorene Eingaben (Jakob 23.11.2026; Anlass: Yahoo korrigierte den MDLZ-Schluss vom 18.11. im Betriebscache, die alte
Schicht las darauf durch und die Referenz war nicht mehr erreichbar):
- **Referenz schreiben:** Die Bewertung läuft in einer leeren Schicht `eingefroren/` und protokolliert jeden Lesezugriff
  über `lesepfad` (daten/schicht.py, `erfassen`). Danach werden alle gelesenen Dateien (Kurse, Universum, SEC-Caches,
  SIC) in diese Schicht kopiert; `eingefroren.json` hält SHA-256 je Datei, die Pfade, die schon fehlten, und die
  Dateien, die am Cache vorbei direkt gelesen werden (Audit-Hook auf `open`, etwa kursstatus.csv) mit Prüfsumme.
  Anschließend ein versiegelter Selbstvergleich. Eine vorhandene Referenz wird nicht gelöscht, sondern mit Vermerk
  (`--grund`) nach `ersetzt_<Datum>/` verschoben.
- **Vergleichen:** nur aus einer Laufkopie der eingefrorenen Schicht, versiegelt (`versiegelt`: fehlt eine Datei →
  Abbruch, nie still nachladen), ohne Netz (Socket gesperrt). Direkt gelesene Dateien müssen dieselbe Prüfsumme haben
  wie bei der Referenz, ein direkter Lesezugriff auf andere Dateien unter daten/ bricht ab. Das eingefrorene
  Betriebsuniversum gilt im Betrieb nur für seinen Kalendertag; in der Laufkopie wird deshalb nur sein Tagesstempel
  auf heute gesetzt (Inhalt byteweise gleich), damit es nicht aus Wikipedia neu berechnet wird.
- **SEC-Cache des Betriebs (Jakob 23.11.2026, Abnahme A):** Seit Schritt 1 der SEC-Aktualisierung liest die Bewertung
  SEC-Daten unter `betrieb/cache/` statt `cache/`. Die Laufkopie bildet deshalb jede eingefrorene Datei der SEC-Bereiche
  (`betrieb/seccache.BEREICHE`) zusätzlich auf den Pfad des Betriebs ab (byteweise Kopie, SHA geprüft) und legt die Marke
  der Übernahme an; als fehlend erfasste Pfade gelten auch am neuen Ort als fehlend. Die Referenz bleibt unverändert.
- **`--sec-betrieb` (Abnahme B, Jakob 24.11.2026):** Wie oben, aber die SEC-Dateien kommen aus dem echten SEC-Cache des
  Betriebs (`daten/betrieb/cache/<Bereich>`, Stand nach der SEC-Aktualisierung) statt aus den eingefrorenen Eingaben; alle
  übrigen Eingaben (Kurse, Universum, Kursstatus) bleiben eingefroren. Jede eingefrorene SEC-Datei muss dort vorhanden
  sein (sonst Abbruch). Abweichungen zur Referenz sind hier erwartet; das Werkzeug listet die abweichenden Firmen und
  speichert das Ergebnis (`vergleich_sec_betrieb.pkl`) für den Bericht.

Betriebs- und Entwicklungsdaten bleiben unverändert (alles Schreiben geht in die Schicht).

  .venv\Scripts\python tools\bewertung_vergleich.py --referenz [--grund TEXT]   Referenz schreiben (vor jeder Änderung)
  .venv\Scripts\python tools\bewertung_vergleich.py                             vergleichen; Ausgang 0 nur bei „identisch“
"""
import argparse
import hashlib
import json
import os
import pickle
import shutil
import socket
import subprocess
import sys
import time
from contextlib import ExitStack, contextmanager
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from tradingbot.konfiguration import PROJEKT_WURZEL

STICHTAG = "2026-11-18"
DATEN = PROJEKT_WURZEL / "daten"
ORDNER = DATEN / "betrieb" / "probe" / "bewertung_referenz"
REFERENZ = ORDNER / "referenz.pkl"
EINGEFROREN = ORDNER / "eingefroren"
VERZEICHNIS = ORDNER / "eingefroren.json"
LAUF = ORDNER / "lauf"
UNIVERSUM = Path("betrieb") / "cache" / "universum" / "sp500.parquet"


class Abbruch(RuntimeError):
    """Vergleich nicht möglich (Eingaben geändert, Referenz ohne eingefrorene Eingaben, Netz gesperrt)."""


def sha256(pfad: Path) -> str:
    return hashlib.sha256(Path(pfad).read_bytes()).hexdigest()


# --- Wache: direkte Lesezugriffe unter daten/ (am Cache vorbei) und Netz --------------------------------------------
_WACHE: dict = {"modus": None, "daten": None, "gelesen": set(), "erlaubt": frozenset()}
_HOOK = False


def _hook(ereignis, args):
    w = _WACHE
    if ereignis != "open" or w["modus"] is None or not isinstance(args[0], (str, os.PathLike)):
        return
    schreibend = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND
    if any(c in str(args[1] or "r") for c in "wax+") or (isinstance(args[2], int) and args[2] & schreibend):
        return                                          # nur Lesen (z. B. Anhängen an betriebsfreigaben.log bleibt erlaubt)
    from tradingbot.daten.schicht import SchichtLuecke, aktive_schicht

    voll = Path(args[0]).resolve()
    schicht = aktive_schicht()
    if w["daten"] not in voll.parents or (schicht is not None and (voll == schicht or schicht in voll.parents)):
        return
    rel = voll.relative_to(w["daten"]).as_posix()
    if w["modus"] == "erfassen":
        w["gelesen"].add(rel)
    elif rel not in w["erlaubt"]:
        raise SchichtLuecke(f"direkter Lesezugriff auf daten/{rel} – nicht in den eingefrorenen Eingaben")


@contextmanager
def wache(modus: str, daten: Path, erlaubt=()):
    """`erfassen`: direkte Lesezugriffe unter `daten` sammeln; `versiegelt`: nur `erlaubt` zulassen und Netz sperren."""
    global _HOOK
    if not _HOOK:
        sys.addaudithook(_hook)                          # Audit-Hooks lassen sich nicht entfernen; ohne Modus wirkungslos
        _HOOK = True
    _WACHE.update(modus=modus, daten=Path(daten).resolve(), gelesen=set(), erlaubt=frozenset(erlaubt))
    alt = socket.socket.connect, socket.getaddrinfo

    def gesperrt(*a, **k):
        raise Abbruch("Netzzugriff im versiegelten Vergleich – eine Eingabe würde nachgeladen")
    if modus == "versiegelt":
        socket.socket.connect, socket.getaddrinfo = gesperrt, gesperrt
    try:
        yield _WACHE["gelesen"]
    finally:
        socket.socket.connect, socket.getaddrinfo = alt
        _WACHE.update(modus=None)


# --- Einfrieren, Prüfen, Laufkopie ---------------------------------------------------------------------------------
def einfrieren(protokoll: dict[str, bool], direkt: set[str], schicht: Path, daten: Path) -> dict:
    """Gelesene Originale in die Schicht kopieren (was der Lauf selbst geschrieben hat, bleibt); Verzeichnis zurückgeben."""
    for rel, existierte in sorted(protokoll.items()):
        ziel = schicht / rel
        if existierte and not ziel.exists():
            quelle = daten / rel
            if not quelle.exists():
                raise Abbruch(f"daten/{rel} wurde gelesen, ist aber verschwunden")
            ziel.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(quelle, ziel)
    dateien = {p.relative_to(schicht).as_posix(): sha256(p) for p in sorted(schicht.rglob("*")) if p.is_file()}
    fehlend = sorted(rel for rel in protokoll if rel not in dateien)
    direkt = sorted(set(direkt) - set(protokoll))
    return {"dateien": dateien, "fehlend": fehlend, "direkt": {rel: sha256(daten / rel) for rel in direkt}}


def pruefen(verzeichnis: dict, schicht: Path, daten: Path) -> list[str]:
    """Abweichungen der eingefrorenen Schicht und der direkt gelesenen Dateien gegenüber dem Verzeichnis."""
    aus = []
    for rel, soll in verzeichnis["dateien"].items():
        p = schicht / rel
        if not p.exists() or sha256(p) != soll:
            aus.append(f"eingefroren/{rel}: {'fehlt' if not p.exists() else 'geändert'}")
    vorhanden = {p.relative_to(schicht).as_posix() for p in schicht.rglob("*") if p.is_file()}
    aus += [f"eingefroren/{rel}: nicht im Verzeichnis" for rel in sorted(vorhanden - set(verzeichnis["dateien"]))]
    for rel, soll in verzeichnis["direkt"].items():
        p = daten / rel
        if not p.exists() or sha256(p) != soll:
            aus.append(f"daten/{rel} (direkt gelesen): {'fehlt' if not p.exists() else 'geändert seit der Referenz'}")
    return aus


def laufkopie(schicht: Path, lauf: Path) -> str | None:
    """Laufkopie der eingefrorenen Schicht; Tagesstempel des Betriebsuniversums auf heute (Inhalt unverändert).
    Gibt den ursprünglichen Stempel zurück (None ohne eingefrorenes Universum)."""
    import pyarrow.parquet as pq

    if lauf.exists():
        shutil.rmtree(lauf)
    shutil.copytree(schicht, lauf)
    datei = lauf / UNIVERSUM
    if not datei.exists():
        return None
    tabelle = pq.read_table(datei)
    schema_meta = dict(tabelle.schema.metadata or {})
    meta = json.loads(schema_meta.get(b"tradingbot", b"{}"))
    alt = meta.get("berechnet_am")
    meta.update(berechnet_am=datetime.now(timezone.utc).isoformat(timespec="seconds"), eingefroren_berechnet_am=alt)
    schema_meta[b"tradingbot"] = json.dumps(meta, default=str).encode()
    pq.write_table(tabelle.replace_schema_metadata(schema_meta), datei)
    return alt


def sec_abbilden(lauf: Path, fehlend, quelle: Path | None = None) -> tuple[int, list[str]]:
    """Eingefrorene Dateien der SEC-Bereiche (`cache/<Bereich>`) zusätzlich unter `betrieb/cache/<Bereich>` ablegen,
    byteweise mit SHA-Prüfung, und die Marke der Übernahme schreiben. Gibt (Zahl der Dateien, fehlende Pfade am neuen Ort).
    `quelle` (Abnahme B): Wurzel des echten Betriebsbereichs (`daten/betrieb`); dann wird je eingefrorener SEC-Datei die
    Datei `quelle/<cache/…>` (neuer SEC-Stand) abgelegt statt der eingefrorenen."""
    from tradingbot.betrieb.seccache import BEREICHE, MARKE

    def sec_pfad(rel: str) -> bool:
        return any(rel == f"cache/{b}" or rel.startswith(f"cache/{b}/") for b in BEREICHE)

    zahl = 0
    for datei in sorted(p for p in (lauf / "cache").rglob("*") if p.is_file()) if (lauf / "cache").exists() else []:
        rel = datei.relative_to(lauf).as_posix()
        if not sec_pfad(rel):
            continue
        ziel = lauf / "betrieb" / rel
        if ziel.exists():
            raise Abbruch(f"{ziel.relative_to(lauf).as_posix()} liegt schon in den eingefrorenen Eingaben – Abbildung nicht eindeutig")
        ziel.parent.mkdir(parents=True, exist_ok=True)
        herkunft = datei if quelle is None else Path(quelle) / rel
        if not herkunft.exists():
            raise Abbruch(f"{rel} fehlt im SEC-Cache des Betriebs ({herkunft})")
        shutil.copy2(herkunft, ziel)
        if sha256(ziel) != sha256(herkunft):
            raise Abbruch(f"Abbildung {rel} nicht byteweise gleich")
        zahl += 1
    marke = lauf / "betrieb" / "cache" / MARKE
    marke.parent.mkdir(parents=True, exist_ok=True)
    marke.write_text(json.dumps({"uebernommen_am": datetime.now().isoformat(timespec="seconds"), "dateien": zahl,
                                 "grund": "bewertung_vergleich: Abbildung der eingefrorenen SEC-Dateien (Abnahme A)" if quelle is None
                                 else f"bewertung_vergleich --sec-betrieb: SEC-Dateien aus {quelle} (Abnahme B)"},
                                ensure_ascii=False), encoding="utf-8")
    return zahl, [f"betrieb/{rel}" for rel in fehlend if sec_pfad(rel)]


def archivieren(ordner: Path, grund: str, heute: date) -> Path | None:
    """Vorhandene Referenz (alle Teile) nach `ersetzt_<Datum>[_n]/` verschieben, mit Vermerk; nichts wird gelöscht."""
    teile = [ordner / n for n in ("referenz.pkl", "referenz.json", "schicht", "eingefroren", "eingefroren.json", "lauf")]
    teile = [p for p in teile if p.exists()]
    if not teile:
        return None
    ziel, n = ordner / f"ersetzt_{heute.isoformat()}", 1
    while ziel.exists():
        n += 1
        ziel = ordner / f"ersetzt_{heute.isoformat()}_{n}"
    ziel.mkdir(parents=True)
    for p in teile:
        shutil.move(str(p), str(ziel / p.name))
    (ziel / "VERMERK.txt").write_text(f"ersetzt {heute:%d.%m.%Y}, Grund: {grund}\n", encoding="utf-8")
    return ziel


# --- Rechnen und Vergleichen ---------------------------------------------------------------------------------------
def rechnen(stichtag: str, schicht: Path, *, modus: str, verzeichnis: dict | None = None) -> tuple[dict, float, dict, set]:
    """Bewertung in der Schicht `schicht`. `erfassen`: Protokoll der Lesezugriffe; `versiegelt`: nur eingefrorene Eingaben."""
    from tradingbot.backtest.tresor import betriebsmodus
    from tradingbot.daten import schicht as sch
    from tradingbot.engines.fundamental.aktuell import bewertung_am, rangliste

    with ExitStack() as stapel:
        stapel.enter_context(sch.probe_schicht(schicht))
        stapel.enter_context(betriebsmodus("Probe: Bewertungsvergleich (Laufzeit, nur Schicht)"))
        if modus == "erfassen":
            protokoll = stapel.enter_context(sch.erfassen())
            direkt = stapel.enter_context(wache("erfassen", DATEN))
        else:
            protokoll, direkt = {}, set()
            stapel.enter_context(sch.versiegelt(verzeichnis["fehlend"]))
            stapel.enter_context(wache("versiegelt", DATEN, erlaubt=verzeichnis["direkt"]))
        beginn = time.perf_counter()
        bewertung, symbole, meldungen = bewertung_am(pd.Timestamp(stichtag), aktualisieren=False)
        dauer = time.perf_counter() - beginn
        ergebnis = {"bewertung": bewertung, "symbole": symbole, "meldungen": meldungen,
                    "rangliste_A": rangliste(bewertung, "A"), "rangliste_B": rangliste(bewertung, "B")}
        protokoll, direkt = dict(protokoll), set(direkt)
    return ergebnis, dauer, protokoll, direkt


def unterschiede(alt: pd.DataFrame, neu: pd.DataFrame, name: str) -> list[str]:
    """Leer, wenn beide Tabellen exakt gleich sind (Spalten, Reihenfolge, Datentypen, Werte); sonst die ersten Abweichungen."""
    if alt.equals(neu) and list(alt.columns) == list(neu.columns) and (alt.dtypes == neu.dtypes).all():
        return []
    aus = [f"{name}: Form {alt.shape} gegen {neu.shape}"]
    if list(alt.columns) != list(neu.columns):
        aus.append(f"{name}: Spalten verschieden: {sorted(set(alt.columns) ^ set(neu.columns))}")
        return aus
    unterschiedliche_typen = [s for s in alt.columns if alt[s].dtype != neu[s].dtype]
    if unterschiedliche_typen:
        aus.append(f"{name}: Datentypen verschieden: {unterschiedliche_typen}")
    if alt.shape == neu.shape:
        for s in alt.columns:
            for i in range(len(alt)):
                a, n = alt[s].iloc[i], neu[s].iloc[i]
                if not (a == n if not (pd.api.types.is_scalar(a) and pd.isna(a)) else pd.api.types.is_scalar(n) and pd.isna(n)):
                    aus.append(f"{name}: Zeile {i} ({alt['symbol'].iloc[i] if 'symbol' in alt else i}), Spalte {s}: {a!r} gegen {n!r}")
                    if len(aus) > 20:
                        return aus
    return aus


def git_stand() -> str:
    r = subprocess.run(["git", "describe", "--always", "--dirty"], cwd=PROJEKT_WURZEL, capture_output=True, text=True)
    return r.stdout.strip()


def firmen_abweichend(alt: pd.DataFrame, neu: pd.DataFrame) -> pd.DataFrame:
    """Je Firma (Spalte `firma`): neu/weg oder Spalten mit anderem Wert. Spalten: firma, symbol, art, spalten."""
    a, n = alt.set_index("firma"), neu.set_index("firma")
    zeilen = []
    for f in sorted(set(a.index) | set(n.index), key=str):
        if f not in a.index or f not in n.index:
            z = n.loc[f] if f in n.index else a.loc[f]
            zeilen.append({"firma": f, "symbol": z.get("symbol"), "art": "neu" if f in n.index else "weg", "spalten": []})
            continue
        verschieden = []
        for s in a.columns:
            x, y = a.at[f, s], n.at[f, s] if s in n.columns else None
            gleich = (pd.isna(x) and pd.isna(y)) if (pd.api.types.is_scalar(x) and pd.api.types.is_scalar(y)) else False
            if not gleich:
                try:
                    gleich = bool(x == y)
                except (TypeError, ValueError):
                    gleich = str(x) == str(y)
            if not gleich:
                verschieden.append(s)
        if verschieden:
            zeilen.append({"firma": f, "symbol": a.at[f, "symbol"], "art": "geändert", "spalten": verschieden})
    return pd.DataFrame(zeilen, columns=["firma", "symbol", "art", "spalten"])


def vergleichen(stichtag: str, sec_betrieb: bool = False) -> int:
    from tradingbot.daten.schicht import SchichtLuecke

    if not VERZEICHNIS.exists() or not REFERENZ.exists():
        print("Referenz ohne eingefrorene Eingaben (altes Format oder keine) – mit --referenz neu schreiben")
        return 2
    verzeichnis = json.loads(VERZEICHNIS.read_text(encoding="utf-8"))
    with REFERENZ.open("rb") as f:
        ref = pickle.load(f)
    if ref["stand"]["stichtag"] != stichtag:
        print(f"Referenz gilt für {ref['stand']['stichtag']}, nicht {stichtag}")
        return 2
    abweichend = pruefen(verzeichnis, EINGEFROREN, DATEN)
    if abweichend:
        print("ABBRUCH – eingefrorene Eingaben nicht mehr gleich:\n" + "\n".join(f"  {z}" for z in abweichend[:30]))
        return 2
    stempel = laufkopie(EINGEFROREN, LAUF)
    try:
        abgebildet, fehlend_neu = sec_abbilden(LAUF, verzeichnis["fehlend"], quelle=DATEN / "betrieb" if sec_betrieb else None)
    except Abbruch as f:
        print(f"ABBRUCH – {f}")
        return 2
    verzeichnis = {**verzeichnis, "fehlend": list(verzeichnis["fehlend"]) + fehlend_neu}
    print(f"SEC-Dateien auf den Betriebs-Cache abgebildet: {abgebildet} (byteweise, SHA gleich"
          + (", Quelle: echter SEC-Cache des Betriebs)" if sec_betrieb else ")"))
    print(f"Eingaben: {len(verzeichnis['dateien'])} eingefrorene Dateien, {len(verzeichnis['direkt'])} direkt gelesen (Prüfsumme gleich)"
          + (f"; Betriebsuniversum vom {stempel[:10]} (Tagesstempel in der Laufkopie auf heute)" if stempel else ""))
    try:
        ergebnis, dauer, _, _ = rechnen(stichtag, LAUF, modus="versiegelt", verzeichnis=verzeichnis)
    except (SchichtLuecke, Abbruch) as f:
        print(f"ABBRUCH – {f}")
        return 2
    abw = []
    for teil in ("bewertung", "rangliste_A", "rangliste_B"):
        abw += unterschiede(ref[teil], ergebnis[teil], teil)
    if ref["symbole"] != ergebnis["symbole"]:
        abw.append("Symbol je Firma verschieden")
    if list(ref["meldungen"]) != list(ergebnis["meldungen"]):
        abw.append(f"Meldungen verschieden: {ref['meldungen']} gegen {ergebnis['meldungen']}")
    print(f"Referenz: Git {ref['stand']['git']}, {ref['stand']['dauer_s']} s; jetzt: Git {git_stand()}, {round(dauer, 1)} s")
    if sec_betrieb:
        firmen = firmen_abweichend(ref["bewertung"], ergebnis["bewertung"])
        with (ORDNER / "vergleich_sec_betrieb.pkl").open("wb") as f:
            pickle.dump({"ergebnis": ergebnis, "firmen": firmen, "stand": {"stichtag": stichtag, "git": git_stand(),
                         "gerechnet_um": datetime.now().isoformat(timespec="seconds")}}, f)
        print(f"Mit dem SEC-Stand des Betriebs: {len(firmen)} Firmen abweichend ({len(ergebnis['bewertung'])} bewertet)")
        for z in firmen.itertuples():
            print(f"  {z.symbol or z.firma}: {z.art}" + (f" ({', '.join(z.spalten[:8])}{', …' if len(z.spalten) > 8 else ''})" if z.spalten else ""))
        return 0
    if abw:
        print("NICHT identisch:")
        print("\n".join(f"  {z}" for z in abw))
        return 1
    print(f"identisch ({len(ergebnis['bewertung'])} Firmen, Bewertung und Ranglisten A und B)")
    return 0


def referenz_schreiben(stichtag: str, grund: str | None) -> int:
    if any((ORDNER / n).exists() for n in ("referenz.pkl", "eingefroren")):
        if not grund:
            print("Es gibt schon eine Referenz – zum Ersetzen --grund angeben (sie wird mit Vermerk gesichert, nicht gelöscht)")
            return 2
        print(f"Alte Referenz gesichert: {archivieren(ORDNER, grund, date.today())}")
    EINGEFROREN.mkdir(parents=True)
    ergebnis, dauer, protokoll, direkt = rechnen(stichtag, EINGEFROREN, modus="erfassen")
    verzeichnis = einfrieren(protokoll, direkt, EINGEFROREN, DATEN)
    stand = {"stichtag": stichtag, "git": git_stand(), "gerechnet_um": datetime.now().isoformat(timespec="seconds"),
             "dauer_s": round(dauer, 1), "firmen": len(ergebnis["bewertung"])}
    VERZEICHNIS.write_text(json.dumps({**stand, **verzeichnis}, ensure_ascii=False, indent=1), encoding="utf-8")
    with REFERENZ.open("wb") as f:
        pickle.dump({**ergebnis, "stand": stand}, f)
    (ORDNER / "referenz.json").write_text(json.dumps(stand, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Referenz geschrieben: {stand}; {len(verzeichnis['dateien'])} Dateien eingefroren, {len(verzeichnis['fehlend'])} "
          f"fehlten schon, direkt gelesen: {sorted(verzeichnis['direkt'])}")
    print("Selbstvergleich (versiegelt):")
    return vergleichen(stichtag)


def main() -> int:
    load_dotenv(PROJEKT_WURZEL / ".env")
    a = argparse.ArgumentParser()
    a.add_argument("--referenz", action="store_true", help="Referenz schreiben statt vergleichen")
    a.add_argument("--grund", help="Grund für das Ersetzen einer vorhandenen Referenz (Vermerk)")
    a.add_argument("--stichtag", default=STICHTAG)
    a.add_argument("--sec-betrieb", action="store_true", help="SEC-Dateien aus dem echten SEC-Cache des Betriebs (Abnahme B)")
    arg = a.parse_args()
    return referenz_schreiben(arg.stichtag, arg.grund) if arg.referenz else vergleichen(arg.stichtag, arg.sec_betrieb)


if __name__ == "__main__":
    sys.exit(main())
