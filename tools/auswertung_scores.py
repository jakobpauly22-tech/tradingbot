r"""Fundamental-Scores je Rebalancing-Stichtag für das investierbare Universum (Sitzung 3).

Aufruf:  .venv\Scripts\python tools\auswertung_scores.py
Ergebnis: Cache „fundamental/scores“ (eine Zeile je Stichtag und Firma) und daten/fundamental/auswertung_scores.md
Investierbar: Mitglied am Stichtag, kein Finanzwert (SIC point-in-time), gültige Kursreihe (kaufbar).
Je Firma werden die Jahreswerte einmal berechnet (kennzahlen.jahreswerte_firma) und je Stichtag gefiltert.
Fehlerschwelle 5 % (Ausnahmen beim Berechnen je Firma).
"""
import sys
import warnings
from collections import Counter

import pandas as pd

from tradingbot.daten.abdeckung import rebalancing_stichtage
from tradingbot.daten.cache import standard_cache
from tradingbot.daten.fehlerschwelle import Fehlerschwelle, FehlerschwelleUeberschritten, laut_melden
from tradingbot.daten.index_nachbau import ABNAHME_ZEITRAUM, aktien_splitbereinigt
from tradingbot.daten.sec import cik10, kennzahl_jahreswerte
from tradingbot.daten.sp500_nachbau import ciks_der_zeile, firmen_schluessel, lade_firmendaten
from tradingbot.daten.universum import lade_sic_historien, lade_universum, mitglieder_am, sic_am
from tradingbot.engines.fundamental.kennzahlen import abschluesse_am, jahreswerte_firma, zusammenlegen
from tradingbot.engines.fundamental.multiples import marktwert_am, multiples, perzentil_raenge
from tradingbot.engines.fundamental.scores import accruals_quote, altman, beneish, piotroski
from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration

warnings.simplefilter("ignore")


