"""Nachbau des S&P 500 aus dem point-in-time-Universum, mit oder ohne Finanzwerte.

Gemeinsamer Code für die Gegenprobe (tools/gegenprobe_index.py, ohne Ausschluss) und den Benchmark
„S&P 500 ohne Finanzwerte“ (tools/nachbau_sp500_ohne_finanzwerte.py). Regeln siehe docs/DATENQUALITAET.md:
- je Firma (CIK) eine Spalte; Gattungen und Ticker-Wechsel derselben Firma werden zusammengelegt
- Kurse ab Vorlauf 2011 (Messtag des Streubesitzes liegt meist im Vorjahr), Kalender nur echte Handelstage
- Gewicht: Streubesitz laut SEC-Deckblatt, gegen den Börsenwert geprüft, fortgeschrieben mit dem Kurs
- Finanzwerte: SIC 6000–6999 point-in-time (Code der jeweiligen 10-K, Vorgänger-CIKs eingeschlossen)
- nur Kurse aus dem Cache; Daten enden am 31.12.2024 (Tresor bleibt zu)
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from tradingbot.backtest.tresor import begrenze

from tradingbot.daten.abdeckung import STREUBESITZ
from tradingbot.daten.cache import standard_cache
from tradingbot.daten.fehlerschwelle import Fehlerschwelle
from tradingbot.daten.index_nachbau import (ABNAHME_ZEITRAUM, aktien_splitbereinigt, handelstage, marktwert_index, nachbau_gewichte,
                                            marktwerte_aus_streubesitz, streubesitz_pruefen)
from tradingbot.daten.sec import cik10, kennzahl_jahreswerte
from tradingbot.kennzahlen.rendite import simple_return

VORLAUF = pd.Timestamp("2011-01-03")
START = pd.Timestamp("2016-01-04")
ENDE = pd.Timestamp(ABNAHME_ZEITRAUM[1])
FINANZ_SIC = (6000, 6999)


def firmen_schluessel(zeile, nr):
    return int(zeile["cik"]) if pd.notna(zeile["cik"]) else f"ohne CIK {nr}"


def ciks_der_zeile(zeile) -> list[int]:
    vorgaenger = zeile["vorgaenger_ciks"]
    return ([int(zeile["cik"])] if pd.notna(zeile["cik"]) else []) + [int(c) for c in list(vorgaenger if vorgaenger is not None else [])]


@dataclass
class Firmendaten:
    kurse: dict                         # Firma → DataFrame (ab Vorlauf) oder None (keine gültige Reihe)
    streubesitz_roh: dict               # Firma → DataFrame (wert, filed; Index = Messtag), ungeprüft
    streubesitz_gueltig: dict           # Firma → geprüfte Werte (nur Firmen mit gültigen Kursen)
    verworfen: pd.DataFrame             # verworfene Streubesitzwerte mit Grund
    relevant: pd.DataFrame              # Mitgliedschaften im Zeitraum
    sic: dict = field(default_factory=dict)
    rohkurse: dict = field(default_factory=dict)          # Firma → unbereinigte Reihe (close, split); nur mit rohkurse=True
    rohkurse_status: dict = field(default_factory=dict)   # Firma → "roh" oder Grund für den Rückfall
    # Befund 11, Variante B (Jakob 16.11.2026): Firma → {"symbol", "H", "grund"} für Teilreihen, die die Abnahme nicht
    # bestanden haben und |H − 1| > 0,5 % zeigen; Scores rechnen dafür keinen Marktwert, der Index-Nachbau bleibt bei Teil b.
    rohkurse_unsicher: dict = field(default_factory=dict)


def _kappungs_eintraege() -> list:
    from tradingbot.konfiguration import lade_konfiguration

    return lade_konfiguration("universum_korrekturen").get("kursreihe_ende", []) or []


def kursreihen_ende() -> dict:
    """Gekappte Kursreihen je CIK (config/universum_korrekturen.yaml, `kursreihe_ende`, Einträge ohne `ticker`): letzter
    gültiger Tag für alle Reihen der Firma (dritte Datenkorrektur, E. I. du Pont)."""
    return {int(e["cik"]): pd.Timestamp(str(e["letzter_tag"])) for e in _kappungs_eintraege() if not e.get("ticker_einzeln")}


def kursreihen_ende_je_ticker() -> dict:
    """Gekappte Teilreihen (Einträge mit `ticker_einzeln: true`): (CIK, Ticker) → letzter gültiger Tag; gilt nur für die
    Reihe dieses Tickers, andere Reihen derselben Firma bleiben (fünfte Datenkorrektur DISCK/WBD, Jakob 15.11.2026)."""
    return {(int(e["cik"]), str(e["ticker"]).upper()): pd.Timestamp(str(e["letzter_tag"])) for e in _kappungs_eintraege() if e.get("ticker_einzeln")}


def abspaltungen_tiingo() -> dict:
    """Bestätigte Abspaltungen, die eine Tiingo-Reihe nicht enthält (config/universum_korrekturen.yaml,
    `abspaltungen_tiingo`, Teil c1): (CIK, Ticker) → Liste der Einträge (datum, kursfaktor, …)."""
    from tradingbot.konfiguration import lade_konfiguration

    aus: dict = {}
    for e in lade_konfiguration("universum_korrekturen").get("abspaltungen_tiingo", []) or []:
        aus.setdefault((int(e["cik"]), str(e["ticker"]).upper()), []).append(e)
    return aus


def buche_abspaltungen(k: pd.DataFrame, eintraege: list) -> pd.DataFrame:
    """Bucht den fehlenden Wert der Tochter als zusätzliche Ausschüttung am Ex-Tag (Jakob 15.11.2026).

    Formel: D_T = P_{t−1} · (1 − 1 / f), f = Kursfaktor nach Yahoo-Art = P_{t−1} / (P_{t−1} − Verhältnis · P_Tochter).
    Damit ist die Gesamtrendite am Ex-Tag (P_t + D_t + D_T − P_{t−1}) / P_{t−1} wie bei einer um f bereinigten Reihe;
    Schlusskurse und Marktwerte bleiben unverändert. Quelle: kennzahlen.rendite.simple_return (wissen/02, Abschnitt 2);
    Kriterien docs/FUNDAMENTAL.md, Teil c1.

    Befund 15 (Jakob 16.11.2026): Liegt der Ex-Tag innerhalb der geladenen Reihe, fehlt aber als Handelstag, bricht die
    Korrektur laut ab (DatenkorrekturPasstNicht, wie bei SIVB) statt den Eintrag still zu übergehen. Außerhalb der
    geladenen Reihe (Vorlauf, Tresorgrenze, Kappung) oder am ersten Tag ohne Vortag bleibt die Reihe unverändert.
    """
    k = k.copy()
    if "dividende" not in k.columns:
        k["dividende"] = 0.0
    for e in eintraege:
        tag = pd.Timestamp(str(e["datum"]))
        if k.empty or tag < k.index.min() or tag > k.index.max():
            continue
        if tag not in k.index:
            raise DatenkorrekturPasstNicht(f"{e.get('ticker', '?')}: Ex-Tag der Abspaltung {tag.date()} fehlt in der Kursreihe")
        if k.index.get_loc(tag) == 0:
            continue
        vortag = k["close"].iloc[k.index.get_loc(tag) - 1]
        k.loc[tag, "dividende"] = float(k.loc[tag, "dividende"] or 0.0) + vortag * (1 - 1 / float(e["kursfaktor"]))
    return k


class DatenkorrekturPasstNicht(RuntimeError):
    """Eine konfigurierte Datenkorrektur passt nicht (mehr) zu den Daten; wird nie still übergangen."""


class UniversumVerschoben(RuntimeError):
    """Universum und daten/universum/kursstatus.csv passen über die Zeilennummer nicht mehr zusammen."""


def pruefe_zuordnung(relevant: pd.DataFrame, status: pd.DataFrame) -> None:
    """Wächter (Jakob 17.11.2026): kursstatus.csv ist über die Zeilennummer des Universums verknüpft. Ändert sich das
    Universum (Wikipedia-Abruf des Betriebs am 16.11.2026, 22:18: eine Zeile mehr, ab Stelle 120 alles um eins verschoben),
    bekäme eine Firma still die Kurse eines
    anderen Symbols. Deshalb muss für jede genutzte Zeile, die in kursstatus.csv steht, der Ticker übereinstimmen; sonst
    lauter Abbruch. Behebung der Ursache (Zuordnung über den Schlüssel, eingefrorener Stand) folgt mit eigenem Plan."""
    if "ticker" not in status.columns or "ticker" not in relevant.columns:
        return
    gemeinsam = relevant.index.intersection(status.index)
    a = relevant.loc[gemeinsam, "ticker"].astype(str)
    b = status.loc[gemeinsam, "ticker"].astype(str)
    falsch = a.index[a.to_numpy() != b.to_numpy()]
    if len(falsch):
        beispiele = ", ".join(f"Zeile {i}: {a[i]} ≠ {b[i]}" for i in falsch[:3])
        raise UniversumVerschoben(f"Universum und kursstatus.csv verschoben: {len(falsch)} von {len(gemeinsam)} Zeilen mit anderem "
                                  f"Ticker ({beispiele}) – keine Kurse zugeordnet")


def eingefrorene_kurse() -> dict:
    """Eingefrorene Kurse nach einem Handelsstopp bei Insolvenz (config/universum_korrekturen.yaml, `eingefrorene_kurse`,
    vierte Datenkorrektur): (CIK, Ticker) → Liste der Einträge."""
    from tradingbot.konfiguration import lade_konfiguration

    aus: dict = {}
    for e in lade_konfiguration("universum_korrekturen").get("eingefrorene_kurse", []) or []:
        aus.setdefault((int(e["cik"]), str(e["ticker"]).upper()), []).append(e)
    return aus


def ersetze_eingefrorene(k: pd.DataFrame, eintraege: list) -> pd.DataFrame:
    """Vierte Datenkorrektur (Jakob 13.11.2026, docs/FUNDAMENTAL.md): Eröffnung, Hoch, Tief und Schluss der eingefrorenen
    Tage [erster_tag, letzter_tag] werden durch den ersten echten Kurs nach dem Stopp ersetzt (Dividende 0); der Verlust
    fällt damit auf den ersten Tag des Stopps.

    Schutz: Die Reihe muss an `erster_echter_tag` den `ersatzkurs` zeigen und an den Tagen des Laufs eingefroren sein
    (Schluss gleich dem Vortag ab dem zweiten Tag); sonst DatenkorrekturPasstNicht. Liegt der Zeitraum außerhalb der
    geladenen Reihe (z. B. Tresor-Grenze), bleibt die Reihe unverändert.
    """
    for e in eintraege:
        erster, letzter, echt = (pd.Timestamp(str(e[x])) for x in ("erster_tag", "letzter_tag", "erster_echter_tag"))
        ersatz = float(e["ersatzkurs"])
        if erster not in k.index:
            continue
        lauf = k.loc[erster:letzter]
        if echt not in k.index or abs(float(k.loc[echt, "close"]) - ersatz) > 1e-6 * max(1.0, ersatz):
            raise DatenkorrekturPasstNicht(f"{e['ticker']}: erster echter Kurs am {echt.date()} ist nicht {ersatz}")
        if len(lauf) < 2 or (lauf["close"].diff().iloc[1:].abs() > 1e-9).any():
            raise DatenkorrekturPasstNicht(f"{e['ticker']}: Reihe zwischen {erster.date()} und {letzter.date()} nicht eingefroren")
        k = k.copy()
        for spalte in ("open", "high", "low", "close"):
            if spalte in k.columns:
                k.loc[lauf.index, spalte] = ersatz
        if "dividende" in k.columns:
            k.loc[lauf.index, "dividende"] = 0.0
    return k


def pruefbasis(kurse: pd.DataFrame | None, rohreihe: pd.DataFrame | None) -> tuple:
    """Kurs und Split-Spalte für die Prüfung der Streubesitzwerte (c2 (3), Jakob 15.11.2026).

    Ohne Rohreihe: bereinigte Kursreihe (bisher). Mit abgenommener Rohreihe: Rohkurs auf der Split-Basis der Tresorgrenze,
    C'_t = Roh_t / Π_{t<x≤Grenze} s_x (Tiingo-Splitfaktoren), dazu dieselben Splitfaktoren für die Aktienzahl. C'_t enthält
    keinen verdeckten Faktor H aus Splits nach der Tresorgrenze; C'_e · A_e ist der Börsenwert am Messtag.
    """
    if rohreihe is None or rohreihe.empty:
        return (None, None) if kurse is None else (kurse["close"], kurse["split"])
    from tradingbot.daten.rohkurse_marktwert import faktor_nach

    return rohreihe["close"] / faktor_nach(rohreihe["split"]), rohreihe["split"]


def aktienkorrektur(splits: pd.Series, ereignisse: pd.DataFrame | None):
    """Befund 12 (Jakob 16.11.2026): Faktor für streubesitz_pruefen, der eine mit allen Faktoren nach d bereinigte
    Aktienzahl auf die Kursbasis des Messtags e bringt: K(d, e) für d < e, 1 / K(e, d) für d > e (K =
    Π s_x / f_x aus der Kapitalmaßnahmen-Liste, Abspaltung s = 1; ungeklärte Ereignisse s = f wie bisher)."""
    from tradingbot.daten.kapitalmassnahmen_historie import korrektur

    def faktor(d, e) -> float:
        d, e = pd.Timestamp(d), pd.Timestamp(e)
        if d == e:
            return 1.0
        return korrektur(splits, ereignisse, d, e)[0] if d < e else 1.0 / korrektur(splits, ereignisse, e, d)[0]

    return faktor


def kappe_reihe(k: pd.DataFrame, firma, ticker: str, kappung: dict, kappung_ticker: dict) -> pd.DataFrame:
    """Wendet beide Kappungen auf eine Teilreihe an."""
    if firma in kappung:                                       # dritte Datenkorrektur: Reihe gehört danach einer anderen Firma
        k = k.loc[:kappung[firma]]
    schluessel = (firma, str(ticker).upper())
    if schluessel in kappung_ticker:                           # fünfte Datenkorrektur: nur diese Teilreihe
        k = k.loc[:kappung_ticker[schluessel]]
    return k


def lade_firmendaten(universum: pd.DataFrame, status: pd.DataFrame, sic_historien: dict, *, von=VORLAUF, bis=ENDE,
                     mitglied_ab=START, tiingo=None, rohkurse: bool = False) -> Firmendaten:
    """Kurse, Streubesitz (roh und geprüft) und SIC-Historie je Firma; Fehlerschwelle 5 % beim Laden der Kurse.
    `rohkurse` (c2 (2), nur Backtest-Auswertung): zusätzlich unbereinigte Reihen je Firma, nur wenn jede Teilreihe der
    Firma eine bestandene Abnahme hat (daten/rohkurse_marktwert.py); sonst Grund in `rohkurse_status`. Nur lokale Dateien."""
    from tradingbot.daten.tiingo import TiingoClient
    from tradingbot.konfiguration import lade_konfiguration

    aktien_def = lade_konfiguration("fundamental")["kennzahlen"]["aktien_ausstehend"]
    mitglied_ab, bis = pd.Timestamp(mitglied_ab), pd.Timestamp(bis)
    relevant = universum[(universum["bis"].isna() | (universum["bis"] > mitglied_ab)) & (universum["von"].isna() | (universum["von"] <= bis))]
    pruefe_zuordnung(relevant, status)                       # Wächter: keine still falsch zugeordneten Kurse (17.11.2026)
    cache, tiingo = standard_cache(), tiingo or TiingoClient()
    kappung, kappung_ticker = kursreihen_ende(), kursreihen_ende_je_ticker()
    abspaltungen = abspaltungen_tiingo()
    eingefroren = eingefrorene_kurse()
    roh_kurse, roh_status, roh_ok, roh_unsicher, unsicher, ereignisse = {}, {}, set(), {}, {}, None
    if rohkurse:
        from tradingbot.daten.rohkurse_marktwert import abgenommen, lade_abnahme, rohreihe, unsichere_reihen

        abn = lade_abnahme()
        roh_ok, unsicher = abgenommen(abn), unsichere_reihen(abn)
        from tradingbot.daten.kapitalmassnahmen_historie import lade_ereignisse

        ereignisse = lade_ereignisse()                     # Befund 12: K in der Prüfung der Streubesitzwerte (c3)
    schwelle = Fehlerschwelle("Nachbau: Kurse aus dem Cache")
    kurse: dict = {}
    for nr, z in relevant.iterrows():
        firma = firmen_schluessel(z, nr)
        s = status.loc[nr] if nr in status.index else None
        if s is None or not bool(s["gueltig"]):
            kurse.setdefault(firma, None)
            continue
        fehler = None
        try:
            k = cache.lesen("kurse", s["symbol"])[0] if s["quelle"] == "yfinance" else tiingo.historie(s["symbol"])
            k = begrenze(k)                                   # Tresor: Cache-Kurse nur bis zur Datumsgrenze
            if k is None or k.empty:
                raise LookupError("Kurse nicht im Cache")
            k = k.sort_index().loc[pd.Timestamp(von):bis]
            k = kappe_reihe(k, firma, z["ticker"], kappung, kappung_ticker)
            k = buche_abspaltungen(k, abspaltungen.get((firma, str(z["ticker"]).upper()), []))
            k = ersetze_eingefrorene(k, eingefroren.get((firma, str(z["ticker"]).upper()), []))
            kurse[firma] = k if kurse.get(firma) is None else kurse[firma].combine_first(k)
            if rohkurse and (s["quelle"], s["symbol"]) in unsicher:
                roh_unsicher[firma] = {"symbol": s["symbol"], **unsicher[(s["quelle"], s["symbol"])]}
            if rohkurse and roh_status.get(firma, "roh") == "roh":
                r = rohreihe(s["quelle"], s["symbol"]) if (s["quelle"], s["symbol"]) in roh_ok else None
                if r is None:
                    roh_status[firma] = ("Abnahme fehlt oder nicht bestanden" if (s["quelle"], s["symbol"]) not in roh_ok
                                         else "Rohreihe fehlt") + f" ({s['symbol']})"
                    roh_kurse.pop(firma, None)
                else:
                    r = kappe_reihe(r[["close", "split"]].sort_index().loc[pd.Timestamp(von):bis], firma, z["ticker"], kappung, kappung_ticker)
                    roh_kurse[firma] = r if firma not in roh_kurse else roh_kurse[firma].combine_first(r)
                    roh_status[firma] = "roh"
        except DatenkorrekturPasstNicht:
            raise                                             # nie still als Ladefehler zählen
        except Exception as f:  # zählt gegen die Fehlerschwelle
            fehler = f"{z['ticker']}: {type(f).__name__}"
        schwelle.zaehle(fehler)
    schwelle.pruefe()

    roh, gueltig, verworfen, sic = {}, {}, [], {}
    for firma in kurse:
        if isinstance(firma, str):
            continue
        zeile = relevant[relevant["cik"] == firma].iloc[0]
        reihen, aktien = [], []
        schluss_pruef, split_pruef = pruefbasis(kurse[firma], roh_kurse.get(firma) if roh_status.get(firma) == "roh" else None)
        for cik in ciks_der_zeile(zeile):
            sic.setdefault(firma, []).extend(sic_historien.get(cik, []))
            erst, _ = cache.lesen("sec_erstmeldungen", cik10(cik))
            if erst is None:
                continue
            reihen.append(kennzahl_jahreswerte(erst, STREUBESITZ, "2100-01-01"))
            if kurse[firma] is not None:
                a = kennzahl_jahreswerte(erst, aktien_def, "2100-01-01")
                if len(a):
                    aktien.append(aktien_splitbereinigt(a["wert"], split_pruef))
        sic[firma] = sorted(sic.get(firma, []))
        if not reihen:
            continue
        reihe = pd.concat(reihen).sort_index()
        roh[firma] = reihe[~reihe.index.duplicated(keep="first")]
        if kurse[firma] is not None:
            k_aktien = (aktienkorrektur(split_pruef, ereignisse.get(firma)) if ereignisse is not None and split_pruef is not None
                        else None)
            g, v = streubesitz_pruefen(roh[firma], schluss_pruef, pd.concat(aktien) if aktien else pd.Series(dtype=float), k_aktien)
            gueltig[firma] = g
            verworfen += [{"cik": firma, "ende": e.date(), "wert_mrd": r.wert / 1e9, "grund": r.grund} for e, r in v.iterrows()]
    return Firmendaten(kurse, roh, gueltig, pd.DataFrame(verworfen, columns=["cik", "ende", "wert_mrd", "grund"]), relevant, sic,
                       roh_kurse, roh_status, roh_unsicher)


def finanzwert_maske(sic: dict, tage: pd.DatetimeIndex, firmen: list) -> pd.DataFrame:
    """True, wenn die Firma am Tag nach SIC point-in-time ein Finanzwert ist (vor dem ersten 10-K: erster Code)."""
    maske = pd.DataFrame(False, index=tage, columns=firmen)
    for f in firmen:
        historie = sic.get(f, [])
        if not historie:
            continue
        daten = np.array([d for d, _ in historie], dtype="datetime64[ns]")
        codes = np.array([c for _, c in historie])
        stelle = np.searchsorted(daten, tage.to_numpy(), side="right") - 1
        code = codes[np.clip(stelle, 0, None)]
        maske[f] = (code >= FINANZ_SIC[0]) & (code <= FINANZ_SIC[1])
    return maske


def baue_nachbau(daten: Firmendaten, *, ohne_finanzwerte: bool = False, von=START, bis=ENDE, marktwert_korrektur: bool = False) -> dict:
    """Kettenindex (USD) nach index_nachbau.marktwert_index; Ergebnis: nachbau (index, abdeckung), tage, mitglied.
    `marktwert_korrektur`: Fortschreibung des Streubesitzes ohne Abspaltungen (Datenkorrektur Marktwert, Jakob 13.11.2026)."""
    firmen = sorted(daten.kurse, key=str)
    schluss_voll = pd.DataFrame({f: (daten.kurse[f]["close"] if daten.kurse[f] is not None else pd.Series(dtype=float)) for f in firmen})
    tage = handelstage(schluss_voll, von, bis)
    renditen = pd.DataFrame({f: (simple_return(daten.kurse[f]["close"].shift(1), daten.kurse[f]["close"], daten.kurse[f]["dividende"])
                                 if daten.kurse[f] is not None else pd.Series(dtype=float)) for f in firmen}).reindex(tage)
    mitglied = pd.DataFrame(False, index=tage, columns=firmen)
    for nr, z in daten.relevant.iterrows():
        firma = firmen_schluessel(z, nr)
        anfang = z["von"] if pd.notna(z["von"]) else pd.Timestamp(von)
        schluss_tag = z["bis"] if pd.notna(z["bis"]) else pd.Timestamp(bis) + pd.Timedelta(days=1)
        mitglied[firma] |= (tage >= anfang) & (tage < schluss_tag)
    if ohne_finanzwerte:
        mitglied &= ~finanzwert_maske(daten.sic, tage, firmen)
    korrektur_je_firma = None
    if marktwert_korrektur:
        from tradingbot.daten.kapitalmassnahmen_historie import lade_ereignisse

        ereignisse = lade_ereignisse()
        korrektur_je_firma = {f: (daten.kurse[f]["split"], ereignisse.get(f)) for f in firmen
                              if daten.kurse[f] is not None and "split" in daten.kurse[f].columns and not isinstance(f, str)}
    marktwerte = marktwerte_aus_streubesitz(schluss_voll, daten.streubesitz_gueltig, korrektur_je_firma).reindex(tage)
    nachbau = marktwert_index(renditen.where(mitglied), marktwerte, mitglied)
    gewichte, _ = nachbau_gewichte(renditen.where(mitglied), marktwerte, mitglied)
    return {"nachbau": nachbau, "tage": tage, "mitglied": mitglied, "gewichte": gewichte}


def rueckfall_gewichte(daten: Firmendaten, gewichte: pd.DataFrame, ab) -> pd.DataFrame:
    """Befund 11 (Jakob 16.11.2026): Firmen ohne abgenommene Rohreihe im Index-Nachbau (dort Teil b, gemeldet) mit
    Grund, H-Schätzung (Variante B) und Gewicht ab `ab` (Mittel über die Tage mit Gewicht und Maximum)."""
    g = gewichte.loc[pd.Timestamp(ab):]
    zeilen = []
    for firma, grund in sorted(daten.rohkurse_status.items(), key=lambda x: str(x[0])):
        if grund == "roh" or firma not in g.columns:
            continue
        w = g[firma].dropna()
        u = daten.rohkurse_unsicher.get(firma, {})
        zeilen.append({"firma": firma, "grund": grund, "H": u.get("H"), "tage": len(w),
                       "gewicht_mittel": float(w.mean()) if len(w) else 0.0, "gewicht_max": float(w.max()) if len(w) else 0.0})
    return pd.DataFrame(zeilen, columns=["firma", "grund", "H", "tage", "gewicht_mittel", "gewicht_max"])


BENCHMARK_SCHLUESSEL = "SP500_ohne_finanzwerte"


def lade_benchmark_sp500_ohne_finanzwerte() -> pd.DataFrame:
    """Benchmark „S&P 500 ohne Finanzwerte“ aus dem Cache (Spalten index_usd, index_eur, abdeckung); gebaut von
    tools/nachbau_sp500_ohne_finanzwerte.py, erst nachdem die Gegenprobe bestanden ist (docs/DATENQUALITAET.md)."""
    tabelle, meta = standard_cache().lesen("benchmarks", BENCHMARK_SCHLUESSEL)
    if tabelle is None:
        raise LookupError("Benchmark fehlt im Cache: .venv/Scripts/python tools/nachbau_sp500_ohne_finanzwerte.py ausführen")
    tabelle.attrs.update(meta)
    return tabelle
