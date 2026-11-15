"""c2 (2): Marktwert aus Rohkursen (Weg A, Jakob 15.11.2026) – Abnahme nur gegen splitbereinigte Reihen, Formel,
Sperre c3, Betrieb unberührt. Ohne Netz."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tradingbot.daten.rohkurse_marktwert import abnahme, faktor_nach, fehlende_fuer_c3, pruefe_nur_splitbereinigt
from tradingbot.engines.fundamental.multiples import marktwert_rohkurs

TAGE = pd.bdate_range("2015-01-01", "2024-12-31")


def _roh(split_tag="2020-06-01", faktor=4.0):
    """Unbereinigte Reihe mit einem echten Split (4:1) und Kursbewegung."""
    preis = pd.Series(100 * np.exp(np.linspace(0, 0.8, len(TAGE))), index=TAGE)
    preis[preis.index >= split_tag] /= faktor
    split = pd.Series(0.0, index=TAGE)
    split[split_tag] = faktor
    return pd.DataFrame({"close": preis, "split": split})


def _bereinigt(roh, verdeckt=1.0, dividende=0.5):
    """Nur splitbereinigt wie Yahoo `close` (auto_adjust=False): Roh / Π Splits danach / verdeckter Faktor nach 2024."""
    b = pd.DataFrame({"close": roh["close"] / faktor_nach(roh["split"]) / verdeckt, "split": roh["split"],
                      "dividende": 0.0}, index=roh.index)
    b.loc[b.index[::63], "dividende"] = dividende                       # vierteljährliche Ausschüttung
    return b


def test_abnahme_bestanden_mit_split_und_dividenden():
    roh = _roh()
    e = abnahme(roh, _bereinigt(roh))
    assert e["bestanden"] and e["H"] == pytest.approx(1.0) and e["anteil_ok"] == 1.0


def test_abnahme_erkennt_verdeckten_faktor_nach_der_tresorgrenze():
    roh = _roh()
    e = abnahme(roh, _bereinigt(roh, verdeckt=15.0))                     # z. B. ORLY 15:1 im Jahr 2025
    assert e["bestanden"] and e["H"] == pytest.approx(15.0)


def test_abnahme_mit_abspaltung_als_split_bei_yahoo():
    """Yahoo führt eine Abspaltung als „Split“ und bereinigt close darum; der Rohkurs kennt keinen Split."""
    roh = _roh()
    b = _bereinigt(roh)
    b.loc["2018-03-01", "split"] = 1.25
    b.loc[b.index < "2018-03-01", "close"] /= 1.25
    assert abnahme(roh, b)["bestanden"]


def test_abnahme_gegen_dividendenbereinigte_reihe_faellt_durch():
    """Adj Close driftet mit jeder Ausschüttung gegen den Rohkurs: so darf nie geprüft werden."""
    roh = _roh()
    b = _bereinigt(roh, dividende=2.0)
    with pytest.raises(ValueError, match="nur splitbereinigt"):
        pruefe_nur_splitbereinigt(b.rename(columns={"close": "adj_close"}).assign(close=b["close"]))
    with pytest.raises(ValueError, match="nur splitbereinigt"):
        pruefe_nur_splitbereinigt(b.drop(columns="dividende"))
    # dividendenbereinigt als „close“ untergeschoben: Faktor Π (1 − D/P) über alle späteren Ausschüttungen
    r = b["dividende"] / b["close"]
    adj = b["close"] * (1 - r)[::-1].cumprod()[::-1].shift(-1).fillna(1.0)
    e = abnahme(roh, b.assign(close=adj))
    assert not e["bestanden"] and e["max_abw"] > 0.05


def test_abnahme_falsche_firma_und_zu_kurz():
    roh = _roh()
    fremd = _bereinigt(roh).assign(close=lambda d: d["close"] * (1 + 0.3 * np.sin(np.arange(len(d)) / 50)))
    assert not abnahme(roh, fremd)["bestanden"]
    kurz = _roh().loc["2024-06-01":]
    e = abnahme(kurz, _bereinigt(_roh()).loc["2024-06-01":])
    assert not e["bestanden"] and "gemeinsame Tage" in e["grund"]


def test_marktwert_rohkurs_formel():
    roh = _roh()
    kurse = _bereinigt(roh, verdeckt=15.0)
    aktien = pd.DataFrame({"wert": [1_000_000_000.0], "filed": [pd.Timestamp("2020-02-15")]}, index=[pd.Timestamp("2020-01-31")])
    vor = marktwert_rohkurs("2020-03-31", roh, kurse, aktien, None, plausibilitaet=False)
    assert vor["marktwert"] == pytest.approx(roh["close"].loc[:"2020-03-31"].iloc[-1] * 1e9) and vor["splitfaktor"] == 1.0
    nach = marktwert_rohkurs("2020-12-31", roh, kurse, aktien, None, plausibilitaet=False, max_alter_monate=15)
    assert nach["splitfaktor"] == 4.0                                   # Split zwischen Messtag und Stichtag
    assert nach["marktwert"] == pytest.approx(roh["close"].loc[:"2020-12-31"].iloc[-1] * 1e9 * 4.0)
    # der verdeckte Faktor der bereinigten Reihe wirkt nicht
    assert nach["rohkurs"] == pytest.approx(kurse["close"].loc[:"2020-12-31"].iloc[-1] * 15.0)


def test_marktwert_rohkurs_ohne_aktienzahl_oder_rohkurs():
    roh = _roh()
    leer = marktwert_rohkurs("2010-01-04", roh, _bereinigt(roh), None, None)
    assert leer["marktwert"] is None and "Rohkurs" in leer["grund"]
    assert marktwert_rohkurs("2020-03-31", roh, _bereinigt(roh), None, None)["grund"].startswith("keine Aktienzahl")


def test_sperre_c3_listet_fehlende_reihen():
    status = pd.DataFrame({"quelle": ["yfinance", "yfinance", "tiingo", "yfinance"], "symbol": ["ORLY", "META", "SIVBQ", "WEG"],
                           "gueltig": [True, True, True, True]})
    abn = pd.DataFrame({"quelle": ["yfinance", "tiingo"], "symbol": ["ORLY", "SIVBQ"], "bestanden": [True, False]})
    assert fehlende_fuer_c3(status, abn, {"weg"}) == ["META (yfinance)"]
    assert fehlende_fuer_c3(status, pd.DataFrame(columns=["quelle", "symbol", "bestanden"]), set()) == [
        "SIVBQ (tiingo)", "META (yfinance)", "ORLY (yfinance)", "WEG (yfinance)"]


def test_betrieb_liest_keine_rohkurse():
    """Tageslauf und Betriebsbewertung hängen nicht von den Rohkursen ab (Jakob 15.11.2026)."""
    wurzel = Path(__file__).resolve().parents[2] / "src" / "tradingbot"
    for datei in list((wurzel / "betrieb").rglob("*.py")) + [wurzel / "engines" / "fundamental" / "aktuell.py"]:
        text = datei.read_text(encoding="utf-8")
        assert "rohkurse_marktwert" not in text and "marktwert_rohkurs" not in text and "rohkurse=True" not in text, datei


def test_marktwert_rohkurs_abspaltung_als_tiingo_split_ueber_k():
    """Tiingo führt manche Abspaltungen als splitFactor (MRK/Organon 2021: 1,048); K aus der Liste nimmt sie heraus,
    Faktoren außerhalb der Liste bleiben und werden als ungeklärt gemeldet."""
    roh = _roh()
    roh.loc["2020-08-03", "split"] = 1.048
    aktien = pd.DataFrame({"wert": [1e9], "filed": [pd.Timestamp("2020-02-15")]}, index=[pd.Timestamp("2020-01-31")])
    liste = pd.DataFrame({"art": ["abspaltung", "split"], "split_faktor": [1.0, 4.0], "geprueft": [True, True]},
                         index=pd.DatetimeIndex(["2020-08-03", "2020-06-01"]))
    mit = marktwert_rohkurs("2020-12-31", roh, _bereinigt(roh), aktien, None, ereignisse=liste, plausibilitaet=False)
    assert mit["splitfaktor"] == pytest.approx(4.0) and mit["ungeklaert"] == []
    ohne = marktwert_rohkurs("2020-12-31", roh, _bereinigt(roh), aktien, None, ereignisse=None, plausibilitaet=False)
    assert ohne["splitfaktor"] == pytest.approx(4.0 * 1.048) and len(ohne["ungeklaert"]) == 2
