r"""Gewerteter Backtest des Schattenbuchs „regime“ auf den Entwicklungsdaten (docs/REGIME.md, Abschnitte 1–4, 7–7c).

Aufruf:  .venv\Scripts\python tools\backtest_regime.py --festlegung <Commit>

`--festlegung`: Commit, in dem die Festlegungen eingefroren wurden. Das Werkzeug bricht ab, wenn docs/REGIME.md oder der
Code der Regime-Engine seitdem geändert wurde. Jeder Aufruf ist ein gewerteter Lauf und kommt in daten/regime/varianten.csv.

Gerechnet werden V1 (einzige gewertete Variante), die Diagnosen D1–D4, Kaufen und Halten (Zwilling) und die statische
Mischung. Der Bericht enthält die Kriterien a–c je Hälfte, aber **kein Gesamturteil**: Das fällt erst nach dem US-Langtest.
Ergebnis: daten/backtests/<zeitstempel>_regime_*/, Bericht docs/berichte/<datum>_regime_backtest.md.

`--steuermodus jahresende_nur_wertreihe --vergleich-ablage <Ordner> …` (Befund 3, Jakob 16.11.2026): rechnet mit dem
Rechenweg bis 15.11.2026 und prüft, ob er die Ablage eines früheren Laufs trifft. Kein gewerteter Lauf, keine Ablage, kein
Eintrag in daten/regime/varianten.csv, kein Bericht; Exit 2 bei Abweichung.
"""
import argparse
import hashlib
import shutil
import subprocess
import sys
import warnings
from datetime import datetime
from pathlib import Path

import pandas as pd

ETF = "SPYI.DE"
DATEN_AB, ERSTE_BEWERTUNG, ENDE = "2012-01-01", pd.Timestamp("2012-10-31"), pd.Timestamp("2024-12-31")
HAELFTEN = [(pd.Timestamp("2012-11-01"), pd.Timestamp("2018-11-30")), (pd.Timestamp("2018-12-01"), pd.Timestamp("2024-12-31"))]
KAPITAL = 10_000.0
EINGEFROREN = ["docs/REGIME.md", "src/tradingbot/engines/regime"]
MAKRO_REIHEN = ["T10Y3M", "BAA10Y", "UNRATE", "ECBDFR"]
STEUERMODI = ("jahresende_aus_kasse", "jahresende_nur_wertreihe")
WERTE_SPALTEN = ["wert", "cash", "steuern_kumuliert", "wert_nach_steuern"]


