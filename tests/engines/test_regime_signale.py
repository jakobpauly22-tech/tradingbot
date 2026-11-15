"""Regime-Engine: Signale, Variante V1 und Haltepflicht (docs/REGIME.md, Abschnitte 1–3 und 7a)."""
import numpy as np
import pandas as pd
import pytest

from tradingbot.engines.regime import signale as rs


def _monate(werte, ende="2020-12"):
    index = pd.period_range(end=ende, periods=len(werte), freq="M").to_timestamp()
    return pd.Series([float(w) for w in werte], index=index)


def _tageswerte(monatswerte: dict) -> pd.Series:
    """Tagesreihe mit konstantem Wert je Monat, z. B. {"2020-01": 1.5}."""
    teile = [pd.Series(w, index=pd.bdate_range(pd.Period(m).start_time, pd.Period(m).end_time)) for m, w in monatswerte.items()]
    return pd.concat(teile)


# --- Monatsenden ---

def test_monatsenden_letzter_handelstag_und_offener_monat():
    tage = pd.bdate_range("2024-10-01", "2024-12-18")
    assert list(rs.monatsenden(tage)) == [pd.Timestamp("2024-10-31"), pd.Timestamp("2024-11-29"), pd.Timestamp("2024-12-18")]
    assert list(rs.monatsenden(tage, letzter_monat_abgeschlossen=False)) == [pd.Timestamp("2024-10-31"), pd.Timestamp("2024-11-29")]


# --- Trend ---

def test_trend_zehn_monate_einschliesslich_aktuellem():
    assert rs.trend_aus(_monate([100] * 9 + [99])) is True          # 99 < 99,9
    assert rs.trend_aus(_monate([100] * 9 + [101])) is False
    assert rs.trend_aus(_monate([100] * 10)) is False               # gleich dem Durchschnitt: nicht „aus“
    assert rs.trend_aus(_monate([100] * 9)) is None                 # zu wenig Historie
    # nur die letzten 10 Monate zählen: ein alter hoher Kurs ändert nichts
    assert rs.trend_aus(_monate([1000] + [100] * 9 + [101])) is False


# --- Zinskurve ---

def test_zinskurve_durchschnitt_des_laufenden_monats():
    w = _tageswerte({"2019-05": 0.10, "2019-06": -0.10})
    assert rs.zinskurve_aus(w, "2019-06-28") is True
    assert rs.zinskurve_aus(w, "2019-05-31") is False
    assert rs.zinskurve_aus(w, "2019-07-31") is None                # keine Werte im laufenden Monat
    gemischt = pd.Series([0.3, -0.1, -0.1], index=pd.to_datetime(["2019-06-03", "2019-06-04", "2019-06-05"]))
    assert rs.zinskurve_aus(gemischt, "2019-06-28") is False        # Durchschnitt +0,033, nicht der letzte Wert


# --- Kreditaufschlag ---

def test_kreditaufschlag_gegen_zehn_monatsdurchschnitte():
    monate = [str(p) for p in pd.period_range("2019-03", "2019-12", freq="M")]
    assert rs.kredit_aus(_tageswerte(dict(zip(monate, [2.0] * 9 + [2.5]))), "2019-12-31") is True
    assert rs.kredit_aus(_tageswerte(dict(zip(monate, [2.0] * 9 + [1.9]))), "2019-12-31") is False
    assert rs.kredit_aus(_tageswerte(dict(zip(monate, [2.0] * 10))), "2019-12-31") is False
    assert rs.kredit_aus(_tageswerte(dict(zip(monate[1:], [2.0] * 8 + [2.5]))), "2019-12-31") is None    # nur 9 Monate
    luecke = _tageswerte(dict(zip(monate, [2.0] * 9 + [2.5])))
    assert rs.kredit_aus(luecke[luecke.index.to_period("M") != pd.Period("2019-07")], "2019-12-31") is None


# --- Sahm-Regel ---

