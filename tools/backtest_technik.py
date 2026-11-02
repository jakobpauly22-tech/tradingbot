r"""Gewertete Backtests der Satellite-Strategien (Sitzung 5, Entscheidungen Jakob 03.11.2026, config/technik.yaml).

Aufruf:
  .venv\Scripts\python tools\backtest_technik.py --nur-pruefen   Daten prüfen, Zeitraum bestimmen, nichts simulieren
  .venv\Scripts\python tools\backtest_technik.py                 fünf Varianten rechnen und berichten

Varianten (jede zählt): crossover, momentum, price_channel, rsi2, regime (alle vier mit ADX-Schalter).
Kriterien je Variante, nach Kosten, 1.250 €, in BEIDEN Hälften des Zeitraums: Sharpe ≥ Buy & Hold (alle ETFs gleich
gewichtet, quartalsweise, gleiche Kosten) und maximaler Drawdown nicht schlechter als −20 %.
Sperren (laut, Exit 2): auffällige Kursreihen ohne dokumentierte Freigabe (`universum.datenfreigaben`) oder
offene Umsetzung des Buy-&-Hold-Vergleichs (`erfolgskriterien.buy_and_hold_umsetzung`).
Ergebnis: daten/backtests/<zeitstempel>_technik_<variante>/, Bericht docs/berichte/<datum>_technik_satellite.md,
Zeilen in daten/technik/varianten.csv.
"""
import argparse
import sys
import warnings
from datetime import datetime

import pandas as pd

from tradingbot.backtest.bericht import fuehre_lauf_aus
from tradingbot.backtest.marktdaten import Instrument, Marktdaten
from tradingbot.backtest.simulation import TeilportfolioDefinition
from tradingbot.backtest.strategie import FesteGewichte
from tradingbot.daten.kurse import lade_kurse, lade_kurse_eur
from tradingbot.daten.makro import lade_makro
from tradingbot.engines.technik.daten import gewerteter_beginn, haelften, pruefe_etf_kurse
from tradingbot.engines.technik.strategien import REGELN, SatelliteStrategie
from tradingbot.kennzahlen.performance import kennzahlen, risikofreie_tagesrendite
from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration

warnings.simplefilter("ignore")
VARIANTEN = {"crossover": (["crossover"], False), "momentum": (["momentum"], False), "price_channel": (["price_channel"], False),
             "rsi2": (["rsi2"], False), "regime": (list(REGELN), True)}


def lade_universum_kurse(k: dict) -> tuple[dict, dict, dict]:
    """Kurse in EUR je ETF (optional über eine freigegebene Ersatzquelle desselben Produkts), Währungen, Befunde."""
    von, bis = str(k["backtest"]["daten_ab"]), str(k["backtest"]["gewertet_bis"])
    kurse, waehrungen, befunde = {}, {}, {}
    for e in k["universum"]["etfs"]:
        quelle = e.get("kursquelle") or e["ticker"]
        if quelle != e["ticker"]:
            roh = lade_kurse_eur(quelle, von, bis)            # Ersatzquelle desselben Produkts, in EUR umgerechnet
        else:
            roh = lade_kurse(e["ticker"], von, bis)
        kurse[e["ticker"]] = roh
        waehrungen[e["ticker"]] = "EUR"
        b = pruefe_etf_kurse(roh) if quelle == e["ticker"] else [x for x in pruefe_etf_kurse(roh) if "währung" not in x]
        if b:
            befunde[e["ticker"]] = b
    return kurse, waehrungen, befunde


