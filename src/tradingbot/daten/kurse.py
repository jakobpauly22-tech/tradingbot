"""Tageskurse über yfinance mit lokalem Cache und Umrechnung in Euro.

Bereinigung (wichtig für Backtests):
- `close` ist der Schlusskurs, wie Yahoo ihn liefert: um Splits bereinigt, NICHT um Dividenden.
  Komplett unbereinigte Kurse bietet Yahoo nicht an.
- Den dividendenbereinigten Kurs (Yahoo „Adj Close“) speichern wir bewusst nicht: Yahoo rechnet ihn
  nach jeder Dividende rückwirkend um, ein Backtest wäre dann nicht reproduzierbar. Die Gesamtrendite
  rechnet `tradingbot.kennzahlen.rendite.total_return_index` aus `close` und `dividende` selbst.
- Ändert Yahoo die Bereinigung rückwirkend (neuer Split, Datenkorrektur), erkennt der Abgleich der
  überlappenden Tage das und lädt die ganze Historie neu.

Es werden nur abgeschlossene Handelstage gespeichert (Datum vor `heute`), damit nie eine halbe
Tageskerze in Signale oder Backtests gerät.

Bekannte Lücke: yfinance kennt keine Kurse von Aktien, die nicht mehr gelistet sind
(Survivorship Bias). Für den ETF-Core unkritisch; für das Einzelaktien-Schattenportfolio später lösen.
"""
from __future__ import annotations

import logging
import warnings
from datetime import date, datetime, timedelta, timezone
from typing import Callable

import pandas as pd

from tradingbot.daten.abruf import DatenFehler, Drossel, mit_wiederholung
from tradingbot.daten.cache import ParquetCache, standard_cache
from tradingbot.daten.pruefung import pruefe_kurse

log = logging.getLogger(__name__)

SPALTEN = ["open", "high", "low", "close", "volume", "dividende", "split"]
PREIS_SPALTEN = ["open", "high", "low", "close", "dividende"]
_YAHOO_SPALTEN = {
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Volume": "volume",
    "Dividends": "dividende",
    "Stock Splits": "split",
}
UEBERLAPPUNG_TAGE = 7          # so viele Kalendertage werden beim Nachladen erneut geholt und abgeglichen
TOLERANZ_ABGLEICH = 0.005      # 0,5 % Abweichung im Schlusskurs gilt als geänderte Bereinigung
BEREICH = "kurse"

# Abrufer: (ticker, start, ende inklusive) -> (Rohdaten im Yahoo-Format, Währung)
Abrufer = Callable[[str, date, date], tuple[pd.DataFrame, str | None]]

_yahoo_drossel = Drossel(min_abstand_s=0.5)


def yfinance_abruf(ticker: str, start: date, ende: date) -> tuple[pd.DataFrame, str | None]:
    """Holt Tageskerzen von Yahoo. `ende` ist inklusive (yfinance selbst behandelt `end` exklusiv)."""
    import yfinance as yf

    def abruf():
        _yahoo_drossel.warten()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            objekt = yf.Ticker(ticker)
            roh = objekt.history(
                start=start.isoformat(),
                end=(ende + timedelta(days=1)).isoformat(),
                interval="1d",
                auto_adjust=False,
                actions=True,
            )
            waehrung = (objekt.history_metadata or {}).get("currency")
        return roh, waehrung

    return mit_wiederholung(abruf, beschreibung=f"yfinance {ticker}", wiederholen_bei=(Exception,))


def normalisieren(roh: pd.DataFrame | None) -> pd.DataFrame:
    """Bringt Yahoo-Rohdaten in das Bot-Format: feste Spalten, Index = Handelstag ohne Zeitzone."""
    if roh is None or roh.empty:
        return pd.DataFrame(columns=SPALTEN, index=pd.DatetimeIndex([], name="datum"), dtype=float)
    daten = roh.rename(columns=_YAHOO_SPALTEN)
    for spalte in SPALTEN:
        if spalte not in daten:
            daten[spalte] = 0.0
    daten = daten[SPALTEN].astype(float)
    index = pd.DatetimeIndex(roh.index)
    if index.tz is not None:
        index = index.tz_localize(None)  # Ortszeit der Börse behalten, dann Uhrzeit abschneiden
    daten.index = pd.DatetimeIndex(index.normalize(), name="datum")
    daten = daten[~daten.index.duplicated(keep="last")].sort_index()
    return daten


