r"""Abschluss-Backtest Phase 2: Gesamtdepot (Realbuch) mit eingehängtem Risk-Manager gegen den MSCI ACWI IMI.

Aufruf:  .venv\Scripts\python tools\backtest_phase2.py
Festgeschrieben vor dem Lauf: docs/PHASE2.md, config/backtest.yaml `phase2_gesamtdepot` (03.11.2026).
Ergebnis: docs/berichte/<datum>_phase2_gesamtdepot.md, Tabellen in daten/backtests/<zeitstempel>_phase2_gesamtdepot/.
"""
import copy
import json
import math
import sys
import warnings
from datetime import datetime

import pandas as pd

from tradingbot.backtest.kosten import Kostenmodell
from tradingbot.backtest.marktdaten import Instrument, Marktdaten
from tradingbot.backtest.simulation import Ausfuehrungsregeln, TeilportfolioDefinition, simuliere
from tradingbot.backtest.strategie import SparplanKern
from tradingbot.daten.kurse import echte_anteilspreise, lade_kurse
from tradingbot.daten.makro import lade_makro
from tradingbot.kennzahlen.performance import cagr, drawdown, kennzahlen, risikofreie_tagesrendite, xirr, zeitgewichtete_rendite
from tradingbot.kennzahlen.rendite import total_return_index
from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration
from tradingbot.risiko.manager import Kontext, OrderVorschlag, RiskManager

warnings.simplefilter("ignore")