def vergleiche_mit_ablage(erg: dict, ordner: list[Path], *, toleranz: float = 1e-6) -> tuple[list[str], list[str]]:
    """Vergleicht Werte, Trades und Kriterien eines Laufs mit früheren Ablagen. Rückgabe (geprüft, Abweichungen).

    Zugeordnet wird über den Teilportfolio-Ordner der Ablage (regime_V1, benchmark_regime_V1, regime_mischung, …).
    Werte relativ mit `toleranz`, Trades auf Datum, Richtung und Stückzahl exakt, Kriterien a–c exakt.
    """
    reihen = {}
    for lauf in [*erg["laeufe"].values(), erg["lauf_mischung"]]:
        for n, e in lauf.ergebnisse.items():
            reihen[n] = e
            reihen[f"benchmark_{n}"] = lauf.zwillinge[n]
    geprueft, abweichungen = [], []
    for o in ordner:
        for unter in sorted(x for x in Path(o).iterdir() if x.is_dir() and (x / "werte.csv").exists()):
            e = reihen.get(unter.name)
            if e is None:
                abweichungen.append(f"{unter}: kein passendes Teilportfolio im Lauf")
                continue
            alt = pd.read_csv(unter / "werte.csv", index_col="datum", parse_dates=True)
            neu = e.werte
            if not alt.index.equals(neu.index):
                abweichungen.append(f"{unter.name}: Handelstage weichen ab ({len(alt)} gegen {len(neu)})")
                continue
            for spalte in WERTE_SPALTEN:
                rel = ((neu[spalte] - alt[spalte]).abs() / alt[spalte].abs().clip(lower=1.0)).max()
                if rel > toleranz:
                    tag = ((neu[spalte] - alt[spalte]).abs()).idxmax()
                    abweichungen.append(f"{unter.name}.{spalte}: größte relative Abweichung {rel:.2e} am {tag.date()} "
                                        f"({alt.loc[tag, spalte]:.4f} gegen {neu.loc[tag, spalte]:.4f})")
            t_alt = pd.read_csv(unter / "trades.csv", parse_dates=["datum"])[["datum", "richtung", "stueck"]].reset_index(drop=True)
            t_neu = e.trades[["datum", "richtung", "stueck"]].reset_index(drop=True)
            t_neu = t_neu.assign(datum=pd.to_datetime(t_neu.datum))
            if not (len(t_alt) == len(t_neu) and (t_alt.values == t_neu.values).all()):
                abweichungen.append(f"{unter.name}: Trades weichen ab ({len(t_alt)} gegen {len(t_neu)})")
            geprueft.append(f"{Path(o).name}/{unter.name}: {len(alt)} Tage, {len(t_alt)} Trades")
        kdatei = Path(o) / "kriterien.csv"
        if kdatei.exists():
            k_alt = pd.read_csv(kdatei)
            for r_alt, r_neu in zip(k_alt.itertuples(), erg["kriterien"].itertuples()):
                for c in "abc":
                    if bool(getattr(r_alt, c)) != bool(getattr(r_neu, c)):
                        abweichungen.append(f"Kriterium {c} Hälfte {r_alt.haelfte}: {getattr(r_alt, c)} gegen {getattr(r_neu, c)}")
                for c in ("v1_sharpe", "kuh_sharpe", "mischung_sharpe", "v1_max_dd", "kuh_max_dd"):
                    if abs(getattr(r_alt, c) - getattr(r_neu, c)) > toleranz:
                        abweichungen.append(f"{c} Hälfte {r_alt.haelfte}: {getattr(r_alt, c):.6f} gegen {getattr(r_neu, c):.6f}")
            geprueft.append(f"{Path(o).name}/kriterien.csv")
    return geprueft, abweichungen


def pruefe_festlegung(commit: str, wurzel: Path) -> str | None:
    """Fehlertext, wenn der Commit fehlt oder die eingefrorenen Dateien seitdem geändert wurden; sonst None."""
    def git(*args):
        return subprocess.run(["git", *args], cwd=wurzel, capture_output=True, text=True)

    if not commit or git("cat-file", "-e", f"{commit}^{{commit}}").returncode != 0:
        return f"Festlegungs-Commit {commit!r} gibt es nicht"
    geaendert = git("diff", "--name-only", commit, "--", *EINGEFROREN).stdout.split()
    neu = [z[3:] for z in git("status", "--porcelain", "--", *EINGEFROREN).stdout.splitlines() if z.startswith("??")]
    if geaendert or neu:
        return f"Seit dem Festlegungs-Commit {commit} geändert: {', '.join(geaendert + neu)} – erst neu einfrieren"
    return None


