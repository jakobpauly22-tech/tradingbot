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


def korrigiere(kurse: pd.DataFrame, korrekturen: list[dict]) -> tuple[pd.DataFrame, list[str]]:
    """Dokumentierte Korrekturen (config/technik.yaml `universum.korrekturen`): Regel „vortagesschluss“ setzt alle
    Preise des Tages auf den Schlusskurs des Vortags."""
    k, protokoll = kurse.copy(), []
    for c in korrekturen:
        tag = pd.Timestamp(str(c["datum"]))
        if c["regel"] != "vortagesschluss" or tag not in k.index:
            raise SystemExit(f"Korrektur nicht anwendbar: {c}")
        vortag = float(k.loc[k.index < tag, "close"].iloc[-1])
        alt = k.loc[tag, ["open", "high", "low", "close"]].round(3).tolist()
        k.loc[tag, ["open", "high", "low", "close"]] = vortag
        protokoll.append(f"{c['ticker']} {tag.date()}: O/H/T/S {alt} → {vortag:.3f} (Vortagesschluss; {c['grund']})")
    return k, protokoll


def plausibilitaet_ersatzquelle(original: str, ersatz_eur: pd.DataFrame, von, bis) -> dict:
    """Median der Abweichung |Ersatz / Original − 1| an Tagen mit Umsatz im Original, beide Reihen in EUR."""
    orig = lade_kurse_eur(original, von, bis)
    tage = orig.index[orig["volume"] > 0]
    j = pd.concat([orig["close"], ersatz_eur["close"]], axis=1, keys=["orig", "ersatz"]).loc[tage].dropna()
    abw = (j["ersatz"] / j["orig"] - 1).abs()
    return {"tage": len(j), "median": float(abw.median()), "p95": float(abw.quantile(0.95)),
            "je_jahr": {int(y): float(v) for y, v in abw.groupby(abw.index.year).median().items()},
            "originalwaehrung": orig.attrs.get("originalwaehrung")}


def plausibilitaet_ausschuettend(p: dict, kurse_ersatz: pd.DataFrame) -> dict:
    """Rendite p.a. inklusive Dividenden (reinvestiert, ohne Steuern) des Ersatz-ETFs gegen den ersetzten ETF."""
    from tradingbot.kennzahlen.performance import cagr
    from tradingbot.kennzahlen.rendite import total_return_index
    von, bis = str(p["von"]), str(p["bis"])
    vergleich = lade_kurse(p["vergleich"], von, bis)
    r_e, r_v = cagr(total_return_index(kurse_ersatz.loc[von:bis])), cagr(total_return_index(vergleich.loc[von:bis]))
    ohne_div = cagr(kurse_ersatz.loc[von:bis, "close"])
    jahre_ohne = sorted(set(range(pd.Timestamp(von).year, pd.Timestamp(bis).year + 1))
                        - set(kurse_ersatz.loc[von:bis].index[kurse_ersatz.loc[von:bis, "dividende"] > 0].year))
    return {"ersatz": r_e, "vergleich": r_v, "differenz_pp": (r_e - r_v) * 100, "nur_kurs": ohne_div,
            "jahre_ohne_ausschuettung": jahre_ohne, "max_pp": float(p["max_pp"]), "bestanden": abs(r_e - r_v) * 100 <= float(p["max_pp"])}


