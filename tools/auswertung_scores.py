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
from tradingbot.engines.fundamental.aktienzahl import lade_aktienfakten, signal_alt_neu, vergleich_fuer_abschluesse
from tradingbot.engines.fundamental.kennzahlen import abschluesse_am, jahreswerte_firma, zusammenlegen
from tradingbot.engines.fundamental.multiples import marktwert_am, multiples, perzentil_raenge
from tradingbot.engines.fundamental.filter import anwenden as filter_anwenden
from tradingbot.engines.fundamental.scores import _w, accruals_quote, altman, beneish, piotroski
from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration

warnings.simplefilter("ignore")
Z2_GRUND = "Altman Z'' "


def main(argv=None) -> int:
    import argparse
    a = argparse.ArgumentParser(description="Fundamental-Scores je Stichtag")
    a.add_argument("--eq-offer-splitbereinigt", action="store_true",
                   help="Datenkorrektur Piotroski EQ_OFFER (Jakob 13.11.2026): Ergebnis in Cache „fundamental/scores_eq_offer“ "
                        "mit Vergleichsspalten zur bisherigen Rechnung; der Cache „fundamental/scores“ bleibt unberührt")
    korrektur = a.parse_args(argv).eq_offer_splitbereinigt
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
    werte, aktien, aktienfakten = {}, {}, {}
    for firma, kurse in daten.kurse.items():
        if isinstance(firma, str) or kurse is None:
            continue
        fehler = None
        try:
            zeile = daten.relevant[daten.relevant["cik"] == firma].iloc[0]
            erst = zusammenlegen([cache.lesen("sec_erstmeldungen", cik10(c))[0] for c in ciks_der_zeile(zeile)])
            werte[firma] = jahreswerte_firma(erst, kennzahlen)
            if korrektur:
                aktienfakten[firma] = lade_aktienfakten(ciks_der_zeile(zeile), cache=cache)
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
            eq = (vergleich_fuer_abschluesse(t, aktienfakten.get(firma), tag, daten.kurse[firma]["split"]) if korrektur else None)
            p, a, b, acc, m = (piotroski(t, eq_offer=eq), altman(t, industrie=industrie, marktwert_ek=mw), beneish(t), accruals_quote(t),
                               multiples(t, mw))
            try:
                cfo_t = _w(t, "operativer_cashflow", 0)
            except Exception:
                cfo_t = None
            cfo_t = None if cfo_t is None or pd.isna(cfo_t) else float(cfo_t)
            fe = filter_anwenden(sic=sic, piotroski=p, altman=a, beneish=b, cfo_t=cfo_t, konfig=konfig)
            if korrektur:                             # Vergleichsspalten: bisherige Rechnung und beide Wege (Gegenprobe)
                p_alt = piotroski(t)
                fe_alt = filter_anwenden(sic=sic, piotroski=p_alt, altman=a, beneish=b, cfo_t=cfo_t, konfig=konfig)
                eq_alt, eq_neu = signal_alt_neu(t, eq)
                e = eq or {}
                z.update({"eq_alt": eq_alt, "eq_neu": eq_neu, "eq_quelle": e.get("quelle"), "eq_split_faktor": e.get("split_faktor"),
                          "eq_t": e.get("wert_t"), "eq_t_tabelle": _w(t, "gewichtete_aktien", 0), "eq_vj_erst": e.get("wert_vj_erst"),
                          "eq_vj_tabelle": _w(t, "gewichtete_aktien", 1), "eq_vj_einreichung": e.get("wert_vj_einreichung"),
                          "eq_vj_split": e.get("wert_vj_split"), "eq_konzept": e.get("konzept"),
                          "piotroski_alt": p_alt["wert"], "piotroski_hochgerechnet_alt": p_alt["wert_hochgerechnet"] if p_alt["hochgerechnet"] else None,
                          "piotroski_n_alt": p_alt["anzahl_signale"], "ausgeschlossen_alt": fe_alt.ausgeschlossen,
                          "filter_gruende_alt": " | ".join(fe_alt.gruende)})
            z.update({"piotroski": p["wert"], "piotroski_fehlend": ";".join(p["fehlend"]),
                      "piotroski_n": p["anzahl_signale"], "piotroski_hochgerechnet": p["wert_hochgerechnet"] if p["hochgerechnet"] else None,
                      "cfo_t": cfo_t, "ausgeschlossen": fe.ausgeschlossen, "filter_gruende": " | ".join(fe.gruende),
                      "filter_hinweise": " | ".join(fe.hinweise),
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
    schluessel = "scores_eq_offer" if korrektur else "scores"
    cache.schreiben("fundamental", schluessel, tabelle.astype({"firma": "int64"}),
                    {"stichtage": len(stichtage), "zeitraum": list(ABNAHME_ZEITRAUM),
                     **({"datenkorrektur": "Piotroski EQ_OFFER splitbereinigt (Jakob 13.11.2026)"} if korrektur else {})})

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
    text += ["", "## Ausschlussquoten mit der Regel vom 02.11.2026 (an allen bewertbaren Firmen je Jahr)", "",
             "Piotroski: exakter Wert bei 9 Signalen, hochgerechnet bei 7–8, sonst übersprungen. Altman: Z hart im verarbeitenden Gewerbe "
             "(SIC 2000–3999), Versorger (SIC 49) ohne Altman, übrige Z'' nur mit zweitem Signal (Piotroski ≤ 3 oder CFO < 0). "
             "Beneish > −1,78 raus, fehlend übersprungen.", "",
             "| Jahr | Piotroski ≤ 3 | Altman Z Industrie | Z'' + 2. Signal | Z'' nur Warnhinweis | Beneish > −1,78 | ausgeschlossen gesamt | "
             "Piotroski hochgerechnet | Piotroski übersprungen | Beneish übersprungen |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for jahr, g in bewertbar.assign(jahr=bewertbar["stichtag"].dt.year).groupby("jahr"):
        gr, hw = g["filter_gruende"].fillna(""), g["filter_hinweise"].fillna("")
        text.append(f"| {jahr} | {anteil(gr.str.contains('Piotroski'), g)} | {anteil(gr.str.contains('verarbeitendes Gewerbe'), g)} | "
                    f"{anteil(gr.str.contains(Z2_GRUND, regex=False), g)} | {anteil(hw.str.contains('Warnhinweis'), g)} | "
                    f"{anteil(gr.str.contains('Beneish'), g)} | {anteil(g['ausgeschlossen'].fillna(False).astype(bool), g)} | "
                    f"{anteil(hw.str.contains('Piotroski hochgerechnet'), g)} | {anteil(hw.str.contains('Piotroski übersprungen'), g)} | "
                    f"{anteil(hw.str.contains('Beneish übersprungen'), g)} |")
    # Vergleich alte Regel (jeder Altman-Gefahrenzone raus) – damit die Wirkung der Entscheidung sichtbar bleibt
    alt = (bewertbar["piotroski"] <= 3) | (bewertbar["altman_zone"] == "gefahr") | (bewertbar["beneish"] > filt["beneish_max"])
    text += ["", f"Zum Vergleich alte Regel (jede Altman-Gefahrenzone raus, Piotroski nur bei 9 Signalen): {alt.mean():.0%} ausgeschlossen; "
             f"neue Regel: {bewertbar['ausgeschlossen'].fillna(False).astype(bool).mean():.0%}.", "",
             "## Je SIC-Division: Z''-Gefahrenzone nur Warnhinweis vs. ausgeschlossen (Firmen-Stichtage)", "",
             "| Division | bewertbar | Z'' Warnhinweis | Z'' + 2. Signal | ausgeschlossen gesamt |", "| --- | --- | --- | --- | --- |"]
    from tradingbot.engines.fundamental.multiples import sic_division
    bd = bewertbar.assign(division=bewertbar["sic"].map(sic_division))
    for div, g in bd.groupby("division"):
        gr, hw = g["filter_gruende"].fillna(""), g["filter_hinweise"].fillna("")
        text.append(f"| {div} | {len(g)} | {hw.str.contains('Warnhinweis').sum()} | {gr.str.contains(Z2_GRUND, regex=False).sum()} | "
                    f"{int(g['ausgeschlossen'].fillna(False).astype(bool).sum())} |")
    beispiele = bewertbar[bewertbar["filter_hinweise"].fillna("").str.contains("Warnhinweis")].sort_values("stichtag").groupby("firma").tail(1)
    text += ["", f"Firmen mit Z''-Warnhinweis am letzten Stichtag ({stichtage[-1].date()}): "
             f"{int((beispiele['stichtag'] == stichtage[-1]).sum())}"]
    fehlend = Counter(x.split("@")[0] for spalte in ("piotroski_fehlend", "altman_fehlend", "beneish_fehlend")
                      for v in bewertbar[spalte].dropna() for x in v.split(";") if x)
    gruende_mw = bewertbar["marktwert_grund"].dropna().str.replace(r"[\d.,]+", "x", regex=True).value_counts().head(5).to_dict()
    text += ["", "## Häufigste fehlende Posten (Anzahl Firmen-Stichtage)", "", ", ".join(f"{k}: {v}" for k, v in fehlend.most_common(12)), "",
             f"Kein Marktwert, Gründe: {gruende_mw}", "",
             f"Negativer EV (markiert, ohne EBIT/EV): {int(bewertbar['ev_negativ'].fillna(False).sum())} Firmen-Stichtage."]
    ziel = PROJEKT_WURZEL / "daten" / "fundamental"
    ziel.mkdir(parents=True, exist_ok=True)
    (ziel / ("auswertung_scores_eq_offer.md" if korrektur else "auswertung_scores.md")).write_text("\n".join(text), encoding="utf-8")
    print("\n".join(text))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FehlerschwelleUeberschritten as fehler:
        sys.exit(laut_melden(fehler))
