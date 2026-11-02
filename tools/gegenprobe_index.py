r"""Gegenprobe: Nachbau des S&P 500 (ohne Ausschluss) gegen den offiziellen S&P 500 Total Return (^SP500TR).

Aufruf:  .venv\Scripts\python tools\gegenprobe_index.py
Ergebnis: daten/universum/gegenprobe_index.md und .csv (Indexreihen)

Abnahmekriterien und Zeitraum (01.04.2016–31.12.2024) aus index_nachbau / docs/DATENQUALITAET.md. Wird ein Kriterium
verfehlt: Ursachen suchen und mit Jakob besprechen, nicht nachjustieren. Der Nachbau beginnt Anfang 2016, damit die
Kette am ersten Abnahmetag einen Vortag hat; Daten enden am 31.12.2024 (Tresor bleibt zu).
Je Firma (CIK) eine Spalte: Gattungen und Ticker-Wechsel derselben Firma werden zusammengelegt, Gewicht nach
Streubesitz laut SEC-Deckblatt, fortgeschrieben mit dem Kurs. Nur Kurse aus dem Cache, kein Netz (außer ^SP500TR).
"""
import sys
import warnings

import pandas as pd

from tradingbot.daten.abdeckung import STREUBESITZ
from tradingbot.daten.cache import standard_cache
from tradingbot.daten.fehlerschwelle import Fehlerschwelle, FehlerschwelleUeberschritten, laut_melden
from tradingbot.daten.index_nachbau import ABNAHME_ZEITRAUM, abnahme_gegenprobe, marktwert_index, marktwerte_aus_streubesitz
from tradingbot.daten.kurse import lade_kurse
from tradingbot.daten.sec import cik10, kennzahl_jahreswerte
from tradingbot.daten.tiingo import TiingoClient
from tradingbot.daten.universum import lade_universum
from tradingbot.kennzahlen.rendite import simple_return
from tradingbot.konfiguration import PROJEKT_WURZEL

warnings.simplefilter("ignore")
START, ENDE = pd.Timestamp("2016-01-04"), pd.Timestamp(ABNAHME_ZEITRAUM[1])


def _ciks(z) -> list[int]:
    return ([int(z["cik"])] if pd.notna(z["cik"]) else []) + [int(c) for c in list(z["vorgaenger_ciks"] if z["vorgaenger_ciks"] is not None else [])]