def test_sahm_wert_formel():
    # 15 Monate: 12 × 4,0, dann 4,0 / 4,5 / 5,0 → Ū3 = 4,5; Minimum der 12 Vormonats-Mittel = 4,0 → S = 0,5
    u = _monate([4.0] * 13 + [4.5, 5.0])
    assert rs.sahm_wert(u) == pytest.approx(0.5)
    assert rs.arbeitsmarkt_aus(u) is True
    assert rs.arbeitsmarkt_aus(_monate([4.0] * 13 + [4.4, 5.0])) is False       # S = 0,4667
    assert rs.sahm_wert(_monate([4.0] * 14)) is None                            # 15 Monate nötig
    assert rs.sahm_wert(_monate([5.0] * 12 + [4.8, 4.6, 4.4])) == pytest.approx(4.6 - 4.8)   # darf negativ sein: Ū3 = 4,6 gegen Minimum 4,8


def test_sahm_minimum_nur_aus_den_zwoelf_vormonaten():
    # Ein tiefes Mittel vor mehr als 12 Monaten zählt nicht; der jüngste Monat selbst zählt nicht zum Minimum.
    u = _monate([3.0, 3.0, 3.0] + [4.0] * 12 + [4.2, 4.2, 4.2])
    assert rs.sahm_wert(u) == pytest.approx(0.2)


def test_sahm_luecke_gibt_keinen_wert():
    u = _monate([4.0] * 15)
    assert rs.sahm_wert(u.drop(u.index[7])) is None


# --- Variante V1 und Diagnosen ---

@pytest.mark.parametrize("trend,kurve,kredit,arbeit,erwartet", [
    (True, False, False, False, False),      # Trend allein reicht nicht
    (False, True, True, True, False),        # Makro ohne Trend reicht nicht
    (True, True, False, False, True),
    (True, False, True, False, True),
    (True, False, False, True, True),
    (False, False, False, False, False),
])
def test_v1_trend_und_mindestens_ein_makrosignal(trend, kurve, kredit, arbeit, erwartet):
    assert rs.rohzustand("V1", trend, kurve, kredit, arbeit) is erwartet


def test_v1_ohne_vollstaendige_signale_kein_zustand():
    assert rs.rohzustand("V1", True, None, True, True) is None
    assert rs.rohzustand("V1", None, False, False, False) is None


def test_diagnosen_nutzen_nur_ihr_signal():
    assert rs.rohzustand("D1", True, False, False, False) is True
    assert rs.rohzustand("D2", True, False, True, True) is False
    assert rs.rohzustand("D3", False, False, True, None) is True
    assert rs.rohzustand("D4", True, True, True, None) is None
    with pytest.raises(ValueError, match="unbekannte Variante"):
        rs.rohzustand("V2", True, True, True, True)


# --- Haltepflicht ---

def _zustand(roh):
    index = pd.period_range("2020-01", periods=len(roh), freq="M").to_timestamp("M")
    return rs.mit_haltepflicht(pd.Series(roh, index=index, dtype=object)).tolist()


def test_haltepflicht_naechster_wechsel_fruehestens_zwei_monate_spaeter():
    A, R = True, False            # A = Risiko aus, R = Risiko an
    assert _zustand([R, R, A, R, R]) == [R, R, A, A, R]            # Wechsel bei m, m+1 gesperrt, m+2 erlaubt
    assert _zustand([R, R, A, R, A]) == [R, R, A, A, A]            # Rohsignal bei m+2 wieder „aus“: kein Wechsel
    assert _zustand([R, A, R, A, R, A]) == [R, R, R, A, A, A]      # Zickzack: m1 und m4 gesperrt, Wechsel nur bei m3
    assert _zustand([A, R, R]) == [A, A, R]                        # die erste Bewertung zählt als Wechsel


def test_haltepflicht_ohne_zustand_am_anfang_und_lauter_abbruch_danach():
    assert _zustand([None, None, True, False, False]) == [None, None, True, True, False]
    with pytest.raises(ValueError, match="kein Rohzustand"):
        _zustand([False, None, False])


# --- Zusammenspiel und Point-in-time ---

class _Makro:
    """MakroStand-Attrappe: merkt sich, mit welchem Stichtag jede Reihe abgefragt wurde."""

    def __init__(self, reihen):
        self.reihen, self.abfragen = reihen, []

    def __call__(self, reihe, stichtag):
        self.abfragen.append((reihe, pd.Timestamp(stichtag)))
        werte = self.reihen[reihe]
        return werte[werte.index < pd.Timestamp(stichtag)] if reihe != "UNRATE" else werte


