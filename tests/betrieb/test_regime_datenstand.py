"""Befund 4 (Plan freigegeben von Jakob 16.11.2026; docs/REGIME.md, Abschnitt 9c): Datenstand der Makroreihen im Protokoll,
Neuberechnung mit genau diesem Stand, nachgeholte Bewertung ohne den Vortageswert der Tagesreihen."""
import pandas as pd

from test_regimebuch import Makro, kursreihe
from tradingbot.betrieb import regimebuch

VORTAG = pd.Timestamp("2027-01-28")          # Donnerstag vor dem Bewertungstag 29.01.2027 (Monatsende der Reihe und Xetra)


class MakroSpaet(Makro):
    """Zinskurve invers (−0,5), nur am 28.01.2027 +100: Mit diesem Wert ist der Januar-Durchschnitt positiv (Zinskurve an),
    ohne ihn negativ (aus). `fehlt`: Beobachtungen, die FRED am Abend noch nicht hat."""

    def __init__(self, fehlt=()):
        super().__init__()
        self.fehlt = {pd.Timestamp(t) for t in fehlt}

    def stand(self, reihe, stichtag):
        werte = super().stand(reihe, stichtag)
        if reihe == "T10Y3M":
            werte = werte.copy()
            if VORTAG in werte.index:
                werte[VORTAG] = 100.0
        return werte[~werte.index.isin(self.fehlt)]


REIHE = kursreihe("2027-03-31")


def _bis_janember():
    z, _ = regimebuch.bewerten("2026-11-16", REIHE, Makro().laden, {})
    z, s = regimebuch.bewerten("2026-11-30", REIHE, Makro().laden, z)
    assert s.neu == ["2026-11"] and z["protokoll"]["2026-11"]["datenstand"]["T10Y3M"] == "2026-11-27"
    z, s = regimebuch.bewerten("2027-01-04", REIHE, Makro().laden, z)
    assert s.neu == ["2026-12"]
    return z


def test_puenktlich_ohne_vortag_neuberechnung_mit_demselben_datenstand():
    z = _bis_janember()
    z, s = regimebuch.bewerten("2027-01-29", REIHE, MakroSpaet(fehlt=[VORTAG]).laden, z)
    jan = z["protokoll"]["2027-01"]
    assert jan["art"] == "bewertung" and jan["kurve_aus"] is True and jan["datenstand"]["T10Y3M"] == "2027-01-27"
    z, s = regimebuch.bewerten("2027-02-26", REIHE, MakroSpaet().laden, z)   # FRED hat den 28.01. jetzt
    assert s.neu == ["2027-02"] and not any("2027-01" in x for x in s.laut), s.laut


def test_alter_eintrag_ohne_datenstand_meldet_datenstand_als_ursache():
    z = _bis_janember()
    z, _ = regimebuch.bewerten("2027-01-29", REIHE, MakroSpaet(fehlt=[VORTAG]).laden, z)
    del z["protokoll"]["2027-01"]["datenstand"]                                                  # Eintrag wie vor dem 17.11.2026
    z, s = regimebuch.bewerten("2027-02-26", REIHE, MakroSpaet().laden, z)
    (meldung,) = [x for x in s.laut if "2027-01" in x]
    assert "Zinskurve: protokolliert aus, neu gerechnet an" in meldung and "Ursache: Datenstand" in meldung
    assert "geänderte Kurshistorie" not in meldung and z["protokoll"]["2027-01"]["kurve_aus"] is True      # das Protokoll gilt
    z, s = regimebuch.bewerten("2027-03-31", REIHE, MakroSpaet().laden, z)
    assert not any("2027-01" in x for x in s.laut)                                                # nur einmal gemeldet


def test_echte_abweichung_bleibt_geaenderte_kurshistorie():
    z = _bis_janember()
    z, _ = regimebuch.bewerten("2027-01-29", REIHE, MakroSpaet(fehlt=[VORTAG]).laden, z)
    del z["protokoll"]["2027-01"]["datenstand"]
    z["protokoll"]["2027-01"]["kredit_aus"] = True                                                # Protokoll anders als jede Rechnung
    _, s = regimebuch.bewerten("2027-02-26", REIHE, MakroSpaet().laden, z)
    (meldung,) = [x for x in s.laut if "2027-01" in x and "Kreditaufschlag" in x]
    assert "geänderte Kurshistorie" in meldung


def test_nachgeholt_sieht_dasselbe_wie_puenktlich():
    z = _bis_janember()
    z, s = regimebuch.bewerten("2027-02-01", REIHE, MakroSpaet().laden, z)   # Abend des 29.01. verpasst
    jan = z["protokoll"]["2027-01"]
    assert s.neu == ["2027-01"] and jan["art"] == "nachgeholt"
    assert jan["kurve_aus"] is True and jan["datenstand"]["T10Y3M"] == "2027-01-27"              # ohne den Wert vom 28.01.
    assert jan["datenstand"]["UNRATE"] == "2026-12-01"                                             # Monatsreihe unverändert
    assert jan["werte"]["kurve"] == -0.5                                                            # Anzeige mit demselben Stand
