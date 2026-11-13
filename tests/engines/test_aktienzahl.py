"""Datenkorrektur Piotroski EQ_OFFER (Jakob 13.11.2026): Aktienzahl t und t−1 auf gleicher Split-Basis.

Nachgestellt: Split 3:1 zwischen den Einreichungen (wie ein Split im Februar vor dem 10-K im März), Reverse-Split,
Vergleichswert fehlt (Rückfall B), Split erst nach dem Stichtag, Point-in-Time und Tresor."""
import pandas as pd
import pytest

from tradingbot.engines.fundamental import aktienzahl as az
from tradingbot.engines.fundamental.scores import piotroski

DEF = {"einheit": "shares", "konzepte": ["us-gaap:WeightedAverageNumberOfSharesOutstandingBasic",
                                         "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding"]}
BASIC = "us-gaap:WeightedAverageNumberOfSharesOutstandingBasic"
DILUTED = "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding"


def _roh(werte):
    """werte: (Begriff, start, ende, wert, filed, accn, form)."""
    einheiten = {}
    for name, start, ende, wert, filed, accn, *form in werte:
        _, _, konzept = name.partition(":")
        einheiten.setdefault(konzept, []).append({"start": start, "end": ende, "val": wert, "filed": filed, "accn": accn,
                                                  "form": form[0] if form else "10-K"})
    return {"facts": {"us-gaap": {k: {"units": {"shares": v}} for k, v in einheiten.items()}}}


# 10-K GJ 2022 (Ende 31.12.2022, eingereicht 20.02.2023): 2022 = 100 Mio., 2021 = 101 Mio.
# Split 3:1 am 15.01.2024; 10-K GJ 2023 (eingereicht 20.02.2024, nach dem Split, rückwirkend): 2023 = 297, 2022 = 300
SPLIT_FAKTEN = _roh([
    (BASIC, "2021-01-01", "2021-12-31", 101e6, "2023-02-20", "a22"),
    (BASIC, "2022-01-01", "2022-12-31", 100e6, "2023-02-20", "a22"),
    (BASIC, "2022-01-01", "2022-12-31", 300e6, "2024-02-20", "a23"),
    (BASIC, "2023-01-01", "2023-12-31", 297e6, "2024-02-20", "a23"),
    (BASIC, "2023-01-01", "2023-03-31", 75e6, "2023-05-01", "q1"),          # Quartal: keine Jahresdauer, fällt raus
])
SPLITS = pd.Series([0.0, 3.0, 0.0], index=pd.to_datetime(["2024-01-12", "2024-01-15", "2024-01-16"]))


def _fakten(roh=SPLIT_FAKTEN):
    return az.aktienfakten(roh, DEF)


def _tabelle(t, vj):
    """Abschlüsse wie kennzahlen.abschluesse_am (Zeile 0 = t) mit den Erstmeldungen der Aktienzahl."""
    return pd.DataFrame({"gewichtete_aktien": [t, vj]}, index=pd.to_datetime(["2023-12-31", "2022-12-31"]))


def test_aktienfakten_nur_jahreswerte_alle_einreichungen():
    f = _fakten()
    assert len(f) == 4 and set(f["accn"]) == {"a22", "a23"} and list(f.columns) == az.SPALTEN


def test_split_zwischen_den_einreichungen_weg_a_und_b():
    eq = az.eq_offer_vergleich(_fakten(), "2023-12-31", "2022-12-31", "2024-04-01", SPLITS)
    assert eq["quelle"] == "einreichung" and eq["wert_t"] == 297e6 and eq["wert_vj"] == 300e6     # A: aus demselben 10-K
    assert eq["wert_vj_erst"] == 100e6 and eq["split_faktor"] == 3.0 and eq["wert_vj_split"] == 300e6   # B: Gegenprobe
    alt, neu = az.signal_alt_neu(_tabelle(297e6, 100e6), eq)
    assert (alt, neu) == (0, 1)                                       # bisher „neue Aktien“, korrekt „keine“
    t = _tabelle(297e6, 100e6)
    assert piotroski(t)["signale"]["eq_offer"] == 0
    p = piotroski(t, eq_offer=eq)
    assert p["signale"]["eq_offer"] == 1 and p["zwischenwerte"]["aktien_quelle"] == "einreichung"


