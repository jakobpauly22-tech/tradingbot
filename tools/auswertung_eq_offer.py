r"""Wirkung der Datenkorrektur Piotroski EQ_OFFER (Jakob 13.11.2026) auf Signale, Filter und Auswahl, ohne Kennzahlen.

Aufruf:  .venv\Scripts\python tools\auswertung_eq_offer.py
Voraussetzung: Cache „fundamental/scores_eq_offer“ (tools\auswertung_scores.py --eq-offer-splitbereinigt).
Ergebnis: docs/berichte/2026-11-13_piotroski_eq_offer.md (Abschnitte Signale, Gegenprobe, Filter, Auswahl A und B).

Gewerteter Zeitraum laut config/fundamental.yaml `backtest` (01.10.2016 bis 31.12.2024), Tresor bleibt zu.
Die Auswahl je Stichtag wird ohne Kurse nachgestellt (Mitgliedschaft: gehaltene Titel mit Zielgewicht, Puffer 30,
Branchengrenze, 20 Titel); das genügt, um geänderte Titel zu zählen. Kennzahlen kommen aus dem Neulauf
(tools\backtest_fundamental.py), für B nur nach ausdrücklicher Entscheidung (Rückschaufehler, docs/FUNDAMENTAL.md).
"""
import sys
import warnings
from pathlib import Path

import pandas as pd

from tradingbot.daten.cache import standard_cache
from tradingbot.engines.fundamental.aktuell import konfig_variante
from tradingbot.engines.fundamental.filter import piotroski_fuer_filter
from tradingbot.engines.fundamental.schatten import auswahl
from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration

sys.path.insert(0, str(Path(__file__).parent))
from backtest_fundamental import ranglisten_aus_scores  # noqa: E402

warnings.simplefilter("ignore")
BERICHT = PROJEKT_WURZEL / "docs" / "berichte" / "2026-11-13_piotroski_eq_offer.md"
SPLIT_VERDACHT = (0.7, 1.4)        # Verhältnis t / t−1 außerhalb dieses Bands ohne Split-Ereignis: möglicher Split ohne Ereignis


def _nn(x):
    return None if pd.isna(x) else x


def piotroski_wert(wert, hoch) -> float | None:
    p = {"wert": _nn(wert), "wert_hochgerechnet": _nn(hoch)}
    w = piotroski_fuer_filter(p)
    return None if w is None else float(w)


def _skalierung(r) -> bool:
    """Verhältnis ≈ 10^(±3k): Erstmeldung oder Vergleichswert in Tausend statt Stück (XBRL-Skalierungsfehler)."""
    import math
    if r is None or pd.isna(r) or r <= 0:
        return False
    e = math.log10(r)
    return abs(e) >= 2.5 and abs(e - 3 * round(e / 3)) < 0.01


def _klasse(a, erst, faktor) -> str:
    """Ursache einer Abweichung zwischen Weg A und der Erstmeldung bzw. Weg B."""
    if erst and _skalierung(a / erst):
        return "Skalierungsfehler der Erstmeldung"
    if faktor is not None and not pd.isna(faktor) and faktor != 1.0 and abs(a / (erst * faktor) - 1) > 0.01:
        return "Faktor der Kursreihe passt nicht (z. B. Abspaltung als Split geführt)"
    if faktor is None or pd.isna(faktor) or faktor == 1.0:
        return "ohne Split-Ereignis (fehlendes Ereignis, Aktiendividende oder Neuausweis)"
    return "sonstige"


def alte_rechnung(scores: pd.DataFrame) -> pd.DataFrame:
    """Dieselbe Tabelle mit den Piotroski-Werten der bisherigen Rechnung (Spalten *_alt)."""
    return scores.assign(piotroski=scores["piotroski_alt"], piotroski_hochgerechnet=scores["piotroski_hochgerechnet_alt"],
                         piotroski_n=scores["piotroski_n_alt"])


