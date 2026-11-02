r"""Gegenprobe: Nachbau des S&P 500 (ohne Ausschluss) gegen den offiziellen S&P 500 Total Return (^SP500TR).

Aufruf:  .venv\Scripts\python tools\gegenprobe_index.py
Ergebnis: daten/universum/gegenprobe_index.md und .csv; verworfene Streubesitzwerte in gegenprobe_streubesitz_verworfen.csv

Abnahmekriterien und Zeitraum (01.04.2016–31.12.2024) aus index_nachbau / docs/DATENQUALITAET.md. Wird ein Kriterium
verfehlt: Ursachen suchen und mit Jakob besprechen, nicht weiter anpassen. Aufbau des Nachbaus: daten/sp500_nachbau.py.

Läufe: 1 nicht bestanden (Programmierfehler, Garmin-Datenfehler); 2 bestanden mit Streubesitz-Obergrenze 105 %;
3 (03.11.2026) mit Obergrenze 130 % (Jakob: Streubesitz Ende Q2 und Aktienzahl zum Deckblattdatum haben verschiedene
Stichtage, dazwischen Rückkäufe und Kursbewegungen); 4 (03.11.2026) für den Zeitraum nach der 2-%-Regel ab 01.10.2016.
"""
import sys
import warnings

import pandas as pd

from tradingbot.daten.fehlerschwelle import FehlerschwelleUeberschritten, laut_melden
from tradingbot.daten.index_nachbau import ABNAHME_ZEITRAUM, STREUBESITZ_ANTEIL_MAX, abnahme_gegenprobe
from tradingbot.daten.kurse import lade_kurse
from tradingbot.daten.sp500_nachbau import ENDE, VORLAUF, baue_nachbau, lade_firmendaten
from tradingbot.daten.universum import lade_sic_historien, lade_universum
from tradingbot.konfiguration import PROJEKT_WURZEL

warnings.simplefilter("ignore")
LAUF, VORHERIGER = 4, 3
AENDERUNG = ("Zeitraum nach der Regel für den gewerteten Beginn (erster Stichtag, ab dem alle folgenden unter 2 % nicht kaufbarem "
             "Gewicht liegen): 01.10.2016 statt 01.04.2016. Nachbau, Daten und Kriterien unverändert, keine Anpassung (Jakob 03.11.2026).")


def main() -> int:
    universum, _ = lade_universum()
    status = pd.read_csv(PROJEKT_WURZEL / "daten" / "universum" / "kursstatus.csv").set_index("index")
    daten = lade_firmendaten(universum, status, lade_sic_historien(universum))
    ergebnis_nachbau = baue_nachbau(daten)
    nachbau, tage = ergebnis_nachbau["nachbau"], ergebnis_nachbau["tage"]
    referenz = lade_kurse("^SP500TR", VORLAUF, ENDE)["close"]
    ergebnis = abnahme_gegenprobe(nachbau["index"], referenz)

    ziel = PROJEKT_WURZEL / "daten" / "universum"
    pd.concat({"nachbau": nachbau["index"], "abdeckung": nachbau["abdeckung"], "referenz": referenz.reindex(tage)}, axis=1).to_csv(ziel / "gegenprobe_index.csv")
    v = daten.verworfen
    v.to_csv(ziel / "gegenprobe_streubesitz_verworfen.csv", index=False)
    geprueft = sum(len(r) for f, r in daten.streubesitz_roh.items() if f in daten.streubesitz_gueltig)
    gruende = v["grund"].str.replace(r"[\d.,]+[-%]?", "x", regex=True).value_counts().to_dict() if len(v) else {}
    abn = nachbau["abdeckung"].loc[ABNAHME_ZEITRAUM[0]:]
    k = ergebnis["kriterien"]
    text = [f"# Gegenprobe Index-Nachbau gegen S&P 500 Total Return – Lauf {LAUF}", "",
            f"Vorheriger Lauf: daten/universum/gegenprobe_index_lauf{VORHERIGER}.md. Änderung in Lauf {LAUF}: {AENDERUNG} "
            f"Streubesitz-Obergrenze {STREUBESITZ_ANTEIL_MAX:.0%} des Börsenwerts.", "",
            f"Zeitraum {ergebnis['zeitraum'][0]} bis {ergebnis['zeitraum'][1]}, {ergebnis['tage']} gemeinsame Handelstage. "
            f"Abdeckung der Mitglieder mit Rendite und Gewicht im Abnahmezeitraum: Median {abn.median():.1%}, Minimum {abn.min():.1%}; "
            f"je Jahr (Median): {abn.groupby(abn.index.year).median().round(3).to_dict()}.", "",
            f"Streubesitz: {geprueft} Werte geprüft, {len(v)} verworfen ({len(v)/max(geprueft,1):.1%}); Gründe: {gruende}.", "",
            "| Kriterium | Wert | Grenze | bestanden |", "| --- | --- | --- | --- |",
            f"| Korrelation der Tagesrenditen | {k['korrelation']['wert']:.4f} | ≥ 0,99 | {'ja' if k['korrelation']['bestanden'] else 'NEIN'} |",
            f"| größte Abweichung einer Jahresrendite | {k['jahresabweichung_max']['wert']*100:.2f} Pp. | ≤ 1 Pp. | {'ja' if k['jahresabweichung_max']['bestanden'] else 'NEIN'} |",
            f"| Abweichung annualisierte Rendite | {k['annualisiert_abweichung']['wert']*100:+.2f} Pp. | ≤ 0,5 Pp. | {'ja' if k['annualisiert_abweichung']['bestanden'] else 'NEIN'} |",
            "", f"**Gesamt: {'bestanden' if ergebnis['bestanden'] else 'NICHT bestanden – nicht weiter anpassen, mit Jakob besprechen'}**", "",
            "| Jahr | Nachbau | S&P 500 TR | Abweichung |", "| --- | --- | --- | --- |"]
    text += [f"| {j}{' (ab ' + pd.Timestamp(ABNAHME_ZEITRAUM[0]).strftime('%d.%m.') + ')' if j == pd.Timestamp(ABNAHME_ZEITRAUM[0]).year else ''} | {r.nachbau:.2%} | {r.referenz:.2%} | {r.abweichung*100:+.2f} Pp. |" for j, r in ergebnis["jahre"].iterrows()]
    (ziel / "gegenprobe_index.md").write_text("\n".join(text), encoding="utf-8")
    print("\n".join(text))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FehlerschwelleUeberschritten as fehler:
        sys.exit(laut_melden(fehler))
