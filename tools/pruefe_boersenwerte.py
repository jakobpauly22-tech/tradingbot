r"""Börsenwert-Prüfung aller gültigen Kursreihen (Rückmeldung Jakob 02.11.2026).

Aufruf:  .venv\Scripts\python tools\pruefe_boersenwerte.py
Ergebnis: daten/universum/boersenwert_pruefung.csv und .md

Je gültiger Reihe: Börsenwert je Handelstag = Schlusskurs × ausstehende Aktien laut SEC-Deckblatt
(dei:EntityCommonStockSharesOutstanding, gültig ab dem Tag nach der Einreichung, splitbereinigt auf die Basis der
Kurse). Der Median über den relevanten Mitgliedszeitraum (ab 2012) muss zwischen 0,5 Mrd. und 10 Bio. USD liegen
(kursquellen.plausibel); sonst ist es vermutlich die falsche Aktie oder eine falsche Aktienzahl. Nur Prüfung, nichts
wird geändert. Fehlerschwelle 5 % (fehlende Kurse oder SEC-Daten im Cache).
"""
import sys
import warnings

import pandas as pd

from tradingbot.backtest.tresor import begrenze

from tradingbot.daten.cache import standard_cache
from tradingbot.daten.fehlerschwelle import Fehlerschwelle, FehlerschwelleUeberschritten, laut_melden
from tradingbot.daten.index_nachbau import aktien_splitbereinigt
from tradingbot.daten.kursquellen import plausibel
from tradingbot.daten.sec import cik10, kennzahl_jahreswerte
from tradingbot.daten.tiingo import TiingoClient
from tradingbot.daten.universum import lade_universum
from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration

warnings.simplefilter("ignore")
AKTIEN = lade_konfiguration("fundamental")["kennzahlen"]["aktien_ausstehend"]


def kurse_aus_cache(quelle: str, symbol: str, cache, tiingo) -> pd.DataFrame | None:
    """Kurse nur aus dem Cache (kein Netzabruf)."""
    if quelle == "yfinance":
        k, _ = cache.lesen("kurse", symbol)
        k = begrenze(k)                     # Tresor: nur bis zur Datumsgrenze
        return k
    return tiingo.historie(symbol)


def aktien_reihe(ciks: list[int], cache, splits: pd.Series) -> pd.Series:
    """Ausstehende Aktien je Gültigkeitstag (Tag nach filed), splitbereinigt; mehrere CIKs (Vorgänger) zusammengelegt."""
    teile = []
    for cik in ciks:
        erst, _ = cache.lesen("sec_erstmeldungen", cik10(cik))
        if erst is None:
            continue
        w = kennzahl_jahreswerte(erst, AKTIEN, "2100-01-01")
        if len(w):
            bereinigt = aktien_splitbereinigt(w["wert"], splits)            # Index: Stichtag des Deckblatts
            teile.append(pd.Series(bereinigt.to_numpy(), index=(w["filed"] + pd.Timedelta(days=1)).to_numpy()))
    if not teile:
        return pd.Series(dtype=float)
    r = pd.concat(teile).sort_index()
    return r[~r.index.duplicated(keep="last")]


def main() -> int:
    universum, _ = lade_universum()
    status = pd.read_csv(PROJEKT_WURZEL / "daten" / "universum" / "kursstatus.csv")
    gueltig = status[status["gueltig"].astype(bool)]
    cache, tiingo = standard_cache(), TiingoClient()
    schwelle = Fehlerschwelle("Börsenwert-Prüfung")
    zeilen = []
    for _, s in gueltig.iterrows():
        z = universum.loc[int(s["index"])]
        ciks = ([int(z["cik"])] if pd.notna(z["cik"]) else []) + [int(c) for c in list(z["vorgaenger_ciks"] if z["vorgaenger_ciks"] is not None else [])]
        fehler = None
        try:
            k = kurse_aus_cache(s["quelle"], s["symbol"], cache, tiingo)
            if k is None or k.empty:
                raise LookupError("Kurse nicht im Cache")
            aktien = aktien_reihe(ciks, cache, k["split"])
            p = plausibel(k, aktien, z["von"], z["bis"])
            zeilen.append({"index": int(s["index"]), "ticker": z["ticker"], "name": z["name"], "quelle": s["quelle"], "symbol": s["symbol"],
                           "boersenwert_median_mrd": None if p["boersenwert_median"] is None else p["boersenwert_median"] / 1e9,
                           "ok": p["ok"], "grund": p["grund"]})
        except Exception as f:  # zählt gegen die Fehlerschwelle
            fehler = f"{z['ticker']}: {type(f).__name__} {str(f)[:60]}"
            zeilen.append({"index": int(s["index"]), "ticker": z["ticker"], "name": z["name"], "quelle": s["quelle"], "symbol": s["symbol"],
                           "boersenwert_median_mrd": None, "ok": False, "grund": "Fehler: " + fehler})
        schwelle.zaehle(fehler)
    schwelle.pruefe()

    t = pd.DataFrame(zeilen)
    ziel = PROJEKT_WURZEL / "daten" / "universum"
    t.to_csv(ziel / "boersenwert_pruefung.csv", index=False)
    ohne_aktien = t["grund"].eq("keine Aktienzahl zur Prüfung")
    auffaellig = t[~t["ok"]]
    text = ["# Börsenwert-Prüfung der gültigen Kursreihen", "",
            f"Geprüft: {len(t)} gültige Reihen. Plausibel: {int(t['ok'].sum())} (davon ohne Aktienzahl, also ungeprüft: {int(ohne_aktien.sum())}). "
            f"Auffällig: {len(auffaellig)}.", "",
            f"Median Börsenwert über alle: {t['boersenwert_median_mrd'].median():.1f} Mrd. USD; kleinster {t['boersenwert_median_mrd'].min():.2f}, "
            f"größter {t['boersenwert_median_mrd'].max():.0f} Mrd. USD.", "",
            "| Ticker | Name | Quelle | Symbol | Börsenwert (Median, Mrd. USD) | Grund |", "| --- | --- | --- | --- | --- | --- |"]
    text += [f"| {r.ticker} | {r['name']} | {r.quelle} | {r.symbol} | {'' if pd.isna(r.boersenwert_median_mrd) else f'{r.boersenwert_median_mrd:.2f}'} | {r.grund} |"
             for _, r in auffaellig.iterrows()]
    (ziel / "boersenwert_pruefung.md").write_text("\n".join(text), encoding="utf-8")
    print("\n".join(text))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FehlerschwelleUeberschritten as fehler:
        sys.exit(laut_melden(fehler))
