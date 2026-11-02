r"""Auswertung „Kursabdeckung je Stichtag“ (Rückmeldung Jakob 03.11.2026) auf Basis von daten/universum/kursstatus.csv.

Aufruf:  .venv\Scripts\python tools\auswertung_abdeckung.py [--stichtage N]
Ergebnis: daten/universum/auswertung_abdeckung.md und .csv
1. Nicht kaufbar: Mitglieder ohne gültige Kursreihe am Rebalancing-Stichtag (Anzahl, Indexgewicht nach Streubesitz).
2. Rückfall-Regel: gültige Reihen, die mit dem Delisting enden, je Jahr und Grund.
Speicherschonend: SEC-Erstmeldungen werden Firma für Firma gelesen, behalten wird nur der Streubesitzwert.
Aktiengattungen einer Firma (gleiche CIK) zählen beim Gewicht einmal. Fehlerschwelle: über 5 % fehlende SEC-Daten oder
fehlgeschlagene Abfragen → Abbruch mit Exit-Code 1, keine Ergebnisdatei.
"""
import argparse
import sys
import warnings

import pandas as pd

from tradingbot.daten.abdeckung import SCHWELLE_GEWICHT, STREUBESITZ, nicht_kaufbar_je_stichtag, rebalancing_stichtage, rueckfall_faelle
from tradingbot.daten.cache import standard_cache
from tradingbot.daten.delisting import delisting_grund_mit_korrektur, einreichungen
from tradingbot.daten.fehlerschwelle import Fehlerschwelle, FehlerschwelleUeberschritten, laut_melden
from tradingbot.daten.sec import SecClient, cik10, kennzahl_jahreswerte
from tradingbot.daten.universum import ist_finanzwert, lade_sic_historien, lade_universum, mitglieder_am, sic_am
from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration

warnings.simplefilter("ignore")


def _markdown(tabelle: pd.DataFrame) -> str:
    if tabelle.empty:
        return "keine Fälle"
    kopf = ["Jahr"] + [str(c) for c in tabelle.columns]
    zeilen = ["| " + " | ".join(kopf) + " |", "| " + " | ".join("---" for _ in kopf) + " |"]
    zeilen += ["| " + " | ".join([str(j)] + [str(int(v)) for v in z]) + " |" for j, z in tabelle.iterrows()]
    return "\n".join(zeilen)


def _ciks(zeile) -> list[int]:
    return ([int(zeile["cik"])] if pd.notna(zeile["cik"]) else []) + [int(c) for c in list(zeile["vorgaenger_ciks"] if zeile["vorgaenger_ciks"] is not None else [])]


