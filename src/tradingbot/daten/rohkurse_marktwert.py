"""Rohkurse (unbereinigt) für den Marktwert im Backtest: Abnahme je Reihe und Vollständigkeit für c3 (Jakob 15.11.2026,
docs/FUNDAMENTAL.md, „c2 (2): Marktwert aus Rohkursen – Abnahme und Stichprobe“).

Warum: Die Kursreihen im Cache (Yahoo `close`, Tiingo nach `normalisieren`) sind rückwirkend um alle Splits bereinigt,
auch um Splits nach der Tresorgrenze. Der Tresor schneidet die Split-Einträge ab, die Bereinigung bleibt in den alten
Kursen (verdeckter Faktor H). Der Marktwert braucht deshalb den unbereinigten Kurs:

    MW_T = Roh_T · A_d · Π_{d<e≤T} s_e          (engines/fundamental/multiples.marktwert_rohkurs)

Abnahme: v_t = Roh_t / C_t gegen eine NUR splitbereinigte Reihe C (nie dividendenbereinigt: Adj Close driftet mit jeder
Ausschüttung). Erwartet v_t = H · Π_{t<e≤Grenze} f_e mit den Split-Faktoren f_e der verglichenen Reihe C (Yahoo führt
Abspaltungen als „Split“ und bereinigt `close` darum). Bestanden: ≥ 250 gemeinsame Tage ab 2011, |v_t/(H·Πf) − 1| ≤ 1 %
an ≥ 99 % der Tage. Diese Datei liest nur lokale Dateien, nie das Netz. Tageslauf und Betriebsbewertung nutzen sie nicht.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

import pandas as pd

TOLERANZ, ANTEIL_MIN, MIN_TAGE, AB = 0.01, 0.99, 250, pd.Timestamp("2011-01-01")
SPALTEN_ABNAHME = ["quelle", "symbol", "ticker", "tage", "H", "anteil_ok", "max_abw", "bestanden", "name_tiingo", "grund"]


def abnahme_datei(ablage: Path | None = None) -> Path:
    from tradingbot.daten.tiingo_rohkurse import ordner

    return (ablage or ordner()) / "abnahme.csv"


def rohreihe(quelle: str, symbol: str, *, ablage: Path | None = None, tiingo_wurzel: Path | None = None) -> pd.DataFrame | None:
    """Unbereinigte Reihe (Spalten close, split; split 0 = kein Split) bis zur Tresorgrenze, nur aus lokalen Dateien.
    Yahoo-Reihen: Nachlader-Ablage (roh_bis_tresor); Tiingo-Reihen: unbereinigte Werte aus dem Tiingo-Kurs-Cache."""
    from tradingbot.backtest.tresor import begrenze
    from tradingbot.daten.tiingo_rohkurse import lade_rohkurse

    if quelle == "yfinance":
        k = lade_rohkurse(symbol, ablage=ablage)
        return None if k is None else k[["close", "split"]].assign(name=k.attrs.get("name"))
    if tiingo_wurzel is None:
        from tradingbot.konfiguration import PROJEKT_WURZEL

        tiingo_wurzel = PROJEKT_WURZEL / "daten" / "cache" / "tiingo"
    datei = Path(tiingo_wurzel) / "kurse" / f"{symbol.lower().replace('/', '_')}.json.gz"
    if not datei.exists():
        return None
    with gzip.open(datei, "rt", encoding="utf-8") as f:
        roh = json.load(f)
    if not roh:
        return None
    t = pd.DataFrame(roh)
    t.index = pd.DatetimeIndex(pd.to_datetime(t["date"]).dt.tz_localize(None).dt.normalize(), name="datum")
    k = pd.DataFrame({"close": t["close"].astype(float), "split": t["splitFactor"].astype(float).replace(1.0, 0.0)}).sort_index()
    return begrenze(k).assign(name=None)


def pruefe_nur_splitbereinigt(k: pd.DataFrame) -> None:
    """Die Vergleichsreihe muss nur splitbereinigt sein: Dividenden getrennt in `dividende`, keine Spalte „adj…“."""
    if any(str(c).lower().startswith("adj") for c in k.columns) or "dividende" not in k.columns:
        raise ValueError("Abnahme nur gegen eine nur splitbereinigte Reihe (close mit getrennter Spalte dividende, ohne Adj Close)")


def faktor_nach(split: pd.Series) -> pd.Series:
    """Π der Split-Faktoren strikt nach dem Tag (0 oder 1 = kein Split)."""
    s = split.fillna(0).replace(0, 1.0).astype(float).sort_index()
    return s[::-1].cumprod()[::-1].shift(-1).fillna(1.0)


def abnahme(roh: pd.DataFrame, bereinigt: pd.DataFrame) -> dict:
    """Abnahme einer Rohreihe gegen die nur splitbereinigte Reihe desselben Titels (Kriterien siehe Modulkopf)."""
    pruefe_nur_splitbereinigt(bereinigt)
    b = bereinigt.sort_index()
    erwartet = faktor_nach(b["split"] if "split" in b.columns else pd.Series(0.0, index=b.index))
    gemeinsam = roh.index.intersection(b.index)
    gemeinsam = gemeinsam[(gemeinsam >= AB) & (roh["close"].reindex(gemeinsam) > 0).to_numpy() & (b["close"].reindex(gemeinsam) > 0).to_numpy()]
    if len(gemeinsam) == 0:
        return {"tage": 0, "H": float("nan"), "anteil_ok": 0.0, "max_abw": float("nan"), "bestanden": False, "grund": "keine gemeinsamen Tage"}
    v = roh["close"].reindex(gemeinsam) / b["close"].reindex(gemeinsam)
    q = v / erwartet.reindex(gemeinsam)
    h = float(q.median())
    abw = (q / h - 1).abs()
    anteil = float((abw <= TOLERANZ).mean())
    bestanden = len(gemeinsam) >= MIN_TAGE and anteil >= ANTEIL_MIN
    grund = "" if bestanden else (f"nur {len(gemeinsam)} gemeinsame Tage" if len(gemeinsam) < MIN_TAGE
                                  else f"nur {anteil:.1%} der Tage innerhalb 1 %")
    return {"tage": len(gemeinsam), "H": h, "anteil_ok": anteil, "max_abw": float(abw.max()), "bestanden": bestanden, "grund": grund}


SPLIT_TOLERANZ, SPLIT_TAGE = 0.01, 1        # Befund 10 (Jakob 16.11.2026): Faktor ±1 %, Datum ±1 Handelstag
OHNE_AKTIENWIRKUNG = {"abspaltung", "nicht_zugehoerig"}


def _ereignisse(split: pd.Series | None) -> pd.Series:
    if split is None:
        return pd.Series(dtype=float)
    s = split.fillna(0).astype(float).sort_index()
    s = s[(s > 0) & ((s - 1).abs() > 1e-9) & (s.index >= AB)]
    return s


def splitabgleich(tiingo_split: pd.Series, yahoo_split: pd.Series, liste: pd.DataFrame | None = None) -> dict:
    """Zweites Abnahmekriterium „Splitspalte“ (Befund 10, docs/FUNDAMENTAL.md, festgehalten 16.11.2026 11:21).

    Gerechnet wird mit den Tiingo-Splitfaktoren der Rohreihe; geprüft wird, ob sie zu den Yahoo-Ereignissen und deren
    Einordnung in `config/kapitalmassnahmen_historie.yaml` passen. Paarung: Tiingo-Datum höchstens 1 Handelstag (der
    Yahoo-Reihe) vom Yahoo-Datum entfernt, jedes Ereignis höchstens einmal. Je Yahoo-Ereignis nach Art der Liste:
    split oder nicht in der Liste → Partner mit Faktor ±1 % des Yahoo-Faktors; kombiniert → Partner mit Faktor ±1 % des
    geprüften split_faktor; abspaltung, nicht_zugehoerig → kein Partner; unklar → nie bestanden. Änderung nach dem ersten
    Lauf (Jakob 16.11.2026 12:45): Ein Tiingo-Faktor genau am Datum einer Abspaltung der Liste (Yahoo-, Tiingo- und
    Listendatum gleich) gilt als bestanden und wird als Hinweis gemeldet; K behandelt ihn. Jedes Tiingo-Ereignis ohne
    Yahoo-Partner: nicht bestanden. `liste`: Einträge der CIKs der Reihe (Index datum, Spalten art, split_faktor).
    Rückgabe {"bestanden", "grund", "hinweis"} (grund leer bei bestanden, sonst alle Abweichungen, durch „; “ getrennt)."""
    ys, ts = _ereignisse(yahoo_split), _ereignisse(tiingo_split)
    tage = yahoo_split.index.sort_values()
    frei = dict(ts.items())
    fehler = []

    def nachbarn(tag) -> list:
        pos = int(tage.searchsorted(tag))
        return [tage[i] for i in range(max(0, pos - SPLIT_TAGE), min(len(tage), pos + SPLIT_TAGE + 1))]

    def eintrag(tag):
        if liste is None or liste.empty:
            return None, None
        for t in [tag] + [n for n in nachbarn(tag) if n != tag]:
            if t in liste.index:
                z = liste.loc[t]
                return (z.iloc[0] if isinstance(z, pd.DataFrame) else z), t
        return None, None

    hinweise = []
    for tag, fy in ys.items():
        n = nachbarn(tag)
        kandidaten = sorted((t for t in frei if n[0] <= t <= n[-1]), key=lambda t: abs((t - tag).days))
        tiingo_tag = kandidaten[0] if kandidaten else None
        ft = frei.pop(tiingo_tag) if kandidaten else None
        z, listen_tag = eintrag(tag)
        art = str(z["art"]) if z is not None else None
        d = f"{tag.date()}"
        if art == "unklar":
            fehler.append(f"{d}: Yahoo {fy:g} in der Liste unklar (nicht eingeordnet)")
        elif art in OHNE_AKTIENWIRKUNG:
            if ft is not None and art == "abspaltung" and tiingo_tag == tag and listen_tag == tag:
                hinweise.append(f"{d}: Tiingo-Faktor {ft:g} an Abspaltung der Liste (über K behandelt)")
            elif ft is not None:
                fehler.append(f"{d}: Tiingo-Faktor {ft:g} an einem Tag mit Art „{art}“"
                              + ("" if art != "abspaltung" else " (Datum weicht ab)"))
        else:
            soll = float(z["split_faktor"]) if art == "kombiniert" and pd.notna(z["split_faktor"]) else fy
            if art == "kombiniert" and pd.isna(z["split_faktor"]):
                fehler.append(f"{d}: kombiniert ohne geprüften Split-Faktor")
            elif ft is None:
                fehler.append(f"{d}: Split {soll:g} fehlt bei Tiingo" + (f" (Art {art})" if art else " (nicht in der Liste)"))
            elif abs(ft / soll - 1) > SPLIT_TOLERANZ:
                fehler.append(f"{d}: Tiingo {ft:g} statt {soll:g}" + (f" (Art {art})" if art else ""))
    for t, ft in sorted(frei.items()):
        fehler.append(f"{t.date()}: Tiingo-Faktor {ft:g} ohne Yahoo-Ereignis")
    return {"bestanden": not fehler, "grund": "; ".join(fehler), "hinweis": "; ".join(hinweise)}


def lade_abnahme(datei: Path | None = None) -> pd.DataFrame:
    d = datei or abnahme_datei()
    if not Path(d).exists():
        return pd.DataFrame(columns=SPALTEN_ABNAHME)
    return pd.read_csv(d)


def abgenommen(abn: pd.DataFrame) -> set[tuple[str, str]]:
    """(quelle, symbol) der bestandenen Rohreihen."""
    if abn.empty:
        return set()
    ok = abn[abn["bestanden"].astype(str).str.lower() == "true"]
    return set(zip(ok["quelle"], ok["symbol"]))


def fehlende_fuer_c3(status: pd.DataFrame, abn: pd.DataFrame, dauerhaft_nicht_verfuegbar: set[str]) -> list[str]:
    """Sperre c3: gültige Reihen des Universums ohne Abnahme-Eintrag (bestanden oder nicht), außer Yahoo-Symbole, die der
    Nachlader als dauerhaft nicht verfügbar führt (Tiingo-Ticker klein geschrieben)."""
    from tradingbot.daten.tiingo_rohkurse import tiingo_ticker

    erfasst = set(zip(abn["quelle"], abn["symbol"])) if not abn.empty else set()
    g = status[status["gueltig"].astype(bool)]
    fehlend = []
    for quelle, symbol in sorted(set(zip(g["quelle"], g["symbol"]))):
        if (quelle, symbol) in erfasst:
            continue
        if quelle == "yfinance" and tiingo_ticker(symbol) in dauerhaft_nicht_verfuegbar:
            continue
        fehlend.append(f"{symbol} ({quelle})")
    return fehlend


def dauerhaft_nicht_verfuegbar(ablage: Path | None = None) -> set[str]:
    """Tiingo-Ticker, die der Nachlader als dauerhaft nicht verfügbar führt (Kurs-404 und nicht in Tiingos Liste)."""
    from tradingbot.daten.tiingo_rohkurse import Nachlader

    datei = (ablage or abnahme_datei().parent) / "stand.json"
    if not datei.exists():
        return set()
    stand = json.loads(datei.read_text(encoding="utf-8"))
    return {t for t, e in stand.get("fehler", {}).items() if Nachlader._dauerhaft(e, t)}


def schwelle_der_abnahme(abn: pd.DataFrame) -> str | None:
    """Befund 14 (Jakob 16.11.2026): Text, wenn mehr als 5 % der Reihen mit Rohreihe die Abnahme nicht bestanden haben
    (dieselbe Schwelle wie die Fehlerschwelle in tools/pruefe_rohkurse.py); sonst None."""
    from tradingbot.daten.fehlerschwelle import SCHWELLE

    if abn.empty:
        return None
    nicht = int((abn["bestanden"].astype(str).str.lower() != "true").sum())
    anteil = nicht / len(abn)
    if anteil <= SCHWELLE:
        return None
    return f"Fehlerschwelle der Abnahme überschritten: {nicht} von {len(abn)} Reihen nicht bestanden ({anteil:.1%} > {SCHWELLE:.0%})"


def sperre_c3() -> list[str]:
    """Sperre für den gewerteten Neulauf c3 (leer = frei): Reihen ohne Abnahme der Rohkurse und, seit Befund 14, eine
    überschrittene Fehlerschwelle der Abnahme (erster Eintrag). Nur lokale Dateien."""
    from tradingbot.konfiguration import PROJEKT_WURZEL

    status = pd.read_csv(PROJEKT_WURZEL / "daten" / "universum" / "kursstatus.csv")
    abn = lade_abnahme()
    schwelle = schwelle_der_abnahme(abn)
    return ([schwelle] if schwelle else []) + fehlende_fuer_c3(status, abn, dauerhaft_nicht_verfuegbar())


def unsichere_reihen(abn: pd.DataFrame, grenze: float = 0.005) -> dict[tuple[str, str], dict]:
    """Befund 11, Variante B (Jakob 16.11.2026): Reihen, die die Abnahme nicht bestanden haben und deren H-Schätzung um
    mehr als 0,5 % von 1 abweicht. Für sie gibt es keinen Marktwert (Teil b enthielte den verdeckten Faktor); ohne
    H-Schätzung (NaN) bleibt Teil b. Rückgabe (quelle, symbol) → {"H", "grund"}."""
    if abn.empty:
        return {}
    nicht = abn[abn["bestanden"].astype(str).str.lower() != "true"]
    h = pd.to_numeric(nicht["H"], errors="coerce")
    nicht = nicht[h.notna() & ((h - 1).abs() > grenze)]
    return {(z.quelle, z.symbol): {"H": float(z.H), "grund": str(z.grund) if pd.notna(z.grund) else ""} for z in nicht.itertuples()}


def c3_argumente(parser) -> None:
    """Gemeinsame Schalter der Werkzeuge des Neulaufs c3 (docs/FUNDAMENTAL.md, Checkliste c3)."""
    parser.add_argument("--c3", action="store_true",
                        help="Neulauf c3: alle Datenkorrekturen (Marktwert Teil b in der Fortschreibung, Streubesitz-Prüfung und "
                             "Marktwert mit Rohkursen); startet nur, wenn jede Reihe eine Abnahme der Rohkurse hat")
    parser.add_argument("--probe", action="store_true", help="mit --c3: Teilabdeckung erlaubt, eigene Ausgaben, zählt nie als c3")


def c3_sperre_melden(c3: bool, probe: bool) -> str | None:
    """Text für den Abbruch, wenn c3 ohne --probe gesperrt ist; sonst None."""
    if not c3 or probe:
        return None
    return sperrtext(sperre_c3())


def sperrtext(gruende: list[str]) -> str | None:
    """Abbruchtext aus sperre_c3(): Fehlerschwelle (Befund 14) und Reihen ohne Abnahme; None, wenn frei."""
    if not gruende:
        return None
    schwelle = [g for g in gruende if g.startswith("Fehlerschwelle")]
    fehlend = [g for g in gruende if not g.startswith("Fehlerschwelle")]
    teile = [f"Sperre c3: {s} (mit Jakob besprechen, nichts anpassen; oder --probe)" for s in schwelle]
    if fehlend:
        teile.append(f"Sperre c3: {len(fehlend)} Reihen ohne Abnahme der Rohkurse (erst nachladen und tools/pruefe_rohkurse.py, "
                     f"oder --probe): {', '.join(fehlend[:30])}" + (" …" if len(fehlend) > 30 else ""))
    return " | ".join(teile)
