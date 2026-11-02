"""Fundamental-Rangliste zu einem einzelnen Stichtag für den Betrieb (Paper Trading, Bücher Fundamental A und B).

Gleiche Rechnung wie im Backtest (tools/auswertung_scores.py und tools/backtest_fundamental.py): Mitglieder am
Stichtag, keine Finanzwerte (SIC point-in-time), gültige Kursreihe, aktueller Jahresabschluss; Scores, Filter
(filter.anwenden), Gesamtscore. Variante A: Originalgewichte (Qualität 50 %, Bewertung 50 %); Variante B: nur
Qualitätshälfte (Entscheidung Jakob 02.11.2026, docs/FUNDAMENTAL.md). Läuft im Betrieb nur im Betriebsmodus (Daten ab
2025); Kurse der Mitglieder werden vorher bis zur letzten abgeschlossenen NYSE-Sitzung aktualisiert.
"""
from __future__ import annotations

import copy
import warnings
from datetime import date, timedelta

import pandas as pd

from tradingbot.daten.cache import standard_cache
from tradingbot.daten.fehlerschwelle import Fehlerschwelle
from tradingbot.daten.index_nachbau import aktien_splitbereinigt
from tradingbot.daten.kurse import lade_kurse
from tradingbot.daten.sec import cik10, kennzahl_jahreswerte
from tradingbot.daten.sp500_nachbau import ciks_der_zeile, firmen_schluessel, lade_firmendaten
from tradingbot.daten.universum import lade_sic_historien, lade_universum, mitglieder_am, sic_am
from tradingbot.engines.fundamental.filter import anwenden as filter_anwenden
from tradingbot.engines.fundamental.filter import piotroski_fuer_filter
from tradingbot.engines.fundamental.gesamtscore import gesamtscore
from tradingbot.engines.fundamental.kennzahlen import abschluesse_am, jahreswerte_firma, zusammenlegen
from tradingbot.engines.fundamental.multiples import marktwert_am, multiples
from tradingbot.engines.fundamental.scores import _w, accruals_quote, altman, beneish, piotroski
from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration

VARIANTEN = {"A": {"qualitaet": 0.5, "bewertung": 0.5}, "B": {"qualitaet": 1.0, "bewertung": 0.0}}


def konfig_variante(konfig: dict, variante: str) -> dict:
    k = copy.deepcopy(konfig)
    k["score"]["gewichte"] = dict(VARIANTEN[variante])
    return k


def kurse_aktualisieren(symbole: list[str], bis: date) -> list[str]:
    """Lädt die Kurse der Symbole bis `bis` in den Cache (inkrementell). Gibt Symbole mit Fehler zurück."""
    fehler = []
    for s in symbole:
        try:
            lade_kurse(s, "2011-01-01", bis, heute=bis + timedelta(days=1))
        except Exception as f:  # noqa: BLE001 – Fehler werden gemeldet, nicht verschluckt
            fehler.append(f"{s}: {type(f).__name__}")
    return fehler


