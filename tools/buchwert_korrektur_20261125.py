r"""Datenkorrektur Buchwert: Fremdwährungskasse zum Kurs des Laufs (Befund 1, Jakob 25.11.2026, D3 „korrigieren“).

Befund: Bis 25.11.2026 steckte die USD-Kasse der Fundamental-Bücher mit dem Kurs der jeweiligen Ausführung im Buchwert
(`Journal.kasse`), nicht zum Kurs des Laufs. Seit Befund 1 rechnet der Tageslauf mit `Journal.kasse_bewertet`
(EUR-Kasse + USD-Kasse / EURUSD des Laufs). Damit die Reihe am Tag der Umstellung nicht springt, werden die gespeicherten
Buchwerte rückwirkend in die neue Konvention gebracht.

Regeln (Plan vom 25.11.2026, Punkt 3):
- Kassenstand je Lauf: Kassenereignisse des Buchs (Ausführungen, Tausche, Kassenbuchungen) zeitlich geordnet; gewählt
  wird der längste Anfang mit Zeit ≤ Laufende (Ereignis `tageslauf`, letztes mit diesem Xetra-Tag), dessen Kasse in der
  alten Konvention auf den Cent der gespeicherten Kasse entspricht (Ausführungen, die während des Laufs eintrafen, hat
  erst der nächste Lauf eingelesen, z. B. Tausch am 09.11.2026 um 22:07:21). Kein solcher Anfang → Bruch.
- Laufkurs EURUSD: aus den in diesem Lauf eingelesenen USD-Ausführungen (preis / preis_eur, exakt), sonst zurückgerechnet
  Σ Stück × USD-Schluss (NYSE-Tag des Laufs, Kurs-Cache des Betriebs) / (Wert − Kasse). Rückrechnung und Beleg müssen
  auf 1e-4 übereinstimmen, die Rückrechnungen beider Bücher eines Laufs ebenso; sonst Bruch.
- Korrektur: Δ = EUR-Kasse + USD-Kasse / Laufkurs − gespeicherte Kasse; Wert und Wert mit Modellgebühr + Δ; Spalte
  `kasse` neu, Spalte `fx` = Laufkurs. Positionsteil unverändert. Zeilen ohne Fremdwährung bleiben unberührt.
- Idempotent: Zeilen mit gesetztem `fx`, deren Kasse schon der neuen Konvention entspricht, werden übersprungen.

  .venv\Scripts\python tools\buchwert_korrektur_20261125.py               Probelauf: Bericht, Journal nur lesend
  .venv\Scripts\python tools\buchwert_korrektur_20261125.py --ausfuehren  Sicherung, Korrektur, Ereignis „korrektur“
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

BUECHER = ("fundamental_a", "fundamental_b")
CENT = 0.005
FX_TOLERANZ = 1e-4
BERLIN = ZoneInfo("Europe/Berlin")
BERICHT = "docs/berichte/2026-11-25_buchwert_fremdwaehrungskasse.md"
GRUND = ("Befund 1 (Jakob 25.11.2026, D3): Fremdwährungskasse im Buchwert zum Kurs des Laufs statt zum Kurs der "
         "Ausführung; rückwirkende Korrektur, damit die Reihe bei der Umstellung nicht springt")


# --- Kassenereignisse ---------------------------------------------------------------------------------------------------
@dataclass
class Ereignis:
    zeit: datetime                                   # Ortszeit Berlin, ohne Zone
    quelle: str
    d_alt: float                                     # Änderung von Journal.kasse (alte Konvention, EUR)
    d_waehrung: dict[str, float]                     # Änderung von Journal.kasse_je_waehrung
    ticker: str | None = None
    d_stueck: float = 0.0
    fx_beleg: float | None = None                    # preis / preis_eur einer USD-Ausführung = Laufkurs beim Einlesen


def _lokal(zeit: str) -> datetime:
    t = pd.Timestamp(zeit)
    if t.tzinfo is not None:
        t = t.tz_convert(BERLIN).tz_localize(None)
    return t.to_pydatetime()


def kassenereignisse(db: sqlite3.Connection, buch: str) -> list[Ereignis]:
    """Alle Kassenereignisse des Buchs in derselben Rechnung wie Journal.kasse / kasse_je_waehrung, zeitlich geordnet.
    Dividenden (Tabelle) und Kapitalmaßnahmen werden nicht unterstützt: vorhanden → ValueError."""
    if db.execute("SELECT COUNT(*) FROM dividenden WHERE buch=?", (buch,)).fetchone()[0]:
        raise ValueError(f"{buch}: Dividenden-Tabelle nicht leer – Rekonstruktion nicht vorgesehen")
    if db.execute("SELECT COUNT(*) FROM kapitalmassnahmen_posten WHERE buch=?", (buch,)).fetchone()[0]:
        raise ValueError(f"{buch}: Kapitalmaßnahmen vorhanden – Rekonstruktion nicht vorgesehen")
    erg = []
    for z in db.execute("SELECT * FROM ausfuehrungen WHERE buch=?", (buch,)):
        w = z["waehrung"] or "EUR"
        preis = z["preis"] if z["preis"] is not None else z["preis_eur"]
        d = {w: -z["richtung"] * z["stueck"] * preis}
        gw = z["gebuehr_waehrung"] or "EUR"
        d[gw] = d.get(gw, 0.0) - (z["gebuehr"] if z["gebuehr"] is not None and gw != "EUR" else z["gebuehr_eur"])
        beleg = z["preis"] / z["preis_eur"] if w == "USD" and z["preis"] and z["preis_eur"] else None
        erg.append(Ereignis(_lokal(z["zeit"]), f"Ausführung {z['exec_id']}", -z["richtung"] * z["stueck"] * z["preis_eur"] - z["gebuehr_eur"],
                            d, z["ticker"], z["richtung"] * z["stueck"], beleg))
    for z in db.execute("SELECT * FROM tausche WHERE buch=?", (buch,)):
        d = {z["von"]: -z["betrag_von"]}
        d[z["nach"]] = d.get(z["nach"], 0.0) + z["betrag_nach"]
        gw = z["gebuehr_ibkr_waehrung"] if z["gebuehr_ibkr"] is not None else "EUR"
        if gw and gw != "EUR":
            d[gw] = d.get(gw, 0.0) - z["gebuehr_ibkr"]
        else:
            d["EUR"] = d.get("EUR", 0.0) - z["gebuehr_eur"]
        erg.append(Ereignis(_lokal(z["zeit"]), f"Tausch {z['exec_id']}", -z["gebuehr_eur"], d))
    for z in db.execute("SELECT * FROM kassenbuchungen WHERE buch=?", (buch,)):
        erg.append(Ereignis(_lokal(z["gebucht"]), f"Kassenbuchung {z['beleg_id']}", z["betrag_eur"], {z["waehrung"]: z["betrag"]}))
    return sorted(erg, key=lambda e: (e.zeit, e.quelle))


@dataclass
class Stand:
    kasse_alt: float
    kassen: dict[str, float]
    bestand: dict[str, float]


def stand(start: float, ereignisse: list[Ereignis]) -> Stand:
    alt, kassen, bestand = start, {"EUR": start}, {}
    for e in ereignisse:
        alt += e.d_alt
        for w, b in e.d_waehrung.items():
            kassen[w] = kassen.get(w, 0.0) + b
        if e.ticker:
            bestand[e.ticker] = bestand.get(e.ticker, 0.0) + e.d_stueck
    return Stand(alt, kassen, {t: s for t, s in bestand.items() if abs(s) > 1e-9})


# --- Läufe --------------------------------------------------------------------------------------------------------------
_LAUF = re.compile(r"Xetra (\d\d)\.(\d\d)\.(\d{4}), NYSE (\d\d)\.(\d\d)\.(\d{4})")


def laeufe(db: sqlite3.Connection) -> dict[str, tuple[datetime, str]]:
    """Xetra-Tag → (Ende des letzten Laufs dieses Tags, NYSE-Tag) aus den Ereignissen `tageslauf`."""
    erg = {}
    for z in db.execute("SELECT zeit, text FROM ereignisse WHERE art='tageslauf' ORDER BY zeit"):
        m = _LAUF.search(z["text"])
        if m:
            erg[f"{m[3]}-{m[2]}-{m[1]}"] = (_lokal(z["zeit"]), f"{m[6]}-{m[5]}-{m[4]}")
    return erg


# --- Rekonstruktion und Korrektur ---------------------------------------------------------------------------------------
@dataclass
class Zeile:
    buch: str
    tag: str
    wert: float
    kasse: float
    wert_modell: float | None
    fx_gespeichert: str | None
    laufende: datetime | None = None
    nyse: str | None = None
    anfang: int | None = None                        # Zahl der eingelesenen Kassenereignisse
    stand: Stand | None = None
    fx_beleg: float | None = None
    fx_rueck: float | None = None
    fx: float | None = None
    fx_quelle: str = ""
    kasse_neu: float | None = None
    status: str = ""                                 # unverändert | korrigieren | bereits korrigiert | Bruch
    hinweise: list[str] = field(default_factory=list)

    @property
    def fremd(self) -> dict[str, float]:
        return {w: b for w, b in (self.stand.kassen if self.stand else {}).items() if w != "EUR"}

    @property
    def delta(self) -> float:
        return 0.0 if self.kasse_neu is None or self.status != "korrigieren" else self.kasse_neu - self.kasse

    @property
    def wert_neu(self) -> float:
        return self.wert + self.delta

    @property
    def wert_modell_neu(self) -> float | None:
        return None if self.wert_modell is None else self.wert_modell + self.delta


def rekonstruieren(db: sqlite3.Connection, schluss_usd, buecher=BUECHER) -> list[Zeile]:
    """Plan der Korrektur für alle Buchwert-Zeilen der Bücher. `schluss_usd(ticker, tag) -> float | None`."""
    lauf = laeufe(db)
    zeilen: list[Zeile] = []
    for buch in buecher:
        start = db.execute("SELECT startkapital FROM buecher WHERE buch=?", (buch,)).fetchone()[0]
        ev = kassenereignisse(db, buch)
        voll = stand(start, ev)
        # Prüfung des Modells: alle Ereignisse ergeben genau die Rechnung des Journals
        if abs(voll.kasse_alt - _kasse_journal(db, buch, start)) > 1e-6:
            raise ValueError(f"{buch}: Kassenereignisse ergeben nicht Journal.kasse – Abbruch")
        vorher = 0
        for r in db.execute("SELECT * FROM buchwerte WHERE buch=? ORDER BY tag", (buch,)).fetchall():
            z = Zeile(buch, r["tag"], r["wert"], r["kasse"], r["wert_modell"], r["fx"] if "fx" in r.keys() else None)
            zeilen.append(z)
            if r["tag"] not in lauf:
                z.status, z.hinweise = "Bruch", ["kein Ereignis tageslauf für diesen Tag"]
                continue
            z.laufende, z.nyse = lauf[r["tag"]]
            fxg = json.loads(z.fx_gespeichert) if z.fx_gespeichert else None   # schon neue Konvention (Korrektur oder Tageslauf)
            treffer = [k for k in range(len(ev) + 1) if (k == 0 or ev[k - 1].zeit <= z.laufende)
                       and abs(_kasse(stand(start, ev[:k]), fxg) - z.kasse) < CENT]
            if not treffer:
                z.status, z.hinweise = "Bruch", ["kein Anfang der Kassenereignisse ergibt die gespeicherte Kasse"]
                continue
            z.anfang = max(treffer)
            z.stand = stand(start, ev[:z.anfang])
            if fxg is not None:
                z.status, z.fx, z.fx_quelle, z.kasse_neu = "bereits korrigiert", fxg.get("USD"), "gespeichert", z.kasse
                vorher = z.anfang
                continue
            belege = [e.fx_beleg for e in ev[min(vorher, z.anfang):z.anfang] if e.fx_beleg]
            vorher = z.anfang
            if belege:
                z.fx_beleg = belege[-1]
                if max(belege) - min(belege) > FX_TOLERANZ:
                    z.hinweise.append(f"Belegkurse im Lauf uneinheitlich: {min(belege):.5f}–{max(belege):.5f}")
            pos = z.wert - z.kasse
            if z.stand.bestand and pos > 0:
                usd = 0.0
                for t, s in z.stand.bestand.items():
                    k = schluss_usd(t, z.nyse)
                    if k is None:
                        z.hinweise.append(f"kein USD-Schluss für {t} am {z.nyse}")
                        usd = None
                        break
                    usd += s * k
                z.fx_rueck = None if usd is None else usd / pos
    _laufkurs_festlegen(zeilen)
    for z in zeilen:
        if z.status in ("Bruch", "bereits korrigiert"):
            continue
        if not z.fremd:
            z.status = "unverändert"
            continue
        if z.fx is None:
            z.status = "Bruch"
            continue
        z.kasse_neu = z.stand.kassen.get("EUR", 0.0) + sum(b / z.fx for b in z.fremd.values())
        if set(z.fremd) != {"USD"}:
            z.status, z.hinweise = "Bruch", z.hinweise + [f"Fremdwährungen {sorted(z.fremd)} – nur USD vorgesehen"]
        else:
            z.status = "korrigieren"
    return zeilen


def _kasse(st: Stand, fx: dict[str, float] | None) -> float:
    """Kasse des Stands: alte Konvention (fx None) oder neue (EUR + Fremdwährung / fx, wie Journal.kasse_bewertet)."""
    fremd = {w: b for w, b in st.kassen.items() if w != "EUR"}
    if fx is None or not fremd:
        return st.kasse_alt
    return st.kassen.get("EUR", 0.0) + sum(b / fx[w] for w, b in fremd.items())


def _kasse_journal(db, buch, start) -> float:
    q = lambda sql: db.execute(sql, (buch,)).fetchone()[0]  # noqa: E731
    return (start + q("SELECT COALESCE(SUM(-richtung * stueck * preis_eur - gebuehr_eur), 0) FROM ausfuehrungen WHERE buch=?")
            + q("SELECT COALESCE(SUM(betrag_eur), 0) FROM dividenden WHERE buch=?") - q("SELECT COALESCE(SUM(gebuehr_eur), 0) FROM tausche WHERE buch=?")
            + q("SELECT COALESCE(SUM(betrag_eur), 0) FROM kassenbuchungen WHERE buch=?"))


def _laufkurs_festlegen(zeilen: list[Zeile]) -> None:
    """Ein Lauf hat einen EURUSD für alle Bücher: Beleg aus einer Ausführung (exakt), sonst Mittel der Rückrechnungen."""
    for tag in sorted({z.tag for z in zeilen}):
        tz = [z for z in zeilen if z.tag == tag and z.status not in ("Bruch", "bereits korrigiert")]
        belege = [z.fx_beleg for z in tz if z.fx_beleg]
        rueck = [z.fx_rueck for z in tz if z.fx_rueck]
        fehler = []
        if rueck and max(rueck) - min(rueck) > FX_TOLERANZ:
            fehler.append(f"Rückrechnungen der Bücher weichen ab: {', '.join(f'{x:.5f}' for x in rueck)}")
        if belege and max(belege) - min(belege) > FX_TOLERANZ:
            fehler.append(f"Belegkurse der Bücher weichen ab: {', '.join(f'{x:.5f}' for x in belege)}")
        if belege and rueck and abs(belege[0] - sum(rueck) / len(rueck)) > FX_TOLERANZ:
            fehler.append(f"Beleg {belege[0]:.5f} ≠ Rückrechnung {sum(rueck) / len(rueck):.5f}")
        if fehler:
            for z in tz:
                if z.fremd:
                    z.status, z.hinweise = "Bruch", z.hinweise + fehler
            continue
        fx, quelle = (belege[0], "Ausführung") if belege else ((sum(rueck) / len(rueck), "Rückrechnung") if rueck else (None, ""))
        for z in tz:
            z.fx, z.fx_quelle = fx, quelle


def ausfuehren(db: sqlite3.Connection, zeilen: list[Zeile]) -> int:
    n = 0
    for z in zeilen:
        if z.status != "korrigieren":
            continue
        db.execute("UPDATE buchwerte SET wert=?, kasse=?, wert_modell=?, fx=? WHERE buch=? AND tag=?",
                   (z.wert_neu, z.kasse_neu, z.wert_modell_neu, json.dumps({"USD": z.fx}, sort_keys=True), z.buch, z.tag))
        n += 1
    return n


# --- Bericht ------------------------------------------------------------------------------------------------------------
def _e(x: float | None, nk: int = 2) -> str:
    if x is None:
        return "–"
    return f"{x:,.{nk}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def abgleich_mit_journal(db: sqlite3.Connection, zeilen: list[Zeile]) -> list[str]:
    """Querprüfung: Kasse neu am letzten Tag je Buch = Journal.kasse_bewertet (Code des Tageslaufs) mit demselben Laufkurs,
    sofern seither nichts mehr eingelesen wurde. Rechnet auf einer Kopie im Arbeitsspeicher-Ordner (Journal ergänzt Spalten)."""
    import tempfile
    from pathlib import Path

    from tradingbot.betrieb.journal import Journal

    erg = []
    with tempfile.TemporaryDirectory() as tmp:
        kopie = sqlite3.connect(Path(tmp) / "j.sqlite")
        db.backup(kopie)
        kopie.close()
        j = Journal(Path(tmp) / "j.sqlite")
        try:
            for buch in dict.fromkeys(z.buch for z in zeilen):
                z = [x for x in zeilen if x.buch == buch][-1]
                if z.status not in ("korrigieren", "bereits korrigiert") or z.stand is None:
                    continue
                if len(kassenereignisse(j.db, buch)) != z.anfang:
                    erg.append(f"{buch}: seit dem Lauf vom {z.tag} neue Kassenereignisse – Querprüfung entfällt")
                    continue
                code = j.kasse_bewertet(buch, {"USD": z.fx})
                ok = abs(code - z.kasse_neu) < 1e-6
                erg.append(f"{buch} {z.tag}: Kasse neu {_e(z.kasse_neu, 4)} €, Journal.kasse_bewertet {_e(code, 4)} € – "
                           f"{'gleich' if ok else 'ABWEICHUNG'}")
        finally:
            j.schliessen()
    return erg


def bericht(zeilen: list[Zeile], *, ausgefuehrt: bool, jetzt: datetime, sicherung: str | None = None,
            querpruefung: list[str] = ()) -> str:
    z_all = zeilen
    t = [f"# Datenkorrektur Buchwert: Fremdwährungskasse zum Laufkurs ({jetzt:%d.%m.%Y})", "",
         f"Stand: {'**ausgeführt** ' + f'{jetzt:%d.%m.%Y %H:%M}' if ausgefuehrt else '**Probelauf**, Journal nur gelesen'}"
         + (f"; Sicherung vorher: `{sicherung}`" if sicherung else ""), "",
         "Grundlage: Befund 1, Entscheidungen Jakob 25.11.2026 (D3 korrigieren, D4 Spalte `kasse` neu plus `fx`). Werkzeug "
         "`tools/buchwert_korrektur_20261125.py`, Regeln im Kopf des Werkzeugs.", "",
         "Δ = EUR-Kasse + USD-Kasse / Laufkurs − gespeicherte Kasse; Wert und Wert mit Modellgebühr verschieben sich um Δ, "
         "der Positionsteil bleibt.", ""]
    for buch in dict.fromkeys(z.buch for z in z_all):
        zb = [z for z in z_all if z.buch == buch]
        t += [f"## {buch}", "",
              "| Tag | NYSE | Laufkurs (Quelle) | EUR-Kasse | USD-Kasse $ | Kasse alt | Kasse neu | Δ | Wert alt | Wert neu | Modell alt | Modell neu | Status |",
              "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
        for z in zb:
            usd = z.fremd.get("USD") if z.stand else None
            eur = z.stand.kassen.get("EUR") if z.stand else None
            fx = f"{_e(z.fx, 5)} ({z.fx_quelle})" if z.fx and z.fremd else "–"
            t.append(f"| {z.tag} | {z.nyse or '–'} | {fx} | {_e(eur)} | {_e(usd)} | {_e(z.kasse)} | "
                     f"{_e(z.kasse_neu if z.fremd else z.kasse)} | {_e(z.delta)} | {_e(z.wert)} | {_e(z.wert_neu)} | {_e(z.wert_modell)} | "
                     f"{_e(z.wert_modell_neu)} | {z.status} |")
        letzte = zb[-1]
        t += ["", f"Wert am {letzte.tag}: alt {_e(letzte.wert)} €, neu {_e(letzte.wert_neu)} € "
                  f"(gegen 10.000 €: {_e((letzte.wert / 10_000 - 1) * 100)} % → {_e((letzte.wert_neu / 10_000 - 1) * 100)} %)", ""]
        for z in zb:
            for h in z.hinweise:
                t.append(f"- {z.tag}: {h}")
        t.append("")
    br = [z for z in z_all if z.status == "Bruch"]
    t += ["## Abnahme (Plan Punkt 5.4)", "",
          f"- Rekonstruierte Kasse (alte Konvention) je Tag auf den Cent gleich der gespeicherten: "
          f"{'ja' if not any('Anfang' in h for z in br for h in z.hinweise) else 'nein'} "
          f"({sum(1 for z in z_all if z.stand)} von {len(z_all)} Zeilen).",
          f"- Laufkurs je Tag in beiden Büchern gleich (≤ 1e-4) und mit Belegkursen verträglich: "
          f"{'ja' if not any('weichen' in h or '≠' in h for z in br for h in z.hinweise) else 'nein'}.",
          f"- Brüche: {len(br)}" + (" – " + ", ".join(f"{z.buch} {z.tag}" for z in br) if br else "") + ".",
          f"- Zu korrigieren: {sum(1 for z in z_all if z.status == 'korrigieren')}, bereits korrigiert: "
          f"{sum(1 for z in z_all if z.status == 'bereits korrigiert')}, unverändert: {sum(1 for z in z_all if z.status == 'unverändert')}.",
          "- Andere Bücher (real, crossover, momentum, regime): nicht angefasst.",
          *[f"- Querprüfung mit dem Code des Tageslaufs: {q}" for q in querpruefung], ""]
    return "\n".join(t)


# --- Ablauf -------------------------------------------------------------------------------------------------------------
def _schluss_aus_cache(cache):
    gelesen: dict[str, pd.DataFrame | None] = {}

    def schluss(ticker: str, tag: str) -> float | None:
        if ticker not in gelesen:
            gelesen[ticker] = cache.lesen("kurse", ticker)[0]
        df = gelesen[ticker]
        if df is None:
            return None
        df = df.copy()
        df.index = pd.to_datetime(df.index).tz_localize(None) if getattr(df.index, "tz", None) else pd.to_datetime(df.index)
        ts = pd.Timestamp(tag)
        return float(df.loc[ts, "close"]) if ts in df.index else None
    return schluss


def main() -> int:
    from dotenv import load_dotenv

    from tradingbot.backtest.tresor import betriebsmodus
    from tradingbot.betrieb.journal import Journal
    from tradingbot.betrieb.kurscache import betriebs_kurscache
    from tradingbot.betrieb.speicher import betriebspfad
    from tradingbot.betrieb.sperre import laufsperre
    from tradingbot.konfiguration import PROJEKT_WURZEL

    load_dotenv(PROJEKT_WURZEL / ".env")
    a = argparse.ArgumentParser()
    a.add_argument("--ausfuehren", action="store_true")
    a.add_argument("--journal", help="anderes Journal (z. B. Kopie für eine Probe)")
    arg = a.parse_args()
    jetzt = datetime.now()
    with betriebsmodus("Buchwert-Korrektur 25.11.2026" + ("" if arg.ausfuehren else ", Probelauf")):
        with laufsperre(betriebspfad("tageslauf.sperre"), zweck="Buchwert-Korrektur"):
            pfad = arg.journal or betriebspfad("journal.sqlite")
            schluss = _schluss_aus_cache(betriebs_kurscache())
            if not arg.ausfuehren:                      # Probelauf: Journal nur lesend öffnen (auch keine Spaltenergänzung)
                db = sqlite3.connect(f"file:{pfad}?mode=ro", uri=True)
                db.row_factory = sqlite3.Row
                zeilen = rekonstruieren(db, schluss)
                quer = abgleich_mit_journal(db, zeilen)
                db.close()
                text = bericht(zeilen, ausgefuehrt=False, jetzt=jetzt, querpruefung=quer)
                if any(z.status == "korrigieren" for z in zeilen):   # nach der Ausführung den Bericht nicht überschreiben
                    (PROJEKT_WURZEL / BERICHT).write_text(text, encoding="utf-8")
                print(text)
                print(f"\nProbelauf – nichts geändert. Bericht: {BERICHT}. Mit --ausfuehren korrigieren.")
                return 0
            j = Journal(pfad)
            zeilen = rekonstruieren(j.db, schluss)
            if any(z.status == "Bruch" for z in zeilen):
                print("ABBRUCH, nichts geändert: Brüche vorhanden (siehe Probelauf).")
                return 1
            ziel = j.sichern(None)
            if ziel is None:
                print("ABBRUCH, nichts geändert: keine Sicherung (JOURNAL_BACKUP_DIR fehlt).")
                return 1
            with j.db:
                n = ausfuehren(j.db, zeilen)
                for buch in BUECHER:
                    zb = [z for z in zeilen if z.buch == buch and z.status == "korrigieren"]
                    if zb:
                        j.db.execute("INSERT INTO ereignisse (zeit, art, buch, text) VALUES (?,?,?,?)",
                                     (jetzt.isoformat(timespec="seconds"), "korrektur", buch,
                                      f"Buchwerte {zb[0].tag}–{zb[-1].tag} ({len(zb)} Tage) in neue Konvention gebracht, Δ "
                                      f"{zb[0].delta:+.2f} … {zb[-1].delta:+.2f} €; alte Werte in {ziel.name} und {BERICHT}. Grund: {GRUND}"))
            nachher = rekonstruieren(j.db, schluss)
            text = bericht(zeilen, ausgefuehrt=True, jetzt=jetzt, sicherung=ziel.name)
            (PROJEKT_WURZEL / BERICHT).write_text(text, encoding="utf-8")
            print(text)
            offen = [z for z in nachher if z.status == "korrigieren"]
            print(f"\n{n} Zeilen korrigiert; zweiter Durchgang: {len(offen)} offen (erwartet 0).")
            return 0 if not offen else 1


if __name__ == "__main__":
    sys.exit(main())
