r"""Baut den Benchmark „S&P 500 ohne Finanzwerte“ (USD und EUR) und legt ihn im Cache ab.

Aufruf:  .venv\Scripts\python tools\nachbau_sp500_ohne_finanzwerte.py
Voraussetzung: Gegenprobe des Nachbaus bestanden (docs/DATENQUALITAET.md, Lauf 4). Gleicher Aufbau wie dort
(daten/sp500_nachbau.py), nur ohne Finanzwerte (SIC 6000–6999 point-in-time, inklusive REITs).
EUR: Index in USD geteilt durch EUR/USD desselben Tages (fehlender Wechselkurs: letzter bekannter, kein Blick nach vorn).
Ergebnis: Cache „benchmarks/SP500_ohne_finanzwerte“ und daten/benchmarks/sp500_ohne_finanzwerte.md (Kontrolle).
"""
import sys
import warnings
from datetime import datetime, timezone

import pandas as pd

from tradingbot.daten.cache import standard_cache
from tradingbot.daten.fehlerschwelle import FehlerschwelleUeberschritten, laut_melden
from tradingbot.daten.index_nachbau import ABNAHME_ZEITRAUM, marktwerte_aus_streubesitz
from tradingbot.daten.kurse import lade_kurse
from tradingbot.daten.sp500_nachbau import BENCHMARK_SCHLUESSEL, ENDE, START, VORLAUF, baue_nachbau, finanzwert_maske, lade_firmendaten
from tradingbot.daten.universum import lade_sic_historien, lade_universum
from tradingbot.konfiguration import PROJEKT_WURZEL

warnings.simplefilter("ignore")


def _jahre(reihe: pd.Series, ab) -> pd.Series:
    r = reihe.loc[pd.Timestamp(ab) - pd.Timedelta(days=7):].dropna()
    ende = r.groupby(r.index.year).last()
    erster = r.loc[:pd.Timestamp(ab)].iloc[-1] if len(r.loc[:pd.Timestamp(ab)]) else r.iloc[0]
    return pd.concat([pd.Series([erster], index=[ende.index[0] - 1]), ende]).pct_change().dropna()


def main() -> int:
    universum, _ = lade_universum()
    status = pd.read_csv(PROJEKT_WURZEL / "daten" / "universum" / "kursstatus.csv").set_index("index")
    daten = lade_firmendaten(universum, status, lade_sic_historien(universum))
    ohne = baue_nachbau(daten, ohne_finanzwerte=True)
    voll = baue_nachbau(daten)
    tage = ohne["tage"]

    eurusd = lade_kurse("EURUSD=X", VORLAUF, ENDE)["close"]
    eurusd = eurusd.reindex(eurusd.index.union(tage)).ffill().reindex(tage)
    usd = ohne["nachbau"]["index"]
    eur = 100 * (usd / usd.iloc[0]) / (eurusd / eurusd.iloc[0])
    tabelle = pd.DataFrame({"index_usd": usd, "index_eur": eur, "abdeckung": ohne["nachbau"]["abdeckung"], "eurusd": eurusd})
    tabelle.index.name = "datum"
    standard_cache().schreiben("benchmarks", BENCHMARK_SCHLUESSEL, tabelle, {
        "beschreibung": "S&P 500 ohne Finanzwerte (SIC 6000–6999 point-in-time), Nachbau aus dem point-in-time-Universum, Total Return",
        "gewichtung": "Streubesitz laut SEC-Deckblatt, gegen den Börsenwert geprüft (30–130 %), fortgeschrieben mit dem Kurs",
        "gegenprobe": "Lauf 4 bestanden (docs/DATENQUALITAET.md)", "gewertet_ab": ABNAHME_ZEITRAUM[0], "bis": str(ENDE.date()),
        "erstellt_am": datetime.now(timezone.utc).isoformat(timespec="seconds")})

    # Kontrolle: Jahresrenditen, Anteil der ausgeschlossenen Finanzwerte am vollen Nachbau
    firmen = list(voll["mitglied"].columns)
    fin = finanzwert_maske(daten.sic, tage, firmen) & voll["mitglied"]
    mw = marktwerte_aus_streubesitz(pd.DataFrame({f: (daten.kurse[f]["close"] if daten.kurse[f] is not None else pd.Series(dtype=float)) for f in firmen}),
                                    daten.streubesitz_gueltig).reindex(tage)
    anteil_fin = (mw.where(fin).sum(axis=1) / mw.where(voll["mitglied"]).sum(axis=1)).resample("YE").mean()
    spx = lade_kurse("^SP500TR", VORLAUF, ENDE)["close"]
    ab = ABNAHME_ZEITRAUM[0]
    j = pd.DataFrame({"ohne_fin_usd": _jahre(usd, ab), "ohne_fin_eur": _jahre(eur, ab), "voll_usd": _jahre(voll["nachbau"]["index"], ab),
                      "sp500tr_usd": _jahre(spx, ab), "anteil_finanzwerte": anteil_fin.groupby(anteil_fin.index.year).last()})
    ziel = PROJEKT_WURZEL / "daten" / "benchmarks"
    ziel.mkdir(parents=True, exist_ok=True)
    abn = tabelle["abdeckung"].loc[ab:]
    text = ["# Benchmark „S&P 500 ohne Finanzwerte“ – Kontrolle", "",
            f"Gewertet ab {ab} bis {ENDE.date()}; Abdeckung Median {abn.median():.1%}, Minimum {abn.min():.1%}. Abgelegt im Cache unter benchmarks/{BENCHMARK_SCHLUESSEL}.", "",
            "| Jahr | ohne Finanzwerte (USD) | ohne Finanzwerte (EUR) | Nachbau voll (USD) | S&P 500 TR (USD) | Gewicht Finanzwerte im vollen Nachbau |",
            "| --- | --- | --- | --- | --- | --- |"]
    text += [f"| {jahr}{' (ab ' + pd.Timestamp(ab).strftime('%d.%m.') + ')' if jahr == pd.Timestamp(ab).year else ''} | {r.ohne_fin_usd:.2%} | {r.ohne_fin_eur:.2%} | {r.voll_usd:.2%} | {r.sp500tr_usd:.2%} | {r.anteil_finanzwerte:.1%} |"
             for jahr, r in j.iterrows()]
    gesamt = lambda s: (s.loc[ab:].iloc[-1] / s.loc[:ab].iloc[-1]) ** (365.25 / (ENDE - pd.Timestamp(ab)).days) - 1  # noqa: E731
    text += ["", f"Annualisiert {ab} bis {ENDE.date()}: ohne Finanzwerte {gesamt(usd):.2%} (USD) / {gesamt(eur):.2%} (EUR); "
             f"voller Nachbau {gesamt(voll['nachbau']['index']):.2%}; S&P 500 TR {gesamt(spx):.2%} (USD)."]
    (ziel / "sp500_ohne_finanzwerte.md").write_text("\n".join(text), encoding="utf-8")
    print("\n".join(text))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FehlerschwelleUeberschritten as fehler:
        sys.exit(laut_melden(fehler))
