r"""Unabhängige Stichprobe zum Marktwert aus Rohkursen (c2 (2), Kriterien vor dem Lauf festgehalten in docs/FUNDAMENTAL.md,
„c2 (2): Marktwert aus Rohkursen – Abnahme und Stichprobe“, Jakob 15.11.2026). Nur lesend, ohne Netz.

Aufruf:  .venv\Scripts\python tools\stichprobe_marktwert_roh.py [--nur-auswahl]
Gewertet erst nach dem Nachladen der Rohkurse ab 01.12.2026 und vor c3. `--nur-auswahl` zeigt nur die 20 Firmen-Messtage
(ohne Marktwerte), um die Auswahl zu prüfen.
Ergebnis: docs/berichte/<Datum>_stichprobe_marktwert_roh.md

Unabhängige Quelle: Streubesitz vom Deckblatt des 10-K (dei:EntityPublicFloat, ungeprüft), von der Firma selbst am Messtag
gerechnet. Einheiten: 20 Firmen-Messtage 2016–2024 des Fundamental-Universums (ohne Finanzwerte), Startwert 15112026; fest
MA, UPS, GOOGL (Alphabet); mindestens 3 Firmen mit verdecktem Faktor H ≠ 1; jedes Jahr mindestens einmal.
Kandidat nur mit Streubesitz > 0, Messtag in der Indexmitgliedschaft; H ≠ 1 nur bei Firmen, die die Rohreihe nutzen
(Zuordnung über die Kursreihe, nicht den Ticker) – Präzisierung vom 15.11.2026 vor dem gewerteten Lauf.
Kriterium: 0,70 ≤ q = Streubesitz / MW_Roh ≤ 1,05. Abweichungen gehen an Jakob, nichts wird angepasst.
"""
import argparse
import random
import sys
import warnings
from datetime import datetime

import pandas as pd

from tradingbot.daten.cache import standard_cache
from tradingbot.daten.rohkurse_marktwert import lade_abnahme
from tradingbot.daten.sec import cik10, kennzahl_jahreswerte
from tradingbot.daten.sp500_nachbau import ciks_der_zeile, lade_firmendaten
from tradingbot.daten.tiingo import TiingoClient
from tradingbot.daten.universum import lade_sic_historien, lade_universum, sic_am
from tradingbot.daten.kursstatus import lade_kursstatus
from tradingbot.daten.kapitalmassnahmen_historie import lade_ereignisse
from tradingbot.engines.fundamental.aktienzahl import lade_aktienfakten
from tradingbot.engines.fundamental.kennzahlen import zusammenlegen
from tradingbot.engines.fundamental.multiples import marktwert_korrigiert, marktwert_rohkurs
from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration

warnings.simplefilter("ignore")
STARTWERT, ANZAHL, JAHRE = 15112026, 20, range(2016, 2025)
FEST = {"MA": 1141391, "UPS": 1090727, "GOOGL": 1652044}
Q_MIN, Q_MAX, H_MIN_ANZAHL = 0.70, 1.05, 3
# Eingefrorene Auswahl (15.11.2026, vor dem gewerteten Lauf; docs/FUNDAMENTAL.md): Die Zufallsauswahl hängt über die Firmen
# mit H ≠ 1 vom Stand der Abnahme ab und würde sich nach dem Nachladen verschieben. Der gewertete Lauf nutzt genau diese 20.
FESTE_AUSWAHL = [("MA", 1141391, "2020-06-30"), ("UPS", 1090727, "2021-06-30"), ("GOOGL", 1652044, "2018-06-29"),
                 ("J", 52988, "2019-03-29"), ("LEN", 920760, "2017-05-31"), ("AMCR", 1748790, "2023-12-31"),
                 ("ANDV", 50104, "2016-06-30"), ("CF", 1324404, "2022-06-30"), ("PANW", 1327567, "2024-01-31"),
                 ("FISV", 798354, "2021-06-30"), ("KMX", 1170010, "2016-08-31"), ("WAT", 1000697, "2016-10-01"),
                 ("FANG", 1539838, "2023-06-30"), ("EIX", 827052, "2016-06-30"), ("FLR", 1124198, "2018-06-29"),
                 ("FBHS", 1519751, "2020-06-30"), ("SNA", 91440, "2019-06-28"), ("NOV", 1021860, "2017-06-30"),
                 ("HAS", 46080, "2016-06-24"), ("KLAC", 319201, "2020-12-31")]