def bewertung_am(tag, *, aktualisieren: bool = True) -> tuple[pd.DataFrame, dict, list[str]]:
    """Bewertungstabelle aller investierbaren Firmen am Stichtag (eine Zeile je Firma) und Yahoo-Symbol je Firma."""
    warnings.simplefilter("ignore")
    tag = pd.Timestamp(tag)
    konfig = lade_konfiguration("fundamental")
    kennzahlen, filt = konfig["kennzahlen"], konfig["filter"]
    aktualitaet = konfig["kennzahlen_regeln"]["aktualitaet_monate"]
    industrie_von, industrie_bis = filt["altman"]["industrie_sic"]
    universum, _ = lade_universum()
    status = pd.read_csv(PROJEKT_WURZEL / "daten" / "universum" / "kursstatus.csv").set_index("index")
    aktiv = mitglieder_am(universum, tag)
    meldungen = []
    if aktualisieren:
        symbole = sorted({status.loc[nr, "symbol"] for nr in aktiv.index if nr in status.index and bool(status.loc[nr, "gueltig"])
                          and status.loc[nr, "quelle"] == "yfinance"})
        meldungen += [f"Kurs nicht aktualisiert: {m}" for m in kurse_aktualisieren(symbole, tag.date())]
    daten = lade_firmendaten(universum, status, lade_sic_historien(universum), mitglied_ab=tag, bis=tag)
    cache = standard_cache()
    mitglieder = mitglieder_am(daten.relevant, tag)
    symbol_je_firma = {}
    for nr, z in mitglieder.iterrows():
        f = firmen_schluessel(z, nr)
        if nr in status.index and bool(status.loc[nr, "gueltig"]):
            symbol_je_firma.setdefault(f, status.loc[nr, "symbol"])
    zeilen = []
    schwelle = Fehlerschwelle("Betrieb: Fundamental-Bewertung je Firma")
    for firma in sorted({firmen_schluessel(z, nr) for nr, z in mitglieder.iterrows()}):
        if isinstance(firma, str) or daten.kurse.get(firma) is None:
            continue
        sic = sic_am(daten.sic.get(firma, []), tag)
        if sic is None or 6000 <= sic <= 6999:
            continue
        fehler = None
        try:
            zeile = daten.relevant[daten.relevant["cik"] == firma].iloc[0]
            erst = zusammenlegen([cache.lesen("sec_erstmeldungen", cik10(c))[0] for c in ciks_der_zeile(zeile)])
            werte = jahreswerte_firma(erst, kennzahlen)
            kurse = daten.kurse[firma]
            a = kennzahl_jahreswerte(erst, kennzahlen["aktien_ausstehend"], "2100-01-01") if len(erst) else pd.DataFrame()
            aktien = (pd.Series(aktien_splitbereinigt(a["wert"], kurse["split"]).to_numpy(), index=(a["filed"] + pd.Timedelta(days=1)).to_numpy()).sort_index()
                      if len(a) else pd.Series(dtype=float))
            t, info = abschluesse_am(werte, tag, aktualitaet_monate=aktualitaet)
            if t.empty or info["veraltet"]:
                schwelle.zaehle(None)
                continue
            mw, _ = marktwert_am(tag, kurse["close"], aktien, daten.streubesitz_gueltig.get(firma))
            industrie = industrie_von <= sic <= industrie_bis
            p, alt, ben, acc, m = piotroski(t), altman(t, industrie=industrie, marktwert_ek=mw), beneish(t), accruals_quote(t), multiples(t, mw)
            cfo = _w(t, "operativer_cashflow", 0)
            e = filter_anwenden(sic=sic, piotroski=p, altman=alt, beneish=ben, cfo_t=cfo, konfig=konfig)
            zeilen.append({"firma": firma, "symbol": symbol_je_firma.get(firma), "sic": sic, "schluss_usd": float(kurse["close"].iloc[-1]),
                           "kursdatum": kurse.index[-1], "piotroski_filter": piotroski_fuer_filter(p), "accruals": acc["wert"], "ep": m["ep"],
                           "ebit_ev": m["ebit_ev"], "ausgeschlossen": e.ausgeschlossen, "gruende": list(e.gruende), "hinweise": list(e.hinweise),
                           "piotroski_hoch": p["hochgerechnet"]})
        except Exception as f:  # zählt gegen die Fehlerschwelle
            fehler = f"{firma}: {type(f).__name__} {str(f)[:60]}"
        schwelle.zaehle(fehler)
    schwelle.pruefe()
    return pd.DataFrame(zeilen), symbol_je_firma, meldungen


def rangliste(bewertung: pd.DataFrame, variante: str) -> pd.DataFrame:
    """Gesamtscore-Rangliste des gefilterten Universums für Variante A oder B (bester zuerst), Spalte `ticker` = Yahoo-Symbol."""
    k = konfig_variante(lade_konfiguration("fundamental"), variante)
    g = bewertung[~bewertung["ausgeschlossen"] & bewertung["symbol"].notna()].copy()
    g["piotroski_filter"] = g["piotroski_filter"].astype(float)
    r = gesamtscore(g, k)
    r["ticker"] = r["symbol"]
    return r