def main() -> int:
    universum, _ = lade_universum()
    relevant = universum[(universum["bis"].isna() | (universum["bis"] > START)) & (universum["von"].isna() | (universum["von"] <= ENDE))]
    status = pd.read_csv(PROJEKT_WURZEL / "daten" / "universum" / "kursstatus.csv").set_index("index")
    cache, tiingo = standard_cache(), TiingoClient()
    tage = pd.bdate_range(START, ENDE)

    schwelle = Fehlerschwelle("Gegenprobe: Kurse aus dem Cache")
    rendite, schluss, mitglied = {}, {}, {}
    for nr, z in relevant.iterrows():
        firma = int(z["cik"]) if pd.notna(z["cik"]) else f"ohne CIK {nr}"
        maske = pd.Series((tage >= (z["von"] if pd.notna(z["von"]) else START)) & (tage < (z["bis"] if pd.notna(z["bis"]) else ENDE + pd.Timedelta(days=1))), index=tage)
        mitglied[firma] = mitglied.get(firma, pd.Series(False, index=tage)) | maske
        s = status.loc[nr] if nr in status.index else None
        if s is None or not bool(s["gueltig"]):
            continue
        fehler = None
        try:
            k = cache.lesen("kurse", s["symbol"])[0] if s["quelle"] == "yfinance" else tiingo.historie(s["symbol"])
            if k is None or k.empty:
                raise LookupError("Kurse nicht im Cache")
            k = k.sort_index()
            r = simple_return(k["close"].shift(1), k["close"], k["dividende"]).reindex(tage)
            c = k["close"].reindex(tage)
            # erste Gattung mit Kurs gewinnt; weitere Gattungen derselben Firma füllen nur Lücken (Ticker-Wechsel)
            rendite[firma] = rendite[firma].combine_first(r.where(maske)) if firma in rendite else r.where(maske)
            schluss[firma] = schluss[firma].combine_first(c) if firma in schluss else c
        except Exception as f:
            fehler = f"{z['ticker']}: {type(f).__name__}"
        schwelle.zaehle(fehler)
    schwelle.pruefe()

    firmen = sorted(mitglied, key=str)
    R = pd.DataFrame({f: rendite.get(f, pd.Series(float("nan"), index=tage)) for f in firmen})
    C = pd.DataFrame({f: schluss.get(f, pd.Series(float("nan"), index=tage)) for f in firmen})
    M = pd.DataFrame(mitglied)[firmen]
    streubesitz = {}
    for f in firmen:
        if isinstance(f, str):
            continue
        teile = []
        for cik in _ciks(relevant[relevant["cik"] == f].iloc[0]):
            erst, _ = cache.lesen("sec_erstmeldungen", cik10(cik))
            if erst is not None:
                teile.append(kennzahl_jahreswerte(erst, STREUBESITZ, "2100-01-01"))
        if teile:
            streubesitz[f] = pd.concat(teile).sort_index()
    MW = marktwerte_aus_streubesitz(C, streubesitz)
    nachbau = marktwert_index(R, MW, M)

    referenz = lade_kurse("^SP500TR", START - pd.Timedelta(days=10), ENDE)["close"]
    ergebnis = abnahme_gegenprobe(nachbau["index"], referenz)

    ziel = PROJEKT_WURZEL / "daten" / "universum"
    pd.concat({"nachbau": nachbau["index"], "abdeckung": nachbau["abdeckung"], "referenz": referenz.reindex(tage)}, axis=1).to_csv(ziel / "gegenprobe_index.csv")
    abn = nachbau["abdeckung"].loc[ABNAHME_ZEITRAUM[0]:]
    k = ergebnis["kriterien"]
    text = ["# Gegenprobe Index-Nachbau gegen S&P 500 Total Return", "",
            f"Zeitraum {ergebnis['zeitraum'][0]} bis {ergebnis['zeitraum'][1]}, {ergebnis['tage']} gemeinsame Handelstage. "
            f"Abdeckung der Mitglieder mit Rendite und Gewicht: Median {abn.median():.1%}, Minimum {abn.min():.1%}.", "",
            "| Kriterium | Wert | Grenze | bestanden |", "| --- | --- | --- | --- |",
            f"| Korrelation der Tagesrenditen | {k['korrelation']['wert']:.4f} | ≥ 0,99 | {'ja' if k['korrelation']['bestanden'] else 'NEIN'} |",
            f"| größte Abweichung einer Jahresrendite | {k['jahresabweichung_max']['wert']*100:.2f} Pp. | ≤ 1 Pp. | {'ja' if k['jahresabweichung_max']['bestanden'] else 'NEIN'} |",
            f"| Abweichung annualisierte Rendite | {k['annualisiert_abweichung']['wert']*100:+.2f} Pp. | ≤ 0,5 Pp. | {'ja' if k['annualisiert_abweichung']['bestanden'] else 'NEIN'} |",
            "", f"**Gesamt: {'bestanden' if ergebnis['bestanden'] else 'NICHT bestanden – Ursachen suchen und mit Jakob besprechen, nicht nachjustieren'}**", "",
            "| Jahr | Nachbau | S&P 500 TR | Abweichung |", "| --- | --- | --- | --- |"]
    text += [f"| {j}{' (ab 01.04.)' if j == 2016 else ''} | {r.nachbau:.2%} | {r.referenz:.2%} | {r.abweichung*100:+.2f} Pp. |" for j, r in ergebnis["jahre"].iterrows()]
    (ziel / "gegenprobe_index.md").write_text("\n".join(text), encoding="utf-8")
    print("\n".join(text))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FehlerschwelleUeberschritten as fehler:
        sys.exit(laut_melden(fehler))
