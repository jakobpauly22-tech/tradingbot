r"""Diagnose der Ausschlussfilter (Variante 2, Entscheidung Jakob 02.11.2026).

Frage: Taugen die Filter (Piotroski, Altman, Beneish) als Veto im Risk-Manager?
Vergleich, quartalsweise, gleich gewichtet, ohne Kosten und vor Steuern, 01.10.2016 bis 31.12.2024:
- ohne Filter: alle bewertbaren Firmen (investierbar, aktueller Jahresabschluss),
- mit Filtern: davon nicht ausgeschlossen,
- nur ausgeschlossene, gesamt und je Filtergrund.
Dazu Zahl der ausgeschlossenen Titel je Stichtag und ihre Wertentwicklung nach dem Ausschluss (1 und 4 Quartale),
jeweils gegenüber dem ungefilterten Universum im selben Zeitraum.

Aufruf:  .venv\Scripts\python tools\diagnose_filter.py
Ergebnis: daten/fundamental/diagnose_filter.md; Zeile in daten/fundamental/varianten.csv.
"""
import subprocess
import sys
import warnings
from datetime import datetime

import numpy as np
import pandas as pd

from tradingbot.daten.cache import standard_cache
from tradingbot.daten.fehlerschwelle import FehlerschwelleUeberschritten, laut_melden
from tradingbot.daten.makro import lade_makro
from tradingbot.engines.fundamental.backtest_daten import lade_kurse_und_delistings
from tradingbot.engines.fundamental.filter import anwenden as filter_anwenden
from tradingbot.engines.fundamental.schatten import haltefaktor, kontrollportfolio, signal_und_ausfuehrung
from tradingbot.kennzahlen.performance import kennzahlen, risikofreie_tagesrendite
from tradingbot.kennzahlen.rendite import total_return_index
from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration

warnings.simplefilter("ignore")
VARIANTE = "Variante 2: Diagnose Filter (gleich gewichtet mit gegen ohne Filter, ohne Kosten)"
GRUENDE = {"Piotroski ≤ 3": "Piotroski", "Altman Z Industrie": "verarbeitendes Gewerbe", "Z'' + 2. Signal": "Altman Z'' ", "Beneish": "Beneish"}


def _nn(x):
    return None if pd.isna(x) else x


