"""Backtest-Lauf mit Bericht und Ablage je Lauf (daten/backtests/<zeitstempel>_<name>/, nicht in Git).

Jedes Teilportfolio wird gegen einen Benchmark-Zwilling gerechnet: Buy & Hold des Hauptbenchmarks mit
demselben Startkapital, denselben Kosten und denselben Steuerregeln (eigene Steuergruppe mit dem gleichen
Pauschbetrag-Anteil). So ist der Vergleich auch nach Steuern und nach fiktivem Verkauf am Ende fair.
Vor Steuern wird zusätzlich gegen den kostenfreien Total-Return-Index gemessen.

Ausgewiesen werden drei Ebenen (Entscheidung Jakob, 01.11.2026):
1. vor Steuern, 2. nach laufend gezahlten Steuern, 3. nach Steuern bei fiktivem Verkauf am Ende.
"""
from __future__ import annotations

import json
import platform
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

from tradingbot.backtest.marktdaten import Instrument, Marktdaten
from tradingbot.backtest.simulation import Ergebnis, TeilportfolioDefinition, simuliere
from tradingbot.backtest.strategie import BuyAndHold
from tradingbot.backtest.tresor import TresorFreigabe
from tradingbot.backtest.walk_forward import Fenster, walk_forward
from tradingbot.kennzahlen.performance import cagr, drawdown, kennzahlen, monatsrenditen, risikofreie_tagesrendite
from tradingbot.kennzahlen.rendite import total_return_index

BENCHMARK_PRAEFIX = "benchmark:"


@dataclass
class Lauf:
    name: str
    ergebnisse: dict[str, Ergebnis]            # nur die eigentlichen Teilportfolios
    zwillinge: dict[str, Ergebnis]             # Benchmark-Zwilling je Teilportfolio
    kennzahlen: pd.DataFrame                   # Zeile je Teilportfolio
    fenster: pd.DataFrame = field(default_factory=pd.DataFrame)
    pfad: Path | None = None
    meta: dict = field(default_factory=dict)


def _jahre(werte: pd.Series) -> float:
    return (werte.index[-1] - werte.index[0]).days / 365.25


def _cagr_aus(start: float, ende: float, jahre: float) -> float:
    return (ende / start) ** (1 / jahre) - 1 if jahre > 0 and start > 0 else float("nan")


def kennzahlen_teilportfolio(e: Ergebnis, zwilling: Ergebnis, benchmark_tr: pd.Series, rf_tag: pd.Series) -> dict:
    """Kennzahlen auf drei Ebenen plus Regelprüfungen (Core-Notbremse, Satellite-Limits)."""
    k = kennzahlen(e.wert, benchmark_tr, rf_tag)
    jahre = _jahre(e.wert)
    start = float(e.meta["startkapital"])
    nach_verkauf = float(e.meta["wert_nach_liquidation_und_steuern"])
    zw_verkauf = float(zwilling.meta["wert_nach_liquidation_und_steuern"])
    k.update({
        "art": e.meta["art"],
        "rolle": e.meta["rolle"],
        "startkapital": start,
        # Ebene 2: nach laufend gezahlten Steuern
        "endwert_nach_steuern": float(e.wert_nach_steuern.iloc[-1]),
        "cagr_nach_steuern": cagr(e.wert_nach_steuern),
        "benchmark_cagr_nach_steuern": cagr(zwilling.wert_nach_steuern),
        # Ebene 3: nach Steuern bei fiktivem Verkauf am Ende
        "endwert_nach_verkauf_und_steuern": nach_verkauf,
        "cagr_nach_verkauf_und_steuern": _cagr_aus(start, nach_verkauf, jahre),
        "benchmark_endwert_nach_verkauf_und_steuern": zw_verkauf,
        "benchmark_cagr_nach_verkauf_und_steuern": _cagr_aus(start, zw_verkauf, jahre),
        "steuern_gezahlt": float(e.meta["steuern_gezahlt"]),
        "steuer_bei_verkauf": float(e.meta["liquidationssteuer"]),
        "kosten": e.kosten_gesamt,
        "kosten_waehrungstausch": float(e.waehrungstausche["kosten"].sum()) if len(e.waehrungstausche) else 0.0,
        "trades": int(len(e.trades)),
        "verworfen": int(len(e.verworfen)),
    })
    k["differenz_cagr_nach_verkauf_und_steuern"] = k["cagr_nach_verkauf_und_steuern"] - k["benchmark_cagr_nach_verkauf_und_steuern"]
    if e.meta["rolle"] == "satellite":
        # Satellite-Limits (CLAUDE.md): Monat −10 % → Pause; −20 % vom Höchststand → Stopp. Hier nur gemeldet.
        monate = monatsrenditen(e.wert).drop(columns="Jahr").stack()
        k["monate_unter_minus_10"] = [f"{j}-{m:02d}" for (j, m), r in monate.items() if r <= -0.10]
        dd = drawdown(e.wert)
        k["erster_tag_drawdown_20"] = dd[dd <= -0.20].index[0].date() if (dd <= -0.20).any() else None
    return k


