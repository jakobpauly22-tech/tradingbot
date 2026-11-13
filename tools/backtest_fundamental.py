r"""Erster gewerteter Backtest des Fundamental-Schattenportfolios (Sitzung 4, Regeln vom 02.11.2026).

Aufruf:  .venv\Scripts\python tools\backtest_fundamental.py
Voraussetzung: Cache „fundamental/scores“ (tools/auswertung_scores.py).
Ergebnis: daten/backtests/<zeitstempel>_fundamental_schatten/ (Lauf mit Steuern samt Ablage) plus
fundamental_bericht.md; Kopie unter daten/fundamental/backtest_bericht.md; Zeile in daten/fundamental/varianten.csv.

Zeitraum: gewerteter Backtest 01.10.2016 bis 31.12.2024 (config/fundamental.yaml `backtest`); Tresor bleibt zu.
Erfolgskriterien (vor dem Lauf festgeschrieben, docs/FUNDAMENTAL.md): (a) Rendite p.a. nach Kosten vor Steuern ≥
Kontrollportfolio; (b) Sharpe nach Kosten ≥ Sharpe S&P 500 ohne Finanzwerte (EUR) und maximaler Drawdown höchstens
5 Prozentpunkte schlechter.
"""
import shutil
import sys
import warnings
from collections import Counter
from datetime import datetime

import pandas as pd

from tradingbot.backtest.bericht import fuehre_lauf_aus
from tradingbot.backtest.marktdaten import Delisting, Instrument, Marktdaten
from tradingbot.backtest.simulation import TeilportfolioDefinition, simuliere
from tradingbot.backtest.steuern import Steuerregeln
from tradingbot.daten.cache import standard_cache
from tradingbot.daten.delisting import delisting_grund_mit_korrektur, delisting_rendite, einreichungen
from tradingbot.daten.fehlerschwelle import Fehlerschwelle, FehlerschwelleUeberschritten, laut_melden
from tradingbot.daten.index_nachbau import ABNAHME_ZEITRAUM
from tradingbot.daten.kurse import in_euro, lade_kurse, lade_kurse_eur
from tradingbot.daten.makro import lade_makro
from tradingbot.daten.sec import SecClient
from tradingbot.daten.sp500_nachbau import lade_benchmark_sp500_ohne_finanzwerte, lade_firmendaten
from tradingbot.daten.universum import lade_sic_historien, lade_universum
from tradingbot.engines.fundamental.filter import anwenden as filter_anwenden
from tradingbot.engines.fundamental.filter import piotroski_fuer_filter
from tradingbot.engines.fundamental.gesamtscore import gesamtscore
from tradingbot.engines.fundamental.multiples import sic_division
from tradingbot.engines.fundamental.schatten import FundamentalSchatten, kontrollportfolio
from tradingbot.kennzahlen.performance import kennzahlen, risikofreie_tagesrendite
from tradingbot.kennzahlen.rendite import total_return_index
from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration

warnings.simplefilter("ignore")
NAME = "fundamental_schatten"
# Neuberechnung derselben Variante (zählt nicht als neue Variante, Jakob 02.11.2026)
ANLASS = "Kostenmodell Währungstausch: USD-Kasse, Netto-Tausch statt je Order"
VARIANTE = "Variante 1: Regeln vom 02.11.2026 (Gesamtscore 50/50, Puffer 30, Drift 2,5–7,5 %, SIC2 ≤ 25 %)"


def _nn(x):
    return None if pd.isna(x) else x


