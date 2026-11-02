r"""Rechenwege der Fundamental-Scores an echten 10-K, zum Nachrechnen von Hand (Wunsch Jakob 03.11.2026).

Aufruf:  .venv\Scripts\python tools\rechenweg_10k.py
Ergebnis: docs/rechenwege/<fall>.md – je Eingangswert XBRL-Begriff, Teil des Abschlusses, Geschäftsjahr und Fundstelle
(10-K mit Accession-Nummer, Einreichungsdatum, Link), dazu Zwischenrechnungen und Ergebnis. Die Zahlen sind öffentliche
Angaben aus den SEC-Einreichungen; die Dokumente enthalten keine Texte aus den Berichten.
"""
import sys
import warnings

import pandas as pd

from tradingbot.backtest.tresor import begrenze

from tradingbot.daten.cache import standard_cache
from tradingbot.daten.sec import cik10, kennzahl_jahreswerte
from tradingbot.engines.fundamental.kennzahlen import abschluesse_am, jahreswerte_firma
from tradingbot.engines.fundamental.multiples import marktwert_am
from tradingbot.engines.fundamental.scores import altman, beneish, piotroski
from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration

warnings.simplefilter("ignore")
K = lade_konfiguration("fundamental")["kennzahlen"]
TEIL = {"umsatz": "GuV", "umsatzkosten": "GuV", "bruttoergebnis": "GuV", "operatives_ergebnis": "GuV", "jahresueberschuss": "GuV",
        "ergebnis_vor_steuern": "GuV", "zinsaufwand": "GuV/Anhang", "vertriebs_verwaltungskosten": "GuV", "gewichtete_aktien": "GuV (EPS)",
        "operativer_cashflow": "Kapitalflussrechnung", "abschreibungen": "Kapitalflussrechnung", "bilanzsumme": "Bilanz",
        "umlaufvermoegen": "Bilanz", "kurzfristige_verbindlichkeiten": "Bilanz", "verbindlichkeiten": "Bilanz",
        "langfristige_finanzschulden": "Bilanz", "eigenkapital_inkl_minderheiten": "Bilanz", "gewinnruecklagen": "Bilanz",
        "forderungen": "Bilanz", "sachanlagen_netto": "Bilanz", "eigenkapital": "Bilanz", "aktien_ausstehend": "Deckblatt"}

FAELLE = [
    {"datei": "apple_gj2019", "titel": "Apple Inc., Geschäftsjahr 2019 (Ende 28.09.2019)", "cik": 320193, "symbol": "AAPL",
     "stichtag": "2019-11-01", "scores": ["piotroski", "beneish", "altman_z"]},
    {"datei": "walmart_gj2020", "titel": "Walmart Inc., Geschäftsjahr 2020 (Ende 31.01.2020)", "cik": 104169, "symbol": "WMT",
     "stichtag": "2020-03-25", "scores": ["altman_z2"]},
]


def fundstelle(erst, kennzahl, ende):
    """10-K, aus dem der Wert stammt (Erstmeldung): Accession, Einreichungsdatum, Begriff."""
    d = K[kennzahl]
    for konzept in d["konzepte"]:
        tax, name = konzept.split(":")
        z = erst[(erst["taxonomie"] == tax) & (erst["konzept"] == name) & (erst["ende"] == ende) & (erst["einheit"] == d["einheit"])]
        if d["art"] == "dauer":
            z = z[z["start"].notna() & ((z["ende"] - z["start"]).dt.days.between(350, 380))]
        if len(z):
            r = z.sort_values("filed").iloc[0]
            return r["accn"], r["filed"].date(), konzept
    return None, None, None


def link(cik, accn):
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{accn.replace('-', '')}/{accn}-index.htm"


def mio(x):
    return "–" if x is None or pd.isna(x) else f"{x/1e6:,.0f}".replace(",", ".")