def _zwilling(d: TeilportfolioDefinition, benchmark_ticker: str) -> TeilportfolioDefinition:
    return TeilportfolioDefinition(
        f"{BENCHMARK_PRAEFIX}{d.name}", d.startkapital, BuyAndHold({benchmark_ticker: 1.0}),
        [Instrument(benchmark_ticker)], art=d.art, steuergruppe=f"{BENCHMARK_PRAEFIX}{d.name}", rolle=d.rolle,
    )


def fuehre_lauf_aus(
    name: str,
    definitionen: list[TeilportfolioDefinition],
    marktdaten: Marktdaten,
    start,
    ende,
    *,
    benchmark_ticker: str | None = None,
    rf_zins_prozent: pd.Series | None = None,
    fenster: list[Fenster] | None = None,
    tresor_freigabe: TresorFreigabe | None = None,
    konfig: dict | None = None,
    konfig_daten: dict | None = None,
    ablage: bool = True,
    ablage_wurzel: Path | None = None,
    jetzt: datetime | None = None,
    **simulations_optionen,
) -> Lauf:
    """Simuliert Teilportfolios samt Benchmark-Zwillingen, berechnet Kennzahlen und legt den Lauf ab."""
    from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration

    konfig = json.loads(json.dumps(konfig or lade_konfiguration("backtest"), default=str))  # Kopie
    konfig_daten = konfig_daten or lade_konfiguration("daten")
    benchmark_ticker = benchmark_ticker or konfig_daten["benchmarks"]["core"]["haupt"]["ticker"]
    if benchmark_ticker not in marktdaten.kurse:
        raise ValueError(f"Benchmark {benchmark_ticker} fehlt in den Marktdaten")
    # Basiszins-Schlüssel nach JSON-Kopie wieder als Zahl
    konfig["steuern"]["basiszins_prozent"] = {int(j): v for j, v in konfig["steuern"]["basiszins_prozent"].items()}
    anteile = konfig["steuern"].setdefault("pauschbetrag_anteil", {})
    zwillinge = [_zwilling(d, benchmark_ticker) for d in definitionen]
    for d, z in zip(definitionen, zwillinge):
        anteile[z.steuergruppe] = float(anteile.get(d.steuergruppe, 1.0))

    alle = definitionen + zwillinge
    optionen = dict(tresor_freigabe=tresor_freigabe, konfig=konfig, **simulations_optionen)
    if fenster:
        tr_gesamt = total_return_index(marktdaten.kurse[benchmark_ticker])
        ergebnisse, fenster_tabelle = walk_forward(alle, marktdaten, fenster, benchmark=tr_gesamt, **optionen)
        fenster_tabelle = fenster_tabelle[~fenster_tabelle.teilportfolio.str.startswith(BENCHMARK_PRAEFIX)].reset_index(drop=True)
    else:
        ergebnisse = simuliere(alle, marktdaten, start, ende, **optionen)
        fenster_tabelle = pd.DataFrame()

    eigene = {d.name: ergebnisse[d.name] for d in definitionen}
    zw = {d.name: ergebnisse[z.name] for d, z in zip(definitionen, zwillinge)}
    tage = next(iter(eigene.values())).wert.index
    bench = marktdaten.kurse[benchmark_ticker]
    benchmark_tr = total_return_index(bench.loc[bench.index <= tage[-1]]).reindex(tage).ffill()

    rf_hinweis = None
    if rf_zins_prozent is None:
        try:
            from tradingbot.daten.makro import lade_makro

            rf_zins_prozent = lade_makro(konfig.get("risikofreier_zins", "ECBDFR"))
        except Exception as fehler:  # ohne FRED-Zugang: Kennzahlen mit r_f = 0, im Bericht vermerkt
            rf_hinweis = f"Risikofreier Zins nicht verfügbar ({type(fehler).__name__}), gerechnet mit 0 %"
            rf_zins_prozent = pd.Series(0.0, index=tage[:1])
    rf_tag = risikofreie_tagesrendite(rf_zins_prozent, tage)

    tabelle = pd.DataFrame({n: kennzahlen_teilportfolio(e, zw[n], benchmark_tr, rf_tag) for n, e in eigene.items()}).T
    lauf = Lauf(name, eigene, zw, tabelle, fenster_tabelle)
    lauf.meta = {
        "name": name,
        "erstellt_um": (jetzt or datetime.now()).isoformat(timespec="seconds"),
        "zeitraum": [str(tage[0].date()), str(tage[-1].date())],
        "benchmark": benchmark_ticker,
        "risikofreier_zins": konfig.get("risikofreier_zins", "ECBDFR"),
        "rf_hinweis": rf_hinweis,
        "tresor": {"gesperrt_ab": str(konfig["tresor"]["gesperrt_ab"]),
                   "freigabe": tresor_freigabe.__dict__ if tresor_freigabe else None},
        "datenstand": marktdaten.datenstand,
        "git": _git_stand(PROJEKT_WURZEL),
        "python": platform.python_version(),
        "teilportfolios": {d.name: {"strategie": d.strategie.name, "startkapital": d.startkapital, "art": d.art,
                                    "rolle": d.rolle, "steuergruppe": d.steuergruppe,
                                    "instrumente": [i.__dict__ for i in d.instrumente]} for d in definitionen},
        "walk_forward": [{k: str(v.date()) for k, v in f.__dict__.items()} for f in fenster] if fenster else None,
    }
    if ablage:
        lauf.pfad = _ablegen(lauf, ablage_wurzel or PROJEKT_WURZEL / "daten" / "backtests", PROJEKT_WURZEL)
    return lauf