class OhneNetz:
    def get(self, *a, **k):
        raise RuntimeError("Tiingo-Abruf in diesem Werkzeug verboten (nur Cache)")


def auswahl(kandidaten: pd.DataFrame, fest: dict, mit_h: set, startwert: int = STARTWERT, anzahl: int = ANZAHL,
            jahre=JAHRE, h_min: int = H_MIN_ANZAHL) -> pd.DataFrame:
    """Deterministische Auswahl der Firmen-Messtage (Spalten firma, messtag, jahr). Je Firma höchstens ein Messtag.
    Reihenfolge: feste Firmen, dann `h_min` Firmen aus `mit_h`, dann fehlende Jahre, dann zufällig bis `anzahl`."""
    rng = random.Random(startwert)
    k = kandidaten.sort_values(["firma", "messtag"]).reset_index(drop=True)
    gewaehlt, firmen = [], set()

    def nimm(teil: pd.DataFrame) -> bool:
        teil = teil[~teil["firma"].isin(firmen)]
        if teil.empty:
            return False
        z = teil.iloc[rng.randrange(len(teil))]
        gewaehlt.append(z)
        firmen.add(z["firma"])
        return True

    for firma in fest.values():
        nimm(k[k["firma"] == firma])
    h_firmen = sorted(f for f in mit_h if f in set(k["firma"]) and f not in firmen)
    for f in rng.sample(h_firmen, min(h_min, len(h_firmen))):
        nimm(k[k["firma"] == f])
    for jahr in jahre:
        if not any(z["jahr"] == jahr for z in gewaehlt):
            nimm(k[k["jahr"] == jahr])
    while len(gewaehlt) < anzahl and nimm(k):
        pass
    return pd.DataFrame(gewaehlt).reset_index(drop=True)


def mitglied_am(relevant: pd.DataFrame, firma: int, tag: pd.Timestamp) -> bool:
    """Firma am Tag Indexmitglied (von ≤ Tag < bis; fehlendes von/bis = offen)."""
    z = relevant[relevant["cik"] == firma]
    return bool(((z["von"].isna() | (z["von"] <= tag)) & (z["bis"].isna() | (tag < z["bis"]))).any())


def firmen_mit_h(abn: pd.DataFrame, status: pd.DataFrame, rohkurse_status: dict) -> set:
    """Firmen (CIK) mit verdecktem Faktor H ≠ 1 in einer bestandenen Abnahme; Zuordnung über die Kursreihe (Quelle, Symbol)
    der Universumszeile, nicht über den Ticker; nur Firmen, die die Rohreihe auch nutzen (Status „roh“)."""
    if abn.empty:
        return set()
    ok = abn[(abn["bestanden"].astype(str).str.lower() == "true") & ((abn["H"] - 1).abs() > 0.005)]
    paare = set(zip(ok["quelle"], ok["symbol"]))
    uni = status.reset_index()
    from tradingbot.daten.universum import lade_universum

    universum, _ = lade_universum()
    aus = set()
    for _, z in uni.iterrows():
        if (z["quelle"], z["symbol"]) in paare and z["index"] in universum.index and pd.notna(universum.loc[z["index"], "cik"]):
            firma = int(universum.loc[z["index"], "cik"])
            if rohkurse_status.get(firma) == "roh":
                aus.add(firma)
    return aus