def main() -> int:
    cache = standard_cache()
    ziel = PROJEKT_WURZEL / "docs" / "rechenwege"
    ziel.mkdir(parents=True, exist_ok=True)
    for fall in FAELLE:
        erst, _ = cache.lesen("sec_erstmeldungen", cik10(fall["cik"]))
        t, info = abschluesse_am(jahreswerte_firma(erst, K), fall["stichtag"])
        jahre = list(t.index)
        abgeleitet = set(info["abgeleitet"])
        z = [f"# Rechenweg: {fall['titel']}", "",
             f"Stichtag {fall['stichtag']} (Tag nach Bekanntwerden des 10-K). Werte in Mio. USD. Quelle: SEC-XBRL-Fakten (Erstmeldung).",
             "Abgeleitete Werte sind mit „abgeleitet“ markiert (Regeln in `engines/fundamental/kennzahlen.py`).", "",
             "## Eingangswerte", "", "| Posten | Teil | " + " | ".join(f"GJ {e.date()}" for e in jahre) + " | Begriff / Fundstelle |",
             "| --- | --- | " + " | ".join("---" for _ in jahre) + " | --- |"]
        for kennzahl in sorted(TEIL):
            if kennzahl not in t.columns or kennzahl == "aktien_ausstehend":
                continue
            werte = " | ".join(mio(t[kennzahl].iloc[i]) + (" (abgeleitet)" if f"{kennzahl}@{jahre[i].date()}" in abgeleitet else "") for i in range(len(jahre)))
            accn, filed, konzept = fundstelle(erst, kennzahl, jahre[0])
            quelle = f"{konzept}; 10-K {accn} vom {filed} ([Index]({link(fall['cik'], accn)}))" if accn else "abgeleitet bzw. siehe Vorjahres-10-K"
            z.append(f"| {kennzahl} | {TEIL[kennzahl]} | {werte} | {quelle} |")
        if "piotroski" in fall["scores"]:
            p = piotroski(t)
            zw = p["zwischenwerte"]
            z += ["", "## Piotroski F-Score", "", "Formeln im Docstring von `scores.piotroski` (Piotroski 2000). Ursprünglich für Value-Aktien, hier allgemeiner Qualitätsfilter.", "",
                  "| Signal | Rechnung | Wert | Punkt |", "| --- | --- | --- | --- |",
                  f"| ROA > 0 | JÜ_t / BS_t−1 = {mio(t['jahresueberschuss'].iloc[0])} / {mio(t['bilanzsumme'].iloc[1])} | {zw['roa']:.4f} | {p['signale']['roa']} |",
                  f"| CFO > 0 | CF_t / BS_t−1 = {mio(t['operativer_cashflow'].iloc[0])} / {mio(t['bilanzsumme'].iloc[1])} | {zw['cfo']:.4f} | {p['signale']['cfo']} |",
                  f"| ΔROA > 0 | ROA_t − ROA_t−1, ROA_t−1 = {mio(t['jahresueberschuss'].iloc[1])} / {mio(t['bilanzsumme'].iloc[2])} = {zw['roa_vj']:.4f} | {zw['roa'] - zw['roa_vj']:+.4f} | {p['signale']['delta_roa']} |",
                  f"| ACCRUAL | CFO > ROA | {zw['cfo']:.4f} vs. {zw['roa']:.4f} | {p['signale']['accrual']} |",
                  f"| ΔLEVER ≤ 0 | LFS/Ø BS: t {zw['lever']:.4f}, t−1 {zw['lever_vj']:.4f} | {zw['lever'] - zw['lever_vj']:+.4f} | {p['signale']['delta_lever']} |",
                  f"| ΔLIQUID > 0 | UV/kfr. Verb.: t {zw['liquid']:.4f}, t−1 {zw['liquid_vj']:.4f} | {zw['liquid'] - zw['liquid_vj']:+.4f} | {p['signale']['delta_liquid']} |",
                  f"| EQ_OFFER | gew. Aktien t ≤ t−1: {mio(t['gewichtete_aktien'].iloc[0])} vs. {mio(t['gewichtete_aktien'].iloc[1])} (Mio. Stück) | – | {p['signale']['eq_offer']} |",
                  f"| ΔMARGIN > 0 | Bruttomarge: t {zw['marge']:.4f}, t−1 {zw['marge_vj']:.4f} | {zw['marge'] - zw['marge_vj']:+.4f} | {p['signale']['delta_margin']} |",
                  f"| ΔTURN > 0 | Umsatz/BS_Vorjahr: t {zw['turn']:.4f}, t−1 {zw['turn_vj']:.4f} | {zw['turn'] - zw['turn_vj']:+.4f} | {p['signale']['delta_turn']} |",
                  "", f"**F-Score = {p['wert']}**"]
        if "beneish" in fall["scores"]:
            b = beneish(t)
            v = b["variablen"]
            z += ["", "## Beneish M-Score (8 Variablen)", "", "Formeln im Docstring von `scores.beneish` (Beneish 1999). Gewichte: −4,84 + 0,920·DSRI + 0,528·GMI + 0,404·AQI + 0,892·SGI + 0,115·DEPI − 0,172·SGAI + 4,679·TATA − 0,327·LVGI.", "",
                  "| Variable | Wert | Gewicht | Beitrag |", "| --- | --- | --- | --- |"]
            from tradingbot.engines.fundamental.scores import BENEISH
            z += [f"| {k.upper()} | {x:.4f} | {BENEISH[k]:+.3f} | {BENEISH[k] * x:+.4f} |" for k, x in v.items()]
            z += ["", f"**M = {b['wert']:.4f}** (Konstante −4,84); Schwelle −1,78 → {'Verdacht' if b['wert'] > -1.78 else 'unauffällig'}"]
        if "altman_z" in fall["scores"] or "altman_z2" in fall["scores"]:
            industrie = "altman_z" in fall["scores"]
            mw, mw_text = None, ""
            if industrie:
                kurse, _ = cache.lesen("kurse", fall["symbol"])
                kurse = begrenze(kurse)                     # Tresor: nur bis zur Datumsgrenze
                a = kennzahl_jahreswerte(erst, K["aktien_ausstehend"], fall["stichtag"])
                from tradingbot.daten.index_nachbau import aktien_splitbereinigt
                aktien = aktien_splitbereinigt(a["wert"], kurse["split"])
                aktien.index = a["filed"].to_numpy() + pd.Timedelta(days=1)
                mw, grund = marktwert_am(fall["stichtag"], kurse["close"], aktien, None)
                kurs = kurse["close"].loc[:fall["stichtag"]].iloc[-1]
                faktor = float(kurse["split"][kurse["split"] > 0].loc[pd.Timestamp(fall["stichtag"]):].prod()) or 1.0
                mw_text = (f"Marktwert EK am Stichtag = Schlusskurs {kurse['close'].loc[:fall['stichtag']].index[-1].date()} × ausstehende Aktien laut Deckblatt "
                           f"({a.index[-1].date()}, 10-K): {kurs * faktor:,.2f} USD × {a['wert'].iloc[-1]:,.0f} = **{mw/1e6:,.0f} Mio. USD** "
                           f"(Kurs unbereinigt; spätere Splits Faktor {faktor:g} herausgerechnet).")
            r = altman(t, industrie=industrie, marktwert_ek=mw)
            namen = ["X1 = (UV − kfr. Verb.)/BS", "X2 = Gewinnrücklagen/BS", "X3 = EBIT/BS", "X4 = " + ("Marktwert EK/Verbindlichkeiten" if industrie else "Buchwert EK/Verbindlichkeiten")] + (["X5 = Umsatz/BS"] if industrie else [])
            from tradingbot.engines.fundamental.scores import ALTMAN_1968, ALTMAN_Z2
            modell = ALTMAN_1968 if industrie else ALTMAN_Z2
            ueberschrift = "Z (1968, verarbeitendes Gewerbe)" if industrie else "Z'' (übrige Firmen)"
            z += ["", f"## Altman {ueberschrift}", "", mw_text, "",
                  "| Bestandteil | Wert | Gewicht | Beitrag |", "| --- | --- | --- | --- |"]
            z += [f"| {n} | {x:.4f} | {g} | {g * x:+.4f} |" for n, x, g in zip(namen, r["x"], modell["gewichte"])]
            z += ["", f"**{r['variante']} = {r['wert']:.4f}** → Zone: {r['zone']} (Gefahr < {modell['gefahr']}, sicher > {modell['sicher']})"]
        (ziel / f"{fall['datei']}.md").write_text("\n".join(z), encoding="utf-8")
        print(f"geschrieben: docs/rechenwege/{fall['datei']}.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
