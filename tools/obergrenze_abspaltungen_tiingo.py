r"""Teil c1, Methodenwechsel a): Obergrenze der Wirkung möglicher Scheinverluste aus unbereinigten Abspaltungen in
Tiingo-Reihen auf Backtest A und den Index-Nachbau (Jakob 15.11.2026, festgehalten vor der Rechnung in
docs/FUNDAMENTAL.md, Abschnitt „Teil c1: Methodenwechsel nach dem dritten Lauf“). Nur lesend, ohne Netzabruf.

Aufruf:  .venv\Scripts\python tools\obergrenze_abspaltungen_tiingo.py
Ergebnis: docs/berichte/2026-11-15_abspaltungen_obergrenze.md

Kandidaten: Ereignisse (Treffer und „unklar“) aus docs/berichte/2026-11-13_abspaltungen_tiingo_3.md.
- Backtest A: Kandidatentage (≤ −3 %, auch Zwei-Tage-Fenster) mit Bestand zum Vortagesschluss.
- Index-Nachbau: Ereignisse mit schlechtester Gesamtrendite ≤ −15 %, nur Tage innerhalb der Mitgliedschaft.
Jeder Kandidatentag gilt als vollständiger Scheinverlust (Rendite 0). Schwelle: beide Differenzen < 0,05 Pp. p. a.
Rechenlogik: src/tradingbot/backtest/obergrenze_scheinverluste.py.
"""
import dataclasses
import sys
import warnings
from datetime import datetime

import pandas as pd

from tradingbot.backtest.obergrenze_scheinverluste import (INDEX_SCHWELLE, bestand_zum_vortag, kandidatentage, korrigierte_werte,
                                                           lies_ereignisse, neutralisiere, schlechteste_rendite)
from tradingbot.daten.index_nachbau import ABNAHME_ZEITRAUM, abnahme_gegenprobe
from tradingbot.daten.kurse import in_euro, lade_kurse
from tradingbot.daten.sp500_nachbau import ENDE, VORLAUF, baue_nachbau, lade_firmendaten
from tradingbot.daten.tiingo import TiingoClient
from tradingbot.daten.universum import lade_sic_historien, lade_universum
from tradingbot.kennzahlen.performance import cagr
from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration

warnings.simplefilter("ignore")
SCHWELLE_PP = 0.05
QUELLE = PROJEKT_WURZEL / "docs" / "berichte" / "2026-11-13_abspaltungen_tiingo_3.md"
BERICHT = PROJEKT_WURZEL / "docs" / "berichte" / "2026-11-15_abspaltungen_obergrenze.md"
LAEUFE = {"20261113T100231_fundamental_schatten_eq_offer": "maßgeblich", "20261113T100150_fundamental_schatten_eq_bisher": "Information"}


class OhneNetz:
    """Sitzung für den Tiingo-Client, die jeden Abruf verweigert: nur Cache (Monatsgrenze, Jakob 15.11.2026)."""

    def get(self, *a, **k):
        raise RuntimeError("Tiingo-Abruf in diesem Werkzeug verboten (nur Cache)")


def obergrenze_buch(ordner: str, kandidaten: dict, kurse_eur: dict) -> dict:
    basis = PROJEKT_WURZEL / "daten" / "backtests" / ordner
    name = ordner.split("_", 1)[1]
    werte = pd.read_csv(basis / name / "werte.csv", index_col="datum", parse_dates=True)
    if (werte["einzahlung"].fillna(0) != 0).iloc[1:].any():
        raise RuntimeError(f"{ordner}: Einzahlungen im Lauf, Rechnung setzt einen Lauf ohne Einzahlungen voraus")
    trades = pd.read_csv(basis / name / "trades.csv")
    tage = werte.index
    bestand = bestand_zum_vortag(trades, tage)
    wert_vortag = werte["wert"].shift(1)
    korrektur = pd.Series(0.0, index=tage)
    faelle = []
    for (firma, ticker), tage_firma in kandidaten.items():
        titel = f"CIK{firma}"
        if titel not in bestand.columns or titel not in kurse_eur:
            continue
        preis = kurse_eur[titel]["close"].reindex(kurse_eur[titel].index.union(tage)).ffill()
        for tag, r in tage_firma.items():
            if tag not in tage:
                continue
            stueck = bestand.at[tag, titel]
            if stueck <= 0:
                continue
            vortag = tage[tage.get_loc(tag) - 1]
            gewicht = stueck * preis.at[vortag] / wert_vortag.at[tag]
            korrektur.at[tag] += -gewicht * r
            faelle.append({"ticker": ticker, "tag": tag.date(), "rendite": r, "gewicht": gewicht, "wirkung": -gewicht * r})
    neu = korrigierte_werte(werte["wert"], korrektur)
    return {"ordner": ordner, "cagr_alt": cagr(werte["wert"]), "cagr_neu": cagr(neu), "faelle": pd.DataFrame(faelle),
            "zeitraum": (tage[0].date(), tage[-1].date())}