def main() -> int:
    arg = argparse.ArgumentParser()
    arg.add_argument("--nur-pruefen", action="store_true")
    a = arg.parse_args()
    k = lade_konfiguration("technik")
    bt = lade_konfiguration("backtest")
    kurse, waehrungen, befunde = lade_universum_kurse(k)
    freigaben = {f["ticker"]: f for f in k["universum"].get("datenfreigaben") or []}
    offen = {t: b for t, b in befunde.items() if t not in freigaben}
    start = gewerteter_beginn(kurse, k["backtest"]["daten_ab"], 12)
    ende = pd.Timestamp(str(k["backtest"]["gewertet_bis"]))
    print(f"Gewerteter Zeitraum: {start.date()} bis {ende.date()}; Hälften: "
          + ", ".join(f"{x.date()}–{y.date()}" for x, y in haelften(start, ende, int(k["backtest"]["haelften"]))))
    for t, b in befunde.items():
        status = "freigegeben" if t in freigaben else "OFFEN"
        print(f"{t} ({status}):")
        for x in b[:8]:
            print("   ", x)
        if len(b) > 8:
            print(f"    … {len(b) - 8} weitere")
    if offen:
        print(f"\nSPERRE: {len(offen)} Kursreihe(n) auffällig ohne dokumentierte Entscheidung – mit Jakob besprechen.")
        return 2
    umsetzung = k["erfolgskriterien"].get("buy_and_hold_umsetzung")
    if not umsetzung or umsetzung == "offen":
        print("\nSPERRE: Umsetzung des Buy-&-Hold-Vergleichs ist offen (erfolgskriterien.buy_and_hold_umsetzung).")
        return 2
    if a.nur_pruefen:
        return 0

    m = Marktdaten(kurse, waehrungen)
    instrumente = [Instrument(e["ticker"], "etf", e["steuerart"]) for e in k["universum"]["etfs"]]
    sp = k["backtest"]
    bh_gewichte = {e["ticker"]: 1.0 / len(instrumente) for e in k["universum"]["etfs"]}
    definitionen = {}
    for name, (regeln, regime) in VARIANTEN.items():
        definitionen[name] = TeilportfolioDefinition(f"technik_{name}", float(sp["kapital"]),
                                                     SatelliteStrategie(regeln, kurse, k, regime=regime), instrumente,
                                                     art="schatten", steuergruppe=sp["steuergruppe"], rolle="satellite")
    bh = TeilportfolioDefinition("buy_and_hold", float(sp["kapital"]), FesteGewichte(bh_gewichte, "Q"), instrumente,
                                 art="schatten", steuergruppe=sp["steuergruppe"], rolle="satellite")
    optionen = {}
    if umsetzung == "ohne_gebuehrenregel":          # gleiche Kosten, aber Käufe unter 125 € erlaubt
        from tradingbot.backtest.simulation import Ausfuehrungsregeln
        optionen_bh = {"regeln": Ausfuehrungsregeln(max_gebuehr_anteil=1.0)}
    elif umsetzung == "kostenfrei":                 # strengere Messlatte: ohne Kosten (wie das Kontrollportfolio)
        from tradingbot.backtest.kosten import Kostenmodell
        optionen_bh = {"kosten": Kostenmodell.ohne_kosten()}
    else:
        raise SystemExit(f"Unbekannte Umsetzung des Buy-&-Hold-Vergleichs: {umsetzung}")
    laeufe = {}
    for name, d in definitionen.items():
        laeufe[name] = fuehre_lauf_aus(f"technik_{name}", [d], m, start, ende, benchmark_ticker="SXR8.DE", konfig=bt, **optionen)
    lauf_bh = fuehre_lauf_aus("technik_buy_and_hold", [bh], m, start, ende, benchmark_ticker="SXR8.DE", konfig=bt, **optionen_bh)

    rf = lade_makro(bt.get("risikofreier_zins", "ECBDFR"))
    abschnitte = [("gesamt", start, ende)] + [(f"Hälfte {i + 1}", x, y) for i, (x, y) in enumerate(haelften(start, ende, int(sp["haelften"])))]
    grenze_dd = float(k["erfolgskriterien"]["max_drawdown_mindestens"])

    def kz(werte, von, bis):
        w = werte.loc[von:bis]
        return kennzahlen(w, None, risikofreie_tagesrendite(rf, w.index))

    bh_wert = lauf_bh.ergebnisse["buy_and_hold"].wert
    zeilen = []
    for name, lauf in laeufe.items():
        e = lauf.ergebnisse[f"technik_{name}"]
        for abschnitt, von, bis in abschnitte:
            s, b = kz(e.wert, von, bis), kz(bh_wert, von, bis)
            zeilen.append({"variante": name, "abschnitt": abschnitt, "cagr": s["cagr"], "sharpe": s["sharpe"], "max_dd": s["max_drawdown"],
                           "bh_cagr": b["cagr"], "bh_sharpe": b["sharpe"], "bh_max_dd": b["max_drawdown"],
                           "sharpe_ok": s["sharpe"] >= b["sharpe"], "dd_ok": s["max_drawdown"] >= grenze_dd})
    t = pd.DataFrame(zeilen)
    bewertung = {}
    for name in VARIANTEN:
        h = t[(t.variante == name) & (t.abschnitt != "gesamt")]
        bewertung[name] = bool(h["sharpe_ok"].all() and h["dd_ok"].all())

    # Varianten zählen
    ziel = PROJEKT_WURZEL / "daten" / "technik"
    ziel.mkdir(parents=True, exist_ok=True)
    datei = ziel / "varianten.csv"
    alt = pd.read_csv(datei) if datei.exists() else pd.DataFrame()
    neu = pd.DataFrame([{"datum": datetime.now().isoformat(timespec="seconds"), "variante": n, "git": laeufe[n].meta["git"].get("commit"),
                         "lauf": laeufe[n].pfad.name if laeufe[n].pfad else "", "bestanden": bewertung[n]} for n in VARIANTEN])
    varianten = pd.concat([alt, neu], ignore_index=True)
    varianten.to_csv(datei, index=False)

    # Bericht
    pz = lambda x: f"{x:.2%}".replace(".", ",")  # noqa: E731
    zahl = lambda x: f"{x:.2f}".replace(".", ",")  # noqa: E731
    ok = lambda b: "ja" if b else "**nein**"  # noqa: E731
    text = [f"# Satellite-Strategien der Technik-Engine – gewertete Backtests", "",
            f"Stand {datetime.now():%d.%m.%Y %H:%M}. Zeitraum {start.date()} bis {ende.date()}, Kapital {sp['kapital']:,.0f} € (Schatten), "
            f"{len(instrumente)} ETFs/ETCs laut `config/technik.yaml`. Getestete Varianten bisher: {varianten['variante'].nunique()}.", "",
            f"Buy & Hold: alle ETFs gleich gewichtet, quartalsweise, gleiche Kosten (Umsetzung: {umsetzung}).", "",
            "## Ergebnis je Variante (Kriterien in beiden Hälften)", "", "| Variante | bestanden |", "| --- | --- |"]
    text += [f"| {n} | {'**ja**' if b else 'nein'} |" for n, b in bewertung.items()]
    text += ["", "## Kennzahlen nach Kosten, vor Steuern", "",
             "| Variante | Abschnitt | Rendite p.a. | Sharpe | max. Drawdown | B&H Rendite | B&H Sharpe | B&H Drawdown | Sharpe ≥ B&H | DD ≥ −20 % |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in t.itertuples():
        text.append(f"| {r.variante} | {r.abschnitt} | {pz(r.cagr)} | {zahl(r.sharpe)} | {pz(r.max_dd)} | {pz(r.bh_cagr)} | {zahl(r.bh_sharpe)} | "
                    f"{pz(r.bh_max_dd)} | {ok(r.sharpe_ok)} | {ok(r.dd_ok)} |")
    text += ["", "## Handel und Kosten", "", "| Variante | Trades | verworfene Orders | Kosten | Steuern gezahlt | Rendite nach Verkauf und Steuern |",
             "| --- | --- | --- | --- | --- | --- |"]
    for name, lauf in {**laeufe, "buy_and_hold": lauf_bh}.items():
        kk = lauf.kennzahlen.iloc[0]
        text.append(f"| {name} | {int(kk['trades'])} | {int(kk['verworfen'])} | {kk['kosten']:,.0f} € | {kk['steuern_gezahlt']:,.0f} € | "
                    f"{pz(kk['cagr_nach_verkauf_und_steuern'])} |")
    text += ["", "Ablage der Läufe: " + ", ".join(f"`{l.pfad.relative_to(PROJEKT_WURZEL)}`" for l in [*laeufe.values(), lauf_bh] if l.pfad)]
    bericht = "\n".join(text)
    ordner = PROJEKT_WURZEL / "docs" / "berichte"
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / f"{datetime.now():%Y-%m-%d}_technik_satellite.md").write_text(bericht, encoding="utf-8")
    t.to_csv(ziel / "kriterien.csv", index=False)
    print(bericht)
    return 0


if __name__ == "__main__":
    sys.exit(main())