def main(argv=None) -> int:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--nur-auswahl", action="store_true")
    arg = a.parse_args(argv)
    konfig = lade_konfiguration("fundamental")
    universum, _ = lade_universum()
    status = lade_kursstatus(universum)                 # über den Schlüssel (Befund 19, Schritt 2)
    daten = lade_firmendaten(universum, status, lade_sic_historien(universum), tiingo=TiingoClient(sitzung=OhneNetz()), rohkurse=True)

    kandidaten = []
    for firma, sb in daten.streubesitz_roh.items():
        if isinstance(firma, str) or daten.kurse.get(firma) is None or sb is None or not len(sb):
            continue
        for messtag, z in sb.iterrows():
            messtag = pd.Timestamp(messtag)
            sic = sic_am(daten.sic.get(firma, []), messtag)
            if (messtag.year in JAHRE and sic is not None and not 6000 <= sic <= 6999 and float(z["wert"]) > 0
                    and mitglied_am(daten.relevant, firma, messtag)):
                kandidaten.append({"firma": firma, "messtag": messtag, "jahr": messtag.year, "streubesitz": float(z["wert"])})
    kandidaten = pd.DataFrame(kandidaten)
    mit_h = firmen_mit_h(lade_abnahme(), status, daten.rohkurse_status)
    wahl = auswahl(kandidaten, FEST, mit_h)
    if not arg.nur_auswahl:                    # gewertet: eingefrorene Auswahl, Streubesitz aus den Kandidaten
        fest = pd.DataFrame([{"firma": f, "messtag": pd.Timestamp(m)} for _, f, m in FESTE_AUSWAHL])
        wahl = fest.merge(kandidaten, on=["firma", "messtag"], how="left")
        if wahl["streubesitz"].isna().any():
            raise RuntimeError("Eingefrorene Auswahl passt nicht mehr zu den Daten: " + ", ".join(
                str(x) for x in wahl[wahl["streubesitz"].isna()]["firma"]))
    namen = {int(z["cik"]): z["ticker"] for _, z in daten.relevant.iterrows() if pd.notna(z["cik"])}

    zeilen, cache, ereignisse = [], standard_cache(), lade_ereignisse()
    max_alter = konfig.get("marktwert_korrektur", {}).get("aktien_max_alter_monate", 15)
    for w in wahl.itertuples():
        z = {"ticker": namen.get(w.firma, w.firma), "firma": w.firma, "messtag": w.messtag.date(), "streubesitz": w.streubesitz,
             "fest": w.firma in FEST.values(), "h": w.firma in mit_h, "kurs": daten.rohkurse_status.get(w.firma, "keine Rohreihe")}
        if not arg.nur_auswahl:
            zeile = daten.relevant[daten.relevant["cik"] == w.firma].iloc[0]
            erst = zusammenlegen([cache.lesen("sec_erstmeldungen", cik10(c))[0] for c in ciks_der_zeile(zeile)])
            akt = kennzahl_jahreswerte(erst, konfig["kennzahlen"]["aktien_ausstehend"], "2100-01-01") if len(erst) else pd.DataFrame()
            akt = akt[["wert", "filed"]] if len(akt) else None
            ersatz = lade_aktienfakten(ciks_der_zeile(zeile), cache=cache, mit_quartalen=True)
            b = marktwert_korrigiert(w.messtag, daten.kurse[w.firma], akt, None, ereignisse=ereignisse.get(w.firma),
                                     ersatz_fakten=ersatz, max_alter_monate=max_alter)
            z.update({"mw_teil_b": b["marktwert"]})
            if z["kurs"] == "roh":
                r = marktwert_rohkurs(w.messtag, daten.rohkurse[w.firma], daten.kurse[w.firma], akt, None, ersatz_fakten=ersatz, ereignisse=ereignisse.get(w.firma),
                                      max_alter_monate=max_alter, plausibilitaet=False)
                z.update({"mw_roh": r["marktwert"], "grund": r["grund"], "aktien_quelle": r["quelle"], "splitfaktor": r["splitfaktor"]})
                if r["marktwert"]:
                    z["q"] = w.streubesitz / r["marktwert"]
                    z["bestanden"] = Q_MIN <= z["q"] <= Q_MAX
        zeilen.append(z)
    t = pd.DataFrame(zeilen)
    vollstaendig = not arg.nur_auswahl and "q" in t.columns and t["q"].notna().all()
    titel = "Auswahl (ohne Marktwerte)" if arg.nur_auswahl else ("gewertet" if vollstaendig else "UNVOLLSTÄNDIG – zählt nicht")
    text = [f"# Stichprobe Marktwert aus Rohkursen – {titel}", "",
            f"Erstellt {datetime.now():%d.%m.%Y %H:%M} mit `tools/stichprobe_marktwert_roh.py`. Kriterien vor dem Lauf festgehalten "
            "(docs/FUNDAMENTAL.md, „c2 (2)“): Quelle Streubesitz (dei:EntityPublicFloat), 20 Firmen-Messtage 2016–2024, Startwert "
            f"15112026, fest MA/UPS/GOOGL, ≥ 3 mit H ≠ 1, jedes Jahr; Kriterium {Q_MIN:.2f} ≤ q ≤ {Q_MAX:.2f}. Nichts wird angepasst.", "",
            f"Kandidaten: {len(kandidaten)} Firmen-Messtage, Firmen mit H ≠ 1 im Universum: {len(mit_h)}.", ""]
    if arg.nur_auswahl:
        text += ["| Ticker | Messtag | Streubesitz (Mrd. USD) | fest | H ≠ 1 | Rohreihe |", "| --- | --- | --- | --- | --- | --- |"]
        text += [f"| {r.ticker} | {r.messtag} | {r.streubesitz / 1e9:.1f} | {'ja' if r.fest else ''} | {'ja' if r.h else ''} | {r.kurs} |"
                 for r in t.itertuples()]
    else:
        nicht = int((t.get("bestanden") == False).sum()) if "bestanden" in t.columns else 0  # noqa: E712
        text += [f"Ergebnis: {int(t.get('bestanden', pd.Series(dtype=bool)).fillna(False).sum())} von {len(t)} innerhalb, {nicht} außerhalb, "
                 f"{int(t.get('q', pd.Series(index=t.index, dtype=float)).isna().sum())} ohne Wert.", "",
                 "| Ticker | Messtag | Streubesitz | MW_Roh | q | MW Teil b | q bisher | Split-Faktor | Aktienzahl | Rohreihe | Kriterium |",
                 "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for r in t.itertuples():
            mw_roh, mw_b = getattr(r, "mw_roh", None), getattr(r, "mw_teil_b", None)
            q = getattr(r, "q", None)
            qb = r.streubesitz / mw_b if mw_b and mw_b == mw_b else None
            text.append(f"| {r.ticker} | {r.messtag} | {r.streubesitz / 1e9:.1f} | {(mw_roh or float('nan')) / 1e9:.1f} | "
                        f"{q if q == q and q is not None else float('nan'):.3f} | {(mw_b or float('nan')) / 1e9:.1f} | {qb if qb else float('nan'):.3f} | "
                        f"{getattr(r, 'splitfaktor', float('nan')):.4g} | {getattr(r, 'aktien_quelle', '')} | {r.kurs} | "
                        f"{'ja' if getattr(r, 'bestanden', False) is True else ('NEIN' if getattr(r, 'bestanden', None) is False else '–')} |")
    bericht = PROJEKT_WURZEL / "docs" / "berichte" / f"{datetime.now():%Y-%m-%d}_stichprobe_marktwert_roh{'_auswahl' if arg.nur_auswahl else ''}.md"
    bericht.write_text("\n".join(text) + "\n", encoding="utf-8")
    print("\n".join(text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