def mitgliedschaft(ranglisten: dict, konfig: dict) -> dict[pd.Timestamp, set[str]]:
    """Auswahl je Stichtag ohne Kurse: gehaltene Titel mit Zielgewicht 1/titel (kein Drift), sonst Regeln wie im Backtest."""
    sp = konfig["schattenportfolio"]
    titel = int(sp["titel"])
    gehalten: set[str] = set()
    ergebnis = {}
    for tag in sorted(ranglisten):
        gewichte = pd.Series({t: 1.0 / titel for t in gehalten}, dtype=float)
        ziel, _ = auswahl(ranglisten[tag], gewichte, titel=titel, puffer=int(sp["puffer_rang"]),
                          max_je_branche=int(float(sp["max_branchenanteil"]) * titel), band=tuple(float(x) for x in sp["drift_band"]))
        gehalten = {t for t, w in ziel.items() if pd.isna(w) or w > 0}
        ergebnis[tag] = set(gehalten)
    return ergebnis


def main() -> int:
    konfig = lade_konfiguration("fundamental")
    start, ende = pd.Timestamp(str(konfig["backtest"]["gewertet_ab"])), pd.Timestamp(str(konfig["backtest"]["gewertet_bis"]))
    cache = standard_cache()
    scores, meta = cache.lesen("fundamental", "scores_eq_offer")
    if scores is None:
        raise SystemExit("Cache fundamental/scores_eq_offer fehlt: tools/auswertung_scores.py --eq-offer-splitbereinigt")
    alt_cache, _ = cache.lesen("fundamental", "scores")
    uni, _ = cache.lesen("universum", "sp500")
    namen = {int(z["cik"]): z["ticker"] for _, z in uni.sort_values("von", na_position="first").iterrows() if pd.notna(z["cik"])}
    name = lambda f: namen.get(int(f), f"CIK{int(f)}")  # noqa: E731
    s = scores[(scores["stichtag"] >= start) & (scores["stichtag"] <= ende) & ~scores["veraltet"].astype(bool)].copy()
    s["jahr"] = s["stichtag"].dt.year
    text = ["# Datenkorrektur Piotroski „keine neuen Aktien“: Wirkung auf Signale, Filter und Auswahl", "",
            f"Erstellt mit `tools/auswertung_eq_offer.py` aus dem Cache `fundamental/scores_eq_offer` ({meta.get('datenkorrektur', '')}). "
            f"Zeitraum {start.date()} bis {ende.date()} ({s['stichtag'].nunique()} Stichtage), Tresor zu. "
            "Die Korrektur wurde vor dieser Auswertung als übernommen festgehalten (docs/FUNDAMENTAL.md); diese Zahlen dokumentieren "
            "nur die Wirkung.", ""]

    # --- Kontrolle: bisherige Rechnung im neuen Cache = alter Cache -----------------------------------------------
    if alt_cache is not None:
        a = alt_cache[(alt_cache["stichtag"] >= start) & (alt_cache["stichtag"] <= ende) & ~alt_cache["veraltet"].astype(bool)]
        v = a.merge(s, on=["stichtag", "firma"], suffixes=("_cache", ""))
        gleich = ((v["piotroski_cache"].fillna(-1) == v["piotroski_alt"].fillna(-1))
                  & (v["ausgeschlossen_cache"].astype(bool) == v["ausgeschlossen_alt"].astype(bool)))
        text += [f"Kontrolle: bisherige Rechnung im neuen Lauf gegen den Cache `fundamental/scores` vom ersten Lauf: "
                 f"{int(gleich.sum())} von {len(v)} Firmen-Stichtagen gleich (Piotroski und Ausschluss); "
                 f"Zeilen nur in einem der beiden: {abs(len(a) - len(s))}. Piotroski-Werte verschieden: "
                 f"{int((v['piotroski_cache'].fillna(-1) != v['piotroski_alt'].fillna(-1)).sum())}. Die übrigen Abweichungen betreffen nur "
                 "die gespeicherte Spalte „ausgeschlossen“ (der alte Cache stammt von vor der Rundungsregel für hochgerechnete "
                 "Piotroski-Werte; der Backtest wendet die Filter ohnehin neu an) oder Marktwerte nach späteren Kursdaten. Deshalb wird "
                 "der Vergleichslauf aus demselben Cache gerechnet (Spalten der bisherigen Rechnung, Cache `fundamental/scores_eq_offer_bisher`), "
                 "nicht aus dem alten.", ""]
    cache.schreiben("fundamental", "scores_eq_offer_bisher", alte_rechnung(scores).astype({"firma": "int64"}),
                    {**meta, "datenkorrektur": "Vergleich: bisherige Rechnung EQ_OFFER aus scores_eq_offer (Jakob 13.11.2026)"})

    # --- Quelle der Vergleichswerte ---------------------------------------------------------------------------------
    hat_eq = s["eq_alt"].notna() | s["eq_neu"].notna()
    q = s.loc[hat_eq, "eq_quelle"].fillna("keine").value_counts()
    text += ["## Quelle des Vorjahreswerts", "",
             f"Firmen-Stichtage mit Signal EQ_OFFER: {int(hat_eq.sum())}. Weg A (Vergleichswert aus derselben Einreichung): "
             f"{int(q.get('einreichung', 0))}; Rückfall B (Erstmeldung mit Split-Faktoren): {int(q.get('split', 0))}; "
             f"keine bekannte Aktienzahl im neuen Weg (Rückfall auf die bisherige Rechnung): {int(q.get('keine', 0))}.", ""]
    kons_t = s["eq_t"].notna() & s["eq_t_tabelle"].notna() & (s["eq_t"] != s["eq_t_tabelle"])
    kons_vj = s["eq_vj_erst"].notna() & s["eq_vj_tabelle"].notna() & (s["eq_vj_erst"] != s["eq_vj_tabelle"])
    text += [f"Konsistenz mit der Tabelle der Abschlüsse: Wert t abweichend in {int(kons_t.sum())}, Erstmeldung t−1 abweichend in "
             f"{int(kons_vj.sum())} Firmen-Stichtagen.", ""]

    # --- Signale ------------------------------------------------------------------------------------------------------
    beide = s["eq_alt"].notna() & s["eq_neu"].notna()
    d = s[beide]
    geaendert = d[d["eq_alt"] != d["eq_neu"]]
    text += ["## Signal „keine neuen Aktien“: geänderte Fälle", "",
             f"Mit beiden Werten: {len(d)} Firmen-Stichtage; geändert {len(geaendert)} ({len(geaendert) / max(len(d), 1):.2%}), "
             f"davon 0→1 (bisher fälschlich „neue Aktien“) {int((geaendert['eq_neu'] == 1).sum())}, 1→0 {int((geaendert['eq_neu'] == 0).sum())}. "
             f"Betroffene Firmen: {geaendert['firma'].nunique()}.", "",
             "| Jahr | Firmen-Stichtage | geändert | 0→1 | 1→0 | Firmen |", "| --- | --- | --- | --- | --- | --- |"]
    for j, g in d.groupby("jahr"):
        x = g[g["eq_alt"] != g["eq_neu"]]
        text.append(f"| {j} | {len(g)} | {len(x)} | {int((x['eq_neu'] == 1).sum())} | {int((x['eq_neu'] == 0).sum())} | {x['firma'].nunique()} |")
    mit_split = geaendert["eq_split_faktor"].fillna(1.0) != 1.0
    text += ["", f"Davon mit Split-Ereignis zwischen den Einreichungen: {int(mit_split.sum())}; ohne Split-Ereignis: {int((~mit_split).sum())}.", "",
             "Geänderte Firmen (Ticker, Split-Faktor, Anzahl Stichtage):", ""]
    je = geaendert.groupby("firma").agg(n=("stichtag", "size"), faktor=("eq_split_faktor", "max"), von=("stichtag", "min")).sort_values("von")
    text.append(", ".join(f"{name(f)} ({z.faktor:g}, {z.n})" for f, z in je.iterrows()) or "–")

    # --- Gegenprobe A gegen B -------------------------------------------------------------------------------------
    ab = s[s["eq_vj_einreichung"].notna() & s["eq_vj_split"].notna() & s["eq_t"].notna()]
    sig_a, sig_b = (ab["eq_t"] <= ab["eq_vj_einreichung"]), (ab["eq_t"] <= ab["eq_vj_split"])
    unterschied = ab[sig_a != sig_b]
    rel = (ab["eq_vj_einreichung"] / ab["eq_vj_split"] - 1).abs()
    text += ["", "## Gegenprobe Weg A gegen Weg B", "",
             f"Beide Wege verfügbar: {len(ab)} Firmen-Stichtage. Gleiches Signal: {int((sig_a == sig_b).sum())}; verschieden: {len(unterschied)}. "
             f"Abweichung der Vorjahreswerte: Median {rel.median():.3%}, über 1 %: {int((rel > 0.01).sum())}, über 10 %: {int((rel > 0.10).sum())}.", ""]
    if len(unterschied):
        u = unterschied.assign(r=unterschied["eq_vj_einreichung"] / unterschied["eq_vj_split"],
                               klasse=[_klasse(a, e, f) for a, e, f in zip(unterschied["eq_vj_einreichung"], unterschied["eq_vj_erst"],
                                                                           unterschied["eq_split_faktor"])])
        text += ["Ursachen (Firmen-Stichtage): " + ", ".join(f"{k} {n}" for k, n in u["klasse"].value_counts().items()) + ".", "",
                 "Verschiedene Signale je Firma (Ticker, Faktor der Kursreihe, Verhältnis A/B, Ursache, Stichtage):", "",
                 ", ".join(f"{name(f)} ({g['eq_split_faktor'].iloc[0]:g}, {g['r'].median():.3f}, {g['klasse'].iloc[0]}, {len(g)})"
                           for f, g in u.groupby("firma", sort=False)), ""]

    # --- A weicht von der Erstmeldung ab, ohne Split -------------------------------------------------------------
    ohne = s[(s["eq_quelle"] == "einreichung") & (s["eq_split_faktor"].fillna(1.0) == 1.0) & s["eq_vj_erst"].notna()]
    rel_e = (ohne["eq_vj_einreichung"] / ohne["eq_vj_erst"] - 1)
    abw = ohne[rel_e != 0]
    abw_sig = abw[(abw["eq_t"] <= abw["eq_vj_einreichung"]) != (abw["eq_t"] <= abw["eq_vj_erst"])]
    gross = abw[rel_e[rel_e != 0].abs() > 0.4]
    text += ["## Weg A weicht von der Erstmeldung ab, ohne Split-Ereignis (getrennt ausgewiesen)", "",
             f"{len(abw)} von {len(ohne)} Firmen-Stichtagen ({abw['firma'].nunique()} Firmen); Median der Abweichung {rel_e[rel_e != 0].abs().median():.3%}; "
             f"mit geändertem Signal: {len(abw_sig)} ({abw_sig['firma'].nunique()} Firmen); Abweichung über 40 % "
             f"(Hinweis auf einen Split ohne Yahoo-/Tiingo-Ereignis oder eine Aktiendividende): {gross['firma'].nunique()} Firmen.", ""]
    if len(abw_sig):
        x = abw_sig.assign(r=abw_sig["eq_vj_einreichung"] / abw_sig["eq_vj_erst"],
                           klasse=[_klasse(a, e, 1.0) for a, e in zip(abw_sig["eq_vj_einreichung"], abw_sig["eq_vj_erst"])])
        x = x.groupby("firma").agg(n=("stichtag", "size"), r=("r", "median"), klasse=("klasse", "first"))
        text += ["Mit geändertem Signal (Ticker, Verhältnis A/Erstmeldung, Ursache, Stichtage):", "",
                 ", ".join(f"{name(f)} ({z.r:.3f}, {z.klasse}, {z.n})" for f, z in x.iterrows()), ""]

    # --- Mögliche Splits ohne Ereignis im Rückfall B ---------------------------------------------------------------
    b = s[(s["eq_quelle"] == "split") & (s["eq_split_faktor"].fillna(1.0) == 1.0) & s["eq_t"].notna() & s["eq_vj_erst"].notna()]
    verdacht = b[~(b["eq_t"] / b["eq_vj_erst"]).between(*SPLIT_VERDACHT)]
    text += ["## Rückfall B ohne Split-Ereignis: Verdachtsfälle", "",
             f"Rückfall B ohne Faktor: {len(b)} Firmen-Stichtage; Verhältnis t/t−1 außerhalb {SPLIT_VERDACHT}: {len(verdacht)} "
             f"({verdacht['firma'].nunique()} Firmen). Diese bleiben unbereinigt (nichts wird geraten).", ""]
    if len(verdacht):
        text += [", ".join(f"{name(z.firma)} {z.stichtag.date()} ({z.eq_t / z.eq_vj_erst:.2f})" for z in verdacht.head(40).itertuples()), ""]

    # --- Piotroski und Filter --------------------------------------------------------------------------------------
    s["p_alt"] = [piotroski_wert(w, h) for w, h in zip(s["piotroski_alt"], s["piotroski_hochgerechnet_alt"])]
    s["p_neu"] = [piotroski_wert(w, h) for w, h in zip(s["piotroski"], s["piotroski_hochgerechnet"])]
    pv = s[s["p_alt"].notna() | s["p_neu"].notna()]
    p_geaendert = pv[pv["p_alt"].fillna(-1) != pv["p_neu"].fillna(-1)]
    grenze = int(konfig["filter"]["piotroski_min"])
    rein = pv[(pv["p_alt"] < grenze) & (pv["p_neu"] >= grenze)]
    raus = pv[(pv["p_alt"] >= grenze) & (pv["p_neu"] < grenze)]
    aus_alt, aus_neu = s["ausgeschlossen_alt"].astype(bool), s["ausgeschlossen"].astype(bool)
    text += ["## Piotroski und Filter", "",
             f"Piotroski-Wert (für den Filter) geändert: {len(p_geaendert)} Firmen-Stichtage. Grenze Piotroski ≤ {grenze - 1}: "
             f"nicht mehr ausgeschlossen {len(rein)} ({rein['firma'].nunique()} Firmen), neu ausgeschlossen {len(raus)} ({raus['firma'].nunique()} Firmen). "
             f"Ausschluss gesamt (alle Filter): bisher {int(aus_alt.sum())}, korrigiert {int(aus_neu.sum())}; "
             f"gewechselt {int((aus_alt != aus_neu).sum())}.", ""]
    if len(rein) or len(raus):
        text += ["Grenzwechsel (Ticker Stichtag alt→neu): " + ", ".join(
            f"{name(z.firma)} {z.stichtag.date()} {z.p_alt:.0f}→{z.p_neu:.0f}" for z in pd.concat([rein, raus]).sort_values("stichtag").itertuples()), ""]

    # --- Ranglisten und Auswahl A und B ----------------------------------------------------------------------------
    text += ["## Auswahl Fundamental A und B (ohne Kurse nachgestellt)", "",
             "| Buch | Stichtage mit anderer Auswahl | Titelwechsel gesamt | Titel nur bisher | Titel nur korrigiert |", "| --- | --- | --- | --- | --- |"]
    details = []
    for buch in ("A", "B"):
        k = konfig_variante(konfig, buch)
        r_neu, _ = ranglisten_aus_scores(s.drop(columns=["jahr", "p_alt", "p_neu"]), k)
        r_alt, _ = ranglisten_aus_scores(alte_rechnung(s.drop(columns=["jahr", "p_alt", "p_neu"])), k)
        m_neu, m_alt = mitgliedschaft(r_neu, k), mitgliedschaft(r_alt, k)
        tage = [t for t in sorted(m_neu) if m_neu[t] != m_alt.get(t, set())]
        nur_alt = set().union(*[m_alt[t] - m_neu[t] for t in tage]) if tage else set()
        nur_neu = set().union(*[m_neu[t] - m_alt[t] for t in tage]) if tage else set()
        wechsel = sum(len(m_neu[t] ^ m_alt[t]) // 2 for t in tage)
        n = lambda menge: ", ".join(sorted(name(int(x[3:])) for x in menge)) or "–"  # noqa: E731
        text.append(f"| {buch} | {len(tage)} von {len(m_neu)} | {wechsel} | {len(nur_alt)} | {len(nur_neu)} |")
        details += [f"- **{buch}:** nur bisher {n(nur_alt)}; nur korrigiert {n(nur_neu)}."]
    text += [""] + details + ["", "Titelwechsel = Plätze je Stichtag, die mit einem anderen Titel besetzt sind (Summe über die Stichtage)."]

    BERICHT.parent.mkdir(parents=True, exist_ok=True)
    BERICHT.write_text("\n".join(text) + "\n", encoding="utf-8")
    print("\n".join(text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