def _git_stand(wurzel: Path) -> dict:
    def git(*args):
        return subprocess.run(["git", *args], cwd=wurzel, capture_output=True, text=True, check=True).stdout.strip()

    try:
        return {"commit": git("rev-parse", "--short", "HEAD"), "unsaubere_dateien": bool(git("status", "--porcelain"))}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": "unbekannt", "unsaubere_dateien": None}


def _ablegen(lauf: Lauf, wurzel: Path, projekt: Path) -> Path:
    zeitstempel = lauf.meta["erstellt_um"].replace(":", "").replace("-", "")
    pfad = Path(wurzel) / f"{zeitstempel}_{lauf.name}"
    pfad.mkdir(parents=True, exist_ok=False)
    for name, e in {**lauf.ergebnisse, **{f"{BENCHMARK_PRAEFIX}{n}": z for n, z in lauf.zwillinge.items()}}.items():
        ordner = pfad / name.replace(":", "_")
        ordner.mkdir()
        e.werte.to_csv(ordner / "werte.csv")
        e.trades.to_csv(ordner / "trades.csv", index=False)
        e.verworfen.to_csv(ordner / "verworfen.csv", index=False)
        e.steuerereignisse.to_csv(ordner / "steuerereignisse.csv", index=False)
        e.steuern_gruppe.to_csv(ordner / "steuern_gruppe.csv")
    if not lauf.fenster.empty:
        lauf.fenster.to_csv(pfad / "walk_forward.csv", index=False)
    (pfad / "kennzahlen.json").write_text(json.dumps(lauf.kennzahlen.to_dict(orient="index"), default=str, indent=2, ensure_ascii=False), encoding="utf-8")
    (pfad / "meta.json").write_text(json.dumps(lauf.meta, default=str, indent=2, ensure_ascii=False), encoding="utf-8")
    konfig_ordner = pfad / "config"
    konfig_ordner.mkdir()
    for datei in (projekt / "config").glob("*.yaml"):
        shutil.copy2(datei, konfig_ordner / datei.name)
    (pfad / "bericht.md").write_text(bericht_markdown(lauf), encoding="utf-8")
    return pfad


