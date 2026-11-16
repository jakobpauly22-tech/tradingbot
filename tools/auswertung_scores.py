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
from tradingbot.daten.kapitalmassnahmen_historie import lade_ereignisse
from tradingbot.engines.fundamental.multiples import marktwert_am, marktwert_korrigiert, marktwert_rohkurs, multiples, perzentil_raenge
from tradingbot.engines.fundamental.filter import anwenden as filter_anwenden
from tradingbot.engines.fundamental.scores import _w, accruals_quote, altman, beneish, piotroski
from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration

warnings.simplefilter("ignore")
Z2_GRUND = "Altman Z'' "
GRUND_UNSICHER = "Abnahme nicht bestanden, H ≠ 1"


def rueckfall_tabelle(tabelle: pd.DataFrame, rohkurse_status: dict, unsicher: dict, namen: dict) -> list[str]:
    """Befund 11 (Jakob 16.11.2026): Firmen ohne Rohkurs-Marktwert (Rückfall auf Teil b oder, Variante B, kein Marktwert)
    mit Grund, H-Schätzung und Zahl der Firmen-Stichtage. `tabelle` braucht die Spalten firma, veraltet, marktwert_kurs."""
    if "marktwert_kurs" not in tabelle.columns:
        return []
    b = tabelle[(tabelle["veraltet"] == False) & tabelle["marktwert_kurs"].notna() & (tabelle["marktwert_kurs"] != "roh")]  # noqa: E712
    text = ["", f"## Rückfall ohne Rohkurs-Marktwert (Befund 11): {b['firma'].nunique()} Firmen, {len(b)} Firmen-Stichtage", "",
            "Variante B: Abnahme nicht bestanden und |H − 1| > 0,5 % → kein Marktwert (fällt bei den Multiples heraus); sonst Teil b.", "",
            "| Firma | Ticker | Kurs | Grund | H | Firmen-Stichtage | davon ohne Marktwert |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for firma, g in b.groupby("firma"):
        u = unsicher.get(firma, {})
        h = f"{u['H']:.4g}" if u else "–"
        text.append(f"| {firma} | {namen.get(firma, '')} | {g['marktwert_kurs'].iloc[-1]} | {rohkurse_status.get(firma, '')} | {h} | {len(g)} | "
                    f"{int(g['marktwert'].isna().sum()) if 'marktwert' in g else 0} |")
    return text


def marktwert_wahl(mr: dict, mw_teil_b, grund_teil_b) -> tuple:
    """c2 (2): Marktwert aus dem Rohkurs; gibt es bis zum Stichtag keinen Rohkurs (Rohreihe beginnt später, z. B. LIN
    ab 31.10.2018), Rückfall auf Teil b wie bei fehlender Rohreihe. Rückgabe (Marktwert, Grund, Kennzeichen Kurs)."""
    if str(mr.get("grund") or "").startswith("kein Rohkurs"):
        return mw_teil_b, grund_teil_b, "Rohkurs erst nach dem Stichtag (Teil b)"
    return mr["marktwert"], mr["grund"], "roh"


def main(argv=None) -> int:
    import argparse
    a = argparse.ArgumentParser(description="Fundamental-Scores je Stichtag")
    a.add_argument("--eq-offer-splitbereinigt", action="store_true",
                   help="Datenkorrektur Piotroski EQ_OFFER (Jakob 13.11.2026): Ergebnis in Cache „fundamental/scores_eq_offer“ "
                        "mit Vergleichsspalten zur bisherigen Rechnung; der Cache „fundamental/scores“ bleibt unberührt")
    a.add_argument("--marktwert-korrektur", action="store_true",
                   help="Datenkorrektur Marktwert (Jakob 13.11.2026): Abspaltungen nicht als Split, Ersatz-Aktienzahl; "
                        "Vergleichsspalten zur bisherigen Rechnung, eigener Cache-Schlüssel (Zusatz „_marktwert“)")
    a.add_argument("--marktwert-rohkurse", action="store_true",
                   help="c2 (2), Jakob 15.11.2026: Marktwert aus unbereinigten Rohkursen (Weg A), schließt --marktwert-korrektur ein; "
                        "Rückfall auf Teil b je Firma ohne abgenommene Rohreihe; eigener Cache-Schlüssel (Zusatz „_roh“). "
                        "Sperre c3: startet nur, wenn jede Reihe eine Abnahme hat (tools/pruefe_rohkurse.py)")
    a.add_argument("--probe", action="store_true",
                   help="mit --marktwert-rohkurse: Teilabdeckung erlaubt (Zusatz „_probe“); zählt nie als c3")
    argumente = a.parse_args(argv)
    korrektur, mw_korrektur, mw_roh = argumente.eq_offer_splitbereinigt, argumente.marktwert_korrektur, argumente.marktwert_rohkurse
    mw_korrektur = mw_korrektur or mw_roh
    if mw_roh and not argumente.probe:
        from tradingbot.daten import rohkurse_marktwert as rm

        sperre = rm.sperrtext(rm.sperre_c3())     # Reihen ohne Abnahme und, seit Befund 14, Fehlerschwelle der Abnahme
        if sperre:
            return laut_melden(RuntimeError(sperre))
    konfig = lade_konfiguration("fundamental")
    kennzahlen, filt, mult = konfig["kennzahlen"], konfig["filter"], konfig["multiples"]
    aktualitaet = konfig["kennzahlen_regeln"]["aktualitaet_monate"]
    industrie_von, industrie_bis = filt["altman"]["industrie_sic"]
    universum, _ = lade_universum()
    status = pd.read_csv(PROJEKT_WURZEL / "daten" / "universum" / "kursstatus.csv").set_index("index")
    daten = lade_firmendaten(universum, status, lade_sic_historien(universum), mitglied_ab=ABNAHME_ZEITRAUM[0], rohkurse=mw_roh)
    stichtage = [t for t in rebalancing_stichtage() if t >= pd.Timestamp(ABNAHME_ZEITRAUM[0])]
    cache = standard_cache()

    # je Firma einmal: Jahreswerte und Aktienzahl
    schwelle = Fehlerschwelle("Scores: Jahreswerte je Firma")
    werte, aktien, aktienfakten, aktien_roh, ersatz_fakten = {}, {}, {}, {}, {}
    ereignisse = lade_ereignisse() if mw_korrektur else {}
    max_alter = konfig.get("marktwert_korrektur", {}).get("aktien_max_alter_monate", 15)
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
            if mw_korrektur:
                ersatz_fakten[firma] = lade_aktienfakten(ciks_der_zeile(zeile), cache=cache, mit_quartalen=True)
                if len(a):
                    aktien_roh[firma] = a[["wert", "filed"]]
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
            if mw_korrektur:                         # Datenkorrektur Marktwert; bisherige Werte als Vergleichsspalten
                mk = marktwert_korrigiert(tag, daten.kurse[firma], aktien_roh.get(firma), daten.streubesitz_gueltig.get(firma),
                                          ereignisse=ereignisse.get(firma), ersatz_fakten=ersatz_fakten.get(firma), max_alter_monate=max_alter)
                z.update({"marktwert_alt": mw, "marktwert_grund_alt": mw_grund, "marktwert_quelle": mk["quelle"],
                          "marktwert_korrekturfaktor": mk["korrektur"], "marktwert_aktien_filed": mk["aktien_filed"],
                          "marktwert_ungeklaert": "; ".join(f"{u['datum']} {u['faktor_kursreihe']:g} ({u['art']})" for u in mk["ungeklaert"]),
                          "ep_alt": multiples(t, mw)["ep"], "ebit_ev_alt": multiples(t, mw)["ebit_ev"]})
                mw, mw_grund = mk["marktwert"], mk["grund"]
                if mw_roh:                           # c2 (2): Rohkurs; Teil b als Vergleich und Rückfall
                    z.update({"marktwert_teil_b": mw, "marktwert_grund_teil_b": mw_grund,
                              "marktwert_kurs": daten.rohkurse_status.get(firma, "keine Kursreihe")})
                    if daten.rohkurse_status.get(firma) == "roh":
                        mr = marktwert_rohkurs(tag, daten.rohkurse[firma], daten.kurse[firma], aktien_roh.get(firma),
                                               daten.streubesitz_gueltig.get(firma), ereignisse=ereignisse.get(firma),
                                               ersatz_fakten=ersatz_fakten.get(firma), max_alter_monate=max_alter)
                        z.update({"marktwert_splitfaktor_roh": mr["splitfaktor"], "marktwert_rohkurs": mr["rohkurs"],
                                  "marktwert_ungeklaert_roh": "; ".join(f"{x['datum']} {x['faktor_kursreihe']:g} ({x['art']})" for x in mr["ungeklaert"])})
                        mw, mw_grund, kurs = marktwert_wahl(mr, mw, mw_grund)
                        z["marktwert_kurs"] = kurs
                    elif firma in daten.rohkurse_unsicher:   # Befund 11, Variante B: Teil b enthielte den verdeckten Faktor
                        u = daten.rohkurse_unsicher[firma]
                        mw, mw_grund = None, f"{GRUND_UNSICHER} ({u['symbol']}, H {u['H']:.4g})"
                        z["marktwert_kurs"] = "kein Marktwert (Befund 11)"
            industrie = industrie_von <= sic <= industrie_bis
            # Weg B: mit Datenkorrektur Marktwert (also in c3) nur echte Splits, Abspaltungen der Liste s = 1 (Befund 13)
            eq = (vergleich_fuer_abschluesse(t, aktienfakten.get(firma), tag, daten.kurse[firma]["split"],
                                             ereignisse=ereignisse.get(firma) if mw_korrektur else None) if korrektur else None)
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
    schluessel = ("scores" + ("_eq_offer" if korrektur else "") + ("_marktwert" if mw_korrektur else "") + ("_roh" if mw_roh else "")
                  + ("_probe" if mw_roh and argumente.probe else ""))
    cache.schreiben("fundamental", schluessel, tabelle.astype({"firma": "int64"}),
                    {"stichtage": len(stichtage), "zeitraum": list(ABNAHME_ZEITRAUM),
                     "datenkorrekturen": (["Piotroski EQ_OFFER splitbereinigt (Jakob 13.11.2026)"] if korrektur else [])
                     + (["Marktwert: Abspaltungen, Ersatz-Aktienzahl, Kursreihe E. I. du Pont gekappt (Jakob 13.11.2026)"] if mw_korrektur else [])
                     + (["Marktwert aus Rohkursen, Weg A (Jakob 15.11.2026)" + (" – PROBE, zählt nicht als c3" if argumente.probe else "")]
                        if mw_roh else [])})

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
    if mw_roh:
        namen = {int(z["cik"]): z["ticker"] for _, z in daten.relevant.iterrows() if pd.notna(z["cik"])}
        text += rueckfall_tabelle(tabelle, daten.rohkurse_status, daten.rohkurse_unsicher, namen)
    ziel = PROJEKT_WURZEL / "daten" / "fundamental"
    ziel.mkdir(parents=True, exist_ok=True)
    # eigener Bericht je Schalter (scores_eq_offer, scores_marktwert, scores_marktwert_roh[_probe]); Basisbericht bleibt
    (ziel / (f"auswertung_{schluessel}.md" if (korrektur or mw_korrektur) else "auswertung_scores.md")).write_text("\n".join(text), encoding="utf-8")
    print("\n".join(text))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FehlerschwelleUeberschritten as fehler:
        sys.exit(laut_melden(fehler))
