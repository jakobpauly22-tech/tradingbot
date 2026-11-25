"""Value at Risk und Expected Shortfall der Risiko-Übersicht (docs/RISIKO_UEBERSICHT.md, Abschnitte 6 und 6a; Festlegungen
Jakob 25.11.2026). Reine Auswertung ohne Wirkung auf Vorschläge oder Orders; liest nur den Kurs-Cache des Betriebs.

Methode (historische Simulation mit vollständiger Neubewertung):
- Fenster: die letzten 501 Xetra-Handelstage bis zum Stichtag (500 Tagesrenditen). US-Kurse und EURUSD werden auf
  Xetra-Tage vorgetragen (Einschränkung: Xetra schließt 17:30, NYSE 22:00 – Renditen nicht zeitgleich).
- Renditen aus dem Gesamtrendite-Index (Kurs plus Dividende am Ex-Tag, `kennzahlen.rendite.total_return_index`), damit
  ein Ex-Tag nicht als Scheinverlust zählt (Lesart von „Pᵢ“ in Abschnitt 6).
- Euro-Sicht: USD-Titel als P_EUR = P_USD / EURUSD; das ist (1 + r_USD) · (1 + r_FX) − 1. Euro-ETFs enthalten ihr
  Währungsrisiko im Kurs. Fremdwährungskasse: r = EURUSD(t−h) / EURUSD(t) − 1; EUR-Kasse: 0.
- Szenario-GuV(t) = Σ heutiger Wert in EUR × rᵢ(t), Haltedauer h = 1 (500 Szenarien) und h = 10 (überlappende echte
  10-Tages-Renditen, 491 Szenarien). √10 · VaR(1 Tag) nur als Vergleichswert.
- VaR/ES: `kennzahlen.performance.var_es_kte_schlechteste` (k-te schlechteste, ohne Interpolation). 99 % „unsicher“.
- ES-Beitrag je Position (und Fremdwährungskasse) = −Mittel ihrer GuV in den k schlechtesten Szenarien des Buchs;
  Summe = ES.
- Ersatzreihen (6a), feste Rangfolge je Titel: eigene Reihe über das ganze Fenster → Vorgänger aus gebuchtem
  Tickerwechsel → Ersatz (US-Einzelaktie → IUSA.DE, ETF → ETF gleicher Region und Anlageklasse aus
  config/risiko_uebersicht.yaml), ohne Beta. Das Fenster wird nie gekürzt. Anteil mit Ersatz am Wert > 25 % →
  „eingeschränkt“; ohne Reihe → „nicht berechenbar“.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np
import pandas as pd

from tradingbot.betrieb.kalender import ist_handelstag
from tradingbot.kennzahlen.performance import var_es_kte_schlechteste
from tradingbot.kennzahlen.rendite import total_return_index
from tradingbot.risiko.klumpen import Basis

FENSTER = 500
HALTEDAUERN = (1, 10)
NIVEAUS = (0.95, 0.99)
UNSICHER = 0.99
ERSATZ_SCHWELLE = 0.25
ERSATZ_EINZELAKTIE = "IUSA.DE"
FX_TICKER = {"USD": "EURUSD=X"}
MAX_ALTER_TAGE = 7                                   # letzter Kurs höchstens 7 Kalendertage vor dem Stichtag

OK, EINGESCHRAENKT, NICHT_BERECHENBAR = "ok", "eingeschränkt", "nicht berechenbar"
EIGEN, VORGAENGER, ERSATZ = "eigen", "Vorgänger", "Ersatz"


def xetra_tage(stichtag, anzahl: int = FENSTER + 1) -> pd.DatetimeIndex:
    """Die letzten `anzahl` Xetra-Handelstage bis einschließlich Stichtag (falls Handelstag), aufsteigend."""
    d = pd.Timestamp(stichtag).date()
    tage: list[date] = []
    while len(tage) < anzahl:
        if ist_handelstag("xetra", d):
            tage.append(d)
        d -= timedelta(days=1)
    return pd.DatetimeIndex(sorted(tage))


def _auf_tage(reihe: pd.Series, tage: pd.DatetimeIndex) -> pd.Series | None:
    """Reihe auf die Xetra-Tage vortragen; None, wenn sie das Fenster nicht ganz abdeckt."""
    reihe = reihe.dropna()
    if reihe.empty:
        return None
    reihe.index = pd.to_datetime(reihe.index).tz_localize(None) if getattr(reihe.index, "tz", None) else pd.to_datetime(reihe.index)
    reihe = reihe[~reihe.index.duplicated(keep="last")].sort_index()
    if reihe.index[0] > tage[0] or reihe.index[-1] < tage[-1] - pd.Timedelta(days=MAX_ALTER_TAGE):
        return None
    return reihe.reindex(reihe.index.union(tage)).ffill().reindex(tage)


def _tri_roh(kurse: pd.DataFrame | None) -> pd.Series | None:
    """Gesamtrendite-Index an den eigenen Handelstagen des Titels (None ohne Kurse)."""
    if kurse is None or kurse.empty:
        return None
    df = kurse.copy()
    df["dividende"] = df["dividende"].fillna(0.0) if "dividende" in df else 0.0
    df = df[df["close"].notna()]
    if df.empty:
        return None
    tri = total_return_index(df)
    tri.index = pd.to_datetime(tri.index).tz_localize(None) if getattr(tri.index, "tz", None) else pd.to_datetime(tri.index)
    return tri


def gesamtrendite_index(kurse: pd.DataFrame | None, tage: pd.DatetimeIndex) -> pd.Series | None:
    """Gesamtrendite-Index in Handelswährung auf den Xetra-Tagen (None, wenn das Fenster nicht abgedeckt ist)."""
    tri = _tri_roh(kurse)
    return None if tri is None else _auf_tage(tri, tage)


def vorgaenger_index(alt: pd.DataFrame | None, neu: pd.DataFrame | None, tag, tage: pd.DatetimeIndex) -> pd.Series | None:
    """Tickerwechsel: Index des Vorgängers bis vor den ersten Kurs des neuen Tickers ab `tag`, danach der neue Ticker;
    der Vorgänger wird am Wechseltag auf den neuen Index skaliert (Renditen bleiben unverändert)."""
    alt_tri, neu_tri = _tri_roh(alt), _tri_roh(neu)
    if alt_tri is None or neu_tri is None:
        return None
    neu_tri = neu_tri[neu_tri.index >= pd.Timestamp(tag)]
    if neu_tri.empty:
        return None
    wechsel = neu_tri.index[0]
    anker = alt_tri[alt_tri.index <= wechsel]
    if anker.empty:
        return None
    teil_alt = alt_tri[alt_tri.index < wechsel] * (neu_tri.iloc[0] / anker.iloc[-1])
    return _auf_tage(pd.concat([teil_alt, neu_tri]), tage)


@dataclass
class Reihenquelle:
    ticker: str
    quelle: str | None                               # eigen | Vorgänger | Ersatz | None (keine Reihe)
    genutzt: str | None                              # Ticker der genutzten Reihe(n)
    hinweis: str = ""


def _eur(index_hw: pd.Series, waehrung: str, fx_reihen: dict[str, pd.Series | None]) -> pd.Series | None:
    if waehrung == "EUR":
        return index_hw
    fx = fx_reihen.get(waehrung)
    return None if fx is None else index_hw / fx


def reihe_fuer(ticker: str, zuordnung, kurse, tage: pd.DatetimeIndex, fx_reihen: dict, etfs: dict,
               vorgaenger: dict[str, tuple[str, str]]) -> tuple[pd.Series | None, Reihenquelle]:
    """Wertreihe in EUR (Gesamtrendite) für einen Titel nach der Rangfolge aus Abschnitt 6a."""
    waehrung = zuordnung.waehrung_notierung or "EUR"
    eigen_hw = gesamtrendite_index(kurse(ticker), tage)
    if eigen_hw is not None:
        r = _eur(eigen_hw, waehrung, fx_reihen)
        if r is not None:
            return r, Reihenquelle(ticker, EIGEN, ticker)
    if ticker in vorgaenger:                                     # Tickerwechsel: Vorgänger bis zum Wechsel, dann eigen
        alt, tag = vorgaenger[ticker]
        idx = vorgaenger_index(kurse(alt), kurse(ticker), tag, tage)
        r = None if idx is None else _eur(idx, waehrung, fx_reihen)
        if r is not None:
            return r, Reihenquelle(ticker, VORGAENGER, f"{alt} bis {pd.Timestamp(tag):%d.%m.%Y}, dann {ticker}")
    for ersatz in _ersatz_kandidaten(ticker, zuordnung, etfs):
        hw = gesamtrendite_index(kurse(ersatz), tage)
        if hw is not None:                                       # Ersatz-ETFs notieren in EUR
            return hw, Reihenquelle(ticker, ERSATZ, ersatz, f"{ticker}: Reihe zu kurz – Ersatz {ersatz} ohne Beta")
    return None, Reihenquelle(ticker, None, None, f"{ticker}: keine Reihe über das ganze Fenster, kein Ersatz")


def _ersatz_kandidaten(ticker: str, zuordnung, etfs: dict) -> list[str]:
    if zuordnung.art == "Einzelaktie":
        return [ERSATZ_EINZELAKTIE] if ticker != ERSATZ_EINZELAKTIE else []
    if zuordnung.art in ("ETF", "ETC"):
        return sorted(t for t, e in etfs.items() if t != ticker and e.get("region") == zuordnung.land
                      and e.get("anlageklasse") == zuordnung.anlageklasse)
    return []


def vorgaenger_aus_journal(journal) -> dict[str, tuple[str, str]]:
    """Neuer Ticker → (alter Ticker, Tag) aus gebuchten Tickerwechseln (nur lesend)."""
    erg: dict[str, tuple[str, str]] = {}
    zeilen = journal.db.execute(
        "SELECT k.beleg_id, k.tag, p.ticker, p.stueck FROM kapitalmassnahmen k JOIN kapitalmassnahmen_posten p "
        "ON p.beleg_id=k.beleg_id AND p.buch=k.buch WHERE k.art='tickerwechsel' AND k.status='gebucht' AND p.ticker IS NOT NULL").fetchall()
    je_beleg: dict[str, dict] = {}
    for z in zeilen:
        b = je_beleg.setdefault(z["beleg_id"], {"tag": z["tag"], "alt": None, "neu": None})
        b["alt" if z["stueck"] < 0 else "neu"] = z["ticker"]
    for b in je_beleg.values():
        if b["alt"] and b["neu"] and b["alt"] != b["neu"]:
            erg[b["neu"]] = (b["alt"], b["tag"])
    return erg


@dataclass
class VarErgebnis:
    name: str
    status: str
    wert_eur: float
    ersatz_anteil: float = 0.0
    quellen: dict[str, Reihenquelle] = field(default_factory=dict)
    kennzahlen: dict[tuple[int, float], dict] = field(default_factory=dict)      # (h, α) → var, es, k, n, unsicher
    beitraege: dict[tuple[int, float], pd.Series] = field(default_factory=dict)  # (h, α) → ES-Beitrag je Posten
    wurzel10_var: dict[float, float] = field(default_factory=dict)              # α → √10 · VaR(1 Tag), nur Vergleich
    sigma_guv_1: float = float("nan")                                           # Std.-Abw. der 1-Tages-GuV (N − 1)
    szenarien: dict[int, pd.DataFrame] = field(default_factory=dict)            # h → GuV je Posten und Szenario-Tag
    hinweise: list[str] = field(default_factory=list)


def fx_reihen_laden(kurse, tage: pd.DatetimeIndex, waehrungen) -> dict[str, pd.Series | None]:
    erg = {}
    for w in sorted(set(waehrungen) - {"EUR"}):
        df = kurse(FX_TICKER[w]) if w in FX_TICKER else None
        erg[w] = None if df is None or df.empty else _auf_tage(df["close"], tage)
    return erg


def var_es(basis: Basis, kurse, stichtag, *, etfs: dict, vorgaenger: dict | None = None) -> VarErgebnis:
    """VaR und ES für eine Bewertungsbasis (Buch oder Gesamtblock). `kurse(ticker) -> DataFrame | None` mit close,
    dividende (Handelswährung, splitbereinigt)."""
    erg = VarErgebnis(basis.name, OK, basis.wert_eur, hinweise=list(basis.hinweise))
    if not basis.vollstaendig:
        erg.status = NICHT_BERECHENBAR
        erg.hinweise.append(f"{basis.name}: Bewertungsbasis unvollständig (Kurs fehlt) – VaR nicht berechenbar")
        return erg
    tage = xetra_tage(stichtag)
    fremd_kasse = {w: b for w, b in basis.kasse_je_waehrung.items() if w != "EUR" and abs(b) > 1e-9}
    waehrungen = {p.zuordnung.waehrung_notierung or "EUR" for p in basis.posten} | set(fremd_kasse)
    fx_reihen = fx_reihen_laden(kurse, tage, waehrungen)
    werte: dict[str, float] = {}
    reihen: dict[str, pd.Series] = {}
    for p in basis.posten:
        if abs(p.wert_eur) < 1e-12:
            continue
        reihe, q = reihe_fuer(p.ticker, p.zuordnung, kurse, tage, fx_reihen, etfs, vorgaenger or {})
        erg.quellen[p.ticker] = q
        if q.hinweis:
            erg.hinweise.append(q.hinweis)
        if reihe is None:
            erg.status = NICHT_BERECHENBAR
            continue
        werte[p.ticker], reihen[p.ticker] = p.wert_eur, reihe
    for w, betrag in fremd_kasse.items():
        fx = fx_reihen.get(w)
        if fx is None or not basis.fx.get(w):
            erg.status = NICHT_BERECHENBAR
            erg.hinweise.append(f"{basis.name}: keine Kursreihe für {w} – VaR nicht berechenbar")
            continue
        werte[f"Kasse {w}"], reihen[f"Kasse {w}"] = betrag / basis.fx[w], 1.0 / fx   # Wert eines USD in EUR
    if erg.status == NICHT_BERECHENBAR:
        return erg
    ersatz = sum(abs(basis_wert(basis, t)) for t, q in erg.quellen.items() if q.quelle == ERSATZ)
    erg.ersatz_anteil = ersatz / basis.wert_eur if basis.wert_eur > 0 else 0.0
    if erg.ersatz_anteil > ERSATZ_SCHWELLE:
        erg.status = EINGESCHRAENKT
        erg.hinweise.append(f"{basis.name}: {erg.ersatz_anteil:.1%} des Werts mit Ersatzreihen – VaR eingeschränkt")
    if not werte:                                                # nur EUR-Kasse: kein Risiko im Modell
        for h in HALTEDAUERN:
            for a in NIVEAUS:
                erg.kennzahlen[(h, a)] = {"var": 0.0, "es": 0.0, "k": None, "n": 0, "unsicher": a >= UNSICHER}
        return erg
    for h in HALTEDAUERN:
        guv = pd.DataFrame({n: werte[n] * (r.iloc[h:].to_numpy() / r.iloc[:-h].to_numpy() - 1.0) for n, r in reihen.items()},
                           index=tage[h:])
        erg.szenarien[h] = guv
        summe = guv.sum(axis=1).to_numpy()
        for a in NIVEAUS:
            v = var_es_kte_schlechteste(summe, a)
            erg.kennzahlen[(h, a)] = {"var": v["var"], "es": v["es"], "k": v["k"], "n": v["n"], "unsicher": a >= UNSICHER}
            erg.beitraege[(h, a)] = -guv.iloc[v["schlechteste"]].mean()
        if h == 1:
            erg.sigma_guv_1 = float(np.std(summe, ddof=1))
    for a in NIVEAUS:
        erg.wurzel10_var[a] = math.sqrt(10) * erg.kennzahlen[(1, a)]["var"]
    return erg


def basis_wert(basis: Basis, ticker: str) -> float:
    return sum(p.wert_eur for p in basis.posten if p.ticker == ticker)


def cache_kurse():
    """Kursquelle aus dem Kurs-Cache des Betriebs, nur lesend (über `lesepfad`, ohne Übernahme und ohne Netz)."""
    from tradingbot.betrieb.kurscache import BEREICH, _wurzel
    from tradingbot.daten.cache import ParquetCache

    cache = ParquetCache(_wurzel())
    gelesen: dict[str, pd.DataFrame | None] = {}

    def kurse(ticker: str) -> pd.DataFrame | None:
        if ticker not in gelesen:
            gelesen[ticker] = cache.lesen(BEREICH, ticker)[0]
        return gelesen[ticker]
    return kurse