def _zusammenfuehren(alt: pd.DataFrame, neu: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
    """Fügt neue Kurse an. Gibt False zurück, wenn die überlappenden Schlusskurse nicht passen."""
    gemeinsam = alt.index.intersection(neu.index)
    if len(gemeinsam):
        abweichung = (neu.loc[gemeinsam, "close"] / alt.loc[gemeinsam, "close"] - 1).abs().max()
        if abweichung > TOLERANZ_ABGLEICH:
            return alt, False
    kombiniert = pd.concat([alt, neu])
    kombiniert = kombiniert[~kombiniert.index.duplicated(keep="last")].sort_index()
    return kombiniert, True


def _als_datum(wert) -> date:
    return pd.Timestamp(wert).date()


def lade_kurse(
    ticker: str,
    start,
    ende=None,
    *,
    cache: ParquetCache | None = None,
    abrufer: Abrufer | None = None,
    heute: date | None = None,
) -> pd.DataFrame:
    """Tageskerzen eines Tickers von `start` bis `ende` (inklusive), in Handelswährung.

    Spalten: open, high, low, close (splitbereinigt), volume, dividende (je Aktie am Ex-Tag),
    split (Faktor am Split-Tag, sonst 0). Index `datum`. Währung steht in `df.attrs["waehrung"]`.
    Fehlende Zeiträume werden nachgeladen, bereits geladene kommen aus dem Cache.
    """
    heute = heute or date.today()
    cache = cache or standard_cache()
    abrufer = abrufer or yfinance_abruf
    start = _als_datum(start)
    ende = min(_als_datum(ende) if ende is not None else heute, heute - timedelta(days=1))
    if ende < start:
        return _mit_attrs(normalisieren(None), ticker, None)

    daten, meta = cache.lesen(BEREICH, ticker)
    geaendert = False
    if daten is None:
        daten, waehrung = _vollabruf(ticker, start, ende, abrufer)
        von, bis, geaendert = start, ende, True
    else:
        von, bis = date.fromisoformat(meta["von"]), date.fromisoformat(meta["bis"])
        waehrung = meta.get("waehrung")
        teilabrufe = []
        if start < von:
            teilabrufe.append((start, von + timedelta(days=UEBERLAPPUNG_TAGE)))
        if ende > bis:
            teilabrufe.append((bis - timedelta(days=UEBERLAPPUNG_TAGE), ende))
        for teil_start, teil_ende in teilabrufe:
            roh, waehrung_neu = abrufer(ticker, teil_start, teil_ende)
            waehrung = waehrung or waehrung_neu
            daten, passt = _zusammenfuehren(daten, normalisieren(roh))
            if not passt:
                log.warning("%s: Bereinigung hat sich geändert (Split oder Korrektur), lade komplette Historie neu", ticker)
                von, bis = min(start, von), max(ende, bis)
                daten, waehrung = _vollabruf(ticker, von, bis, abrufer)
                geaendert = True
                break
            geaendert = True
        von, bis = min(start, von), max(ende, bis)

    daten = daten[daten.index < pd.Timestamp(heute)]
    if geaendert:
        for befund in pruefe_kurse(daten, heute=heute):
            log.warning("%s: %s", ticker, befund)
        cache.schreiben(
            BEREICH,
            ticker,
            daten,
            {
                "quelle": "yfinance",
                "von": von.isoformat(),
                "bis": bis.isoformat(),
                "waehrung": waehrung,
                "abgerufen_um": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            },
        )
    auswahl = daten.loc[pd.Timestamp(start) : pd.Timestamp(ende)].copy()
    return _mit_attrs(auswahl, ticker, waehrung)


def _vollabruf(ticker: str, start: date, ende: date, abrufer: Abrufer) -> tuple[pd.DataFrame, str | None]:
    roh, waehrung = abrufer(ticker, start, ende)
    daten = normalisieren(roh)
    if daten.empty and (ende - start).days > 10:
        raise DatenFehler(f"Keine Kurse für {ticker} zwischen {start} und {ende} (Ticker falsch oder nicht gelistet?)")
    return daten, waehrung


def _mit_attrs(daten: pd.DataFrame, ticker: str, waehrung: str | None) -> pd.DataFrame:
    daten.attrs["ticker"] = ticker
    daten.attrs["waehrung"] = waehrung
    return daten


def in_euro(kurse: pd.DataFrame, waehrung: str | None, eur_kurs: pd.Series | None = None) -> pd.DataFrame:
    """Rechnet Preise und Dividenden in Euro um.

    Formel: Preis_EUR,t = Preis_FW,t / S_t, mit S_t = Einheiten Fremdwährung je 1 EUR (z.B. EURUSD=X).
    Annahmen: Wechselkurs desselben Tages (Yahoo-Tagesschluss, London); fehlt er (unterschiedliche
    Feiertage), gilt der letzte bekannte Kurs, höchstens 5 Tage alt. Kein Blick in die Zukunft.
    Währungskosten beim Umtausch kommen im Backtest dazu, nicht hier.
    Pence-Notierungen (GBp/GBX) werden durch 100 geteilt.
    """
    if waehrung is None:
        raise DatenFehler(f"Währung für {kurse.attrs.get('ticker', '?')} unbekannt")
    faktor = 1.0
    if waehrung in ("GBp", "GBX"):
        waehrung, faktor = "GBP", 0.01
    ergebnis = kurse.copy()
    if waehrung == "EUR":
        ergebnis[PREIS_SPALTEN] = ergebnis[PREIS_SPALTEN] * faktor
    else:
        if eur_kurs is None or eur_kurs.empty:
            raise DatenFehler(f"Wechselkurs EUR/{waehrung} fehlt")
        gesamt_index = kurse.index.union(eur_kurs.index)
        fx = eur_kurs.reindex(gesamt_index).ffill(limit=5).reindex(kurse.index)
        if fx.isna().any():
            erster = fx[fx.isna()].index[0].date()
            raise DatenFehler(f"Wechselkurs EUR/{waehrung} fehlt für {int(fx.isna().sum())} Tage, erstmals {erster}")
        for spalte in PREIS_SPALTEN:
            ergebnis[spalte] = ergebnis[spalte] * faktor / fx
    ergebnis.attrs = {**kurse.attrs, "waehrung": "EUR", "originalwaehrung": waehrung}
    return ergebnis


def lade_kurse_eur(ticker: str, start, ende=None, *, konfig: dict | None = None, **kwargs) -> pd.DataFrame:
    """Wie `lade_kurse`, aber in Euro umgerechnet (Wechselkurs-Ticker aus config/daten.yaml)."""
    from tradingbot.konfiguration import lade_konfiguration

    kurse = lade_kurse(ticker, start, ende, **kwargs)
    waehrung = kurse.attrs.get("waehrung")
    if kurse.empty:
        return kurse
    basis = "GBP" if waehrung in ("GBp", "GBX") else waehrung
    if basis in (None, "EUR"):
        return in_euro(kurse, waehrung)  # bei unbekannter Währung: DatenFehler
    konfig = konfig or lade_konfiguration("daten")
    fx_ticker = konfig["kurse"]["wechselkurse"].get(basis, f"EUR{basis}=X")
    fx_start = pd.Timestamp(start) - pd.Timedelta(days=10)  # Puffer für das Auffüllen an Feiertagen
    fx = lade_kurse(fx_ticker, fx_start, ende, **kwargs)["close"]
    return in_euro(kurse, waehrung, fx)
