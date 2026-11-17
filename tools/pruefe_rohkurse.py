r"""Abnahme der unbereinigten Rohreihen für den Marktwert (c2 (2), Kriterien vor dem Lauf festgehalten in
docs/FUNDAMENTAL.md, „c2 (2): Marktwert aus Rohkursen – Abnahme und Stichprobe“, Jakob 15.11.2026). Nur lesend, ohne Netz.

Aufruf:  .venv\Scripts\python tools\pruefe_rohkurse.py
Ergebnis: daten/cache/tiingo/roh_bis_tresor/abnahme.csv (von lade_firmendaten(rohkurse=True) gelesen) und
docs/berichte/<Datum>_rohkurse_abnahme.md. Wiederholbar: nach dem Nachladen ab 01.12.2026 erneut starten.

Je gültiger Kursreihe des Universums: Rohreihe (Yahoo-Reihen aus dem Nachlader, Tiingo-Reihen aus dem Tiingo-Cache) gegen
die nur splitbereinigte Reihe aus dem Cache (daten/rohkurse_marktwert.abnahme). Yahoo-Reihen zusätzlich mit dem zweiten
Kriterium „Splitspalte“ (Befund 10, Jakob 16.11.2026: Tiingo-Splitfaktoren gegen Yahoo-Ereignisse und
config/kapitalmassnahmen_historie.yaml, daten/rohkurse_marktwert.splitabgleich). Nicht bestanden: Rückfall auf die bisherige
Rechnung. Fehlerschwelle 5 % der Reihen mit Rohreihe; geprüft wird erst am Ende, damit abnahme.csv und Bericht vollständig
sind; die Sperre der c3-Werkzeuge liest die Schwelle aus abnahme.csv (Befund 14).
"""
import sys
import warnings
from datetime import datetime

import pandas as pd

from tradingbot.backtest.tresor import begrenze
from tradingbot.daten.cache import standard_cache
from tradingbot.daten.fehlerschwelle import Fehlerschwelle, FehlerschwelleUeberschritten, laut_melden
from tradingbot.daten.kapitalmassnahmen_historie import lade_ereignisse
from tradingbot.daten.rohkurse_marktwert import (SPALTEN_ABNAHME, abnahme, abnahme_datei, dauerhaft_nicht_verfuegbar,
                                                 fehlende_fuer_c3, rohreihe, schwelle_der_abnahme, splitabgleich)
from tradingbot.daten.sp500_nachbau import ciks_der_zeile
from tradingbot.daten.universum import lade_universum
from tradingbot.daten.tiingo import TiingoClient
from tradingbot.konfiguration import PROJEKT_WURZEL

warnings.simplefilter("ignore")


class OhneNetz:
    def get(self, *a, **k):
        raise RuntimeError("Tiingo-Abruf in diesem Werkzeug verboten (nur Cache)")


FUELLWORTE = {"inc", "corp", "corporation", "co", "company", "plc", "the", "ltd", "class", "holdings", "group", "a", "b", "c", "n", "v"}


def name_passt(a, b) -> bool:
    """Grobe Namensprüfung (nur Meldung, kein Ausschluss): ein gemeinsames Wort ohne Füllwörter wie Inc/Corp/plc, oder
    gleiche Buchstabenfolge ohne Leerzeichen (Conoco Phillips = ConocoPhillips)."""
    if not a or not b or str(a) == "nan" or str(b) == "nan":
        return True
    worte = lambda x: [w for w in "".join(c if c.isalnum() else " " for c in str(x).lower()).split() if w not in FUELLWORTE]  # noqa: E731
    wa, wb = worte(a), worte(b)
    return bool(set(wa) & set(wb)) or "".join(wa) == "".join(wb)


def mit_verdecktem_faktor(t: pd.DataFrame) -> pd.Series:
    """Reihen mit verdecktem Faktor H ≠ 1 (|H − 1| > 0,5 %): Split nach der Tresorgrenze."""
    return (t["H"] - 1).abs() > 0.005


def abschnitt_nicht_bestanden(nicht: pd.DataFrame) -> list[str]:
    """Tabelle der nicht bestandenen Reihen OHNE die Spalte H (Jakob 16.11.2026): Ein Faktor H ≠ 1 verrät einen Split
    nach der Tresorgrenze; er erscheint nur als Anzahl. Bestehende Berichte bleiben unverändert (docs/TRESOR_BEKANNT.md)."""
    n_h = int(mit_verdecktem_faktor(nicht).sum()) if len(nicht) else 0
    zeilen = [f"## Nicht bestanden ({len(nicht)}; davon mit H ≠ 1: {n_h})", "",
              "| Symbol (Quelle) | Tage | Anteil ≤ 1 % | größte Abweichung | Grund |", "| --- | --- | --- | --- | --- |"]
    return zeilen + [f"| {r.symbol} ({r.quelle}) | {r.tage} | {r.anteil_ok:.1%} | {r.max_abw:.1%} | {r.grund} |" for r in nicht.itertuples()]


