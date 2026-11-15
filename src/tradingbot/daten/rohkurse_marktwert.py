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