def lade_universum_kurse(k: dict) -> tuple[dict, dict, dict, dict]:
    """Kurse in EUR je ETF (optional über eine freigegebene Ersatzquelle desselben Produkts), Währungen, Befunde und
    Prüfprotokoll (Korrekturen, Plausibilität der Ersatzquellen)."""
    von, bis = str(k["backtest"]["daten_ab"]), str(k["backtest"]["gewertet_bis"])
    korrekturen = k["universum"].get("korrekturen") or []
    kurse, waehrungen, befunde, protokoll = {}, {}, {}, {"korrekturen": [], "ersatzquellen": {}}
    for e in k["universum"]["etfs"]:
        t = e["ticker"]
        quelle = e.get("kursquelle") or t
        if quelle != t:
            roh = lade_kurse_eur(quelle, von, bis)            # Ersatzquelle desselben Produkts, in EUR umgerechnet
            p = plausibilitaet_ersatzquelle(t, roh, von, bis)
            protokoll["ersatzquellen"][t] = {"quelle": quelle, **p}
            if p["median"] > 0.005:
                befunde.setdefault(t, []).append(f"[ersatzquelle] Median-Abweichung {p['median']:.2%} > 0,5 % gegenüber {t}")
        elif e.get("handelswaehrung", "EUR") != "EUR":
            roh = lade_kurse_eur(t, von, bis)
        else:
            roh = lade_kurse(t, von, bis)
        eigene = [c for c in korrekturen if c["ticker"] == t and c["regel"] != "dividende_ergaenzen"]
        for c in [c for c in korrekturen if c["ticker"] == t and c["regel"] == "dividende_ergaenzen"]:
            tag = roh.index[roh.index >= pd.Timestamp(str(c["datum"]))][0]
            roh = roh.copy()
            roh.loc[tag, "dividende"] = float(c["betrag_eur"])
            protokoll["korrekturen"].append(f"{t} {tag.date()}: Ausschüttung {float(c['betrag_eur']):.4f} € ergänzt ({c['grund']})")
        if eigene:
            roh, log = korrigiere(roh, eigene)
            protokoll["korrekturen"] += log
        for pl in [x for x in (k["universum"].get("plausibilitaet_ersatz") or []) if x["ticker"] == t]:
            erg = plausibilitaet_ausschuettend(pl, roh)
            protokoll.setdefault("ausschuettend", {})[t] = erg
            if not erg["bestanden"]:
                befunde.setdefault(t, []).append(f"[ersatzquelle] Rendite inkl. Dividenden {erg['differenz_pp']:+.3f} Pp. p.a. gegen {pl['vergleich']} "
                                                 f"(Grenze ±{erg['max_pp']}); Jahre ohne Ausschüttung: {erg['jahre_ohne_ausschuettung']}")
        kurse[t] = roh
        waehrungen[t] = e.get("handelswaehrung", "EUR")   # Kurse immer in EUR; Abrechnung über die Kasse der Handelswährung
        b = [x for x in pruefe_etf_kurse(roh) if not (quelle != t or e.get("handelswaehrung", "EUR") != "EUR") or "währung" not in x]
        if b:
            befunde.setdefault(t, []).extend(b)
    return kurse, waehrungen, befunde, protokoll