def main() -> int:
    konfig = lade_konfiguration("fundamental")
    start, ende = pd.Timestamp(str(konfig["backtest"]["gewertet_ab"])), pd.Timestamp(str(konfig["backtest"]["gewertet_bis"]))
    scores, _ = standard_cache().lesen("fundamental", "scores")
    b = scores[(scores["stichtag"] >= start) & (scores["stichtag"] <= ende) & ~scores["veraltet"].astype(bool)].copy()
    gruende = []
    for r in b.itertuples():
        p = {"wert": _nn(r.piotroski), "wert_hochgerechnet": _nn(r.piotroski_hochgerechnet),
             "hochgerechnet": not pd.isna(r.piotroski_hochgerechnet), "anzahl_signale": r.piotroski_n}
        a = None if pd.isna(r.altman) else {"wert": r.altman, "zone": r.altman_zone}
        e = filter_anwenden(sic=int(r.sic), piotroski=p, altman=a, beneish={"wert": _nn(r.beneish)}, cfo_t=_nn(r.cfo_t), konfig=konfig)
        gruende.append(" | ".join(e.gruende))
    b["gruende"] = gruende
    b["ausgeschlossen"] = b["gruende"] != ""
    b["ticker"] = "CIK" + b["firma"].astype(str)

    kurse, delistings, _, namen = lade_kurse_und_delistings(sorted(b["firma"].unique()), start, ende, konfig)
    us = pd.DatetimeIndex(sorted(set().union(*[k.index for k in kurse.values()])))
    us = us[us <= ende]

    def listen(maske):
        return {pd.Timestamp(t): pd.DataFrame({"ticker": g["ticker"].tolist()}) for t, g in b[maske].groupby("stichtag")}

    mengen = {"ohne Filter (alle bewertbaren)": b["ausgeschlossen"] | ~b["ausgeschlossen"],
              "mit Filtern": ~b["ausgeschlossen"], "nur ausgeschlossene": b["ausgeschlossen"]}
    for name, muster in GRUENDE.items():
        mengen[f"ausgeschlossen: {name}"] = b["gruende"].str.contains(muster, regex=False)
    reihen, statistik = {}, {}
    alle_stichtage = sorted(b["stichtag"].unique())
    for name, maske in mengen.items():
        rl = listen(maske)
        # Quartale ohne Titel (kann bei einzelnen Filtergründen vorkommen): leere Liste → Kasse
        for t in alle_stichtage:
            rl.setdefault(pd.Timestamp(t), pd.DataFrame({"ticker": []}))
        werte, st = kontrollportfolio_mit_leeren(rl, kurse, us, delistings, 10_000.0, ende)
        reihen[name], statistik[name] = werte, st
    rf_tag = risikofreie_tagesrendite(lade_makro(konfig["schattenportfolio"].get("risikofreier_zins", "ECBDFR")), us)
    tage = reihen["ohne Filter (alle bewertbaren)"].index
    k = pd.DataFrame({n: kennzahlen(r.reindex(tage).ffill(), None, rf_tag) for n, r in reihen.items()}).T

    # Wertentwicklung je ausgeschlossenem Titel nach dem Ausschluss (1 und 4 Quartale), gegenüber dem Universum
    plan = signal_und_ausfuehrung(alle_stichtage, us, us)
    kauf = {d: e for d, _, e in plan}
    exec_tage = [e for _, _, e in plan]
    tri = {t: total_return_index(kk) for t, kk in kurse.items()}
    zeilen = []
    for q, (d, _, e) in enumerate(plan):
        for h in (1, 4):
            if q + h < len(exec_tage):
                bis = us[us < exec_tage[q + h]][-1]
            elif h == 1:
                bis = us[-1]
            else:
                continue
            g = b[b["stichtag"] == d]
            for r in g.itertuples():
                if r.ticker not in kurse:
                    continue
                f = haltefaktor(kurse[r.ticker], tri[r.ticker], kauf[d], bis, delistings.get(r.ticker))
                if f is not None:
                    zeilen.append({"stichtag": d, "h": h, "ticker": r.ticker, "ausgeschlossen": r.ausgeschlossen, "gruende": r.gruende,
                                   "rendite": f - 1.0, "delisting": delistings[r.ticker].grund if r.ticker in delistings and delistings[r.ticker].letzter_tag <= bis else ""})
    vw = pd.DataFrame(zeilen)
    vw["universum"] = vw.groupby(["stichtag", "h"])["rendite"].transform("mean")
    vw["ueberrendite"] = vw["rendite"] - vw["universum"]

    # --- Variante zählen ------------------------------------------------------------------------------
    ziel = PROJEKT_WURZEL / "daten" / "fundamental"
    varianten_datei = ziel / "varianten.csv"
    alt = pd.read_csv(varianten_datei) if varianten_datei.exists() else pd.DataFrame()
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=PROJEKT_WURZEL, capture_output=True, text=True).stdout.strip()
    varianten = pd.concat([alt, pd.DataFrame([{"datum": datetime.now().isoformat(timespec="seconds"), "variante": VARIANTE,
                                                "anlass": "Diagnose", "git": commit, "lauf": "daten/fundamental/diagnose_filter.md"}])], ignore_index=True)
    varianten.to_csv(varianten_datei, index=False)

    # --- Bericht ------------------------------------------------------------------------------------------
    pz = lambda x: "–" if pd.isna(x) else f"{x:.2%}".replace(".", ",")  # noqa: E731
    zahl = lambda x: "–" if pd.isna(x) else f"{x:.2f}".replace(".", ",")  # noqa: E731
    text = ["# Diagnose der Ausschlussfilter (Variante 2)", "",
            f"{len(alle_stichtage)} Stichtage {pd.Timestamp(alle_stichtage[0]).date()} bis {pd.Timestamp(alle_stichtage[-1]).date()}, "
            f"Wertreihen bis {ende.date()}. Quartalsweise gleich gewichtet, Kauf zur Eröffnung des ersten US-Handelstags nach dem "
            "Signal, ohne Kosten, vor Steuern, Dividenden reinvestiert, Delistings nach der Rückfall-Regel. "
            f"Getestete Varianten bisher: {varianten['variante'].nunique()}.", "",
            "## Portfolios", "", "| Portfolio | Titel je Stichtag (Mittel) | Rendite p.a. | Volatilität | Sharpe | max. Drawdown |",
            "| --- | --- | --- | --- | --- | --- |"]
    for n, z in k.iterrows():
        text.append(f"| {n} | {statistik[n]['titel'].mean():.0f} | {pz(z['cagr'])} | {pz(z['volatilitaet'])} | {zahl(z['sharpe'])} | {pz(z['max_drawdown'])} |")
    text += ["", "Sharpe mit EZB-Einlagesatz (ECBDFR). Portfolios einzelner Filtergründe sind klein und schwanken stark.", "",
             "## Ausgeschlossene Titel je Stichtag", "", "| Stichtag | bewertbar | ausgeschlossen | " + " | ".join(GRUENDE) + " |",
             "| --- | --- | --- |" + " --- |" * len(GRUENDE)]
    for d, g in b.groupby("stichtag"):
        text.append(f"| {pd.Timestamp(d).date()} | {len(g)} | {int(g['ausgeschlossen'].sum())} | "
                    + " | ".join(str(int(g["gruende"].str.contains(m, regex=False).sum())) for m in GRUENDE.values()) + " |")
    text += ["", "## Wertentwicklung nach dem Ausschluss (je Titel und Stichtag, gegenüber dem Mittel aller bewertbaren)", "",
             "| Gruppe | Horizont | Fälle | mittlere Rendite | mittlere Überrendite | Median Überrendite | Anteil schlechter als Universum | Delistings (Pleite / Übernahme) |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    gruppen = {"ausgeschlossen (alle)": vw["ausgeschlossen"], "nicht ausgeschlossen": ~vw["ausgeschlossen"]}
    for name, muster in GRUENDE.items():
        gruppen[name] = vw["gruende"].str.contains(muster, regex=False)
    for name, maske in gruppen.items():
        for h in (1, 4):
            g = vw[maske & (vw["h"] == h)]
            if g.empty:
                continue
            text.append(f"| {name} | {h} Q | {len(g)} | {pz(g['rendite'].mean())} | {pz(g['ueberrendite'].mean())} | "
                        f"{pz(g['ueberrendite'].median())} | {pz((g['ueberrendite'] < 0).mean())} | "
                        f"{int((g['delisting'] == 'pleite').sum())} / {int((g['delisting'] == 'uebernahme').sum())} |")
    quartal = vw[vw["h"] == 1].groupby(["stichtag", "ausgeschlossen"])["rendite"].mean().unstack()
    if True in quartal.columns and False in quartal.columns:
        diff = (quartal[True] - quartal[False]).dropna()
        t_wert = diff.mean() / (diff.std(ddof=1) / np.sqrt(len(diff))) if len(diff) > 1 else float("nan")
        text += ["", f"Quartale, in denen die ausgeschlossenen Titel schlechter liefen als die behaltenen: {int((diff < 0).sum())} von {len(diff)}; "
                 f"mittlerer Abstand je Quartal {pz(diff.mean())} (t-Wert {zahl(t_wert)})."]
    schlimmste = vw[(vw["h"] == 4) & vw["ausgeschlossen"]].nsmallest(10, "rendite")
    text += ["", "Größte Verluste ausgeschlossener Titel in den 4 Quartalen nach dem Ausschluss: "
             + ", ".join(f"{namen.get(int(r.ticker[3:]), r.ticker)} {pd.Timestamp(r.stichtag).date()} {pz(r.rendite)} ({r.gruende.split(' | ')[0]})"
                         for r in schlimmste.itertuples())]
    bericht = "\n".join(text)
    (ziel / "diagnose_filter.md").write_text(bericht, encoding="utf-8")
    vw.to_csv(ziel / "diagnose_filter_vorwaerts.csv", index=False)
    print(bericht)
    return 0


def kontrollportfolio_mit_leeren(rl, kurse, kalender, delistings, kapital, ende):
    """Wie `kontrollportfolio`, Quartale ohne Titel bleiben Kasse (Faktor 1)."""
    voll = {d: r for d, r in rl.items() if len(r)}
    if len(voll) == len(rl):
        return kontrollportfolio(rl, kurse, kalender, delistings, kapital, ende, kalender)
    platzhalter = "__KASSE__"
    kasse = pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 0.0, "dividende": 0.0, "split": 0.0}, index=kalender)
    rl2 = {d: (r if len(r) else pd.DataFrame({"ticker": [platzhalter]})) for d, r in rl.items()}
    werte, st = kontrollportfolio(rl2, {**kurse, platzhalter: kasse}, kalender, delistings, kapital, ende, kalender)
    st.loc[[len(rl[d]) == 0 for d in st["stichtag"]], "titel"] = 0
    return werte, st


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FehlerschwelleUeberschritten as fehler:
        sys.exit(laut_melden(fehler))