def abschnitt_verdeckt(t: pd.DataFrame) -> list[str]:
    """Verdeckter Faktor H ≠ 1 bei bestandenen Reihen: nur die Anzahl, ohne Namen und Faktor (Jakob 16.11.2026)."""
    n = int((t["bestanden"] & mit_verdecktem_faktor(t)).sum())
    return [f"## Verdeckter Faktor H ≠ 1 (Split nach der Tresorgrenze; Rohkurs nötig): {n} Reihen", "",
            "Nur als Anzahl, ohne Namen und Faktor (Tresor, Jakob 16.11.2026); die Werte stehen in abnahme.csv (nicht in Git)."]


def liste_der_reihe(ciks: set[int], ereignisse: dict[int, pd.DataFrame]) -> pd.DataFrame | None:
    """Einträge der Kapitalmaßnahmen-Liste für alle CIKs, deren Universumszeilen die Reihe nutzen (Befund 10)."""
    teile = [ereignisse[c] for c in sorted(ciks) if c in ereignisse]
    if not teile:
        return None
    t = pd.concat(teile).sort_index()
    return t[~t.index.duplicated(keep="first")]


def ciks_je_reihe(status: pd.DataFrame, universum: pd.DataFrame) -> dict[tuple[str, str], set[int]]:
    """(quelle, symbol) → CIKs aller gültigen Universumszeilen mit dieser Reihe (Index von kursstatus = Zeile im Universum)."""
    ergebnis: dict = {}
    for nr, z in status[status["gueltig"].astype(bool)].iterrows():
        if nr in universum.index:
            ergebnis.setdefault((z["quelle"], z["symbol"]), set()).update(ciks_der_zeile(universum.loc[nr]))
    return ergebnis