def rechne(kurse: pd.DataFrame, verlaeufe: dict[str, pd.DataFrame], rf_zins: pd.Series, *, konfig: dict | None = None,
           start=ERSTE_BEWERTUNG, ende=ENDE, haelften=HAELFTEN, ablage_wurzel: Path | None = None, ablage: bool = True) -> dict:
    """Simuliert V1, D1–D4, Kaufen und Halten (Zwilling von V1) und die statische Mischung; Kriterien je Hälfte für V1."""
    from tradingbot.backtest.bericht import fuehre_lauf_aus
    from tradingbot.backtest.marktdaten import Instrument, Marktdaten
    from tradingbot.backtest.simulation import TeilportfolioDefinition
    from tradingbot.engines.regime import buch
    from tradingbot.kennzahlen.performance import kennzahlen, risikofreie_tagesrendite

    m = Marktdaten({ETF: kurse})
    tage = m.kalender[(m.kalender >= pd.Timestamp(start)) & (m.kalender <= pd.Timestamp(ende))]
    rf_tag = risikofreie_tagesrendite(rf_zins, tage)

    def lauf(name, strategie):
        d = TeilportfolioDefinition(name, KAPITAL, strategie, [Instrument(ETF, "etf")], art="schatten", steuergruppe="schatten", rolle="core")
        return fuehre_lauf_aus(name, [d], m, start, ende, benchmark_ticker=ETF, rf_zins_prozent=rf_zins, konfig=konfig,
                               ablage=ablage, ablage_wurzel=ablage_wurzel)

    zustaende = {v: t["risiko_aus"].dropna() for v, t in verlaeufe.items()}
    erster = zustaende["V1"].index[0]
    if erster != pd.Timestamp(start):
        raise RuntimeError(f"Regime: erste Bewertung am {erster.date()}, festgelegt ist {pd.Timestamp(start).date()} – nicht still übernehmen")
    laeufe = {v: lauf(f"regime_{v}", buch.RegimeStrategie(ETF, z, name=f"Regime {v}")) for v, z in zustaende.items()}

    anteile = [buch.aktienanteil(zustaende["V1"], tage, von, bis) for von, bis in haelften]
    grenztag = tage[tage < haelften[1][0]][-1]                     # letzter Handelstag der ersten Hälfte: Signal für das neue Gewicht
    gewicht_ab = pd.Series({pd.Timestamp(start): anteile[0], grenztag: anteile[1]})
    lauf_mischung = lauf("regime_mischung", buch.MischungStrategie(ETF, gewicht_ab))

    v1 = laeufe["V1"].ergebnisse["regime_V1"]
    kuh = laeufe["V1"].zwillinge["regime_V1"]
    mischung = lauf_mischung.ergebnisse["regime_mischung"]
    kriterien = buch.kriterien_je_haelfte(v1.wert_nach_steuern, kuh.wert_nach_steuern, mischung.wert_nach_steuern, haelften, rf_tag)
    kriterien["aktienanteil"] = anteile

    zeilen = []
    reihen = {**{v: l.ergebnisse[f"regime_{v}"] for v, l in laeufe.items()}, "Kaufen und Halten": kuh, "Mischung": mischung}
    for name, e in reihen.items():
        z = zustaende.get(name)
        for nr, (von, bis) in enumerate(haelften, start=1):
            kz = kennzahlen(buch.abschnitt(e.wert_nach_steuern, von, bis), None, rf_tag)
            tr = e.trades[(e.trades.datum >= von) & (e.trades.datum <= bis)] if len(e.trades) else e.trades
            zeilen.append({"portfolio": name, "haelfte": nr, "cagr": kz["cagr"], "sharpe": kz["sharpe"], "max_dd": kz["max_drawdown"],
                           "trades": len(tr), "aktienanteil": buch.aktienanteil(z, tage, von, bis) if z is not None else None})
    gesamt = pd.DataFrame({name: {"endwert_nach_steuern": float(e.wert_nach_steuern.iloc[-1]), "steuern_gezahlt": float(e.meta["steuern_gezahlt"]),
                                  "endwert_nach_verkauf_und_steuern": float(e.meta["wert_nach_liquidation_und_steuern"]),
                                  "kosten": e.kosten_gesamt, "trades": len(e.trades), "verworfen": len(e.verworfen)}
                           for name, e in reihen.items()}).T
    return {"laeufe": laeufe, "lauf_mischung": lauf_mischung, "kriterien": kriterien, "je_haelfte": pd.DataFrame(zeilen),
            "gesamt": gesamt, "anteile": anteile, "zustaende": zustaende}