def ranglisten_aus_scores(scores: pd.DataFrame, konfig: dict) -> tuple[dict, pd.DataFrame]:
    """Wendet die Filter mit dem aktuellen Code an und bildet je Stichtag die Gesamtscore-Rangliste."""
    b = scores[~scores["veraltet"].astype(bool)].copy()
    filt = []
    for r in b.itertuples():
        p = {"wert": _nn(r.piotroski), "wert_hochgerechnet": _nn(r.piotroski_hochgerechnet),
             "hochgerechnet": not pd.isna(r.piotroski_hochgerechnet), "anzahl_signale": r.piotroski_n}
        a = None if pd.isna(r.altman) else {"wert": r.altman, "zone": r.altman_zone}
        e = filter_anwenden(sic=int(r.sic), piotroski=p, altman=a, beneish={"wert": _nn(r.beneish)}, cfo_t=_nn(r.cfo_t), konfig=konfig)
        filt.append((e.ausgeschlossen, piotroski_fuer_filter(p), p["hochgerechnet"], any("Warnhinweis" in h for h in e.hinweise)))
    b["ausgeschlossen"], b["piotroski_filter"], b["piotroski_hoch"], b["z2_warnhinweis"] = zip(*filt)
    b["piotroski_filter"] = b["piotroski_filter"].astype(float)
    ranglisten = {}
    for tag, g in b[~b["ausgeschlossen"]].groupby("stichtag"):
        r = gesamtscore(g[["firma", "sic", "piotroski_filter", "accruals", "ep", "ebit_ev", "piotroski_hoch", "z2_warnhinweis"]], konfig)
        r["ticker"] = "CIK" + r["firma"].astype(str)
        ranglisten[pd.Timestamp(tag)] = r
    return ranglisten, b


def argumente(argv=None):
    """Neuberechnung derselben Variante (keine neue Variante), z. B. Datenkorrektur Piotroski EQ_OFFER (Jakob 13.11.2026):
    --scores scores_eq_offer --name fundamental_schatten_eq_offer --anlass "…" --kopie backtest_bericht_eq_offer.md"""
    import argparse
    a = argparse.ArgumentParser(description="Backtest Fundamental-Schattenportfolio (Variante 1)")
    a.add_argument("--scores", default="scores", help="Schlüssel im Cache „fundamental“ (tools/auswertung_scores.py)")
    a.add_argument("--name", default=NAME, help="Name des Laufs (Ordner unter daten/backtests/)")
    a.add_argument("--anlass", default=ANLASS, help="Anlass der Neuberechnung (Spalte in varianten.csv)")
    a.add_argument("--kopie", default="backtest_bericht.md", help="Dateiname der Berichtskopie unter daten/fundamental/")
    return a.parse_args(argv)


