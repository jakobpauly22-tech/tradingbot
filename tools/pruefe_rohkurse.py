r"""Abnahme der unbereinigten Rohreihen für den Marktwert (c2 (2), Kriterien vor dem Lauf festgehalten in
docs/FUNDAMENTAL.md, „c2 (2): Marktwert aus Rohkursen – Abnahme und Stichprobe“, Jakob 15.11.2026). Nur lesend, ohne Netz.

Aufruf:  .venv\Scripts\python tools\pruefe_rohkurse.py
Ergebnis: daten/cache/tiingo/roh_bis_tresor/abnahme.csv (von lade_firmendaten(rohkurse=True) gelesen) und
docs/berichte/<Datum>_rohkurse_abnahme.md. Wiederholbar: nach dem Nachladen ab 01.12.2026 erneut starten.

Je gültiger Kursreihe des Universums: Rohreihe (Yahoo-Reihen aus dem Nachlader, Tiingo-Reihen aus dem Tiingo-Cache) gegen
die nur splitbereinigte Reihe aus dem Cache (daten/rohkurse_marktwert.abnahme). Nicht bestanden: Rückfall auf die bisherige
Rechnung. Fehlerschwelle 5 % der Reihen mit Rohreihe.
"""
import sys
import warnings
from datetime import datetime

import pandas as pd

from tradingbot.backtest.tresor import begrenze
from tradingbot.daten.cache import standard_cache
from tradingbot.daten.fehlerschwelle import Fehlerschwelle, FehlerschwelleUeberschritten, laut_melden
from tradingbot.daten.rohkurse_marktwert import (SPALTEN_ABNAHME, abnahme, abnahme_datei, dauerhaft_nicht_verfuegbar,
                                                 fehlende_fuer_c3, rohreihe)
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


def main() -> int:
    status = pd.read_csv(PROJEKT_WURZEL / "daten" / "universum" / "kursstatus.csv")
    gueltig = status[status["gueltig"].astype(bool)].drop_duplicates(["quelle", "symbol"])
    cache, tiingo = standard_cache(), TiingoClient(sitzung=OhneNetz())
    zeilen, ohne_roh = [], []
    schwelle = Fehlerschwelle("Rohkurse: Abnahme")
    for z in gueltig.itertuples():
        roh = rohreihe(z.quelle, z.symbol)
        if roh is None:
            ohne_roh.append(f"{z.symbol} ({z.quelle})")
            continue
        try:
            b = cache.lesen("kurse", z.symbol)[0] if z.quelle == "yfinance" else tiingo.historie(z.symbol)
            b = begrenze(b)
            e = abnahme(roh, b)
        except Exception as f:  # noqa: BLE001
            e = {"tage": 0, "H": float("nan"), "anteil_ok": 0.0, "max_abw": float("nan"), "bestanden": False,
                 "grund": f"{type(f).__name__}: {str(f)[:80]}"}
        name_tiingo = roh["name"].iloc[0] if "name" in roh.columns and len(roh) else None
        zeilen.append({"quelle": z.quelle, "symbol": z.symbol, "ticker": z.ticker, **e, "name_tiingo": name_tiingo,
                       "name_universum": z.name_meta if isinstance(z.name_meta, str) else z.name,
                       "name_passt": name_passt(name_tiingo, z.name_meta if isinstance(z.name_meta, str) else z.name)})
        schwelle.zaehle(None if e["bestanden"] else f"{z.symbol}: {e['grund']}")
    t = pd.DataFrame(zeilen)
    datei = abnahme_datei()
    t[SPALTEN_ABNAHME + ["name_universum", "name_passt"]].to_csv(datei, index=False)
    fehlend = fehlende_fuer_c3(status, t, dauerhaft_nicht_verfuegbar())

    nicht = t[~t["bestanden"]]
    verdeckt = t[t["bestanden"] & ((t["H"] - 1).abs() > 0.005)]
    namen = t[~t["name_passt"]]
    text = ["# Abnahme der Rohreihen für den Marktwert (c2 (2))", "",
            f"Erstellt {datetime.now():%d.%m.%Y %H:%M} mit `tools/pruefe_rohkurse.py`. Kriterien vor dem Lauf festgehalten (docs/FUNDAMENTAL.md, "
            "„c2 (2): Marktwert aus Rohkursen – Abnahme und Stichprobe“): Vergleich nur gegen splitbereinigte Reihen, ≥ 250 Tage, "
            "|v/(H·Πf) − 1| ≤ 1 % an ≥ 99 % der Tage. Nichts wurde angepasst.", "",
            f"Gültige Reihen: {len(gueltig)}. Mit Rohreihe: {len(t)}, davon bestanden {int(t['bestanden'].sum())}, nicht bestanden {len(nicht)}. "
            f"Ohne Rohreihe: {len(ohne_roh)}. Für c3 noch offen (ohne Abnahme, nicht dauerhaft unverfügbar): {len(fehlend)}.", "",
            f"## Nicht bestanden ({len(nicht)})", "", "| Symbol (Quelle) | Tage | Anteil ≤ 1 % | größte Abweichung | H | Grund |", "| --- | --- | --- | --- | --- | --- |"]
    text += [f"| {r.symbol} ({r.quelle}) | {r.tage} | {r.anteil_ok:.1%} | {r.max_abw:.1%} | {r.H:.4g} | {r.grund} |" for r in nicht.itertuples()]
    text += ["", f"## Verdeckter Faktor H ≠ 1 (Split nach der Tresorgrenze; Rohkurs nötig) ({len(verdeckt)})", "",
             "| Symbol (Quelle) | H |", "| --- | --- |"] + [f"| {r.symbol} ({r.quelle}) | {r.H:.4f} |" for r in verdeckt.itertuples()]
    text += ["", f"## Name bei Tiingo passt nicht zum Universum ({len(namen)}, nur Meldung)", "",
             "| Symbol | Tiingo | Universum | Abnahme |", "| --- | --- | --- | --- |"]
    text += [f"| {r.symbol} | {r.name_tiingo} | {r.name_universum} | {'bestanden' if r.bestanden else 'nicht bestanden'} |" for r in namen.itertuples()]
    text += ["", f"## Für c3 noch offen ({len(fehlend)})", "", ", ".join(fehlend) or "keine"]
    bericht = PROJEKT_WURZEL / "docs" / "berichte" / f"{datetime.now():%Y-%m-%d}_rohkurse_abnahme.md"
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
