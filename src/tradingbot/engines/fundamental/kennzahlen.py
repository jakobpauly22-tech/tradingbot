"""Jahresabschlüsse je Firma, wie sie am Stichtag bekannt waren (point-in-time).

Grundlage sind die SEC-Erstmeldungen (daten/sec.py): je Konzept und Periode der zuerst gemeldete Wert, bekannt ab dem
Handelstag nach der Einreichung. Je Firma wird einmal eine feste Tabelle aller Jahreswerte gebaut (jahreswerte_firma);
je Stichtag wird daraus nur gefiltert (abschluesse_am). Vorgänger-CIKs (z.B. Google → Alphabet) werden zusammengelegt.

Ableitungen für Posten, die viele Firmen nicht einzeln melden (Abdeckungsprüfung Sitzung 1), jeweils markiert:
- Bruttoergebnis = Umsatz − Umsatzkosten
- Vertriebs- und Verwaltungskosten = Vertriebskosten + Verwaltungskosten
- Verbindlichkeiten = Bilanzsumme − Eigenkapital inklusive Minderheiten
- EBIT (operatives Ergebnis) = Ergebnis vor Steuern + Zinsaufwand
- kurzfristige Finanzschulden = kurzfristiger Teil langfristiger Schulden + kurzfristige Kredite
- langfristige Finanzschulden fehlen → 0 (schuldenfreie Firmen melden den Posten oft nicht)
Aktualität: Das letzte Geschäftsjahr muss höchstens 15 Monate vor dem Stichtag enden (config), sonst nicht bewertbar.
"""
from __future__ import annotations

import pandas as pd

from tradingbot.daten.sec import erstmeldungen, kennzahl_jahreswerte

DAUER_FUER_GJ = ("umsatz", "jahresueberschuss", "operativer_cashflow")   # aus diesen ergeben sich die Geschäftsjahre


def zusammenlegen(erstmeldungen_je_cik: list[pd.DataFrame]) -> pd.DataFrame:
    """Erstmeldungen mehrerer CIKs (Firma und Vorgänger) zu einer Tabelle; je Periode gilt die früheste Meldung."""
    teile = [e.drop(columns=["verfuegbar_ab"], errors="ignore") for e in erstmeldungen_je_cik if e is not None and len(e)]
    if not teile:
        return pd.DataFrame()
    return erstmeldungen(pd.concat(teile, ignore_index=True))


def jahreswerte_firma(erst: pd.DataFrame, definitionen: dict) -> pd.DataFrame:
    """Alle Jahreswerte einer Firma im Langformat: kennzahl, ende, wert, bekannt_ab, konzept, rang.

    Jeder Kandidatenbegriff wird einzeln aufgenommen (rang = Position in der Liste). Welcher Wert gilt, entscheidet erst
    abschluesse_am am Stichtag: der zuerst gemeldete unter den dann bekannten (Erstmeldungs-Regel), bei gleichem Datum der
    vorrangige Begriff. So zählt z.B. bei Walmart das Ergebnis vor Steuern 2019 aus dem 10-K vom März 2020, auch wenn ein
    vorrangiger Begriff erst im 10-K von 2022 auftaucht.
    """
    from tradingbot.backtest.tresor import begrenze

    erst = begrenze(erst, "filed")               # Tresor: nur Einreichungen bis zur Datumsgrenze
    zeilen = []
    for name, d in definitionen.items():
        if d["art"] == "letzter" or erst is None or len(erst) == 0:
            continue
        for rang, konzept in enumerate(d["konzepte"]):
            w = kennzahl_jahreswerte(erst, {**d, "konzepte": [konzept]}, "2100-01-01")
            for ende, r in w.iterrows():
                zeilen.append((name, ende, float(r["wert"]), r["filed"] + pd.Timedelta(days=1), r["konzept"], rang))
    return pd.DataFrame(zeilen, columns=["kennzahl", "ende", "wert", "bekannt_ab", "konzept", "rang"])