def main() -> int:
    arg = argparse.ArgumentParser()
    arg.add_argument("--nur-pruefen", action="store_true")
    arg.add_argument("--anlass", default="", help="z.B. Modellkorrektur (zählt nicht als neue Variante)")
    arg.add_argument("--vergleich", default="", help="CSV mit Kriterien eines früheren Laufs (alt gegen neu)")
    a = arg.parse_args()
    k = lade_konfiguration("technik")
    bt = lade_konfiguration("backtest")
    kurse, waehrungen, befunde, pruefprotokoll = lade_universum_kurse(k)
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
    for t, p in pruefprotokoll["ersatzquellen"].items():
        print(f"Ersatzquelle {p['quelle']} für {t}: {p['tage']} Tage mit Umsatz, Median-Abweichung {p['median']:.3%}, 95-%-Quantil {p['p95']:.3%}")
    for z in pruefprotokoll["korrekturen"]:
        print("Korrektur:", z)
    for etf, erg in pruefprotokoll.get("ausschuettend", {}).items():
        print(f"Plausibilität {etf}: Rendite inkl. Dividenden {erg['ersatz']:.3%} gegen {erg['vergleich']:.3%}, Differenz {erg['differenz_pp']:+.3f} Pp. "
              f"(Grenze ±{erg['max_pp']}) → {'bestanden' if erg['bestanden'] else 'NICHT bestanden'}; Jahre ohne Ausschüttung {erg['jahre_ohne_ausschuettung']}")
    ersatz_fehler = {t: b for t, b in befunde.items() if any("ersatzquelle" in x for x in b)}
    offen = {**offen, **ersatz_fehler}
    if offen:
        print(f"\nSPERRE: {len(offen)} Kursreihe(n) auffällig ohne dokumentierte Entscheidung – mit Jakob besprechen.")
        return 2
    umsetzung = k["erfolgskriterien"].get("buy_and_hold_umsetzung")
    if not umsetzung or umsetzung == "offen":
        print("\nSPERRE: Umsetzung des Buy-&-Hold-Vergleichs ist offen (erfolgskriterien.buy_and_hold_umsetzung).")
        return 2
    if a.nur_pruefen:
        return 0

    from tradingbot.backtest.kosten import Kostenmodell
    from tradingbot.backtest.simulation import simuliere
    from tradingbot.backtest.steuern import Steuerregeln

    fx = {}
    if any(w != "EUR" for w in waehrungen.values()):
        fx["USD"] = lade_kurse(lade_konfiguration("daten")["kurse"]["wechselkurse"].get("USD", "EURUSD=X"),
                               str(k["backtest"]["daten_ab"]), str(k["backtest"]["gewertet_bis"]))["close"]
    m = Marktdaten(kurse, waehrungen, fx)
    instrumente = [Instrument(e["ticker"], "etf", e["steuerart"], gebuehrenplan="EUR" if e.get("handelswaehrung", "EUR") != "EUR" else None)
                   for e in k["universum"]["etfs"]]
    sp = k["backtest"]
    bh_gewichte = {e["ticker"]: 1.0 / len(instrumente) for e in k["universum"]["etfs"]}

    def definition(name, regeln, regime):
        return TeilportfolioDefinition(f"technik_{name}", float(sp["kapital"]), SatelliteStrategie(regeln, kurse, k, regime=regime),
                                       instrumente, art="schatten", steuergruppe=sp["steuergruppe"], rolle="satellite")

    bh = TeilportfolioDefinition("buy_and_hold", float(sp["kapital"]), FesteGewichte(bh_gewichte, "Q"), instrumente,
                                 art="schatten", steuergruppe=sp["steuergruppe"], rolle="satellite")
    if umsetzung == "ohne_gebuehrenregel":          # gleiche Kosten, aber Käufe unter 125 € erlaubt
        from tradingbot.backtest.simulation import Ausfuehrungsregeln
        optionen_bh = {"regeln": Ausfuehrungsregeln(max_gebuehr_anteil=1.0)}
    elif umsetzung == "kostenfrei":                 # strengere Messlatte: ohne Kosten (wie das Kontrollportfolio)
        optionen_bh = {"kosten": Kostenmodell.ohne_kosten()}
    else:
        raise SystemExit(f"Unbekannte Umsetzung des Buy-&-Hold-Vergleichs: {umsetzung}")
    laeufe, ohne_kosten = {}, {}
    for name, (regeln, regime) in VARIANTEN.items():
        laeufe[name] = fuehre_lauf_aus(f"technik_{name}", [definition(name, regeln, regime)], m, start, ende, benchmark_ticker="IUSA.DE", konfig=bt)
        # gleiche Strategie ohne Kosten (keine Gebühren, kein Spread, keine Slippage, kein Tausch), vor Steuern; ganze Stücke bleiben
        ohne_kosten[name] = simuliere([definition(name, regeln, regime)], m, start, ende, kosten=Kostenmodell.ohne_kosten(),
                                      steuern=Steuerregeln.ohne_steuern(), konfig=bt)[f"technik_{name}"]
    lauf_bh = fuehre_lauf_aus("technik_buy_and_hold", [bh], m, start, ende, benchmark_ticker="IUSA.DE", konfig=bt, **optionen_bh)

    rf = lade_makro(bt.get("risikofreier_zins", "ECBDFR"))
    abschnitte = [("gesamt", start, ende)] + [(f"Hälfte {i + 1}", x, y) for i, (x, y) in enumerate(haelften(start, ende, int(sp["haelften"])))]
    grenze_dd = float(k["erfolgskriterien"]["max_drawdown_mindestens"])

    def kz(werte, von, bis):
        w = werte.loc[von:bis]
        return kennzahlen(w, None, risikofreie_tagesrendite(rf, w.index))

    bh_wert = lauf_bh.ergebnisse["buy_and_hold"].wert
    zeilen = []
    for name, lauf in laeufe.items():
        for art, e in (("nach Kosten", lauf.ergebnisse[f"technik_{name}"]), ("ohne Kosten", ohne_kosten[name])):
            for abschnitt, von, bis in abschnitte:
                s_, b = kz(e.wert, von, bis), kz(bh_wert, von, bis)
                zeilen.append({"variante": name, "art": art, "abschnitt": abschnitt, "cagr": s_["cagr"], "sharpe": s_["sharpe"],
                               "max_dd": s_["max_drawdown"], "bh_cagr": b["cagr"], "bh_sharpe": b["sharpe"], "bh_max_dd": b["max_drawdown"],
                               "sharpe_ok": s_["sharpe"] >= b["sharpe"], "dd_ok": s_["max_drawdown"] >= grenze_dd})
    t = pd.DataFrame(zeilen)
    bewertung, ohne_kosten_sharpe = {}, {}
    for name in VARIANTEN:
        h = t[(t.variante == name) & (t.art == "nach Kosten") & (t.abschnitt != "gesamt")]
        bewertung[name] = bool(h["sharpe_ok"].all() and h["dd_ok"].all())
        h0 = t[(t.variante == name) & (t.art == "ohne Kosten") & (t.abschnitt != "gesamt")]
        ohne_kosten_sharpe[name] = bool(h0["sharpe_ok"].all())
    zweig = "b" if (ohne_kosten_sharpe["crossover"] or ohne_kosten_sharpe["momentum"]) else "a"

    def gescheitert(e) -> tuple[int, int, float]:
        v = e.verworfen
        stueck = int(v["grund"].str.startswith("Stückpreis").sum()) if len(v) else 0
        regel = int(v["grund"].str.startswith("Gebühren").sum()) if len(v) else 0
        invest = float((1 - e.werte["cash"] / e.werte["wert"]).mean())
        return stueck, regel, invest

    # Varianten zählen (Neuberechnung mit Anlass zählt nicht als neue Variante)
    ziel = PROJEKT_WURZEL / "daten" / "technik"
    ziel.mkdir(parents=True, exist_ok=True)
    datei = ziel / "varianten.csv"
    alt = pd.read_csv(datei) if datei.exists() else pd.DataFrame()
    neu = pd.DataFrame([{"datum": datetime.now().isoformat(timespec="seconds"), "variante": n, "git": laeufe[n].meta["git"].get("commit"),
                         "lauf": laeufe[n].pfad.name if laeufe[n].pfad else "", "bestanden": bewertung[n], "anlass": a.anlass} for n in VARIANTEN])
    varianten = pd.concat([alt, neu], ignore_index=True)
    varianten.to_csv(datei, index=False)

    # Bericht
    pz = lambda x: f"{x:.2%}".replace(".", ",")  # noqa: E731
    zahl = lambda x: f"{x:.2f}".replace(".", ",")  # noqa: E731
    ok = lambda b: "ja" if b else "**nein**"  # noqa: E731
    text = [f"# Satellite-Strategien der Technik-Engine – gewertete Backtests" + (f" ({a.anlass})" if a.anlass else ""), "",
            f"Stand {datetime.now():%d.%m.%Y %H:%M}. Zeitraum {start.date()} bis {ende.date()}, Kapital {sp['kapital']:,.0f} € (Schatten), "
            f"{len(instrumente)} ETFs/ETCs laut `config/technik.yaml`. Getestete Varianten bisher: {varianten['variante'].nunique()}"
            + (" (diese Neuberechnung zählt nicht als neue Variante)." if a.anlass else "."), "",
            f"Buy & Hold: alle ETFs gleich gewichtet, quartalsweise, Umsetzung `{umsetzung}` (Entscheidung Jakob 03.11.2026).", "",
            "## Daten", ""]
    text.append("- Universum: " + ", ".join(f"{e['ticker']} ({e['klasse']})" for e in k["universum"]["etfs"]))
    for etf, pp in pruefprotokoll["ersatzquellen"].items():
        text.append(f"- **{etf} über Ersatzquelle {pp['quelle']}** (gleicher Fonds, gleiche Anteilsklasse, in EUR umgerechnet): an {pp['tage']} Tagen "
                    f"mit Xetra-Umsatz Median-Abweichung {pz(pp['median'])} (Grenze 0,5 %, bestanden), 95-%-Quantil {pz(pp['p95'])}. "
                    "Abrechnung über die USD-Kasse (Netto-Tausch), Gebühr nach dem Xetra-Plan.")
    for z in pruefprotokoll["korrekturen"]:
        text.append(f"- Korrektur: {z}")
    for etf, erg in pruefprotokoll.get("ausschuettend", {}).items():
        text.append(f"- **Plausibilität {etf}** (inkl. Dividenden) gegen den ersetzten ETF: {pz(erg['ersatz'])} gegen {pz(erg['vergleich'])} p.a., "
                    f"Differenz {erg['differenz_pp']:+.3f} Pp. (Grenze ±{erg['max_pp']}, bestanden); nur Kurs {pz(erg['nur_kurs'])}. "
                    "Die Prüfung rechnet vor Steuern (Total-Return-Index, Dividenden reinvestiert, ohne Steuern und Kosten). Im Backtest "
                    "gehen die Dividenden als Zahlung in die Kasse und werden als Aktienfonds versteuert (Teilfreistellung 30 %).")
    text += ["- Xetra-Gold: Zwei Tage (26. und 29.06.2017) mit Schluss über dem Tageshoch (0,14 % und 0,45 %) unverändert "
             "(Entscheidung Jakob 03.11.2026). Steuer konservativ mit Abgeltungsteuer (§ 23 EStG offen im Steuermodul).", "",
             "## Entscheidungsbaum (docs/TECHNIK.md)", "",
             "| Variante | Sharpe ≥ B&H ohne Kosten in beiden Hälften | Kriterien nach Kosten bestanden |", "| --- | --- | --- |"]
    text += [f"| {n} | {ok(ohne_kosten_sharpe[n])} | {ok(bewertung[n])} |" for n in VARIANTEN]
    text += ["", f"**Zweig {zweig}):** " + ("Weder Crossover noch Momentum erreichen ohne Kosten den Sharpe von Buy & Hold in beiden Hälften: "
             "Die Technik-Engine ist kein Renditebaustein. Echtes Geld bleibt im Core; Crossover und Momentum laufen im Paper Trading als "
             "Schatten vorwärts mit." if zweig == "a" else
             "Mindestens eine von Crossover und Momentum erreicht ohne Kosten den Sharpe von Buy & Hold in beiden Hälften: Mindestkapital "
             "aus dem Kostenbudget (höchstens 0,5 % p.a.) ableiten und einmal neu rechnen (neue Variante)."), "",
             "## Kennzahlen vor Steuern", "",
             "| Variante | Art | Abschnitt | Rendite p.a. | Sharpe | max. Drawdown | B&H Rendite | B&H Sharpe | B&H Drawdown | Sharpe ≥ B&H | DD ≥ −20 % |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in t.itertuples():
        text.append(f"| {r.variante} | {r.art} | {r.abschnitt} | {pz(r.cagr)} | {zahl(r.sharpe)} | {pz(r.max_dd)} | {pz(r.bh_cagr)} | {zahl(r.bh_sharpe)} | "
                    f"{pz(r.bh_max_dd)} | {ok(r.sharpe_ok)} | {ok(r.dd_ok)} |")
    text += ["", "## Handel, Kosten, Investitionsgrad", "",
             "| Variante | Trades | Kosten | Investitionsgrad (Mittel) | gescheitert am Stückpreis | gescheitert an der 125-€-Regel | Steuern gezahlt | Rendite nach Verkauf und Steuern |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for name, lauf in {**laeufe, "buy_and_hold": lauf_bh}.items():
        kk = lauf.kennzahlen.iloc[0]
        e = next(iter(lauf.ergebnisse.values()))
        stueck, regel, invest = gescheitert(e)
        text.append(f"| {name} | {int(kk['trades'])} | {kk['kosten']:,.0f} € | {pz(invest)} | {stueck} | {regel} | {kk['steuern_gezahlt']:,.0f} € | "
                    f"{pz(kk['cagr_nach_verkauf_und_steuern'])} |")
    text += ["", "Gescheiterte Orders zählen je Tag und ETF; bei stehendem Signal wird ein Kauf täglich erneut versucht.", "",
             "## Investitionsgrad je ETF (gekaufter Wert / Zielwert neuer Positionen, Rundung auf ganze Stücke)", "",
             "| ETF | " + " | ".join(laeufe) + " |", "| --- |" + " --- |" * len(laeufe)]
    for etf in [e["ticker"] for e in k["universum"]["etfs"]]:
        zellen = []
        for name, lauf in laeufe.items():
            tr = next(iter(lauf.ergebnisse.values())).trades
            kauf = tr[(tr.ticker == etf) & (tr.richtung > 0) & tr.zielwert.notna()]
            zellen.append(f"{pz((kauf.kurswert / kauf.zielwert).mean())} ({len(kauf)})" if len(kauf) else "–")
        text.append(f"| {etf} | " + " | ".join(zellen) + " |")
    text += ["", "In Klammern: Zahl der Käufe."]
    if a.vergleich:
        vorher = pd.read_csv(a.vergleich)
        text += ["", f"## Vergleich mit dem früheren Lauf (`{a.vergleich}`), nach Kosten", "",
                 "| Variante | Abschnitt | Rendite p.a. vorher | jetzt | Sharpe vorher | jetzt | max. DD vorher | jetzt |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
        jetzt = t[t.art == "nach Kosten"].set_index(["variante", "abschnitt"])
        for r in vorher.itertuples():
            if (r.variante, r.abschnitt) in jetzt.index:
                j = jetzt.loc[(r.variante, r.abschnitt)]
                text.append(f"| {r.variante} | {r.abschnitt} | {pz(r.cagr)} | {pz(j['cagr'])} | {zahl(r.sharpe)} | {zahl(j['sharpe'])} | {pz(r.max_dd)} | {pz(j['max_dd'])} |")
    text += ["", "Ablage der Läufe: " + ", ".join(f"`{l.pfad.relative_to(PROJEKT_WURZEL)}`" for l in [*laeufe.values(), lauf_bh] if l.pfad)]
    bericht = "\n".join(text)
    ordner = PROJEKT_WURZEL / "docs" / "berichte"
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / f"{datetime.now():%Y-%m-%d_%H%M}_technik_satellite.md").write_text(bericht, encoding="utf-8")
    t.to_csv(ziel / "kriterien.csv", index=False)
    print(bericht)
    return 0


if __name__ == "__main__":
    sys.exit(main())
