r"""Gegenprobe: Nachbau des S&P 500 (ohne Ausschluss) gegen den offiziellen S&P 500 Total Return (^SP500TR).

Aufruf:  .venv\Scripts\python tools\gegenprobe_index.py
Ergebnis: daten/universum/gegenprobe_index.md und .csv (Indexreihen)

Abnahmekriterien und Zeitraum (01.04.2016–31.12.2024) aus index_nachbau / docs/DATENQUALITAET.md. Wird ein Kriterium
verfehlt: Ursachen suchen und mit Jakob besprechen, nicht nachjustieren. Daten enden am 31.12.2024 (Tresor bleibt zu).
Je Firma (CIK) eine Spalte: Gattungen und Ticker-Wechsel derselben Firma werden zusammengelegt, Gewicht nach
Streubesitz laut SEC-Deckblatt, fortgeschrieben mit dem Kurs. Nur Kurse aus dem Cache, kein Netz (außer ^SP500TR).

Lauf 2 (03.11.2026) behebt die Ursachen von Lauf 1 (daten/universum/gegenprobe_index_lauf1.md), freigegeben von Jakob:
1. Kurse ab dem ersten Messtag des Streubesitzes (Vorlauf ab 2011), nicht erst ab Beginn des Nachbaus.
2. Kalender nur aus echten US-Handelstagen (index_nachbau.handelstage), nicht alle Werktage.
3. Streubesitz gegen den Börsenwert geprüft (index_nachbau.streubesitz_pruefen); Verworfenes gilt als fehlend und wird gezählt.
"""
import sys
import warnings

import pandas as pd

from tradingbot.daten.abdeckung import STREUBESITZ
from tradingbot.daten.cache import standard_cache
from tradingbot.daten.fehlerschwelle import Fehlerschwelle, FehlerschwelleUeberschritten, laut_melden
from tradingbot.daten.index_nachbau import (ABNAHME_ZEITRAUM, abnahme_gegenprobe, aktien_splitbereinigt, handelstage,
                                            marktwert_index, marktwerte_aus_streubesitz, streubesitz_pruefen)
from tradingbot.daten.kurse import lade_kurse
from tradingbot.daten.sec import cik10, kennzahl_jahreswerte
from tradingbot.daten.tiingo import TiingoClient
from tradingbot.daten.universum import lade_universum
from tradingbot.kennzahlen.rendite import simple_return
from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration

warnings.simplefilter("ignore")
LAUF = 2
VORLAUF, START, ENDE = pd.Timestamp("2011-01-03"), pd.Timestamp("2016-01-04"), pd.Timestamp(ABNAHME_ZEITRAUM[1])
AKTIEN = lade_konfiguration("fundamental")["kennzahlen"]["aktien_ausstehend"]


def _ciks(z) -> list[int]:
    return ([int(z["cik"])] if pd.notna(z["cik"]) else []) + [int(c) for c in list(z["vorgaenger_ciks"] if z["vorgaenger_ciks"] is not None else [])]