def main() -> int:
    bt = lade_konfiguration("backtest")
    p = bt["phase2_gesamtdepot"]
    krit = p["kriterien"]
    etf = p["etf"]
    von, bis = pd.Timestamp(str(p["von"])), pd.Timestamp(str(p["bis"]))
    roh = lade_kurse(etf, von - pd.Timedelta(days=60), bis)
    kurse = echte_anteilspreise(roh, etf, lade_konfiguration("daten").get("kapitalmassnahmen") or [])
    m = Marktdaten({etf: kurse})
    tage = m.kalender[(m.kalender >= von) & (m.kalender <= bis)]
    start = tage[0]
    monate = pd.Series(tage, index=tage).groupby(tage.to_period("M")).first()
    einzahlungen = pd.Series(float(p["einzahlung_eur"]), index=pd.DatetimeIndex([d for d in monate if d > start]))
    kosten = Kostenmodell.aus_konfig(bt)
    gebuehr = lambda n, w: kosten.gebuehren_eur("EUR", n, w, 1.0)   # noqa: E731

    # Risk-Manager mit den Regeln des Realbuchs; Bot-Budget = Start plus Einzahlungen bis zum Tag
    rm = RiskManager.aus_konfig()
    rm.kosten = kosten
    buch = p["risk_buch"]
    eingezahlt = einzahlungen.cumsum()

    def risk(lauf, tag, ticker, richtung, stueck, letzter_kurs, limit):
        budget = float(p["start_eur"]) + float(eingezahlt.loc[:tag].iloc[-1]) if len(eingezahlt.loc[:tag]) else float(p["start_eur"])
        rm.b = copy.deepcopy(rm.b)
        rm.b["buecher"][buch]["budget_eur"] = budget
        wert = lauf.portfolio.cash + sum(s * float(m.schluss.loc[:tag].iloc[-2][t]) for t, s in lauf.portfolio.bestand().items())
        v = OrderVorschlag(f"bt-{tag:%Y%m%d}-{ticker}-{richtung}", tag, buch, ticker, richtung, int(stueck), letzter_kurs, "etf", limit=limit)
        k = Kontext(buch=buch, kasse=lauf.portfolio.cash, wert=wert, bestand={t: int(s) for t, s in lauf.portfolio.bestand().items()},
                    orders_heute=lauf.orders_je_tag.get(tag, 0), kasse_je_waehrung={"EUR": lauf.portfolio.cash})
        return rm.pruefe(v, k)

    konfig = copy.deepcopy(bt)
    konfig["steuern"]["pauschbetrag_anteil"] = {**konfig["steuern"].get("pauschbetrag_anteil", {}), "depot": 1.0, "zwilling": 1.0}
    real = TeilportfolioDefinition("realbuch", float(p["start_eur"]), SparplanKern(etf, gebuehr, aufschlag=float(p["kauf_limit_aufschlag"])),
                                   [Instrument(etf, "etf")], steuergruppe="depot", einzahlungen=einzahlungen,
                                   kauf_limit_aufschlag=float(p["kauf_limit_aufschlag"]), risk_pruefung=risk)
    zwilling = TeilportfolioDefinition("zwilling", float(p["start_eur"]), SparplanKern(etf, gebuehr, mit_limit=False), [Instrument(etf, "etf")],
                                       steuergruppe="zwilling", einzahlungen=einzahlungen)
    erg = simuliere([real, zwilling], m, start, bis, kosten=kosten, regeln=Ausfuehrungsregeln.aus_konfig(bt), konfig=konfig)
    r, z = erg["realbuch"], erg["zwilling"]

    # --- Prüfung 1: Regeln eingehalten -------------------------------------------------------------------------------
    pruef1 = []
    if (r.werte["cash"] < -1e-6).any():
        pruef1.append("negative Kasse")
    if (r.bestaende < -1e-9).any().any():
        pruef1.append("Short-Bestand")
    stueck_aus_trades = r.trades.assign(s=r.trades.richtung * r.trades.stueck).groupby("datum")["s"].sum().reindex(r.bestaende.index).fillna(0).cumsum()
    if len(r.bestaende.columns) and (stueck_aus_trades - r.bestaende[etf]).abs().max() > 1e-6:
        pruef1.append("Bestand weicht vom Trade-Protokoll ab")
    if r.meta["risk_geprueft"] != len(r.trades) + len(r.meta["vetos"]):
        pruef1.append(f"nicht jede Order lief durch den Risk-Manager ({r.meta['risk_geprueft']} Prüfungen, {len(r.trades)} Trades, {len(r.meta['vetos'])} Vetos)")
    if pruef1:
        print("ABBRUCH, Prüfung 1 verletzt:", "; ".join(pruef1))
        return 2

    # --- Renditen (TWR) und XIRR --------------------------------------------------------------------------------------
    e_r, e_z = r.werte["einzahlung"], z.werte["einzahlung"]
    def ebenen(x):
        nach_verkauf = x.wert_nach_steuern.copy()
        nach_verkauf.iloc[-1] = float(x.meta["wert_nach_liquidation_und_steuern"])
        return {"vor Steuern": x.wert, "nach Steuern": x.wert_nach_steuern, "nach Verkauf und Steuern": nach_verkauf}
    idx = total_return_index(kurse.loc[start:bis])
    idx = idx / idx.iloc[0]
    rf = risikofreie_tagesrendite(lade_makro(bt.get("risikofreier_zins", "ECBDFR")), tage)
    zeilen, twr = [], {}
    for name, x, e in (("Realbuch", r, e_r), ("Zwilling", z, e_z)):
        for ebene, w in ebenen(x).items():
            t = zeitgewichtete_rendite(w, e)
            twr[(name, ebene)] = t
            k = kennzahlen(t, None, rf)
            zahl = pd.concat([pd.Series({start: -float(p["start_eur"])}), -e[e > 0], pd.Series({w.index[-1]: float(w.iloc[-1])})])
            zahl = zahl.groupby(level=0).sum()
            zeilen.append({"reihe": name, "ebene": ebene, "twr_pa": cagr(t), "xirr": xirr(zahl), "vola": k["volatilitaet"], "sharpe": k["sharpe"],
                           "max_dd": k["max_drawdown"], "endwert": float(w.iloc[-1])})
    ki = kennzahlen(idx, None, rf)
    zeilen.append({"reihe": "MSCI ACWI IMI (SPYI, kostenfrei, TR)", "ebene": "Index", "twr_pa": cagr(idx), "xirr": float("nan"),
                   "vola": ki["volatilitaet"], "sharpe": ki["sharpe"], "max_dd": ki["max_drawdown"], "endwert": float("nan")})
    t = pd.DataFrame(zeilen)
    get = lambda n, eb: float(t[(t.reihe == n) & (t.ebene == eb)]["twr_pa"].iloc[0])   # noqa: E731
    abw2 = (get("Realbuch", "vor Steuern") - cagr(idx)) * 100
    abw3a = (get("Realbuch", "nach Steuern") - get("Zwilling", "nach Steuern")) * 100
    abw3b = (get("Realbuch", "nach Verkauf und Steuern") - get("Zwilling", "nach Verkauf und Steuern")) * 100
    ok2 = abs(abw2) <= float(krit["max_abweichung_index_pp"])
    ok3 = abs(abw3a) <= float(krit["max_abweichung_zwilling_pp"]) and abs(abw3b) <= float(krit["max_abweichung_zwilling_pp"])
    # Prüfung 4: Notbremse (12 Monate TWR-Rückstand gegen ACWI IMI)
    tw = twr[("Realbuch", "vor Steuern")]
    rueck = (tw / tw.shift(252) - idx.reindex(tw.index) / idx.reindex(tw.index).shift(252)).dropna() * 100
    review_tage = int((rueck < -float(krit["notbremse_pp"])).sum())
    ok4 = review_tage == 0

    # Verfallene Limits und ungenutzte Kasse
    vf = r.meta["verfallen"]
    kauf_tage = pd.DatetimeIndex(r.trades[r.trades.richtung > 0]["datum"])
    wartetage = [int(((kauf_tage[kauf_tage > d][0] if (kauf_tage > d).any() else tage[-1]) - d).days) for d in vf["datum"]] if len(vf) else []
    kassenquote = (r.werte["cash"] / r.werte["wert"])
    invest = 1 - kassenquote
    kosten_r = r.kosten_gesamt

    # --- Ablage und Bericht ----------------------------------------------------------------------------------------------
    stempel = datetime.now()
    ordner = PROJEKT_WURZEL / "daten" / "backtests" / f"{stempel:%Y%m%dT%H%M%S}_phase2_gesamtdepot"
    ordner.mkdir(parents=True, exist_ok=True)
    r.trades.to_csv(ordner / "trades_realbuch.csv", index=False)
    z.trades.to_csv(ordner / "trades_zwilling.csv", index=False)
    r.verworfen.to_csv(ordner / "verworfen_realbuch.csv", index=False)
    r.werte.to_csv(ordner / "werte_realbuch.csv")
    t.to_csv(ordner / "kennzahlen.csv", index=False)
    (ordner / "konfig.json").write_text(json.dumps(p, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    pz = lambda x: "–" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.2%}".replace(".", ",")  # noqa: E731
    zahl = lambda x, n=2: f"{x:,.{n}f}".replace(",", "X").replace(".", ",").replace("X", ".")  # noqa: E731
    ok = lambda b: "**bestanden**" if b else "**verfehlt**"  # noqa: E731
    vetos = r.meta["vetos"]
    text = [f"# Phase 2 – Abschluss-Backtest Gesamtdepot (Realbuch mit Risk-Manager)", "",
            f"Stand {stempel:%d.%m.%Y %H:%M}. Zeitraum {start.date():%d.%m.%Y} bis {tage[-1].date():%d.%m.%Y}. Start {zahl(p['start_eur'], 0)} €, "
            f"danach {len(einzahlungen)} Einzahlungen à {zahl(p['einzahlung_eur'], 0)} € am ersten Handelstag des Monats "
            f"(eingezahlt gesamt {zahl(p['start_eur'] + einzahlungen.sum(), 0)} €). Festgeschrieben vor dem Lauf: `docs/PHASE2.md`.", "",
            f"Anteilspreise: SPYI-Split 25:1 am 23.02.2026 rückgängig gemacht (echte Preise {zahl(float(kurse['close'].loc[start:bis].min()))}–"
            f"{zahl(float(kurse['close'].loc[start:bis].max()))} €), damit ganze Stücke und Mindestorder real geprüft werden.", "",
            "## Kriterien", "", "| Nr. | Prüfung | Ergebnis | Wert |", "| --- | --- | --- | --- |",
            f"| 1 | Regeln eingehalten (Risk-Manager vor jeder Order, keine negative Kasse, kein Short, Bestand = Trades) | **bestanden** | "
            f"{r.meta['risk_geprueft']} Prüfungen, {len(r.trades)} Käufe, {len(vetos)} Vetos |",
            f"| 2 | TWR vor Steuern höchstens {zahl(krit['max_abweichung_index_pp'], 1)} Pp. vom kostenfreien ACWI IMI | {ok(ok2)} | {zahl(abw2)} Pp. p.a. |",
            f"| 3 | TWR nach Steuern und nach Verkauf höchstens {zahl(krit['max_abweichung_zwilling_pp'], 1)} Pp. vom Zwilling | {ok(ok3)} | "
            f"{zahl(abw3a)} / {zahl(abw3b)} Pp. p.a. |",
            f"| 4 | Core-Notbremse nie ausgelöst (12 Monate > {zahl(krit['notbremse_pp'], 0)} Pp. hinter ACWI IMI) | {ok(ok4)} | {review_tage} Tage im Review |",
            "| 5 | Bericht | **bestanden** | diese Datei |", "",
            f"Gesamt: {'alle Kriterien bestanden – Phase 2 sauber gelaufen.' if ok2 and ok3 and ok4 else 'mindestens ein Kriterium verfehlt – mit Jakob besprechen.'}", "",
            "## Kennzahlen (zeitgewichtet; XIRR = geldgewichtet)", "",
            "| Reihe | Ebene | TWR p.a. | XIRR | Volatilität | Sharpe | max. Drawdown | Endwert |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for row in t.itertuples():
        text.append(f"| {row.reihe} | {row.ebene} | {pz(row.twr_pa)} | {pz(row.xirr)} | {pz(row.vola)} | {zahl(row.sharpe)} | {pz(row.max_dd)} | "
                    f"{'–' if math.isnan(row.endwert) else zahl(row.endwert) + ' €'} |")
    text += ["", "## Ablauf", "",
             f"- Käufe: {len(r.trades)} (Zwilling {len(z.trades)}), im Mittel {zahl(r.trades.stueck.mean(), 1)} Stück zu {zahl(r.trades.kurswert.mean())} €.",
             f"- Verfallene Limits: {len(vf)}; Kasse im Mittel zum Zeitpunkt des Verfalls {zahl(vf['kasse'].mean()) if len(vf) else '–'} €, "
             f"ungenutzt im Mittel {zahl(sum(wartetage) / len(wartetage), 1) if wartetage else '–'} Kalendertage bis zum nächsten Kauf.",
             f"- Vetos des Risk-Managers: {len(vetos)}" + (": " + "; ".join(vetos['gruende'].value_counts().head(5).index) if len(vetos) else "") + ".",
             f"- Verworfene Orders gesamt: {len(r.verworfen)} (Gründe: {r.verworfen['grund'].str.replace(r'[\\d.,]+', 'x', regex=True).value_counts().head(4).to_dict() if len(r.verworfen) else {}}).",
             f"- Kassenquote: im Mittel {pz(float(kassenquote.mean()))}, höchstens {pz(float(kassenquote.max()))} (am {kassenquote.idxmax().date():%d.%m.%Y}); "
             f"Investitionsgrad im Mittel {pz(float(invest.mean()))}.",
             f"- Kosten: {zahl(kosten_r)} € (Zwilling {zahl(z.kosten_gesamt)} €); Steuern gezahlt {zahl(r.meta['steuern_gezahlt'])} € "
             f"(Zwilling {zahl(z.meta['steuern_gezahlt'])} €), Steuer bei fiktivem Verkauf {zahl(r.meta['liquidationssteuer'])} €.",
             "", f"Ablage: `{ordner.relative_to(PROJEKT_WURZEL)}`."]
    bericht = "\n".join(text)
    ziel = PROJEKT_WURZEL / "docs" / "berichte" / f"{stempel:%Y-%m-%d}_phase2_gesamtdepot.md"
    ziel.write_text(bericht, encoding="utf-8")
    print(bericht)
    return 0


if __name__ == "__main__":
    sys.exit(main())