def bericht_text(erg: dict, verlauf_v1: pd.DataFrame, *, festlegung: str, git: str, befunde: list[str], anlass: str = "",
                 jetzt: datetime | None = None, pfade: list[str] | None = None) -> str:
    pz = lambda x: "–" if x is None or pd.isna(x) else f"{x:.2%}".replace(".", ",")  # noqa: E731
    zahl = lambda x: "–" if x is None or pd.isna(x) else f"{x:.2f}".replace(".", ",")  # noqa: E731
    ok = lambda b: "ja" if b else "**nein**"  # noqa: E731
    eur = lambda x: f"{x:,.0f} €".replace(",", ".")  # noqa: E731
    jetzt = jetzt or datetime.now()
    k = erg["kriterien"]
    text = ["# Regime-Engine: Backtest des Schattenbuchs auf den Entwicklungsdaten" + (f" ({anlass})" if anlass else ""), "",
            f"Stand {jetzt:%d.%m.%Y %H:%M}. Festlegungen eingefroren in Commit `{festlegung}` (docs/REGIME.md), gerechnet mit Commit `{git}`. "
            f"Gewerteter Zeitraum {HAELFTEN[0][0]:%d.%m.%Y} bis {HAELFTEN[1][1]:%d.%m.%Y}, {eur(KAPITAL)} Schattenkapital, {ETF}, "
            "nach Kosten und Steuern (eigene Steuergruppe ohne Pauschbetrag). Tresor zu.", "",
            "**Kein Gesamturteil in diesem Bericht.** Der US-Langtest 1995–2011 zählt mit (Kriterium b); das Urteil fällt erst danach "
            "(Jakob 15.11.2026). Nach diesem Lauf werden weder Schwellen noch Signale geändert.", "",
            "## Kriterien für V1 je Hälfte", "",
            "| Hälfte | Sharpe V1 | Sharpe Kaufen und Halten | Sharpe Mischung | Aktienanteil V1 = Mischung | max. Drawdown V1 | max. Drawdown KuH | Grenze c (75 %) | a) | b) | c) |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in k.itertuples():
        text.append(f"| {r.haelfte} ({r.von:%d.%m.%Y}–{r.bis:%d.%m.%Y}) | {zahl(r.v1_sharpe)} | {zahl(r.kuh_sharpe)} | {zahl(r.mischung_sharpe)} | "
                    f"{pz(r.aktienanteil)} | {pz(r.v1_max_dd)} | {pz(r.kuh_max_dd)} | {pz(0.75 * r.kuh_max_dd)} | {ok(r.a)} | {ok(r.b)} | {ok(r.c)} |")
    text += ["", "a) Sharpe ≥ Kaufen und Halten; b) Sharpe ≥ statische Mischung mit gleichem Durchschnitts-Aktienanteil; "
             "c) maximaler Drawdown mindestens 25 % kleiner als bei Kaufen und Halten.", "",
             "## Bekannte Verzerrungen und Datenhinweise", "",
             "- **Kasse zu 0 %** (XEON.DE hat die Datenprüfung nicht bestanden): In den Negativzins-Jahren 2015–2022 ist das in „Risiko aus“-Phasen "
             "günstiger als die Realität (Geldmarkt rund −0,4 % p. a.). Das begünstigt V1 gegenüber Kaufen und Halten leicht."]
    text += [f"- {b}" for b in befunde]
    text += ["", "## Alle Portfolios je Hälfte (nach Kosten und Steuern)", "",
             "| Portfolio | Hälfte | Rendite p. a. | Sharpe | max. Drawdown | Trades | Aktienanteil |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in erg["je_haelfte"].itertuples():
        text.append(f"| {r.portfolio} | {r.haelfte} | {pz(r.cagr)} | {zahl(r.sharpe)} | {pz(r.max_dd)} | {r.trades} | {pz(r.aktienanteil)} |")
    text += ["", "V1 ist die einzige gewertete Variante. D1 (nur Trend), D2 (nur Zinskurve), D3 (nur Kreditaufschlag) und D4 (nur Arbeitsmarkt) "
             "sind Diagnosen und zählen als Varianten, werden aber nie gewertet. Der Crossover-Schatten der Technik-Engine hat ein anderes "
             "Universum und Kapital (docs/TECHNIK.md) und ist hier nicht neu gerechnet.", "",
             "## Gesamter Zeitraum (nur zur Einordnung)", "",
             "| Portfolio | Endwert nach Steuern | Steuern gezahlt | Endwert nach fiktivem Verkauf und Steuern | Kosten | Trades | verworfene Orders |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for name, r in erg["gesamt"].iterrows():
        text.append(f"| {name} | {eur(r.endwert_nach_steuern)} | {eur(r.steuern_gezahlt)} | {eur(r.endwert_nach_verkauf_und_steuern)} | "
                    f"{eur(r.kosten)} | {int(r.trades)} | {int(r.verworfen)} |")
    z = erg["zustaende"]["V1"]
    wechsel = z[z.astype(bool) != z.astype(bool).shift(1)]
    text += ["", "## Zustände von V1", "", f"{len(wechsel) - 1} Wechsel nach der ersten Bewertung. Bewertungstag → Zustand (Order am nächsten Handelstag):", ""]
    text += [f"- {t:%d.%m.%Y}: {'Risiko aus' if aus else 'Risiko an'}" for t, aus in wechsel.items()]
    monate = verlauf_v1.dropna(subset=["risiko_aus"])
    text += ["", "Monatsenden mit Signal „aus“ (von " + str(len(monate)) + "): "
             + ", ".join(f"{n} {int(monate[s].astype(bool).sum())}" for n, s in (("Trend", "trend_aus"), ("Zinskurve", "kurve_aus"),
                                                                             ("Kreditaufschlag", "kredit_aus"), ("Arbeitsmarkt", "arbeit_aus"),
                                                                             ("V1 roh", "roh_aus"), ("V1 mit Haltepflicht", "risiko_aus"))) + "."]
    if pfade:
        text += ["", "Ablage der Läufe: " + ", ".join(f"`{p}`" for p in pfade)]
    return "\n".join(text)


def main(argv=None) -> int:
    from tradingbot.daten.fehlerschwelle import laut_melden
    from tradingbot.daten.kurse import echte_anteilspreise, lade_kurse
    from tradingbot.daten.makro import lade_makro
    from tradingbot.engines.regime import signale
    from tradingbot.engines.technik.daten import pruefe_etf_kurse
    from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration

    warnings.simplefilter("ignore")
    a = argparse.ArgumentParser(description="Gewerteter Backtest des Schattenbuchs regime")
    a.add_argument("--festlegung", required=True, help="Commit, in dem die Festlegungen eingefroren wurden")
    a.add_argument("--anlass", default="", help="z. B. Datenkorrektur (zählt trotzdem als Lauf)")
    a.add_argument("--steuermodus", choices=STEUERMODI, default=None,
                   help="Abfluss der Jahressteuer; ohne Angabe laut config/backtest.yaml (gewertet nur jahresende_aus_kasse)")
    a.add_argument("--vergleich-ablage", nargs="+", default=[], help="Ordner früherer Läufe: nur prüfen, ob dieser Lauf sie trifft")
    arg = a.parse_args(argv)
    fehler = pruefe_festlegung(arg.festlegung, PROJEKT_WURZEL)
    if fehler:
        return laut_melden(RuntimeError(fehler))

    roh = lade_kurse(ETF, DATEN_AB, str(ENDE.date()))
    befunde = [f"{ETF}: {b}" for b in pruefe_etf_kurse(roh)]
    duenn = ((roh.open == roh.high) & (roh.high == roh.low) & (roh.low == roh.close)).groupby(roh.index.year).sum()
    befunde.append(f"{ETF} wurde bis 2016 dünn gehandelt: Tage mit Eröffnung = Hoch = Tief = Schluss je Jahr "
                   + ", ".join(f"{j}: {int(n)}" for j, n in duenn.items() if n) + f"; {int((roh.volume == 0).sum())} Tage ohne Umsatz. "
                   "Ausführungen zur Eröffnung sind an solchen Tagen nur Näherungen.")
    kurse = echte_anteilspreise(roh, ETF, lade_konfiguration("daten").get("kapitalmassnahmen") or [])
    makro = signale.makro_stand_aus_cache()
    verlaeufe = {v: signale.regime_verlauf(kurse["close"], makro, variante=v) for v in signale.VARIANTEN}
    bt = lade_konfiguration("backtest")
    if arg.steuermodus:
        bt["steuern"]["zahlung"] = arg.steuermodus
    nur_vergleich = bool(arg.vergleich_ablage) or bt["steuern"].get("zahlung") != "jahresende_aus_kasse"
    if nur_vergleich and not arg.vergleich_ablage:
        return laut_melden(RuntimeError("Der Vergleichsmodus jahresende_nur_wertreihe ist nie gewertet: nur mit --vergleich-ablage"))
    erg = rechne(kurse, verlaeufe, lade_makro("ECBDFR"), konfig=bt, ablage=not nur_vergleich)
    if nur_vergleich:
        geprueft, abweichungen = vergleiche_mit_ablage(erg, [PROJEKT_WURZEL / o for o in arg.vergleich_ablage])
        print(f"Steuermodus {bt['steuern']['zahlung']}, Vergleich mit {len(arg.vergleich_ablage)} Ablage(n):")
        for g in geprueft:
            print(f"  geprüft: {g}")
        if abweichungen:
            print("ABWEICHUNG – vor der Wertung an Jakob:")
            for x in abweichungen:
                print(f"  {x}")
            return 2
        print("Keine Abweichung: Der Lauf trifft die Ablage(n).")
        return 0

    # eingefrorener Makro-Datenstand im Laufordner von V1
    pfad_v1 = erg["laeufe"]["V1"].pfad
    ziel = pfad_v1 / "makro"
    ziel.mkdir()
    summen = []
    for reihe in MAKRO_REIHEN:
        quelle = PROJEKT_WURZEL / "daten" / "cache" / "makro" / f"{reihe}.parquet"
        shutil.copy2(quelle, ziel / quelle.name)
        summen.append(f"{hashlib.sha256(quelle.read_bytes()).hexdigest()}  {quelle.name}")
    (ziel / "sha256.txt").write_text("\n".join(summen), encoding="utf-8")
    for v, t in verlaeufe.items():
        t.to_csv(pfad_v1 / f"verlauf_{v}.csv")

    git = erg["laeufe"]["V1"].meta["git"].get("commit")
    jetzt = datetime.now()
    k = erg["kriterien"]
    datei = PROJEKT_WURZEL / "daten" / "regime" / "varianten.csv"
    datei.parent.mkdir(parents=True, exist_ok=True)
    alt = pd.read_csv(datei) if datei.exists() else pd.DataFrame()
    neu = [{"datum": jetzt.isoformat(timespec="seconds"), "variante": v, "git": git, "festlegung": arg.festlegung,
            "lauf": l.pfad.name, "gewertet": v == "V1", "anlass": arg.anlass,
            **({f"h{r.haelfte}_{c}": bool(getattr(r, c)) for r in k.itertuples() for c in "abc"} if v == "V1" else {})}
           for v, l in {**erg["laeufe"], "Mischung": erg["lauf_mischung"]}.items()]
    pd.concat([alt, pd.DataFrame(neu)], ignore_index=True).to_csv(datei, index=False)
    k.to_csv(pfad_v1 / "kriterien.csv", index=False)

    pfade = [str(l.pfad.relative_to(PROJEKT_WURZEL)).replace("\\", "/") for l in [*erg["laeufe"].values(), erg["lauf_mischung"]]]
    text = bericht_text(erg, verlaeufe["V1"], festlegung=arg.festlegung, git=git, befunde=befunde, anlass=arg.anlass, jetzt=jetzt, pfade=pfade)
    (PROJEKT_WURZEL / "docs" / "berichte" / f"{jetzt:%Y-%m-%d}_regime_backtest.md").write_text(text, encoding="utf-8")
    (pfad_v1 / "bericht_regime.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