def main(argumente) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stichtage", type=int, default=None, help="nur die ersten N Stichtage (Probelauf)")
    args = parser.parse_args(argumente)

    universum, _ = lade_universum()
    relevant = universum[universum["bis"].isna() | (universum["bis"] >= "2012-01-01")]
    status = pd.read_csv(PROJEKT_WURZEL / "daten" / "universum" / "kursstatus.csv")
    gueltig = status.set_index("index")["gueltig"].astype(bool)
    sic = lade_sic_historien(universum)

    cache = standard_cache()
    streubesitz: dict[int, pd.DataFrame] = {}
    schwelle_sec = Fehlerschwelle("Auswertung: SEC-Erstmeldungen aus dem Cache")
    for cik in sorted({c for _, r in relevant.iterrows() for c in _ciks(r)}):
        erst, _ = cache.lesen("sec_erstmeldungen", cik10(cik))
        schwelle_sec.zaehle(None if erst is not None else f"CIK {cik} nicht im Cache")
        streubesitz[cik] = kennzahl_jahreswerte(erst, STREUBESITZ, "2100-01-01") if erst is not None else pd.DataFrame()
        del erst
    schwelle_sec.pruefe()

    def firma(nr):
        zeile = relevant.loc[nr]
        return int(zeile["cik"]) if pd.notna(zeile["cik"]) else f"ohne CIK {nr}"

    def gewicht(nr, tag):
        werte = []
        for cik in _ciks(relevant.loc[nr]):
            s = streubesitz.get(cik)
            if s is not None and len(s):
                bekannt = s[(s["filed"] + pd.Timedelta(days=1)) <= tag]
                if len(bekannt):
                    werte.append((bekannt.index[-1], float(bekannt["wert"].iloc[-1])))
        return max(werte)[1] if werte else None

    def finanzwert(nr, tag):
        for cik in _ciks(relevant.loc[nr]):
            code = sic_am(sic.get(cik, []), tag)
            if code is not None:
                return ist_finanzwert(code)
        return None

    stichtage = rebalancing_stichtage()
    if args.stichtage:
        stichtage = stichtage[: args.stichtage]
    tabelle = nicht_kaufbar_je_stichtag(lambda tag: mitglieder_am(relevant, tag), gueltig, gewicht, finanzwert, stichtage, firma_fn=firma)

    # Rückfall-Fälle: Gründe nur für gültige Reihen, die vor dem Datenende enden
    client, korrekturen = SecClient(), lade_konfiguration("universum_korrekturen").get("delisting", [])
    s = status[status["gueltig"].astype(bool)].copy()
    s["letzter_kurs"] = pd.to_datetime(s["letzter_kurs"])
    endet = s[s["letzter_kurs"] < s["letzter_kurs"].max() - pd.Timedelta(days=30)]
    gruende = {}
    schwelle_delisting = Fehlerschwelle("Auswertung: Delisting-Gründe")
    for _, r in endet.iterrows():
        zeile = relevant.loc[r["index"]]
        try:
            subs, _ = client.submissions(int(zeile["cik"]))
            gruende[r["index"]] = delisting_grund_mit_korrektur(zeile["ticker"], einreichungen(subs), r["letzter_kurs"],
                                                                zeile["grund_abgang"], korrekturen)[0]
            schwelle_delisting.zaehle(None)
        except Exception as fehler:  # Grund bleibt „unbekannt“ (−30 %), Fehler zählt gegen die Schwelle
            schwelle_delisting.zaehle(f"{zeile['ticker']}: {type(fehler).__name__}")
    schwelle_delisting.pruefe()
    rueckfall = rueckfall_faelle(status, gruende)

    ziel = PROJEKT_WURZEL / "daten" / "universum"
    tabelle.to_csv(ziel / "auswertung_abdeckung.csv", index=False)
    ueber = tabelle[tabelle["ueber_schwelle"]]
    zeilen = ["# Kursabdeckung je Stichtag", "",
              f"Datenstand kursstatus.csv: {len(status)} Mitgliedschaften, davon gültig {int(gueltig.sum())}.", "",
              "## 1. Nicht kaufbar (keine gültige Kursreihe am Rebalancing-Stichtag)", "",
              "Firmen (eine je CIK; Gattungen wie GOOG/GOOGL zählen einmal). Gattungen ohne Kurse in Klammern.", "",
              "| Stichtag | Firmen | ohne Kurse | Gewicht | investierbar (ohne Finanzwerte) | davon ohne Kurse | Gewicht | ohne Streubesitzwert |",
              "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for _, z in tabelle.iterrows():
        markierung = " ⚠" if z["ueber_schwelle"] else ""
        zeilen.append(f"| {z['stichtag']} | {z['firmen']} | {z['ohne_gueltige_kurse']} ({z['gattungen_ohne_gueltige_kurse']}) | {z['gewicht_ohne_kurse']:.2%} | "
                      f"{z['investierbar']} | {z['investierbar_ohne_kurse']} | {z['gewicht_investierbar_ohne_kurse']:.2%}{markierung} | {z['ohne_streubesitzwert']} |")
    zeilen += ["", f"Schwelle {SCHWELLE_GEWICHT:.0%} im investierbaren Universum überschritten an {len(ueber)} von {len(tabelle)} Stichtagen.", "",
               "## 2. Rückfall-Regel (gültige Reihe endet mit dem Delisting)", "", _markdown(rueckfall), ""]
    (ziel / "auswertung_abdeckung.md").write_text("\n".join(zeilen), encoding="utf-8")
    print("\n".join(zeilen))


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except FehlerschwelleUeberschritten as fehler:
        sys.exit(laut_melden(fehler))