def main() -> int:
    status = pd.read_csv(PROJEKT_WURZEL / "daten" / "universum" / "kursstatus.csv").set_index("index")
    gueltig = status[status["gueltig"].astype(bool)].drop_duplicates(["quelle", "symbol"])
    cache, tiingo = standard_cache(), TiingoClient(sitzung=OhneNetz())
    universum, _ = lade_universum()
    ciks, ereignisse = ciks_je_reihe(status, universum), lade_ereignisse()
    zeilen, ohne_roh = [], []
    schwelle = Fehlerschwelle("Rohkurse: Abnahme", mindestens=10**9)      # nur am Ende prüfen (Befund 14)
    for z in gueltig.itertuples():
        roh = rohreihe(z.quelle, z.symbol)
        if roh is None:
            ohne_roh.append(f"{z.symbol} ({z.quelle})")
            continue
        try:
            b = cache.lesen("kurse", z.symbol)[0] if z.quelle == "yfinance" else tiingo.historie(z.symbol)
            b = begrenze(b)
            e = abnahme(roh, b)
            e["split_abgleich"] = "entfällt (Tiingo-Reihe)"
            if z.quelle == "yfinance":                    # Befund 10: zweites Kriterium „Splitspalte“
                sa = splitabgleich(roh["split"], b["split"] if "split" in b.columns else pd.Series(0.0, index=b.index),
                                   liste_der_reihe(ciks.get((z.quelle, z.symbol), set()), ereignisse))
                e["split_abgleich"] = ("bestanden" + (f"; Hinweis: {sa['hinweis']}" if sa["hinweis"] else "")
                                       if sa["bestanden"] else sa["grund"])
                if not sa["bestanden"]:
                    e["grund"] = "; ".join(x for x in (e["grund"], f"Splitspalte: {sa['grund']}") if x)
                    e["bestanden"] = False
        except Exception as f:  # noqa: BLE001
            e = {"tage": 0, "H": float("nan"), "anteil_ok": 0.0, "max_abw": float("nan"), "bestanden": False,
                 "grund": f"{type(f).__name__}: {str(f)[:80]}", "split_abgleich": "nicht geprüft"}
        name_tiingo = roh["name"].iloc[0] if "name" in roh.columns and len(roh) else None
        zeilen.append({"quelle": z.quelle, "symbol": z.symbol, "ticker": z.ticker, **e, "name_tiingo": name_tiingo,
                       "name_universum": z.name_meta if isinstance(z.name_meta, str) else z.name,
                       "name_passt": name_passt(name_tiingo, z.name_meta if isinstance(z.name_meta, str) else z.name)})
        schwelle.zaehle(None if e["bestanden"] else f"{z.symbol}: {e['grund']}")
    t = pd.DataFrame(zeilen)
    datei = abnahme_datei()
    t[SPALTEN_ABNAHME + ["split_abgleich", "name_universum", "name_passt"]].to_csv(datei, index=False)
    fehlend = fehlende_fuer_c3(status, t, dauerhaft_nicht_verfuegbar())

    nicht = t[~t["bestanden"]]
    nur_split = t[~t["bestanden"] & t["grund"].fillna("").str.startswith("Splitspalte:")]   # erstes Kriterium bestanden
    namen = t[~t["name_passt"]]
    text = ["# Abnahme der Rohreihen für den Marktwert (c2 (2))", "",
            f"Erstellt {datetime.now():%d.%m.%Y %H:%M} mit `tools/pruefe_rohkurse.py`. Kriterien vor dem Lauf festgehalten (docs/FUNDAMENTAL.md, "
            "„c2 (2): Marktwert aus Rohkursen – Abnahme und Stichprobe“): Vergleich nur gegen splitbereinigte Reihen, ≥ 250 Tage, "
            "|v/(H·Πf) − 1| ≤ 1 % an ≥ 99 % der Tage; Yahoo-Reihen zusätzlich Kriterium „Splitspalte“ (Befund 10, festgehalten "
            "16.11.2026 11:21: Tiingo-Splitfaktoren gegen Yahoo-Ereignisse und Kapitalmaßnahmen-Liste, ±1 Handelstag, ±1 %; "
            "geändert nach dem ersten Lauf, festgehalten 12:45: Tiingo-Faktor genau am Datum einer Abspaltung der Liste gilt "
            "als bestanden). Nichts wurde angepasst.", "",
            f"Gültige Reihen: {len(gueltig)}. Mit Rohreihe: {len(t)}, davon bestanden {int(t['bestanden'].sum())}, nicht bestanden {len(nicht)}. "
            f"Ohne Rohreihe: {len(ohne_roh)}. Für c3 noch offen (ohne Abnahme, nicht dauerhaft unverfügbar): {len(fehlend)}.", "",
            f"Davon nur am Kriterium „Splitspalte“ gescheitert: {len(nur_split)}. "
            f"Fehlerschwelle (Befund 14, sperrt c3): {schwelle_der_abnahme(t) or 'nicht überschritten'}.", "",
            ] + abschnitt_nicht_bestanden(nicht)
    mit_hinweis = t[t["split_abgleich"].fillna("").str.contains("Hinweis:")]
    text += ["", f"## Bestanden mit Tiingo-Faktor an einer Abspaltung der Liste (über K behandelt) ({len(mit_hinweis)})", "",
             "| Symbol (Quelle) | Hinweis |", "| --- | --- |"]
    text += [f"| {r.symbol} ({r.quelle}) | {r.split_abgleich.split('Hinweis: ', 1)[1]} |" for r in mit_hinweis.itertuples()]
    text += [""] + abschnitt_verdeckt(t)
    text += ["", f"## Name bei Tiingo passt nicht zum Universum ({len(namen)}, nur Meldung)", "",
             "| Symbol | Tiingo | Universum | Abnahme |", "| --- | --- | --- | --- |"]
    text += [f"| {r.symbol} | {r.name_tiingo} | {r.name_universum} | {'bestanden' if r.bestanden else 'nicht bestanden'} |" for r in namen.itertuples()]
    text += ["", f"## Für c3 noch offen ({len(fehlend)})", "", ", ".join(fehlend) or "keine"]
    bericht = PROJEKT_WURZEL / "docs" / "berichte" / f"{datetime.now():%Y-%m-%d}_rohkurse_abnahme.md"
    if bericht.exists():                              # früheren Lauf desselben Tages nie überschreiben
        bericht = bericht.with_name(f"{datetime.now():%Y-%m-%d_%H%M}_rohkurse_abnahme.md")
    bericht.write_text("\n".join(text) + "\n", encoding="utf-8")
    print("\n".join(text[:8]))
    try:
        schwelle.pruefe()
    except FehlerschwelleUeberschritten as f:
        laut_melden(f)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
