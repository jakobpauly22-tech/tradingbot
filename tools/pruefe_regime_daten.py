r"""Datenprüfung für die Regime-Engine (docs/REGIME.md, Abschnitte 3, 5 und 6): Abdeckung der Makroreihen und XEON.DE.

Aufruf:  .venv\Scripts\python tools\pruefe_regime_daten.py
Ergebnis: docs/berichte/<Datum>_regime_daten.md

Die Kriterien stehen in docs/REGIME.md und wurden vor dem Laden festgelegt. Besteht XEON.DE nicht, gilt Kasse zu 0 %;
die Kriterien werden nicht angepasst.
"""
import sys
import warnings
from datetime import date

import pandas as pd

XEON_ZEITRAUM = ("2012-01-02", "2024-12-31")
XEON_MAX_LUECKE_TAGE, XEON_MAX_TAGESAENDERUNG, XEON_MAX_ABSTAND_PP = 5, 0.0025, 0.5
# Vorlauf je Test: Entwicklungsdaten ab 01.01.2012 (Sahm-Regel braucht 15 Monate davor), Langtest ab 01.01.1995
ABDECKUNG = {"UNRATE": "1993-10-01", "T10Y3M": "1994-01-01", "BAA10Y": "1994-01-01", "DGS3MO": "1994-01-01"}


def pruefe_geldmarkt_etf(etf: pd.Series, kalender: pd.DatetimeIndex, einlagesatz: pd.Series, *, start=XEON_ZEITRAUM[0]) -> dict:
    """Die drei Kriterien aus docs/REGIME.md, Abschnitt 6. `etf`: Schlusskurse; `kalender`: Handelstage des Vergleichs-ETF;
    `einlagesatz`: EZB-Einlagesatz in Prozent (Stufenreihe, wird je Kalendertag fortgeschrieben)."""
    etf = etf.dropna().sort_index()
    gemeinsam = kalender.intersection(etf.index)
    lage = pd.Series(range(len(kalender)), index=kalender).reindex(gemeinsam)
    luecke = int(lage.diff().max() - 1) if len(lage) > 1 else len(kalender)
    luecke = max(luecke, int(lage.iloc[0]) if len(lage) else len(kalender), len(kalender) - 1 - int(lage.iloc[-1]) if len(lage) else 0)
    erster_ok = len(etf) > 0 and etf.index[0] <= pd.Timestamp(start)
    aenderung = etf.pct_change().dropna()
    spruenge = aenderung[aenderung.abs() > XEON_MAX_TAGESAENDERUNG]
    tage = pd.date_range(etf.index[0], etf.index[-1]) if len(etf) else pd.DatetimeIndex([])
    satz = einlagesatz.reindex(einlagesatz.index.union(tage)).ffill().reindex(tage)
    ende = etf.groupby(etf.index.year).last()
    anfang = ende.shift(1)
    if len(etf):
        anfang.iloc[0] = etf.iloc[0]
    jahre = pd.DataFrame({"etf": (ende / anfang - 1) * 100, "einlagesatz": satz.groupby(satz.index.year).mean()})
    jahre["abstand"] = jahre["etf"] - jahre["einlagesatz"]
    k1, k2 = erster_ok and luecke <= XEON_MAX_LUECKE_TAGE, len(spruenge) == 0
    k3 = bool((jahre["abstand"].abs() <= XEON_MAX_ABSTAND_PP).all()) and len(jahre) > 0
    return {"luecke": luecke, "erster": etf.index[0] if len(etf) else None, "spruenge": spruenge, "jahre": jahre,
            "kriterien": {"1 Lücken": k1, "2 Tagesänderung": k2, "3 Jahresrendite": k3}, "bestanden": k1 and k2 and k3}


def main() -> int:
    from tradingbot.daten.abruf import DatenFehler
    from tradingbot.daten.kurse import lade_kurse
    from tradingbot.daten.makro import erster_datenstand, lade_makro, lade_makro_tabelle, pruefe_abdeckung
    from tradingbot.konfiguration import PROJEKT_WURZEL

    warnings.simplefilter("ignore")
    text = [f"# Regime-Engine: Datenprüfung ({date.today():%d.%m.%Y})", "",
            "Kriterien aus docs/REGIME.md (vor dem Laden festgelegt). Tresor zu: Daten bis 31.12.2024.", "",
            "## Abdeckung der Makroreihen", "", "| Reihe | erster Datenstand | gebraucht ab | erste Beobachtung | ok |", "| --- | --- | --- | --- | --- |"]
    alle_ok = True
    for serie, beginn in ABDECKUNG.items():
        tabelle = lade_makro_tabelle(serie)
        try:
            pruefe_abdeckung(serie, tabelle, beginn)
            ok = True
        except DatenFehler:
            ok = alle_ok = False
        text.append(f"| {serie} | {erster_datenstand(tabelle):%d.%m.%Y} | {pd.Timestamp(beginn):%d.%m.%Y} | {tabelle['datum'].min():%d.%m.%Y} | {'ja' if ok else 'NEIN'} |")
    index = lade_kurse("^SP500TR", "1988-01-01", "2011-12-31")["close"].dropna()
    index_ok = index.index[0] <= pd.Timestamp("1994-03-01")
    alle_ok &= index_ok
    text += ["", f"^SP500TR (Langtest): erster Kurs {index.index[0]:%d.%m.%Y}, {len(index)} Tage bis 31.12.2011 – {'ok' if index_ok else 'NICHT ausreichend'} "
             "(gebraucht: 10 Monatsschlüsse vor dem 01.01.1995).", "",
             f"**Langtest 1995–2011: {'möglich' if alle_ok else 'NICHT möglich – dokumentieren, ohne Langtest werten'}**", ""]

    xeon = lade_kurse("XEON.DE", *XEON_ZEITRAUM)["close"]
    kalender = lade_kurse("SPYI.DE", *XEON_ZEITRAUM)["close"].dropna().index
    e = pruefe_geldmarkt_etf(xeon, kalender, lade_makro("ECBDFR", "2011-06-01", XEON_ZEITRAUM[1]))
    text += ["## XEON.DE", "", f"Erster Kurs {e['erster']:%d.%m.%Y}, größte Lücke {e['luecke']} Handelstage (Kalender SPYI.DE).", "",
             "| Kriterium | bestanden |", "| --- | --- |"] + [f"| {k} | {'ja' if v else 'NEIN'} |" for k, v in e["kriterien"].items()]
    text += ["", f"Tagesänderungen über ±{XEON_MAX_TAGESAENDERUNG:.2%}: {len(e['spruenge'])}"
             + ("" if e["spruenge"].empty else " – " + ", ".join(f"{t:%d.%m.%Y} {w:+.2%}" for t, w in e["spruenge"].items())), "",
             "| Jahr | XEON.DE | EZB-Einlagesatz (Mittel) | Abstand |", "| --- | --- | --- | --- |"]
    text += [f"| {j} | {r.etf:+.2f} % | {r.einlagesatz:+.2f} % | {r.abstand:+.2f} Pp. |" for j, r in e["jahre"].iterrows()]
    text += ["", f"**XEON.DE: {'bestanden – defensive Anlage ist XEON.DE' if e['bestanden'] else 'NICHT bestanden – defensive Anlage ist Kasse zu 0 % (Kriterien werden nicht angepasst)'}**"]
    (PROJEKT_WURZEL / "docs" / "berichte" / f"{date.today():%Y-%m-%d}_regime_daten.md").write_text("\n".join(text), encoding="utf-8")
    print("\n".join(text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
