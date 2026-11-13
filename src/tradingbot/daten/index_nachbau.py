"""Nachbau eines nach Börsenwert gewichteten Total-Return-Index aus dem point-in-time-Universum.

Zweck (Entscheidung Jakob 02.11.2026): Benchmark „S&P 500 ohne Finanzwerte“ (SIC 6000–6999, point-in-time), für den
es keine frei verfügbare Historie gibt. Derselbe Nachbau ohne Ausschluss dient als Gegenprobe gegen den offiziellen
S&P 500 Total Return; die Abweichung zeigt die Qualität von Universum und Kursdaten.

Formel (Laspeyres-Kettenindex, wie bei Indexanbietern):
    w_i,t   = MW_i,t−1 / Σ_j MW_j,t−1              über die Mitglieder am Tag t (Gewichte vom Vortag, kein Look-ahead)
    r_i,t   = (C_i,t + D_i,t − C_i,t−1) / C_i,t−1   Gesamtrendite inklusive Dividende (simple_return)
    I_t     = I_t−1 · (1 + Σ_i w_i,t · r_i,t)
Marktwert MW = Streubesitz laut SEC-Deckblatt, fortgeschrieben mit dem Kurs (marktwerte_aus_streubesitz), je Firma
(nicht je Aktiengattung). Umgestellt am 02.11.2026 vor der ersten Gegenprobe, weil die Aktienzahl auf dem Deckblatt
bei Mehrgattungsfirmen fehlt oder nur eine Gattung zählt. Abweichung zum Original: S&P nutzt tagesaktuelle
Streubesitzfaktoren, wir den jährlichen Wert vom Deckblatt.
Quelle Formel Gesamtrendite: wissen/02_Kapitalmarkttheorie_Portfolio_Anleihen.md, Abschnitt 2; referenz.simple_return.
"""
from __future__ import annotations

import pandas as pd

from tradingbot.kennzahlen.rendite import simple_return


# --- Plausibilität des Streubesitzes gegen den Börsenwert (Entscheidung Jakob 02.11.2026) ------------------------
# Ein fester Bereich reicht nicht (Garmin meldet in drei Jahren das 1.000-Fache, noch unter 10 Bio. USD), und ein
# Abgleich mit dem Median der Firma würde echte Wachstumsfälle verwerfen (Nvidia seit 2016 mehr als verhundertfacht).
STREUBESITZ_ANTEIL_MIN = 0.30        # Streubesitz mindestens 30 % von Kurs × Aktienzahl am Messtag
STREUBESITZ_ANTEIL_MAX = 1.30        # höchstens 130 % (02.11.2026, vorher 105 %): Streubesitz (Messtag Ende Q2) und
                                     # Aktienzahl (Deckblattdatum) haben verschiedene Stichtage; dazwischen Rückkäufe und Kursbewegungen
STREUBESITZ_VERAENDERUNG_FAKTOR = 3.0  # ohne Aktienzahl: Veränderung zum Vorjahr höchstens Faktor 3 neben der Kursveränderung
AKTIEN_ABSTAND_TAGE = 400            # Aktienzahl höchstens so weit vom Messtag entfernt