def main(argv=None) -> int:
    import argparse

    from tradingbot.daten.rohkurse_marktwert import c3_argumente, c3_sperre_melden

    a = argparse.ArgumentParser(description="Obergrenze der Scheinverluste (Teil c1)")
    c3_argumente(a)
    a.add_argument("--backtest", default=None, help="mit --c3: Ordner des Neulaufs Backtest A unter daten/backtests/ (Zusatzregel c1)")
    arg = a.parse_args(argv)
    sperre = c3_sperre_melden(arg.c3, arg.probe)
    if sperre:
        from tradingbot.daten.fehlerschwelle import laut_melden

        return laut_melden(RuntimeError(sperre))
    if arg.c3 and not arg.backtest:
        a.error("--c3 braucht --backtest <Ordner des Neulaufs>")
    laeufe = {arg.backtest: "maßgeblich (c3)"} if arg.c3 else LAEUFE
    bericht = (PROJEKT_WURZEL / "docs" / "berichte" / f"{datetime.now():%Y-%m-%d}_abspaltungen_obergrenze_c3{'_probe' if arg.probe else ''}.md"
               if arg.c3 else BERICHT)
    ereignisse = lies_ereignisse(QUELLE.read_text(encoding="utf-8"))
    universum, _ = lade_universum()
    status = pd.read_csv(PROJEKT_WURZEL / "daten" / "universum" / "kursstatus.csv").set_index("index")
    daten = lade_firmendaten(universum, status, lade_sic_historien(universum), tiingo=TiingoClient(sitzung=OhneNetz()), rohkurse=arg.c3)
    alt = baue_nachbau(daten, marktwert_korrektur=arg.c3)
    mitglied = alt["mitglied"]

    kandidaten_a, kandidaten_index, fehlend, index_faelle = {}, {}, [], []
    for e in ereignisse.itertuples():
        k = daten.kurse.get(e.cik)
        if k is None or k.empty:
            fehlend.append(f"{e.ticker} ({e.cik}) {e.von.date()}")
            continue
        tage = kandidatentage(k, e.von, e.bis)
        if tage.empty:
            fehlend.append(f"{e.ticker} ({e.cik}) {e.von.date()} (keine Kandidatentage in der Reihe)")
            continue
        schluessel = (e.cik, e.ticker)
        kandidaten_a[schluessel] = pd.concat([kandidaten_a.get(schluessel, pd.Series(dtype=float)), tage])
        schlecht = schlechteste_rendite(k, e.von, e.bis)
        if schlecht <= INDEX_SCHWELLE and e.cik in mitglied.columns:
            drin = [t for t in tage.index if t in mitglied.index and mitglied.at[t, e.cik]]
            if drin:
                kandidaten_index.setdefault(e.cik, set()).update(drin)
                index_faelle.append({"ticker": e.ticker, "cik": e.cik, "von": e.von.date(), "bis": e.bis.date(), "schlecht": schlecht,
                                     "tage": ", ".join(str(t.date()) for t in drin), "liste": e.liste})
    kandidaten_a = {s: t[~t.index.duplicated()].sort_index() for s, t in kandidaten_a.items()}

    # Index-Nachbau: Kandidatentage neutralisiert, Gewichte und Marktwerte unverändert
    kurse_neu = dict(daten.kurse)
    for firma, tage in kandidaten_index.items():
        kurse_neu[firma] = neutralisiere(daten.kurse[firma], tage)
    neu = baue_nachbau(dataclasses.replace(daten, kurse=kurse_neu), marktwert_korrektur=arg.c3)
    referenz = lade_kurse("^SP500TR", VORLAUF, ENDE)["close"]
    g_alt, g_neu = abnahme_gegenprobe(alt["nachbau"]["index"], referenz), abnahme_gegenprobe(neu["nachbau"]["index"], referenz)
    von, bis = (pd.Timestamp(z) for z in ABNAHME_ZEITRAUM)
    cagr_index_alt, cagr_index_neu = cagr(alt["nachbau"]["index"].loc[von:bis]), cagr(neu["nachbau"]["index"].loc[von:bis])
    d_index = (cagr_index_neu - cagr_index_alt) * 100

    # Backtest A: Kurse in Euro wie im Backtest (EURUSD=X)
    fx = lade_kurse(lade_konfiguration("daten")["kurse"]["wechselkurse"].get("USD", "EURUSD=X"), VORLAUF, ENDE)["close"]
    kurse_eur = {f"CIK{f}": in_euro(daten.kurse[f], "USD", fx) for f, _ in kandidaten_a if daten.kurse.get(f) is not None}
    buecher = [obergrenze_buch(o, kandidaten_a, kurse_eur) for o in laeufe]
    d_a = (buecher[0]["cagr_neu"] - buecher[0]["cagr_alt"]) * 100
    vernachlaessigbar = abs(d_a) < SCHWELLE_PP and abs(d_index) < SCHWELLE_PP

    text = ["# Teil c1: Obergrenze der Scheinverluste aus Abspaltungen in Tiingo-Reihen", "",
            f"Erstellt {datetime.now():%d.%m.%Y %H:%M} mit `tools/obergrenze_abspaltungen_tiingo.py`. Methode und Schwelle vor der Rechnung "
            "festgehalten (docs/FUNDAMENTAL.md, „Teil c1: Methodenwechsel nach dem dritten Lauf“, Jakob 15.11.2026). Kandidaten: "
            f"{len(ereignisse)} Ereignisse des dritten Laufs ({(ereignisse['liste'] == 'treffer').sum()} Treffer, "
            f"{(ereignisse['liste'] == 'unklar').sum()} unklar). Jeder Kandidatentag gilt als vollständiger Scheinverlust (Rendite 0). "
            "Nichts wurde korrigiert.", "",
            f"## Ergebnis: {'vernachlässigbar – c1 kann geschlossen werden' if vernachlaessigbar else 'Schwelle verfehlt – weiter mit b) (gezielte Prüfung)'}", "",
            "| Messgröße | ohne Neutralisierung | mit Neutralisierung | Differenz | Schwelle | eingehalten |", "| --- | --- | --- | --- | --- | --- |",
            f"| Backtest A ({buecher[0]['ordner']}), CAGR nach Kosten vor Steuern {buecher[0]['zeitraum'][0]}–{buecher[0]['zeitraum'][1]} | "
            f"{buecher[0]['cagr_alt']:.4%} | {buecher[0]['cagr_neu']:.4%} | {d_a:+.4f} Pp. | < 0,05 Pp. | {'ja' if abs(d_a) < SCHWELLE_PP else 'NEIN'} |",
            f"| Index-Nachbau, annualisiert {von.date()}–{bis.date()} | {cagr_index_alt:.4%} | {cagr_index_neu:.4%} | {d_index:+.4f} Pp. | < 0,05 Pp. | "
            f"{'ja' if abs(d_index) < SCHWELLE_PP else 'NEIN'} |", "",
            "Zur Information:", "",
            (f"- Backtest A ({buecher[1]['ordner']}): CAGR {buecher[1]['cagr_alt']:.4%} → {buecher[1]['cagr_neu']:.4%} "
             f"({(buecher[1]['cagr_neu'] - buecher[1]['cagr_alt']) * 100:+.4f} Pp.)." if len(buecher) > 1 else
             "- Neulauf c3 (Zusatzregel aus c1): dieselben Tage und dieselbe Schwelle am Bestand des Neulaufs."
             + (" PROBE – zählt nicht als c3." if arg.probe else "")),
            f"- Gegenprobe Index-Nachbau ohne/mit Neutralisierung: Korrelation {g_alt['kriterien']['korrelation']['wert']:.4f} / "
            f"{g_neu['kriterien']['korrelation']['wert']:.4f}; größte Jahresabweichung {g_alt['kriterien']['jahresabweichung_max']['wert'] * 100:.2f} / "
            f"{g_neu['kriterien']['jahresabweichung_max']['wert'] * 100:.2f} Pp.; Abweichung annualisiert "
            f"{g_alt['kriterien']['annualisiert_abweichung']['wert'] * 100:+.2f} / {g_neu['kriterien']['annualisiert_abweichung']['wert'] * 100:+.2f} Pp.; "
            f"bestanden {'ja' if g_alt['bestanden'] else 'nein'} / {'ja' if g_neu['bestanden'] else 'nein'}.",
            "- Grenzen der Näherung für Backtest A: ohne Neusimulation, ohne Kosten- und Steuerwirkung, ohne geänderte "
            "Rebalancing-Entscheidungen. Zusatzregel: dieselbe Rechnung am Bestand des Neulaufs in Teil c.", "",
            "### Jahresrenditen Index-Nachbau (Differenz durch Neutralisierung)", "", "| Jahr | ohne | mit | Differenz |", "| --- | --- | --- | --- |"]
    for jahr in g_alt["jahre"].index:
        a, n = g_alt["jahre"].at[jahr, "nachbau"], g_neu["jahre"].at[jahr, "nachbau"]
        text.append(f"| {jahr} | {a:.2%} | {n:.2%} | {(n - a) * 100:+.3f} Pp. |")
    text += ["", f"## Backtest A: Kandidatentage mit Bestand ({len(buecher[0]['faelle'])})", "",
             "| Ticker | Tag | Gesamtrendite | Gewicht im Buch | Wirkung auf die Tagesrendite |", "| --- | --- | --- | --- | --- |"]
    for f in buecher[0]["faelle"].sort_values("wirkung", ascending=False).itertuples() if len(buecher[0]["faelle"]) else []:
        text.append(f"| {f.ticker} | {f.tag} | {f.rendite:+.2%} | {f.gewicht:.2%} | {f.wirkung * 100:+.3f} Pp. |")
    text += ["", f"## Index-Nachbau: Ereignisse ≤ −15 % während der Mitgliedschaft ({len(index_faelle)})", "",
             "| Ticker (CIK) | Ereignis | schlechteste Gesamtrendite | Liste | neutralisierte Tage |", "| --- | --- | --- | --- | --- |"]
    for f in index_faelle:
        text.append(f"| {f['ticker']} ({f['cik']}) | {f['von']}" + (f" bis {f['bis']}" if f["bis"] != f["von"] else "")
                    + f" | {f['schlecht']:+.1%} | {f['liste']} | {f['tage']} |")
    if fehlend:
        spaet = [x for x in fehlend if x.split(") ")[1][:10] >= str(von.date())]
        text += ["", f"## Ereignisse ohne Kursreihe im Nachbau oder ohne Kandidatentage ({len(fehlend)})", "",
                 "Der Nachbau lädt nur Mitgliedschaften ab dem 04.01.2016; frühere Ereignisse liegen vor beiden Messzeiträumen "
                 f"(ab {von.date()}). Davon im Messzeitraum: {len(spaet)}" + (f" ({'; '.join(spaet)})" if spaet else "") + ".", ""]
        text += [f"- {x}" for x in fehlend]
    bericht.write_text("\n".join(text) + "\n", encoding="utf-8")
    print("\n".join(text[:20]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