def main() -> int:
    universum, _ = lade_universum()
    relevant = universum[(universum["bis"].isna() | (universum["bis"] > START)) & (universum["von"].isna() | (universum["von"] <= ENDE))]
    status = pd.read_csv(PROJEKT_WURZEL / "daten" / "universum" / "kursstatus.csv").set_index("index")
    cache, tiingo = standard_cache(), TiingoClient()

    # Kurse je Firma über den ganzen Zeitraum ab Vorlauf (Korrektur 1); erste Gattung gewinnt, weitere füllen Lücken
    schwelle = Fehlerschwelle("Gegenprobe: Kurse aus dem Cache")
    kurse_firma: dict = {}
    for nr, z in relevant.iterrows():
        firma = int(z["cik"]) if pd.notna(z["cik"]) else f"ohne CIK {nr}"
        s = status.loc[nr] if nr in status.index else None
        if s is None or not bool(s["gueltig"]):
            kurse_firma.setdefault(firma, None)
            continue
        fehler = None
        try:
            k = cache.lesen("kurse", s["symbol"])[0] if s["quelle"] == "yfinance" else tiingo.historie(s["symbol"])
            if k is None or k.empty:
                raise LookupError("Kurse nicht im Cache")
            k = k.sort_index().loc[VORLAUF:ENDE]
            kurse_firma[firma] = k if kurse_firma.get(firma) is None else kurse_firma[firma].combine_first(k)
        except Exception as f:
            fehler = f"{z['ticker']}: {type(f).__name__}"
        schwelle.zaehle(fehler)
    schwelle.pruefe()

    firmen = sorted(kurse_firma, key=str)
    C_voll = pd.DataFrame({f: (kurse_firma[f]["close"] if kurse_firma[f] is not None else pd.Series(dtype=float)) for f in firmen})
    tage = handelstage(C_voll, START, ENDE)                                    # Korrektur 2
    R = pd.DataFrame({f: (simple_return(kurse_firma[f]["close"].shift(1), kurse_firma[f]["close"], kurse_firma[f]["dividende"])
                          if kurse_firma[f] is not None else pd.Series(dtype=float)) for f in firmen}).reindex(tage)

    M = pd.DataFrame(False, index=tage, columns=firmen)
    for nr, z in relevant.iterrows():
        firma = int(z["cik"]) if pd.notna(z["cik"]) else f"ohne CIK {nr}"
        von = z["von"] if pd.notna(z["von"]) else START
        bis = z["bis"] if pd.notna(z["bis"]) else ENDE + pd.Timedelta(days=1)
        M[firma] |= (tage >= von) & (tage < bis)
    R = R.where(M)

    # Streubesitz je Firma, gegen den Börsenwert geprüft (Korrektur 3)
    streubesitz, verworfen_alle, geprueft = {}, [], 0
    for f in firmen:
        if isinstance(f, str) or kurse_firma[f] is None:
            continue
        reihen, aktien = [], []
        for cik in _ciks(relevant[relevant["cik"] == f].iloc[0]):
            erst, _ = cache.lesen("sec_erstmeldungen", cik10(cik))
            if erst is None:
                continue
            reihen.append(kennzahl_jahreswerte(erst, STREUBESITZ, "2100-01-01"))
            a = kennzahl_jahreswerte(erst, AKTIEN, "2100-01-01")
            if len(a):
                aktien.append(aktien_splitbereinigt(a["wert"], kurse_firma[f]["split"]))
        if not reihen:
            continue
        reihe = pd.concat(reihen).sort_index()
        reihe = reihe[~reihe.index.duplicated(keep="first")]
        gueltig, verworfen = streubesitz_pruefen(reihe, kurse_firma[f]["close"], pd.concat(aktien).sort_index() if aktien else pd.Series(dtype=float))
        geprueft += len(reihe)
        streubesitz[f] = gueltig
        verworfen_alle += [{"cik": f, "ende": e.date(), "wert_mrd": r.wert / 1e9, "grund": r.grund} for e, r in verworfen.iterrows()]

    MW = marktwerte_aus_streubesitz(C_voll, streubesitz).reindex(tage)
    nachbau = marktwert_index(R, MW, M)
    referenz = lade_kurse("^SP500TR", VORLAUF, ENDE)["close"]
    ergebnis = abnahme_gegenprobe(nachbau["index"], referenz)

    ziel = PROJEKT_WURZEL / "daten" / "universum"
    pd.concat({"nachbau": nachbau["index"], "abdeckung": nachbau["abdeckung"], "referenz": referenz.reindex(tage)}, axis=1).to_csv(ziel / "gegenprobe_index.csv")
    pd.DataFrame(verworfen_alle).to_csv(ziel / "gegenprobe_streubesitz_verworfen.csv", index=False)
    abn = nachbau["abdeckung"].loc[ABNAHME_ZEITRAUM[0]:]
    v = pd.DataFrame(verworfen_alle)
    gruende = v["grund"].str.replace(r"[\d.,]+[-%]?", "x", regex=True).value_counts().to_dict() if len(v) else {}
    k = ergebnis["kriterien"]
    text = [f"# Gegenprobe Index-Nachbau gegen S&P 500 Total Return – Lauf {LAUF}", "",
            "Lauf 1 (03.11.2026) war nicht bestanden: daten/universum/gegenprobe_index_lauf1.md. Ursachen und Korrekturen (von Jakob "
            "freigegeben): Kurse ab dem ersten Messtag, nur echte US-Handelstage, Streubesitz gegen den Börsenwert geprüft.", "",
            f"Zeitraum {ergebnis['zeitraum'][0]} bis {ergebnis['zeitraum'][1]}, {ergebnis['tage']} gemeinsame Handelstage "
            f"(Kalender: {len(tage)} Handelstage ab {tage[0].date()}). Abdeckung der Mitglieder mit Rendite und Gewicht im "
            f"Abnahmezeitraum: Median {abn.median():.1%}, Minimum {abn.min():.1%}.", "",
            f"Streubesitz: {geprueft} Werte geprüft, {len(v)} verworfen ({len(v)/max(geprueft,1):.1%}); Gründe: {gruende}.", "",
            "| Kriterium | Wert | Grenze | bestanden |", "| --- | --- | --- | --- |",
            f"| Korrelation der Tagesrenditen | {k['korrelation']['wert']:.4f} | ≥ 0,99 | {'ja' if k['korrelation']['bestanden'] else 'NEIN'} |",
            f"| größte Abweichung einer Jahresrendite | {k['jahresabweichung_max']['wert']*100:.2f} Pp. | ≤ 1 Pp. | {'ja' if k['jahresabweichung_max']['bestanden'] else 'NEIN'} |",
            f"| Abweichung annualisierte Rendite | {k['annualisiert_abweichung']['wert']*100:+.2f} Pp. | ≤ 0,5 Pp. | {'ja' if k['annualisiert_abweichung']['bestanden'] else 'NEIN'} |",
            "", f"**Gesamt: {'bestanden' if ergebnis['bestanden'] else 'NICHT bestanden – Ursachen suchen und mit Jakob besprechen, nicht weiter reparieren'}**", "",
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