def streubesitz_pruefen(reihe: pd.DataFrame, schluss: pd.Series, aktien: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Prüft die Streubesitzwerte einer Firma gegen den Börsenwert am Messtag e.

    Mit Aktienzahl:  0,30 ≤ F_e / (C_e · A_e) ≤ 1,30   (A_e: Aktienzahl nahe e, splitbereinigt wie die Kurse)
    Ohne Aktienzahl: 1/3 ≤ (F_e / F_v) / (C_e / C_v) ≤ 3  (v: letzter akzeptierter Wert davor)
    Eine Aktienzahl zählt nur, wenn C_e · A_e selbst plausibel ist (0,5 Mrd. bis 10 Bio. USD); sonst gilt die Firma
    für diesen Wert als „ohne Aktienzahl“ (z.B. nur eine Aktiengattung gemeldet, Mantelgesellschaft, falsche Einheit).
    Der erste Wert ohne Aktienzahl und ohne Vorgänger bleibt ungeprüft gültig (kein Vergleich möglich).
    Gibt (gültige Werte, verworfene Werte mit Spalte `grund`) zurück; verworfene Werte gelten als fehlend.
    """
    from tradingbot.daten.abdeckung import STREUBESITZ_MAX, STREUBESITZ_MIN

    gueltig, verworfen = [], []
    vorher = None                                           # (F, C) des letzten akzeptierten Werts
    aktien = aktien.dropna().sort_index()
    aktien = aktien[~aktien.index.duplicated(keep="last")]      # gleiche Meldung bei Firma und Vorgänger-CIK
    for e, zeile in reihe.sort_index().iterrows():
        f = float(zeile["wert"])
        kurse_bis = schluss.loc[:e].dropna()
        grund = None
        if not STREUBESITZ_MIN <= f <= STREUBESITZ_MAX:
            grund = "außerhalb 0,5 Mrd. bis 10 Bio. USD"
        elif kurse_bis.empty:
            grund = "kein Kurs am Messtag"
        else:
            c_e = float(kurse_bis.iloc[-1])
            boersenwert = None
            if len(aktien):
                abstand = pd.Series(abs((aktien.index - e).days), index=aktien.index)
                if abstand.min() <= AKTIEN_ABSTAND_TAGE:
                    wert = c_e * float(aktien.loc[abstand.idxmin()])
                    boersenwert = wert if STREUBESITZ_MIN <= wert <= STREUBESITZ_MAX else None
            if boersenwert is not None:
                anteil = f / boersenwert
                if not STREUBESITZ_ANTEIL_MIN <= anteil <= STREUBESITZ_ANTEIL_MAX:
                    grund = f"{anteil:.0%} des Börsenwerts"
            elif vorher is not None:
                verhaeltnis = (f / vorher[0]) / (c_e / vorher[1])
                if not 1 / STREUBESITZ_VERAENDERUNG_FAKTOR <= verhaeltnis <= STREUBESITZ_VERAENDERUNG_FAKTOR:
                    grund = f"Veränderung zum Vorjahr {verhaeltnis:.1f}-fach der Kursveränderung"
            if grund is None:
                vorher = (f, c_e)
        (verworfen if grund else gueltig).append({"ende": e, "wert": f, "filed": zeile["filed"], "grund": grund})
    spalten = ["wert", "filed", "grund"]
    zu_df = lambda z: pd.DataFrame(z, columns=["ende", *spalten]).set_index("ende")  # noqa: E731
    return zu_df(gueltig).drop(columns="grund"), zu_df(verworfen)


def handelstage(schluss: pd.DataFrame, von, bis, mindestanteil: float = 0.5) -> pd.DatetimeIndex:
    """Echte Börsentage: Tage, an denen mindestens `mindestanteil` der im Zeitraum üblichen Zahl an Titeln einen Kurs hat.

    Behebt den Fehler des ersten Gegenprobe-Laufs: Mit allen Werktagen fehlte an US-Feiertagen (z.B. 25.12.2018) jeder
    Marktwert, und am Tag danach (26.12.2018, S&P 500 +5 %) hatte der Nachbau keine Gewichte und blieb stehen.
    """
    teil = schluss.loc[pd.Timestamp(von):pd.Timestamp(bis)]
    anzahl = teil.notna().sum(axis=1)
    return pd.DatetimeIndex(anzahl.index[anzahl >= mindestanteil * anzahl.median()])


def marktwerte_aus_streubesitz(schluss: pd.DataFrame, streubesitz: dict, korrektur_je_firma: dict | None = None) -> pd.DataFrame:
    """Marktwert je Firma und Tag aus dem Streubesitz laut SEC-Deckblatt, fortgeschrieben mit dem Kurs.

    Formel:  MW_i,t = F_i · C_i,t / C_i,e    (F = jüngster bis t bekannte plausible Streubesitz, gemessen am Tag e)
    Begründung (02.11.2026): Die Aktienzahl auf dem Deckblatt fehlt oder ist eine Teilmenge bei Firmen mit mehreren
    Aktiengattungen (z.B. Berkshire, Alphabet, Fox); der Streubesitz wird je Firma über alle Gattungen gemeldet und
    entspricht der Streubesitz-Gewichtung des S&P 500. Point-in-time: F gilt ab dem Tag nach der Einreichung.
    `schluss`: Tage × Firmen (splitbereinigte Schlusskurse); `streubesitz`: Firma → DataFrame(wert, filed; Index = e).
    `korrektur_je_firma` (Datenkorrektur Marktwert, Jakob 13.11.2026): Firma → (Split-Spalte der Kursreihe, eingeordnete
    Ereignisse); dann MW_i,t = F_i · C_i,t / C_i,e · K(e, t), damit eine Abspaltung zwischen e und t den Streubesitz nicht
    erhöht (daten/kapitalmassnahmen_historie.py). None = bisherige Rechnung.
    """
    from tradingbot.daten.kapitalmassnahmen_historie import korrektur_reihe

    from tradingbot.daten.abdeckung import STREUBESITZ_MAX, STREUBESITZ_MIN

    ergebnis = pd.DataFrame(index=schluss.index, columns=schluss.columns, dtype=float)
    for firma in schluss.columns:
        reihe = streubesitz.get(firma)
        if reihe is None or len(reihe) == 0:
            continue
        reihe = reihe[reihe["wert"].between(STREUBESITZ_MIN, STREUBESITZ_MAX)].sort_values("filed")
        c = schluss[firma]
        for i, (e, zeile) in enumerate(reihe.iterrows()):
            ab = zeile["filed"] + pd.Timedelta(days=1)
            bis = reihe["filed"].iloc[i + 1] + pd.Timedelta(days=1) if i + 1 < len(reihe) else None
            vorher = c.loc[:e].dropna()
            if vorher.empty:
                continue
            fenster = (c.index >= ab) & ((c.index < bis) if bis is not None else True)
            werte = zeile["wert"] * c[fenster] / vorher.iloc[-1]
            if korrektur_je_firma and firma in korrektur_je_firma:
                splits, ereignisse = korrektur_je_firma[firma]
                werte = werte * korrektur_reihe(splits, ereignisse, e, werte.index).to_numpy()
            ergebnis.loc[fenster, firma] = werte
    return ergebnis


def aktien_splitbereinigt(aktien: pd.Series, splits: pd.Series) -> pd.Series:
    """Gemeldete Aktienzahl auf die heutige Split-Basis der Kurse bringen.

    Ein Wert vom Datum d wird mit allen Split-Faktoren nach d multipliziert (Yahoo-/Tiingo-Kurse sind rückwirkend
    durch diese Faktoren geteilt). `splits`: Faktor am Split-Tag, sonst 0 oder fehlend.
    """
    faktoren = splits[splits.fillna(0) > 0]
    if faktoren.empty or aktien.empty:
        return aktien.astype(float)
    return pd.Series({d: float(a) * float(faktoren[faktoren.index > d].prod()) for d, a in aktien.items()}).sort_index()


def marktwert_index(renditen: pd.DataFrame, marktwerte: pd.DataFrame, mitglied: pd.DataFrame, basis: float = 100.0) -> pd.DataFrame:
    """Kettenindex aus Tagesrenditen und Marktwerten (Tage × Titel); `mitglied` bool (Tage × Titel).

    Gewichte aus den Marktwerten des Vortags, nur für Titel, die am Tag t Mitglied sind und für die eine Rendite
    vorliegt. Ergebnis: Spalten index, abdeckung (Anteil der Mitglieder mit Rendite und Vortags-Marktwert).
    """
    mw_vortag = marktwerte.shift(1)
    nutzbar = mitglied & renditen.notna() & mw_vortag.notna() & (mw_vortag > 0)
    gewicht_roh = mw_vortag.where(nutzbar)
    gewichte = gewicht_roh.div(gewicht_roh.sum(axis=1), axis=0)
    r_index = (gewichte * renditen).sum(axis=1, min_count=1).fillna(0.0)
    r_index.iloc[0] = 0.0
    abdeckung = nutzbar.sum(axis=1) / mitglied.sum(axis=1).where(mitglied.sum(axis=1) > 0)
    return pd.DataFrame({"index": basis * (1 + r_index).cumprod(), "abdeckung": abdeckung})


# --- Abnahme der Gegenprobe (Entscheidung Jakob 02.11.2026, docs/DATENQUALITAET.md) ----------------------------
# Nachbau ohne Ausschluss gegen den offiziellen S&P 500 Total Return (^SP500TR), beide in USD, gemeinsame Handelstage.
# Wird ein Kriterium verfehlt: erst Ursachen suchen und mit Jakob besprechen, NICHT nachjustieren.
ABNAHME_KORRELATION_MIN = 0.99          # Korrelation der Tagesrenditen
ABNAHME_JAHRESABWEICHUNG_MAX = 0.01     # Abweichung der Jahresrenditen je Kalenderjahr (1 Prozentpunkt)
ABNAHME_ANNUALISIERT_MAX = 0.005        # Abweichung der annualisierten Rendite im Abnahmezeitraum (0,5 Prozentpunkte)
# Zeitraum = gewerteter Backtest (Entscheidung Jakob 02.11.2026); die Kriterien selbst sind unverändert.
def _gewerteter_zeitraum() -> tuple[str, str]:
    """Zeitraum aus config/fundamental.yaml (backtest.gewertet_ab/-bis), Ergebnis der 2-%-Regel."""
    from tradingbot.konfiguration import lade_konfiguration

    b = lade_konfiguration("fundamental")["backtest"]
    return str(b["gewertet_ab"]), str(b["gewertet_bis"])


ABNAHME_ZEITRAUM = _gewerteter_zeitraum()


def abnahme_gegenprobe(nachbau: pd.Series, referenz: pd.Series, zeitraum=ABNAHME_ZEITRAUM) -> dict:
    """Prüft den Nachbau gegen den Referenzindex nach den drei Abnahmekriterien.

    Formeln: Tagesrendite r_t = I_t / I_{t−1} − 1 (gemeinsame Handelstage); Jahresrendite = Indexstand am letzten
    gemeinsamen Handelstag des Jahres / Stand am letzten des Vorjahres − 1 (erstes Jahr ab dem ersten Tag);
    annualisiert geometrisch (CAGR, wissen/01 Abschnitt 5 und „Bezug zum Trading-Bot“).
    Ergebnis: Werte je Kriterium, Grenzen, `bestanden` je Kriterium und gesamt sowie die Jahrestabelle.
    """
    from tradingbot.kennzahlen.performance import cagr

    von, bis = (pd.Timestamp(z) for z in zeitraum)
    beide = pd.concat({"nachbau": nachbau, "referenz": referenz}, axis=1).dropna().loc[von:bis]
    renditen = beide.pct_change().dropna()
    korrelation = float(renditen["nachbau"].corr(renditen["referenz"]))
    jahresende = beide.groupby(beide.index.year).last()
    start = beide.iloc[[0]].set_axis([beide.index[0].year - 1])
    jahre = pd.concat([start, jahresende]).pct_change().dropna()
    jahre["abweichung"] = jahre["nachbau"] - jahre["referenz"]
    annualisiert = cagr(beide["nachbau"]) - cagr(beide["referenz"])
    kriterien = {
        "korrelation": {"wert": korrelation, "grenze": f">= {ABNAHME_KORRELATION_MIN}", "bestanden": korrelation >= ABNAHME_KORRELATION_MIN},
        "jahresabweichung_max": {"wert": float(jahre["abweichung"].abs().max()), "grenze": f"<= {ABNAHME_JAHRESABWEICHUNG_MAX}",
                                 "bestanden": bool((jahre["abweichung"].abs() <= ABNAHME_JAHRESABWEICHUNG_MAX + 1e-12).all())},
        "annualisiert_abweichung": {"wert": float(annualisiert), "grenze": f"|x| <= {ABNAHME_ANNUALISIERT_MAX}",
                                    "bestanden": abs(annualisiert) <= ABNAHME_ANNUALISIERT_MAX + 1e-12},
    }
    return {"kriterien": kriterien, "bestanden": all(k["bestanden"] for k in kriterien.values()),
            "jahre": jahre, "tage": len(beide), "zeitraum": (beide.index[0].date(), beide.index[-1].date())}


def gesamtrenditen(kurse: dict[str, pd.DataFrame], tage: pd.DatetimeIndex) -> pd.DataFrame:
    """Tägliche Gesamtrenditen je Titel (Tage × Titel); fehlende Tage bleiben leer (kein Auffüllen von Renditen)."""
    spalten = {}
    for titel, k in kurse.items():
        k = k.sort_index()
        r = simple_return(k["close"].shift(1), k["close"], k["dividende"])
        spalten[titel] = r.reindex(tage)
    return pd.DataFrame(spalten, index=tage)