def _kurse(monatswerte, start="2019-01"):
    return _tageswerte({str(pd.Period(start) + i): w for i, w in enumerate(monatswerte)})


def test_revidierte_reihe_mit_stand_des_vortags_marktreihen_mit_stand_des_tages():
    monate = [str(p) for p in pd.period_range("2019-01", "2019-12", freq="M")]
    makro = _Makro({"T10Y3M": _tageswerte(dict.fromkeys(monate, 1.0)), "BAA10Y": _tageswerte(dict.fromkeys(monate, 2.0)),
                    "UNRATE": _monate([4.0] * 15, ende="2019-11")})
    rs.signale_am("2019-12-31", _kurse([100] * 12).groupby(lambda t: t.to_period("M")).last(), makro)
    assert dict(makro.abfragen) == {"T10Y3M": pd.Timestamp("2019-12-31"), "BAA10Y": pd.Timestamp("2019-12-31"),
                                    "UNRATE": pd.Timestamp("2019-12-30")}


def test_verlauf_v1_mit_haltepflicht_und_ohne_zustand_vor_voller_historie():
    monate = [str(p) for p in pd.period_range("2018-01", "2020-06", freq="M")]
    kurve = dict.fromkeys(monate, 1.0) | {"2020-02": -0.2, "2020-03": -0.2}
    makro = _Makro({"T10Y3M": _tageswerte(kurve), "BAA10Y": _tageswerte(dict.fromkeys(monate, 2.0)),
                    "UNRATE": _monate([4.0] * 40, ende="2020-06")})
    # 12 ruhige Monate, dann Einbruch im Februar und März 2020, Erholung ab April
    kurse = _kurse([100] * 13 + [80, 70, 110, 115, 120])
    v = rs.regime_verlauf(kurse, makro)

    assert v.index[0] == pd.Timestamp("2019-01-31") and v.index[-1] == pd.Timestamp("2020-06-30")
    assert v["risiko_aus"].iloc[:9].isna().all()                    # Trend braucht 10 Monatsschlüsse
    assert v["risiko_aus"].loc["2019-10-31"] is False
    assert v.loc["2020-02-28", ["trend_aus", "kurve_aus", "roh_aus", "risiko_aus"]].tolist() == [True, True, True, True]
    assert v["roh_aus"].loc["2020-04-30"] is False                  # Kurs über dem Durchschnitt, Kurve wieder positiv
    assert v["risiko_aus"].loc["2020-03-31"] is True
    assert v["risiko_aus"].loc["2020-04-30"] is False               # zwei Monatsenden nach dem Wechsel: erlaubt


def test_verlauf_trend_allein_schaltet_v1_nicht_aus_aber_d1():
    monate = [str(p) for p in pd.period_range("2018-01", "2020-06", freq="M")]
    makro = _Makro({"T10Y3M": _tageswerte(dict.fromkeys(monate, 1.0)), "BAA10Y": _tageswerte(dict.fromkeys(monate, 2.0)),
                    "UNRATE": _monate([4.0] * 40, ende="2020-06")})
    kurse = _kurse([100] * 13 + [80, 70, 110, 115, 120])
    assert not rs.regime_verlauf(kurse, makro)["risiko_aus"].dropna().any()
    assert rs.regime_verlauf(kurse, makro, variante="D1")["risiko_aus"].loc["2020-02-28"] is True


def test_verlauf_nutzt_keine_spaeteren_kurse():
    """Der Zustand eines Monatsendes ändert sich nicht, wenn spätere Kurse dazukommen."""
    monate = [str(p) for p in pd.period_range("2018-01", "2020-06", freq="M")]
    makro = _Makro({"T10Y3M": _tageswerte(dict.fromkeys(monate, -0.5)), "BAA10Y": _tageswerte(dict.fromkeys(monate, 2.0)),
                    "UNRATE": _monate([4.0] * 40, ende="2020-06")})
    rng = np.random.default_rng(7)
    kurse = _kurse(list(100 + rng.normal(0, 5, 18).cumsum()))
    ganz = rs.regime_verlauf(kurse, makro)
    teil = rs.regime_verlauf(kurse.loc[:"2020-01-31"], makro)
    pd.testing.assert_frame_equal(ganz.loc[:"2020-01-31"], teil)


# --- Ankerpunkte an echten Daten (nur Einzelsignale, kein Verlauf von V1; docs/REGIME.md, Abschnitt 7a) ---