def test_rueckfall_b_ohne_vergleichswert():
    roh = _roh([(BASIC, "2022-01-01", "2022-12-31", 100e6, "2023-02-20", "a22"),
                (BASIC, "2023-01-01", "2023-12-31", 297e6, "2024-02-20", "a23")])
    eq = az.eq_offer_vergleich(az.aktienfakten(roh, DEF), "2023-12-31", "2022-12-31", "2024-04-01", SPLITS)
    assert eq["quelle"] == "split" and eq["wert_vj"] == 300e6 and eq["wert_vj_einreichung"] is None
    # ohne Split-Ereignis bleibt B unbereinigt (wie bisher), nichts wird geraten
    eq = az.eq_offer_vergleich(az.aktienfakten(roh, DEF), "2023-12-31", "2022-12-31", "2024-04-01", None)
    assert eq["quelle"] == "split" and eq["wert_vj"] == 100e6 and eq["split_faktor"] == 1.0


def test_reverse_split():
    roh = _roh([(BASIC, "2022-01-01", "2022-12-31", 100e6, "2023-02-20", "a22"),
                (BASIC, "2022-01-01", "2022-12-31", 10e6, "2024-02-20", "a23"),
                (BASIC, "2023-01-01", "2023-12-31", 10.5e6, "2024-02-20", "a23")])
    rs = pd.Series([0.1], index=pd.to_datetime(["2023-06-01"]))
    eq = az.eq_offer_vergleich(az.aktienfakten(roh, DEF), "2023-12-31", "2022-12-31", "2024-04-01", rs)
    assert az.signal_alt_neu(_tabelle(10.5e6, 100e6), eq) == (1, 0)    # bisher „Rückkauf“, tatsächlich +5 % Aktien
    assert eq["wert_vj_split"] == pytest.approx(10e6)


def test_point_in_time_und_split_nach_der_einreichung():
    f = _fakten()
    # vor der Einreichung des 10-K 2023 ist t = 2023 unbekannt
    assert az.eq_offer_vergleich(f, "2023-12-31", "2022-12-31", "2024-02-20", SPLITS)["quelle"] is None
    assert az.eq_offer_vergleich(f, "2023-12-31", "2022-12-31", "2024-02-21", SPLITS)["quelle"] == "einreichung"
    # Split nach der Einreichung von t und nach dem Stichtag: kein Faktor
    spaet = pd.Series([2.0], index=pd.to_datetime(["2024-06-01"]))
    assert az.eq_offer_vergleich(f, "2023-12-31", "2022-12-31", "2024-04-01", spaet)["split_faktor"] == 1.0
    assert az.eq_offer_vergleich(f, "2023-12-31", "2022-12-31", "2024-07-01", spaet)["split_faktor"] == 1.0


def test_gleicher_begriff_wie_t():
    """t nur als Diluted gemeldet: der Vergleichswert muss ebenfalls Diluted sein, nicht Basic aus derselben Einreichung."""
    roh = _roh([(BASIC, "2022-01-01", "2022-12-31", 300e6, "2024-02-20", "a23"),
                (DILUTED, "2022-01-01", "2022-12-31", 303e6, "2024-02-20", "a23"),
                (DILUTED, "2023-01-01", "2023-12-31", 299e6, "2024-02-20", "a23")])
    eq = az.eq_offer_vergleich(az.aktienfakten(roh, DEF), "2023-12-31", "2022-12-31", "2024-04-01")
    assert eq["konzept"] == DILUTED and eq["wert_vj"] == 303e6


def test_erstmeldung_original_vor_berichtigung():
    roh = _roh([(BASIC, "2022-01-01", "2022-12-31", 100e6, "2023-02-20", "b", "10-K/A"),
                (BASIC, "2022-01-01", "2022-12-31", 99e6, "2023-02-20", "c", "10-K")])
    eq = az.eq_offer_vergleich(az.aktienfakten(roh, DEF), "2023-12-31", "2022-12-31", "2024-04-01")
    assert eq["wert_vj_erst"] == 99e6 and eq["quelle"] is None


