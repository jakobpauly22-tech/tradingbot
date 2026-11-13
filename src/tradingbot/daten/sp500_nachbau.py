"""Nachbau des S&P 500 aus dem point-in-time-Universum, mit oder ohne Finanzwerte.

Gemeinsamer Code für die Gegenprobe (tools/gegenprobe_index.py, ohne Ausschluss) und den Benchmark
„S&P 500 ohne Finanzwerte“ (tools/nachbau_sp500_ohne_finanzwerte.py). Regeln siehe docs/DATENQUALITAET.md:
- je Firma (CIK) eine Spalte; Gattungen und Ticker-Wechsel derselben Firma werden zusammengelegt
- Kurse ab Vorlauf 2011 (Messtag des Streubesitzes liegt meist im Vorjahr), Kalender nur echte Handelstage
- Gewicht: Streubesitz laut SEC-Deckblatt, gegen den Börsenwert geprüft, fortgeschrieben mit dem Kurs
- Finanzwerte: SIC 6000–6999 point-in-time (Code der jeweiligen 10-K, Vorgänger-CIKs eingeschlossen)
- nur Kurse aus dem Cache; Daten enden am 31.12.2024 (Tresor bleibt zu)
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from tradingbot.backtest.tresor import begrenze

from tradingbot.daten.abdeckung import STREUBESITZ
from tradingbot.daten.cache import standard_cache
from tradingbot.daten.fehlerschwelle import Fehlerschwelle
from tradingbot.daten.index_nachbau import (ABNAHME_ZEITRAUM, aktien_splitbereinigt, handelstage, marktwert_index,
                                            marktwerte_aus_streubesitz, streubesitz_pruefen)
from tradingbot.daten.sec import cik10, kennzahl_jahreswerte
from tradingbot.kennzahlen.rendite import simple_return

VORLAUF = pd.Timestamp("2011-01-03")
START = pd.Timestamp("2016-01-04")
ENDE = pd.Timestamp(ABNAHME_ZEITRAUM[1])
FINANZ_SIC = (6000, 6999)


def firmen_schluessel(zeile, nr):
    return int(zeile["cik"]) if pd.notna(zeile["cik"]) else f"ohne CIK {nr}"


def ciks_der_zeile(zeile) -> list[int]:
    vorgaenger = zeile["vorgaenger_ciks"]
    return ([int(zeile["cik"])] if pd.notna(zeile["cik"]) else []) + [int(c) for c in list(vorgaenger if vorgaenger is not None else [])]


@dataclass
class Firmendaten:
    kurse: dict                         # Firma → DataFrame (ab Vorlauf) oder None (keine gültige Reihe)
    streubesitz_roh: dict               # Firma → DataFrame (wert, filed; Index = Messtag), ungeprüft
    streubesitz_gueltig: dict           # Firma → geprüfte Werte (nur Firmen mit gültigen Kursen)
    verworfen: pd.DataFrame             # verworfene Streubesitzwerte mit Grund
    relevant: pd.DataFrame              # Mitgliedschaften im Zeitraum
    sic: dict = field(default_factory=dict)


def kursreihen_ende() -> dict:
    """Gekappte Kursreihen je CIK (config/universum_korrekturen.yaml, `kursreihe_ende`): letzter gültiger Tag."""
    from tradingbot.konfiguration import lade_konfiguration

    return {int(e["cik"]): pd.Timestamp(str(e["letzter_tag"])) for e in lade_konfiguration("universum_korrekturen").get("kursreihe_ende", []) or []}


def lade_firmendaten(universum: pd.DataFrame, status: pd.DataFrame, sic_historien: dict, *, von=VORLAUF, bis=ENDE,
                     mitglied_ab=START, tiingo=None) -> Firmendaten:
    """Kurse, Streubesitz (roh und geprüft) und SIC-Historie je Firma; Fehlerschwelle 5 % beim Laden der Kurse."""
    from tradingbot.daten.tiingo import TiingoClient
    from tradingbot.konfiguration import lade_konfiguration

    aktien_def = lade_konfiguration("fundamental")["kennzahlen"]["aktien_ausstehend"]
    mitglied_ab, bis = pd.Timestamp(mitglied_ab), pd.Timestamp(bis)
    relevant = universum[(universum["bis"].isna() | (universum["bis"] > mitglied_ab)) & (universum["von"].isna() | (universum["von"] <= bis))]
    cache, tiingo = standard_cache(), tiingo or TiingoClient()
    kappung = kursreihen_ende()
    schwelle = Fehlerschwelle("Nachbau: Kurse aus dem Cache")
    kurse: dict = {}
    for nr, z in relevant.iterrows():
        firma = firmen_schluessel(z, nr)
        s = status.loc[nr] if nr in status.index else None
        if s is None or not bool(s["gueltig"]):
            kurse.setdefault(firma, None)
            continue
        fehler = None
        try:
            k = cache.lesen("kurse", s["symbol"])[0] if s["quelle"] == "yfinance" else tiingo.historie(s["symbol"])
            k = begrenze(k)                                   # Tresor: Cache-Kurse nur bis zur Datumsgrenze
            if k is None or k.empty:
                raise LookupError("Kurse nicht im Cache")
            k = k.sort_index().loc[pd.Timestamp(von):bis]
            if firma in kappung:                               # dritte Datenkorrektur: Reihe gehört danach einer anderen Firma
                k = k.loc[:kappung[firma]]
            kurse[firma] = k if kurse.get(firma) is None else kurse[firma].combine_first(k)
        except Exception as f:  # zählt gegen die Fehlerschwelle
            fehler = f"{z['ticker']}: {type(f).__name__}"
        schwelle.zaehle(fehler)
    schwelle.pruefe()

    roh, gueltig, verworfen, sic = {}, {}, [], {}
    for firma in kurse:
        if isinstance(firma, str):
            continue
        zeile = relevant[relevant["cik"] == firma].iloc[0]
        reihen, aktien = [], []
        for cik in ciks_der_zeile(zeile):
            sic.setdefault(firma, []).extend(sic_historien.get(cik, []))
            erst, _ = cache.lesen("sec_erstmeldungen", cik10(cik))
            if erst is None:
                continue
            reihen.append(kennzahl_jahreswerte(erst, STREUBESITZ, "2100-01-01"))
            if kurse[firma] is not None:
                a = kennzahl_jahreswerte(erst, aktien_def, "2100-01-01")
                if len(a):
                    aktien.append(aktien_splitbereinigt(a["wert"], kurse[firma]["split"]))
        sic[firma] = sorted(sic.get(firma, []))
        if not reihen:
            continue
        reihe = pd.concat(reihen).sort_index()
        roh[firma] = reihe[~reihe.index.duplicated(keep="first")]
        if kurse[firma] is not None:
            g, v = streubesitz_pruefen(roh[firma], kurse[firma]["close"], pd.concat(aktien) if aktien else pd.Series(dtype=float))
            gueltig[firma] = g
            verworfen += [{"cik": firma, "ende": e.date(), "wert_mrd": r.wert / 1e9, "grund": r.grund} for e, r in v.iterrows()]
    return Firmendaten(kurse, roh, gueltig, pd.DataFrame(verworfen, columns=["cik", "ende", "wert_mrd", "grund"]), relevant, sic)


def finanzwert_maske(sic: dict, tage: pd.DatetimeIndex, firmen: list) -> pd.DataFrame:
    """True, wenn die Firma am Tag nach SIC point-in-time ein Finanzwert ist (vor dem ersten 10-K: erster Code)."""
    maske = pd.DataFrame(False, index=tage, columns=firmen)
    for f in firmen:
        historie = sic.get(f, [])
        if not historie:
            continue
        daten = np.array([d for d, _ in historie], dtype="datetime64[ns]")
        codes = np.array([c for _, c in historie])
        stelle = np.searchsorted(daten, tage.to_numpy(), side="right") - 1
        code = codes[np.clip(stelle, 0, None)]
        maske[f] = (code >= FINANZ_SIC[0]) & (code <= FINANZ_SIC[1])
    return maske


def baue_nachbau(daten: Firmendaten, *, ohne_finanzwerte: bool = False, von=START, bis=ENDE, marktwert_korrektur: bool = False) -> dict:
    """Kettenindex (USD) nach index_nachbau.marktwert_index; Ergebnis: nachbau (index, abdeckung), tage, mitglied.
    `marktwert_korrektur`: Fortschreibung des Streubesitzes ohne Abspaltungen (Datenkorrektur Marktwert, Jakob 13.11.2026)."""
    firmen = sorted(daten.kurse, key=str)
    schluss_voll = pd.DataFrame({f: (daten.kurse[f]["close"] if daten.kurse[f] is not None else pd.Series(dtype=float)) for f in firmen})
    tage = handelstage(schluss_voll, von, bis)
    renditen = pd.DataFrame({f: (simple_return(daten.kurse[f]["close"].shift(1), daten.kurse[f]["close"], daten.kurse[f]["dividende"])
                                 if daten.kurse[f] is not None else pd.Series(dtype=float)) for f in firmen}).reindex(tage)
    mitglied = pd.DataFrame(False, index=tage, columns=firmen)
    for nr, z in daten.relevant.iterrows():
        firma = firmen_schluessel(z, nr)
        anfang = z["von"] if pd.notna(z["von"]) else pd.Timestamp(von)
        schluss_tag = z["bis"] if pd.notna(z["bis"]) else pd.Timestamp(bis) + pd.Timedelta(days=1)
        mitglied[firma] |= (tage >= anfang) & (tage < schluss_tag)
    if ohne_finanzwerte:
        mitglied &= ~finanzwert_maske(daten.sic, tage, firmen)
    korrektur_je_firma = None
    if marktwert_korrektur:
        from tradingbot.daten.kapitalmassnahmen_historie import lade_ereignisse

        ereignisse = lade_ereignisse()
        korrektur_je_firma = {f: (daten.kurse[f]["split"], ereignisse.get(f)) for f in firmen
                              if daten.kurse[f] is not None and "split" in daten.kurse[f].columns and not isinstance(f, str)}
    marktwerte = marktwerte_aus_streubesitz(schluss_voll, daten.streubesitz_gueltig, korrektur_je_firma).reindex(tage)
    nachbau = marktwert_index(renditen.where(mitglied), marktwerte, mitglied)
    return {"nachbau": nachbau, "tage": tage, "mitglied": mitglied}


BENCHMARK_SCHLUESSEL = "SP500_ohne_finanzwerte"


def lade_benchmark_sp500_ohne_finanzwerte() -> pd.DataFrame:
    """Benchmark „S&P 500 ohne Finanzwerte“ aus dem Cache (Spalten index_usd, index_eur, abdeckung); gebaut von
    tools/nachbau_sp500_ohne_finanzwerte.py, erst nachdem die Gegenprobe bestanden ist (docs/DATENQUALITAET.md)."""
    tabelle, meta = standard_cache().lesen("benchmarks", BENCHMARK_SCHLUESSEL)
    if tabelle is None:
        raise LookupError("Benchmark fehlt im Cache: .venv/Scripts/python tools/nachbau_sp500_ohne_finanzwerte.py ausführen")
    tabelle.attrs.update(meta)
    return tabelle