def _echter_stand():
    from tradingbot.daten.cache import standard_cache

    cache = standard_cache()
    if any(cache.lesen("makro", r)[0] is None for r in rs.REIHEN.values()):
        pytest.skip("Makro-Cache fehlt")
    # kein Netz im Test: Tabellen direkt aus dem Cache, Stand mit Tresor
    from tradingbot.daten.makro import stand_mit_tresor

    tabellen = {r: cache.lesen("makro", r)[0] for r in rs.REIHEN.values()}
    return lambda reihe, stichtag: stand_mit_tresor(tabellen[reihe], stichtag)


def test_echte_daten_sahm_regel_in_echtzeit():
    makro = _echter_stand()
    # Ende April 2020 ist erst der März bekannt (4,4 %): Ū3 = (3,6 + 3,5 + 4,4)/3, noch kein Signal
    assert rs.arbeitsmarkt_aus(makro("UNRATE", pd.Timestamp("2020-04-29"))) is False
    # Ende Mai 2020 mit der Erstmeldung für April (14,7 %, später 14,8 %): Ū3 = (3,5 + 4,4 + 14,7)/3 = 7,53
    stand = makro("UNRATE", pd.Timestamp("2020-05-28"))
    assert stand.iloc[-1] == 14.7 and rs.sahm_wert(stand) == pytest.approx(7.53 - 3.5, abs=0.1)
    assert rs.arbeitsmarkt_aus(stand) is True
    assert rs.arbeitsmarkt_aus(makro("UNRATE", pd.Timestamp("2017-06-29"))) is False


def test_echte_daten_zinskurve_juni_2019_invertiert_2017_nicht():
    makro = _echter_stand()
    assert rs.zinskurve_aus(makro("T10Y3M", pd.Timestamp("2019-06-28")), "2019-06-28") is True
    assert rs.zinskurve_aus(makro("T10Y3M", pd.Timestamp("2017-06-30")), "2017-06-30") is False


def test_echte_daten_kreditaufschlag_maerz_2020_weitet_sich():
    makro = _echter_stand()
    assert rs.kredit_aus(makro("BAA10Y", pd.Timestamp("2020-03-31")), "2020-03-31") is True


# --- Betriebsregel für Datenlücken (15.11.2026, nicht Teil von b628678; docs/REGIME.md, Abschnitt 9b) ---

def test_lueckenregel_ist_auf_lueckenlosen_daten_exakt_die_alte_formel():
    rng = np.random.default_rng(7)
    u = _monate(np.round(4.0 + np.cumsum(rng.normal(0, 0.15, 240)), 1))
    for ende in range(15, len(u) + 1):
        teil = u.iloc[:ende]
        alt, neu = rs.sahm_wert(teil), rs.sahm_wert_bei_datenluecke(teil)
        assert alt is not None and neu == pytest.approx(alt, abs=1e-12)
        assert rs.arbeitsmarkt_aus(teil) is bool(alt >= rs.SAHM_SCHWELLE - 1e-9)


def test_lueckenregel_zu_kurze_historie_ist_keine_luecke():
    assert rs.sahm_wert_bei_datenluecke(_monate([4.0] * 14)) is None and rs.arbeitsmarkt_aus(_monate([4.0] * 14)) is None
    assert rs.sahm_wert_bei_datenluecke(pd.Series(dtype=float)) is None