def test_tresor_begrenzt_die_fakten(monkeypatch):
    from tradingbot.backtest import tresor
    monkeypatch.setattr(tresor, "datengrenze", lambda konfig=None: pd.Timestamp("2023-12-31"))
    assert az.eq_offer_vergleich(_fakten(), "2023-12-31", "2022-12-31", "2024-04-01", SPLITS)["quelle"] is None


def test_ohne_korrektur_unveraendert():
    t = _tabelle(297e6, 100e6)
    assert piotroski(t, eq_offer=None)["signale"] == piotroski(t)["signale"]
    assert piotroski(t, eq_offer={"wert_t": None, "wert_vj": None})["signale"]["eq_offer"] == 0       # Rückfall Erstmeldung
    assert az.signal_alt_neu(t, None) == (0, 0)


def test_wirksam_ab_erstem_rebalancing_stichtag_januar_2027():
    from tradingbot.betrieb.buecher import quartalsstichtag
    from tradingbot.konfiguration import lade_konfiguration
    ab = pd.Timestamp(str(lade_konfiguration("fundamental")["piotroski_eq_offer"]["splitbereinigt_ab"]))
    assert ab == pd.Timestamp("2027-01-04") and quartalsstichtag(ab)
    assert not any(quartalsstichtag(d) for d in pd.date_range("2027-01-01", ab - pd.Timedelta(days=1)))
    assert not az.korrektur_aktiv("2027-01-01") and not az.korrektur_aktiv("2026-11-13")
    assert az.korrektur_aktiv("2027-01-04") and az.korrektur_aktiv(pd.Timestamp("2027-01-04 22:30"))


def test_lade_aktienfakten_offline_und_neu_bei_anderem_stand(tmp_path):
    from datetime import datetime

    from tradingbot.daten.cache import ParquetCache

    class Client:
        abrufe = 0

        def companyfacts_aus_cache(self, cik):
            Client.abrufe += 1
            return (SPLIT_FAKTEN, datetime(2026, 11, 2, 10, 0)) if cik == 1 else (None, None)

    cache = ParquetCache(tmp_path)
    cache.schreiben("sec_erstmeldungen", "0000000001", pd.DataFrame({"x": [1]}), {"roh_abgerufen_um": "2026-11-02T10:00:00"})
    f = az.lade_aktienfakten([1, 2], definition=DEF, cache=cache, client=Client())
    assert len(f) == 4 and Client.abrufe == 2                         # CIK 2 ohne companyfacts: fehlt, kein Fehler
    az.lade_aktienfakten([1], definition=DEF, cache=cache, client=Client())
    assert Client.abrufe == 2                                         # gleicher Stand: aus dem Cache
    cache.schreiben("sec_erstmeldungen", "0000000001", pd.DataFrame({"x": [1]}), {"roh_abgerufen_um": "2026-11-20T10:00:00"})
    az.lade_aktienfakten([1], definition=DEF, cache=cache, client=Client())
    assert Client.abrufe == 3                                         # neuer Stand der Erstmeldungen: neu gebaut


def test_erstmals_angewendet_einmal_im_journal(tmp_path):
    from datetime import datetime

    from tradingbot.betrieb.journal import Journal
    from tradingbot.betrieb.tageslauf import datenkorrektur_vermerken

    j = Journal(tmp_path / "journal.sqlite")
    vorher = pd.DataFrame({"symbol": ["WMT", "AAPL"], "eq_offer_alt": [0, 1], "eq_offer_neu": [1, 1], "eq_offer_korrektur_aktiv": [False, False]})
    assert datenkorrektur_vermerken(j, vorher, "2026-12-01") == []
    ab = vorher.assign(eq_offer_korrektur_aktiv=True)
    m = datenkorrektur_vermerken(j, ab, "2027-01-04", datetime(2027, 1, 4, 22, 30))
    assert len(m) == 1 and "2027-01-04" in m[0] and "1 Firmen: WMT" in m[0]
    assert datenkorrektur_vermerken(j, ab, "2027-01-05") == []                  # nur einmal
    assert j.db.execute("SELECT COUNT(*) FROM ereignisse WHERE art='datenkorrektur_angewendet'").fetchone()[0] == 1
    assert datenkorrektur_vermerken(j, pd.DataFrame({"symbol": ["X"]}), "2027-01-04") == []   # alte Attrappen ohne Spalte
