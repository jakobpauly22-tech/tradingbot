"""Kurse in Euro und Delistings für Backtests und Diagnosen der Fundamental-Engine.

Kurse: geprüfte Kursreihen des Universums (daten/sp500_nachbau.lade_firmendaten), USD → EUR mit EURUSD=X
(daten/kurse.in_euro). Delisting: Kursreihe endet vor dem letzten US-Handelstag des Datenbestands; Grund aus den
SEC-Einreichungen (daten/delisting.py), Rendite nach der Rückfall-Regel (Übernahme 0 %, sonst −30 %).
"""
from __future__ import annotations

import pandas as pd

from tradingbot.backtest.marktdaten import Delisting
from tradingbot.daten.delisting import delisting_grund_mit_korrektur, delisting_rendite, einreichungen
from tradingbot.daten.fehlerschwelle import Fehlerschwelle
from tradingbot.daten.index_nachbau import ABNAHME_ZEITRAUM
from tradingbot.daten.kurse import in_euro, lade_kurse
from tradingbot.daten.sec import SecClient
from tradingbot.daten.sp500_nachbau import lade_firmendaten
from tradingbot.daten.universum import lade_sic_historien, lade_universum
from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration


def lade_kurse_und_delistings(firmen, start, ende, konfig: dict) -> tuple[dict, dict, pd.Series, dict]:
    """Gibt (Kurse in EUR je „CIK<nr>“, Delistings je „CIK<nr>“, EURUSD-Kurs, Ticker-Namen je CIK) zurück."""
    start, ende = pd.Timestamp(start), pd.Timestamp(ende)
    universum, _ = lade_universum()
    status = pd.read_csv(PROJEKT_WURZEL / "daten" / "universum" / "kursstatus.csv").set_index("index")
    daten = lade_firmendaten(universum, status, lade_sic_historien(universum), mitglied_ab=ABNAHME_ZEITRAUM[0])
    namen = {int(z["cik"]): z["ticker"] for _, z in daten.relevant.sort_values("von", na_position="first").iterrows() if pd.notna(z["cik"])}
    von = start - pd.Timedelta(days=120)
    fx = lade_kurse(lade_konfiguration("daten")["kurse"]["wechselkurse"].get("USD", "EURUSD=X"), von - pd.Timedelta(days=10), ende)["close"]
    kurse, letzter_tag = {}, {}
    for firma in firmen:
        k = daten.kurse.get(firma)
        if k is None or k.empty:
            continue
        letzter_tag[firma] = k.index.max()
        k = k.loc[von:ende]
        if not k.empty:
            kurse[f"CIK{firma}"] = in_euro(k, "USD", fx)
    us_ende = max(letzter_tag.values())
    client, korrekturen = SecClient(), lade_konfiguration("universum_korrekturen").get("delisting", [])
    delistings, schwelle = {}, Fehlerschwelle("Delisting-Gründe")
    for firma, letzter in letzter_tag.items():
        if letzter >= us_ende or letzter < start:
            continue
        zeile = daten.relevant[daten.relevant["cik"] == firma].sort_values("von", na_position="first").iloc[-1]
        grund, fehler = "unbekannt", None
        try:
            subs, _ = client.submissions(int(firma))
            grund = delisting_grund_mit_korrektur(zeile["ticker"], einreichungen(subs), letzter, zeile.get("grund_abgang"), korrekturen,
                                                 cik=int(firma))[0]
        except Exception as f:  # Grund bleibt „unbekannt“ (−30 %), zählt gegen die Schwelle
            fehler = f"{zeile['ticker']}: {type(f).__name__}"
        schwelle.zaehle(fehler)
        delistings[f"CIK{firma}"] = Delisting(pd.Timestamp(letzter), delisting_rendite(grund, konfig), grund)
    if delistings:
        schwelle.pruefe()
    return kurse, delistings, fx, namen