def abschluesse_am(werte: pd.DataFrame, stichtag, *, jahre: int = 3, aktualitaet_monate: int = 15) -> tuple[pd.DataFrame, dict]:
    """Die letzten `jahre` Geschäftsjahre, die am Stichtag bekannt waren, im Breitformat (Zeile 0 = jüngstes Jahr t).

    Gibt (Tabelle, Info) zurück. Info: ende_t, veraltet (bool), abgeleitet (Liste „kennzahl@jahr“), grund.
    Ein Geschäftsjahr gilt als bekannt, wenn Umsatz, Jahresüberschuss oder operativer Cashflow dafür bekannt sind.
    """
    tag = pd.Timestamp(stichtag)
    bekannt = werte[werte["bekannt_ab"] <= tag]
    gj = sorted(bekannt.loc[bekannt["kennzahl"].isin(DAUER_FUER_GJ), "ende"].unique(), reverse=True)
    if not gj:
        return pd.DataFrame(), {"ende_t": None, "veraltet": True, "abgeleitet": [], "grund": "kein Geschäftsjahr bekannt"}
    # nur aufeinanderfolgende Geschäftsjahre (Abstand 300–430 Tage), höchstens `jahre`
    reihe = [pd.Timestamp(gj[0])]
    for e in gj[1:]:
        if len(reihe) == jahre:
            break
        if 300 <= (reihe[-1] - pd.Timestamp(e)).days <= 430:
            reihe.append(pd.Timestamp(e))
    tabelle = (bekannt[bekannt["ende"].isin(reihe)].sort_values(["bekannt_ab", "rang"])
               .drop_duplicates(["kennzahl", "ende"], keep="first").pivot(index="ende", columns="kennzahl", values="wert"))
    tabelle = tabelle.reindex(reihe)
    tabelle, abgeleitet = _ableiten(tabelle)
    veraltet = (tag - reihe[0]).days > aktualitaet_monate * 30.44
    info = {"ende_t": reihe[0], "veraltet": veraltet, "abgeleitet": abgeleitet,
            "grund": f"letztes Geschäftsjahr {reihe[0].date()} älter als {aktualitaet_monate} Monate" if veraltet else None}
    return tabelle, info


def _spalte(t: pd.DataFrame, name: str) -> pd.Series:
    return t[name] if name in t.columns else pd.Series(float("nan"), index=t.index)


def _ableiten(t: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    t = t.copy()
    markiert: list[str] = []

    def setzen(name, ersatz):
        alt = _spalte(t, name)
        fehlt = alt.isna() & ersatz.notna()
        if fehlt.any():
            t[name] = alt.where(~fehlt, ersatz)
            markiert.extend(f"{name}@{e.date()}" for e in t.index[fehlt])
        elif name not in t.columns:
            t[name] = alt

    setzen("bruttoergebnis", _spalte(t, "umsatz") - _spalte(t, "umsatzkosten"))
    setzen("vertriebs_verwaltungskosten", _spalte(t, "vertriebskosten") + _spalte(t, "verwaltungskosten"))
    setzen("verbindlichkeiten", _spalte(t, "bilanzsumme") - _spalte(t, "eigenkapital_inkl_minderheiten"))
    setzen("operatives_ergebnis", _spalte(t, "ergebnis_vor_steuern") + _spalte(t, "zinsaufwand"))
    teil, kredite = _spalte(t, "langfristige_schulden_kurzfristiger_teil"), _spalte(t, "kurzfristige_kredite")
    summe = teil.fillna(0) + kredite.fillna(0)
    setzen("kurzfristige_finanzschulden", summe.where(teil.notna() | kredite.notna()))
    setzen("langfristige_finanzschulden", pd.Series(0.0, index=t.index).where(_spalte(t, "bilanzsumme").notna()))
    return t, markiert