def test_lueckenregel_ueberspringt_einen_fehlenden_monat_ohne_zu_schaetzen():
    # Wie im Dezember 2025: Der Vormonat des jüngsten Monats fehlt (Oktober nie erhoben). Ū3_m = Mittel aus August, September,
    # November; das Tief über die vorhandenen Monate m−12 … m−1 (der fehlende Monat hat kein Mittel).
    u = _monate([4.0] * 13 + [4.1, 4.2, 4.3, 4.4, 9.9, 4.6], ende="2025-11")       # 9,9 steht für Oktober und wird entfernt
    luecke = u.drop(pd.Timestamp("2025-10-01"))
    assert rs.sahm_wert(luecke) is None
    assert rs.sahm_wert_bei_datenluecke(luecke) == pytest.approx((4.3 + 4.4 + 4.6) / 3 - 4.0)
    assert rs.arbeitsmarkt_aus(luecke) is False                                       # 0,43 < 0,50
    hoch = _monate([4.0] * 13 + [4.1, 4.2, 4.3, 4.5, 9.9, 4.8], ende="2025-11").drop(pd.Timestamp("2025-10-01"))
    assert rs.sahm_wert_bei_datenluecke(hoch) == pytest.approx((4.3 + 4.5 + 4.8) / 3 - 4.0) and rs.arbeitsmarkt_aus(hoch) is True
    # Lücke mitten im Fenster: Mittel über die Lücke hinweg aus drei veröffentlichten Werten; jüngstes Mittel unberührt
    mitte = _monate([4.0] * 10 + [3.4, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.3, 4.6], ende="2026-06").drop(pd.Timestamp("2025-09-01"))
    assert rs.sahm_wert_bei_datenluecke(mitte) == pytest.approx(4.3 - 3.8)            # Tief: (3,4 + 4,0 + 4,0) / 3 = 3,8
    # Lücke am Anfang des Fensters (m − 14), Reihe beginnt davor: zählt als Lücke
    anfang = _monate([4.0] * 20 + [4.5, 5.0], ende="2026-06")
    assert rs.sahm_wert_bei_datenluecke(anfang.drop(anfang.index[-15])) == pytest.approx(0.5)


def test_lueckenregel_mehr_als_ein_fehlender_monat_kein_wert():
    u = _monate([4.0] * 30, ende="2026-06")
    assert rs.sahm_wert_bei_datenluecke(u.drop([u.index[-2], u.index[-5]])) is None
    assert rs.arbeitsmarkt_aus(u.drop([u.index[-2], u.index[-5]])) is None
    assert rs.sahm_wert_bei_datenluecke(u.drop([u.index[-3], u.index[-4]])) is None    # zwei Monate in Folge
    assert rs.arbeitsmarkt_aus(u.drop(u.index[-2])) is False                           # genau einer: Regel greift


def test_lueckenregel_laesst_alle_verlaeufe_gegenueber_b628678_unveraendert():
    """Signale, Rohzustand und Zustand mit Haltepflicht für V1 und D1–D4: heutiger Code gegen den Stand im Festlegungs-Commit
    auf lückenlosen Daten (künstlich). Der Lauf über den echten Backtest-Zeitraum: tools/pruefe_regime_datenluecke.py."""
    import importlib.util
    import subprocess
    from pathlib import Path

    wurzel = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location("pruefe_regime_datenluecke", wurzel / "tools" / "pruefe_regime_datenluecke.py")
    werkzeug = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(werkzeug)
    try:
        alt = werkzeug.signale_aus_commit("b628678", wurzel)
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("Git oder Commit b628678 nicht verfügbar")
    assert not hasattr(alt, "sahm_wert_bei_datenluecke")
    rng = np.random.default_rng(11)
    tage = pd.bdate_range("2012-01-02", "2024-12-31")
    kurse = pd.Series(100 * np.cumprod(1 + rng.normal(0.0002, 0.012, len(tage))), index=tage)
    reihen = {"T10Y3M": pd.Series(np.cumsum(rng.normal(0, 0.05, len(tage))) + 0.5, index=tage),
              "BAA10Y": pd.Series(np.abs(np.cumsum(rng.normal(0, 0.03, len(tage))) + 2.0), index=tage)}
    monate = pd.date_range("2010-01-01", "2024-12-01", freq="MS")
    reihen["UNRATE"] = pd.Series(np.round(5.0 + np.cumsum(rng.normal(0, 0.2, len(monate))), 1), index=monate)

    def makro(reihe, stichtag):
        r = reihen[reihe]
        return r[r.index < pd.Timestamp(stichtag) - pd.Timedelta(days=35 if reihe == "UNRATE" else 0)]

    erg = werkzeug.vergleiche(alt, rs, kurse, makro)
    assert erg["abweichungen"] == [] and all(erg["varianten"].values()) and set(erg["varianten"]) == set(rs.VARIANTEN)
    assert erg["sahm_gleich"] == erg["monate"] == 156
    v1 = rs.regime_verlauf(kurse, makro)
    assert v1["arbeit_aus"].dropna().nunique() == 2 and v1["risiko_aus"].dropna().nunique() == 2   # der Vergleich ist nicht leer