def main() -> int:
    konfig = lade_konfiguration("fundamental")
    kennzahlen, filt, mult = konfig["kennzahlen"], konfig["filter"], konfig["multiples"]
    aktualitaet = konfig["kennzahlen_regeln"]["aktualitaet_monate"]
    industrie_von, industrie_bis = filt["altman"]["industrie_sic"]
    universum, _ = lade_universum()
    status = pd.read_csv(PROJEKT_WURZEL / "daten" / "universum" / "kursstatus.csv").set_index("index")
    daten = lade_firmendaten(universum, status, lade_sic_historien(universum), mitglied_ab=ABNAHME_ZEITRAUM[0])
    stichtage = [t for t in rebalancing_stichtage() if t >= pd.Timestamp(ABNAHME_ZEITRAUM[0])]
    cache = standard_cache()

    # je Firma einmal: Jahreswerte und Aktienzahl
    schwelle = Fehlerschwelle("Scores: Jahreswerte je Firma")
    werte, aktien = {}, {}
    for firma, kurse in daten.kurse.items():
        if isinstance(firma, str) or kurse is None:
            continue
        fehler = None
        try:
            zeile = daten.relevant[daten.relevant["cik"] == firma].iloc[0]
            erst = zusammenlegen([cache.lesen("sec_erstmeldungen", cik10(c))[0] for c in ciks_der_zeile(zeile)])
            werte[firma] = jahreswerte_firma(erst, kennzahlen)
            a = kennzahl_jahreswerte(erst, kennzahlen["aktien_ausstehend"], "2100-01-01") if len(erst) else pd.DataFrame()
            if len(a):
                bereinigt = aktien_splitbereinigt(a["wert"], kurse["split"])
                aktien[firma] = pd.Series(bereinigt.to_numpy(), index=(a["filed"] + pd.Timedelta(days=1)).to_numpy()).sort_index()
        except Exception as f:  # zählt gegen die Fehlerschwelle
            fehler = f"{firma}: {type(f).__name__} {str(f)[:60]}"
        schwelle.zaehle(fehler)
    schwelle.pruefe()

    zeilen = []
    for tag in stichtage:
        mitglieder = mitglieder_am(daten.relevant, tag)
        firmen = {firmen_schluessel(z, nr) for nr, z in mitglieder.iterrows()}
        for firma in sorted(f for f in firmen if f in werte):
            sic = sic_am(daten.sic.get(firma, []), tag)
            if sic is None or 6000 <= sic <= 6999:
                continue
            t, info = abschluesse_am(werte[firma], tag, aktualitaet_monate=aktualitaet)
            z = {"stichtag": tag, "firma": firma, "sic": sic, "ende_t": info["ende_t"], "veraltet": info["veraltet"],
                 "abgeleitet": len(info["abgeleitet"])}
            if t.empty or info["veraltet"]:
                z["grund"] = info["grund"]
                zeilen.append(z)
                continue
            mw, mw_grund = marktwert_am(tag, daten.kurse[firma]["close"], aktien.get(firma, pd.Series(dtype=float)),
                                        daten.streubesitz_gueltig.get(firma))
            industrie = industrie_von <= sic <= industrie_bis
            p, a, b, acc, m = piotroski(t), altman(t, industrie=industrie, marktwert_ek=mw), beneish(t), accruals_quote(t), multiples(t, mw)
            z.update({"piotroski": p["wert"], "piotroski_fehlend": ";".join(p["fehlend"]),
                      "altman": a["wert"], "altman_variante": a["variante"], "altman_zone": a.get("zone"), "altman_fehlend": ";".join(a["fehlend"]),
                      "beneish": b["wert"], "beneish_fehlend": ";".join(b["fehlend"]), "accruals": acc["wert"],
                      "marktwert": mw, "marktwert_grund": mw_grund, "ep": m["ep"], "ebit_ev": m["ebit_ev"], "ev_negativ": m["ev_negativ"]})
            zeilen.append(z)

    tabelle = pd.DataFrame(zeilen)
    raenge = []
    for tag, gruppe in tabelle[tabelle["veraltet"] == False].groupby("stichtag"):  # noqa: E712
        raenge.append(perzentil_raenge(gruppe, min_firmen=mult["gruppe_min_firmen"], kappung=tuple(mult["kappung_perzentile"])))
    tabelle = tabelle.merge(pd.concat(raenge)[["stichtag", "firma", "gruppe_ep", "rang_ep", "gruppe_ebit_ev", "rang_ebit_ev"]],
                            on=["stichtag", "firma"], how="left")
    cache.schreiben("fundamental", "scores", tabelle.astype({"firma": "int64"}), {"stichtage": len(stichtage), "zeitraum": list(ABNAHME_ZEITRAUM)})

    # --- Bericht ------------------------------------------------------------------------------
    b = tabelle.assign(jahr=tabelle["stichtag"].dt.year)
    bewertbar = b[~b["veraltet"]]
    def anteil(maske, basis):
        return f"{maske.sum() / max(len(basis), 1):.0%}"
    text = ["# Fundamental-Scores je Stichtag – Auswertung", "",
            f"{len(stichtage)} Rebalancing-Stichtage {stichtage[0].date()} bis {stichtage[-1].date()}; investierbar = Mitglied, kein Finanzwert, gültige Kurse.", "",
            "## Abdeckung je Jahr (Durchschnitt über die Stichtage)", "",
            "| Jahr | Firmen je Stichtag | veraltet / ohne GJ | Piotroski | Altman | Beneish | Marktwert | E/P-Rang | EBIT/EV-Rang | mit Ableitung |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for jahr, g in b.groupby("jahr"):
        gb = g[~g["veraltet"]]
        n = len(g) / g["stichtag"].nunique()
        text.append(f"| {jahr} | {n:.0f} | {anteil(g['veraltet'], g)} | {anteil(gb['piotroski'].notna(), g)} | {anteil(gb['altman'].notna(), g)} | "
                    f"{anteil(gb['beneish'].notna(), g)} | {anteil(gb['marktwert'].notna(), g)} | {anteil(gb['rang_ep'].notna(), g)} | "
                    f"{anteil(gb['rang_ebit_ev'].notna(), g)} | {anteil(gb['abgeleitet'] > 0, g)} |")
    text += ["", "## Anteil, den jeder Filter ausschließt (an den Firmen mit berechnetem Score)", "",
             "| Jahr | Piotroski ≤ 3 | Altman Gefahrenzone | Beneish > −1,78 | mindestens ein Filter (an allen bewertbaren) |", "| --- | --- | --- | --- | --- |"]
    for jahr, g in bewertbar.assign(jahr=bewertbar["stichtag"].dt.year).groupby("jahr"):
        p = g["piotroski"].dropna(); a = g["altman_zone"].dropna(); m = g["beneish"].dropna()
        raus = (g["piotroski"] <= 3) | (g["altman_zone"] == "gefahr") | (g["beneish"] > filt["beneish_max"])
        text.append(f"| {jahr} | {(p <= 3).mean():.0%} | {(a == 'gefahr').mean():.0%} | {(m > filt['beneish_max']).mean():.0%} | {raus.mean():.0%} |")
    fehlend = Counter(x.split("@")[0] for spalte in ("piotroski_fehlend", "altman_fehlend", "beneish_fehlend")
                      for v in bewertbar[spalte].dropna() for x in v.split(";") if x)
    gruende_mw = bewertbar["marktwert_grund"].dropna().str.replace(r"[\d.,]+", "x", regex=True).value_counts().head(5).to_dict()
    text += ["", "## Häufigste fehlende Posten (Anzahl Firmen-Stichtage)", "", ", ".join(f"{k}: {v}" for k, v in fehlend.most_common(12)), "",
             f"Kein Marktwert, Gründe: {gruende_mw}", "",
             f"Negativer EV (markiert, ohne EBIT/EV): {int(bewertbar['ev_negativ'].fillna(False).sum())} Firmen-Stichtage."]
    ziel = PROJEKT_WURZEL / "daten" / "fundamental"
    ziel.mkdir(parents=True, exist_ok=True)
    (ziel / "auswertung_scores.md").write_text("\n".join(text), encoding="utf-8")
    print("\n".join(text))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FehlerschwelleUeberschritten as fehler:
        sys.exit(laut_melden(fehler))