def main(argv=None) -> int:
    global NAME, ANLASS
    arg = argumente(argv)
    NAME, ANLASS = arg.name, arg.anlass
    konfig = lade_konfiguration("fundamental")
    konfig_bt = lade_konfiguration("backtest")
    sp = konfig["schattenportfolio"]
    start, ende = pd.Timestamp(str(konfig["backtest"]["gewertet_ab"])), pd.Timestamp(str(konfig["backtest"]["gewertet_bis"]))
    cache = standard_cache()
    scores, scores_meta = cache.lesen("fundamental", arg.scores)
    if scores is None:
        raise SystemExit("Cache fundamental/scores fehlt: tools/auswertung_scores.py ausführen")
    scores = scores[(scores["stichtag"] >= start) & (scores["stichtag"] <= ende)]
    ranglisten, bewertbar = ranglisten_aus_scores(scores, konfig)
    firmen = sorted({int(t[3:]) for r in ranglisten.values() for t in r["ticker"]})
    print(f"{len(ranglisten)} Stichtage, {len(firmen)} Firmen in mindestens einer Rangliste")

    universum, _ = lade_universum()
    status = pd.read_csv(PROJEKT_WURZEL / "daten" / "universum" / "kursstatus.csv").set_index("index")
    daten = lade_firmendaten(universum, status, lade_sic_historien(universum), mitglied_ab=ABNAHME_ZEITRAUM[0])
    namen = {int(z["cik"]): z["ticker"] for _, z in daten.relevant.sort_values("von", na_position="first").iterrows() if pd.notna(z["cik"])}

    # Kurse in Euro (USD-Werte mit EURUSD=X), ab einem Vorlauf für die Bewertung am ersten Stichtag
    von = start - pd.Timedelta(days=120)
    fx = lade_kurse(lade_konfiguration("daten")["kurse"]["wechselkurse"].get("USD", "EURUSD=X"), von - pd.Timedelta(days=10), ende)["close"]
    kurse, waehrungen, letzter_tag = {}, {}, {}
    for firma in firmen:
        k = daten.kurse.get(firma)
        if k is None or k.empty:
            continue
        letzter_tag[firma] = k.index.max()
        k = k.loc[von:ende]
        if k.empty:
            continue
        kurse[f"CIK{firma}"] = in_euro(k, "USD", fx)
        waehrungen[f"CIK{firma}"] = "USD"
    benchmarks = {}
    for t in ["SPYI.DE", "SXR8.DE"] + list(sp.get("zusatzbenchmarks", [])):
        k = lade_kurse_eur(t, von, ende)
        benchmarks[t] = k
        waehrungen[t] = k.attrs.get("originalwaehrung", "EUR")

    # Delistings: Kursreihe endet vor dem Ende des Zeitraums (Grund aus SEC-Einreichungen, Regel daten/delisting.py)
    us_ende = max(letzter_tag.values())
    client, korrekturen = SecClient(), lade_konfiguration("universum_korrekturen").get("delisting", [])
    delistings, schwelle = {}, Fehlerschwelle("Backtest: Delisting-Gründe")
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

    m = Marktdaten({**kurse, **benchmarks}, waehrungen, {"USD": fx}, delistings=delistings)
    instrumente = [Instrument(t, "aktie") for t in kurse]
    us_tage = pd.DatetimeIndex(sorted(set().union(*[k.index for k in kurse.values()])))

    def definition():
        return TeilportfolioDefinition(NAME, float(sp["kapital"]), FundamentalSchatten(ranglisten, konfig, m.kalender, us_tage), instrumente,
                                       art="schatten", steuergruppe=sp["steuergruppe"], rolle="core")

    # 1) mit Steuern (drei Ebenen, Ablage mit Konfiguration, Git- und Datenstand)
    d_steuer = definition()
    lauf = fuehre_lauf_aus(NAME, [d_steuer], m, start, ende, benchmark_ticker="SPYI.DE", konfig=konfig_bt)
    mit_steuern = lauf.ergebnisse[NAME]
    # 2) nach Kosten, vor Steuern (ohne Quellensteuer; Grundlage der Kriterien)
    d_vor = definition()
    vor = simuliere([d_vor], m, start, ende, steuern=Steuerregeln.ohne_steuern(), konfig=konfig_bt)[NAME]
    tage = vor.wert.index

    kontroll, kontroll_stat = kontrollportfolio(ranglisten, kurse, m.kalender, delistings, float(sp["kapital"]), ende, us_tage)
    sp_ex = lade_benchmark_sp500_ohne_finanzwerte()["index_eur"]
    reihen = {
        "Schattenportfolio nach Kosten, vor Steuern": vor.wert,
        "Schattenportfolio nach laufenden Steuern": mit_steuern.wert_nach_steuern,
        "Kontrollportfolio (ohne Kosten, vor Steuern)": kontroll,
        "S&P 500 ohne Finanzwerte (EUR, TR)": sp_ex,
        "S&P 500 (SXR8.DE)": total_return_index(m.kurse["SXR8.DE"]),
        "MSCI ACWI IMI (SPYI.DE)": total_return_index(m.kurse["SPYI.DE"]),
    }
    for t in sp.get("zusatzbenchmarks", []):
        reihen[f"S&P 500 Value ({t}, EUR)"] = total_return_index(m.kurse[t])
    reihen = {n: r.reindex(tage.union(r.index)).ffill().reindex(tage).dropna() for n, r in reihen.items()}
    rf_tag = risikofreie_tagesrendite(lade_makro(sp.get("risikofreier_zins", "ECBDFR")), tage)
    k = pd.DataFrame({n: kennzahlen(r, None, rf_tag) for n, r in reihen.items()}).T

    s_vor, s_kon, s_sp = k.loc["Schattenportfolio nach Kosten, vor Steuern"], k.loc["Kontrollportfolio (ohne Kosten, vor Steuern)"], k.loc["S&P 500 ohne Finanzwerte (EUR, TR)"]
    grenze_dd = float(konfig["erfolgskriterien"]["risiko_max_drawdown_pp"]) / 100
    krit_a = s_vor["cagr"] >= s_kon["cagr"]
    krit_b_sharpe = s_vor["sharpe"] >= s_sp["sharpe"]
    krit_b_dd = s_vor["max_drawdown"] >= s_sp["max_drawdown"] - grenze_dd
    krit_b = krit_b_sharpe and krit_b_dd

    # --- Varianten zählen --------------------------------------------------------------------------
    ziel = PROJEKT_WURZEL / "daten" / "fundamental"
    ziel.mkdir(parents=True, exist_ok=True)
    varianten_datei = ziel / "varianten.csv"
    alt = pd.read_csv(varianten_datei) if varianten_datei.exists() else pd.DataFrame(columns=["datum", "variante", "anlass", "git", "lauf", "kriterium_a", "kriterium_b"])
    zeile = {"datum": datetime.now().isoformat(timespec="seconds"), "variante": VARIANTE, "anlass": ANLASS, "git": lauf.meta["git"].get("commit"),
             "lauf": str(lauf.pfad.name if lauf.pfad else ""), "kriterium_a": bool(krit_a), "kriterium_b": bool(krit_b)}
    varianten = pd.concat([alt, pd.DataFrame([zeile])], ignore_index=True)
    varianten.to_csv(varianten_datei, index=False)
    anzahl_varianten = varianten["variante"].nunique()

    # --- Bericht ------------------------------------------------------------------------------------
    pz = lambda x: f"{x:.2%}".replace(".", ",")  # noqa: E731
    zahl = lambda x: f"{x:.2f}".replace(".", ",")  # noqa: E731
    ok = lambda b: "**bestanden**" if b else "**verfehlt**"  # noqa: E731
    text = [f"# Fundamental-Schattenportfolio – erster gewerteter Backtest", "",
            f"Zeitraum {tage[0].date()} bis {tage[-1].date()} ({len(ranglisten)} Rebalancing-Stichtage), virtuell "
            f"{sp['kapital']:,.0f} €, {sp['titel']} Titel. {VARIANTE}. Getestete Varianten bisher: {anzahl_varianten}.", "",
            f"Anlass der Neuberechnung: {ANLASS or '–'}.", "",
            f"Ablage: `{lauf.pfad.relative_to(PROJEKT_WURZEL) if lauf.pfad else '–'}`; Scores-Cache `{arg.scores}`: {scores_meta.get('stichtage', '?')} Stichtage, Zeitraum {scores_meta.get('zeitraum', '?')}.", "",
            "## Erfolgskriterien (vor dem Lauf festgeschrieben)", "",
            "| Kriterium | Schattenportfolio | Vergleich | Ergebnis |", "| --- | --- | --- | --- |",
            f"| (a) Rendite p.a. nach Kosten, vor Steuern ≥ Kontrollportfolio | {pz(s_vor['cagr'])} | {pz(s_kon['cagr'])} | {ok(krit_a)} |",
            f"| (b1) Sharpe nach Kosten ≥ S&P 500 ohne Finanzwerte (EUR) | {zahl(s_vor['sharpe'])} | {zahl(s_sp['sharpe'])} | {ok(krit_b_sharpe)} |",
            f"| (b2) Max. Drawdown höchstens 5 Pp. schlechter | {pz(s_vor['max_drawdown'])} | {pz(s_sp['max_drawdown'])} (Grenze {pz(s_sp['max_drawdown'] - grenze_dd)}) | {ok(krit_b_dd)} |",
            "", f"Gesamt: (a) {ok(krit_a)}, (b) {ok(krit_b)}. "
            + ("Beide bestanden → die Engine geht wie geplant ins Paper Trading." if krit_a and krit_b
               else "Mindestens ein Kriterium verfehlt → Ergebnis dokumentieren und mit Jakob besprechen; keine Anpassung ohne Fehler oder theoretische Begründung."),
            "", "Aussagekraft: 33 Quartale; Vorsprünge unter etwa 5 Prozentpunkten p.a. sind statistisch nicht von Zufall zu unterscheiden.", "",
            "## Kennzahlen (gemeinsamer Kalender, Sharpe mit EZB-Einlagesatz ECBDFR)", "",
            "| Reihe | Rendite p.a. | Volatilität | Sharpe | max. Drawdown | Endwert je 100 |", "| --- | --- | --- | --- | --- | --- |"]
    for n, z in k.iterrows():
        text.append(f"| {n} | {pz(z['cagr'])} | {pz(z['volatilitaet'])} | {zahl(z['sharpe'])} | {pz(z['max_drawdown'])} | {zahl(100 * (1 + z['gesamtrendite']))} |")
    kz = lauf.kennzahlen.loc[NAME]
    text += ["", "Rendite gegenüber SXR8, SPYI und IVE wird nur berichtet, ist kein Kriterium. MSCI ACWI IMI Value Weighted fehlt "
             "(kein ETF, Lücke). IVE ist US-domiziliert und für Privatanleger in der EU nicht handelbar; nur Vergleichsmaßstab.", "",
             "## Steuern (Schatten-Steuergruppe ohne Pauschbetrag)", "",
             f"Rendite p.a. vor Steuern (mit Quellensteuer-Abzug) {pz(kz['cagr'])}, nach laufenden Steuern {pz(kz['cagr_nach_steuern'])}, "
             f"nach fiktivem Verkauf am Ende {pz(kz['cagr_nach_verkauf_und_steuern'])}. Gezahlte Steuern {kz['steuern_gezahlt']:,.0f} €, "
             f"Steuer bei Verkauf {kz['steuer_bei_verkauf']:,.0f} €. Benchmark-Zwilling SPYI.DE nach Verkauf und Steuern "
             f"{pz(kz['benchmark_cagr_nach_verkauf_und_steuern'])}.", "",
             "## Rendite je Kalenderjahr", "", "| Jahr | " + " | ".join(reihen) + " |", "| --- |" + " --- |" * len(reihen)]
    jahre = pd.DataFrame({n: r.groupby(r.index.year).last() for n, r in reihen.items()})
    erste = pd.DataFrame({n: r.iloc[:1] for n, r in reihen.items()})
    jahre_r = pd.concat([erste.rename(index=lambda _: tage[0].year - 1), jahre]).pct_change().dropna(how="all")
    for j, z in jahre_r.iterrows():
        text.append(f"| {j} | " + " | ".join(pz(v) for v in z) + " |")

    # Umschlag, Kosten, verworfene Orders
    trades = vor.trades
    kosten = vor.kosten_gesamt
    tausch = float(vor.waehrungstausche["kosten"].sum()) if len(vor.waehrungstausche) else 0.0
    jahre_anzahl = (tage[-1] - tage[0]).days / 365.25
    umschlag = float(trades.loc[trades.richtung < 0, "kurswert"].sum()) / float(vor.wert.mean()) / jahre_anzahl
    verworfen = Counter(vor.verworfen["grund"].str.replace(r"[\d.,]+", "x", regex=True)) if len(vor.verworfen) else Counter()
    text += ["", "## Umschlag und Kosten (Lauf vor Steuern)", "",
             f"{len(trades)} Trades, Kosten {kosten:,.0f} € ({kosten / float(sp['kapital']) / jahre_anzahl:.2%} des Startkapitals p.a.; "
             f"Gebühren {trades.gebuehr.sum():,.0f} €, Spread und Slippage {trades.spread_slippage.sum():,.0f} €, "
             f"Währungstausch {tausch:,.0f} € in {len(vor.waehrungstausche)} Tauschvorgängen), "
             f"Umschlag (Verkäufe / mittlerer Wert) {umschlag:.0%} p.a.; verworfene Orders: {dict(verworfen) or 'keine'}."]

    # Positionen je Stichtag: Anzahl, Median-Ersatz, Käufe/Verkäufe
    prot = pd.DataFrame(d_vor.strategie.protokoll)
    ersetzt_je = {}
    text += ["", "## Positionen je Stichtag", "",
             "| Stichtag | Positionen | mit Median-Ersatz | Käufe | Verkäufe (Universum / Puffer) | zurück auf 5 % | Piotroski hochgerechnet | Z''-Warnhinweis |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for tag, g in prot.groupby("stichtag"):
        r = ranglisten[tag].set_index("ticker")
        pos = g[g["aktion"] != "verkaufen"]
        mit_ersatz = int((r.loc[pos["ticker"], "ersetzt"] != "").sum())
        ersetzt_je[tag] = mit_ersatz
        verk = g[g["aktion"] == "verkaufen"]
        text.append(f"| {tag.date()} | {len(pos)} | {mit_ersatz} | {int((g['aktion'] == 'kaufen').sum())} | "
                    f"{int(verk['grund'].str.startswith('nicht').sum())} / {int(verk['grund'].str.startswith('Rang').sum())} | "
                    f"{int((g['aktion'] == 'zurück auf Zielgewicht').sum())} | {int(r.loc[pos['ticker'], 'piotroski_hoch'].sum())} | "
                    f"{int(r.loc[pos['ticker'], 'z2_warnhinweis'].sum())} |")

    # Branchen: Anteil je Division im Portfolio gegenüber dem gefilterten Universum (Mittel über die Stichtage)
    anteile_p, anteile_u = [], []
    for tag, g in prot.groupby("stichtag"):
        r = ranglisten[tag].set_index("ticker")
        pos = g[g["aktion"] != "verkaufen"]["ticker"]
        anteile_p.append(r.loc[pos, "sic"].map(lambda s: sic_division(int(s))).value_counts(normalize=True))
        anteile_u.append(r["sic"].map(lambda s: sic_division(int(s))).value_counts(normalize=True))
    div = pd.DataFrame({"Portfolio": pd.concat(anteile_p, axis=1).fillna(0).mean(axis=1),
                        "gefiltertes Universum": pd.concat(anteile_u, axis=1).fillna(0).mean(axis=1)}).fillna(0).sort_index()
    text += ["", "## Anteile je SIC-Division (Mittel über die Stichtage, nach Positionen)", "", "| Division | Portfolio | gefiltertes Universum |", "| --- | --- | --- |"]
    for d_, z in div.iterrows():
        text.append(f"| {d_} | {pz(z['Portfolio'])} | {pz(z['gefiltertes Universum'])} |")

    # Drift: höchstes Einzelgewicht
    schluss = m.schluss.reindex(tage)
    gew = vor.bestaende.mul(schluss[vor.bestaende.columns]).div(vor.wert, axis=0)
    hoechst = gew.max().sort_values(ascending=False)
    text += ["", f"Höchstes Einzelgewicht im Zeitraum: {pz(float(hoechst.iloc[0]))} ({namen.get(int(hoechst.index[0][3:]), hoechst.index[0])}); "
             f"Tage mit einem Titel über 7,5 %: {int((gew.max(axis=1) > 0.075).sum())}."]

    # Delistings
    dl_alle = Counter(d.grund for d in delistings.values())
    dl_p = vor.meta["delistings"]
    text += ["", "## Delistings", "",
             f"Kursreihen, die im Zeitraum enden (Firmen in mindestens einer Rangliste): {dict(dl_alle) or 'keine'}. "
             f"Im Schattenportfolio betroffen: {len(dl_p)}"
             + (": " + ", ".join(f"{namen.get(int(r.ticker[3:]), r.ticker)} ({r.grund}, {r.datum.date()})" for r in dl_p.itertuples()) if len(dl_p) else "") + ".",
             f"Kontrollportfolio: Titel ohne Eröffnungskurs am Ausführungstag (für das Quartal ausgelassen): {int(kontroll_stat['ohne_eroeffnungskurs'].sum())}."]

    # Bestand am Ende
    ende_bestand = vor.bestaende.iloc[-1]
    ende_bestand = ende_bestand[ende_bestand > 0].index
    text += ["", "## Bestand am Ende", "", ", ".join(sorted(namen.get(int(t[3:]), t) for t in ende_bestand))]

    bericht = "\n".join(text)
    if lauf.pfad:
        (lauf.pfad / "fundamental_bericht.md").write_text(bericht, encoding="utf-8")
        prot.to_csv(lauf.pfad / "auswahl_protokoll.csv", index=False)
        vor.trades.to_csv(lauf.pfad / "trades_vor_steuern.csv", index=False)
        pd.DataFrame(reihen).to_csv(lauf.pfad / "wertreihen.csv")
    (ziel / arg.kopie).write_text(bericht, encoding="utf-8")
    print(bericht)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FehlerschwelleUeberschritten as fehler:
        sys.exit(laut_melden(fehler))