# --- Markdown ------------------------------------------------------------------------------------
def _pz(x) -> str:
    return "–" if x is None or pd.isna(x) else f"{x * 100:,.2f} %".replace(",", "X").replace(".", ",").replace("X", ".")


def _eur(x) -> str:
    return "–" if x is None or pd.isna(x) else f"{x:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def _zahl(x, stellen=2) -> str:
    return "–" if x is None or pd.isna(x) else f"{x:.{stellen}f}".replace(".", ",")


def bericht_markdown(lauf: Lauf) -> str:
    m = lauf.meta
    z = [f"# Backtest „{lauf.name}“", "",
         f"Zeitraum {m['zeitraum'][0]} bis {m['zeitraum'][1]}, Benchmark {m['benchmark']} (Total Return), "
         f"risikofreier Zins {m['risikofreier_zins']}. Erstellt {m['erstellt_um']}, Git {m['git']['commit']}"
         + (" (mit nicht committeten Änderungen)" if m["git"].get("unsaubere_dateien") else "") + ".", ""]
    if m.get("rf_hinweis"):
        z += [f"> Hinweis: {m['rf_hinweis']}", ""]
    tresor = m["tresor"]
    z += [f"Tresor: gesperrt ab {tresor['gesperrt_ab']}, "
          + (f"für diesen Lauf geöffnet ({tresor['freigabe']['phase']})." if tresor["freigabe"] else "nicht geöffnet (nur Entwicklungsdaten)."), ""]

    z += ["## Ergebnis auf drei Ebenen", "",
          "| Teilportfolio | Art | Start | vor Steuern | nach Steuern | nach Verkauf und Steuern | Benchmark nach Verkauf und Steuern | Differenz p.a. |",
          "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for n, k in lauf.kennzahlen.iterrows():
        z.append(f"| {n} | {k.art} | {_eur(k.startkapital)} | {_eur(k.endwert)} ({_pz(k.cagr)} p.a.) | "
                 f"{_eur(k.endwert_nach_steuern)} ({_pz(k.cagr_nach_steuern)}) | "
                 f"{_eur(k.endwert_nach_verkauf_und_steuern)} ({_pz(k.cagr_nach_verkauf_und_steuern)}) | "
                 f"{_eur(k.benchmark_endwert_nach_verkauf_und_steuern)} ({_pz(k.benchmark_cagr_nach_verkauf_und_steuern)}) | "
                 f"{_pz(k.differenz_cagr_nach_verkauf_und_steuern)} |")
    z += ["", "Schattenportfolios (Art „schatten“) laufen mit virtuellem Kapital und sind kein Teil des echten Depots.", ""]

    z += ["## Risiko und Vergleich mit der Benchmark (vor Steuern)", "",
          "| Teilportfolio | Vola | Sharpe | Sortino | Max DD | Calmar | VaR 95 % (Tag) | CVaR 95 % | Beta | Alpha p.a. | t(Alpha) | Tracking Error | IR |",
          "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for n, k in lauf.kennzahlen.iterrows():
        z.append(f"| {n} | {_pz(k.volatilitaet)} | {_zahl(k.sharpe)} | {_zahl(k.sortino)} | {_pz(k.max_drawdown)} | {_zahl(k.calmar)} | "
                 f"{_pz(k.var95_tag)} | {_pz(k.cvar95_tag)} | {_zahl(k.beta)} | {_pz(k.alpha_pa)} | {_zahl(k.t_alpha)} | "
                 f"{_pz(k.tracking_error)} | {_zahl(k.information_ratio)} |")
    z += ["", "t(Alpha) mit Newey-West-Standardfehlern; |t| < 2 heißt: Alpha nicht von null zu unterscheiden.", ""]

    z += ["## Kosten, Steuern und Regeln", "",
          "| Teilportfolio | Trades | verworfen | Kosten | Steuern gezahlt | Steuer bei Verkauf | Max DD Dauer | Regelprüfung |",
          "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for n, k in lauf.kennzahlen.iterrows():
        if k.rolle == "satellite":
            monate = k.get("monate_unter_minus_10") or []
            regel = (f"Monat ≤ −10 %: {', '.join(monate) if monate else 'nie'}; "
                     f"−20 % vom Hoch: {k.get('erster_tag_drawdown_20') or 'nie'}")
        else:
            regel = f"Core-Notbremse (12 M > 10 Pp. hinter Benchmark): {k.tage_notbremse_core} Tage"
        z.append(f"| {n} | {k.trades} | {k.verworfen} | {_eur(k.kosten)} | {_eur(k.steuern_gezahlt)} | {_eur(k.steuer_bei_verkauf)} | "
                 f"{k.max_drawdown_dauer_tage} Tage | {regel} |")
    z.append("")

    if not lauf.fenster.empty:
        z += ["## Walk-forward (nur Testfenster)", "", "| Teilportfolio | Testfenster | Rendite | Benchmark | Differenz | Max DD |",
              "| --- | --- | --- | --- | --- | --- |"]
        for _, f in lauf.fenster.iterrows():
            z.append(f"| {f.teilportfolio} | {f.test_ab} bis {f.test_bis} | {_pz(f.rendite)} | {_pz(f.get('benchmark'))} | "
                     f"{_pz(f.get('differenz'))} | {_pz(f.max_drawdown)} |")
        z.append("")

    for n, e in lauf.ergebnisse.items():
        z += [f"## {n}: Jahresrenditen und Steuern", "", f"Strategie: {e.strategie}", "",
              "| Jahr | Rendite vor Steuern | Steuer (zugeordnet) |", "| --- | --- | --- |"]
        jahre = monatsrenditen(e.wert)["Jahr"]
        steuern = e.steuern["steuer"] if "steuer" in e.steuern else pd.Series(dtype=float)
        for jahr, r in jahre.items():
            z.append(f"| {jahr} | {_pz(r)} | {_eur(steuern.get(jahr, 0.0))} |")
        if len(e.verworfen):
            z += ["", "Verworfene Orders nach Grund: " + ", ".join(
                f"{g} ({c})" for g, c in e.verworfen.grund.str.replace(r"[\d.,]+ €", "x €", regex=True).value_counts().items())]
        z.append("")

    z += ["## Annahmen", "",
          "- Signal zum Schlusskurs, Ausführung zur Eröffnung des nächsten Handelstags; ganze Stücke; Kosten laut `config/backtest.yaml`.",
          "- Steuern nach heutigem Recht für alle Jahre (siehe `src/tradingbot/backtest/steuern.py`), Abfluss am Jahresende ohne Zwangsverkauf.",
          "- Benchmark-Zwilling: Buy & Hold des Hauptbenchmarks mit gleichem Kapital, gleichen Kosten und Steuerregeln.",
          "- Datenstand je Ticker und vollständige Konfiguration liegen in `meta.json` und `config/` neben diesem Bericht.", ""]
    return "\n".join(z)
