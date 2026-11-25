"""Risiko-Übersicht Schritt 1: Bewertungsbasis und Klumpen-Kennzahlen (docs/RISIKO_UEBERSICHT.md, Abschnitte 3, 5, 8)."""
import math

import pytest

from tradingbot.konfiguration import lade_konfiguration
from tradingbot.risiko import klumpen as kl
from tradingbot.risiko.zuordnung import Zuordnung


class JournalAttrappe:
    def __init__(self, bestaende, kassen, kassen_w):
        self._b, self._k, self._kw = bestaende, kassen, kassen_w

    def bestand(self, buch):
        return dict(self._b.get(buch, {}))

    def kasse(self, buch):
        return self._k[buch]

    def kasse_je_waehrung(self, buch):
        return dict(self._kw[buch])

    def kasse_bewertet(self, buch, fx):
        fremd = {w: b for w, b in self._kw[buch].items() if w != "EUR"}
        if not fremd:
            return self._k[buch]
        if any(not fx.get(w) for w in fremd):
            raise ValueError(f"{buch}: kein Kurs")
        return self._kw[buch].get("EUR", 0.0) + sum(b / fx[w] for w, b in fremd.items())


def _aktie(t, land="USA", sektor="D Verarbeitendes Gewerbe"):
    return Zuordnung(t, "Einzelaktie", "Aktie", land, sektor, waehrung_notierung="USD", waehrung_wirtschaftlich="USD", kennzeichen="exakt")


def _etf(t, region, wirtsch):
    return Zuordnung(t, "ETF", "Aktien", region, "breit gestreut", waehrung_notierung="EUR", waehrung_wirtschaftlich=wirtsch,
                     kennzeichen="Näherung: Indexregion")


ZUORDNUNG = {"A": _aktie("A"), "B": _aktie("B", sektor="I Dienstleistungen"), "C": _aktie("C", land="Ireland"),
             "IUSA.DE": _etf("IUSA.DE", "USA", "USD"), "EUNN.DE": _etf("EUNN.DE", "Japan", "JPY")}
FX = {"USD": 1.25}


def _basis(journal, buch, kurse, rolle="core"):
    return kl.buchbasis(journal, buch, kurse, FX, rolle, ZUORDNUNG.__getitem__)


@pytest.fixture
def journal():
    # Buch f: drei Aktien 500/300/200 € plus Kasse 0 €; Buch s: zwei ETFs; Buch u: Aktien mit USD-Kasse
    return JournalAttrappe(
        {"f": {"A": 5, "B": 3, "C": 2}, "s": {"IUSA.DE": 10, "EUNN.DE": 10}, "u": {"A": 1}, "g": {"A": 2, "B": 1}},
        {"f": 0.0, "s": 100.0, "u": 1000.0, "g": 0.0},
        {"f": {"EUR": 0.0}, "s": {"EUR": 100.0}, "u": {"EUR": 600.0, "USD": 540.0}, "g": {"EUR": 0.0}})


def test_hhi_und_effektive_titelzahl_von_hand(journal):
    b = _basis(journal, "f", {"A": 100.0, "B": 100.0, "C": 100.0})
    # Gewichte 0,5 / 0,3 / 0,2 → HHI = 0,25 + 0,09 + 0,04 = 0,38; 1/HHI = 2,6316
    k = kl.kennzahlen(b)
    assert k["hhi"] == pytest.approx(0.38) and k["effektive_titel"] == pytest.approx(1 / 0.38)
    assert k["groesste"] == ("A", pytest.approx(0.5)) and k["top5_anteil"] == pytest.approx(1.0)


def test_anteile_ergeben_100_prozent_mit_kasse(journal):
    b = _basis(journal, "s", {"IUSA.DE": 40.0, "EUNN.DE": 50.0}, rolle="satellite")
    k = kl.kennzahlen(b)
    assert b.wert_eur == pytest.approx(1000.0)
    for d, s in k["anteile"].items():
        assert s.sum() == pytest.approx(1.0), d
    assert k["anteile"]["land"].to_dict() == pytest.approx({"Japan": 0.5, "USA": 0.4, "Kasse": 0.1})
    assert k["anteile"]["waehrung_notierung"].to_dict() == pytest.approx({"EUR": 1.0})
    assert k["anteile"]["waehrung_wirtschaftlich"].to_dict() == pytest.approx({"JPY": 0.5, "USD": 0.4, "EUR": 0.1})
    assert k["kasse_anteil"] == pytest.approx(0.1)


def test_etf_wird_nie_aufgeteilt(journal):
    k = kl.kennzahlen(_basis(journal, "s", {"IUSA.DE": 40.0, "EUNN.DE": 50.0}, rolle="satellite"))
    assert set(k["anteile"]["sektor"].index) == {"breit gestreut", "Kasse"}


def test_usd_kasse_zum_laufkurs_kontrollzeile_null(journal):
    # Befund 1 (25.11.2026): EUR 600 + 540 $ / 1,25 = 432 € → Kasse 1.032 € statt 1.000 € (alte Konvention)
    b = _basis(journal, "u", {"A": 100.0})
    k = kl.kennzahlen(b)
    assert b.wert_eur == pytest.approx(1132.0)                           # Konvention des Buchwerts
    assert k["kasse_fremd_buchwert_eur"] == pytest.approx(432.0)
    assert k["kasse_fremd_tageskurs_eur"] == pytest.approx(432.0)
    assert k["kasse_fremd_unterschied_eur"] == pytest.approx(0.0)        # Kontrollzeile (D5)
    w = k["anteile"]["waehrung_notierung"]
    assert w.sum() == pytest.approx(1.0) and w["USD"] == pytest.approx(532 / 1132) and w["EUR"] == pytest.approx(600 / 1132)


def test_fehlender_fx_kurs_alte_konvention_mit_hinweis(journal):
    b = kl.buchbasis(journal, "u", {"A": 100.0}, {}, "core", ZUORDNUNG.__getitem__)
    assert b.kasse_eur == pytest.approx(1000.0) and any("alten Konvention" in h for h in b.hinweise)


def test_drift_core_ueber_und_unter_7_5_prozent():
    j = JournalAttrappe({"c": {"A": 76, "B": 924}, "d": {"A": 74, "B": 926}}, {"c": 0.0, "d": 0.0}, {"c": {}, "d": {}})
    hoch = kl.drift_hinweise(_basis(j, "c", {"A": 1.0, "B": 1.0}), {"core_einzelaktie": 0.075, "satellite_einzelaktie": 0.125})
    assert len([h for h in hoch if " A " in h]) == 1 and "7,6 %" in hoch[0] and "kein Zwangsverkauf" in hoch[0]
    tief = kl.drift_hinweise(_basis(j, "d", {"A": 1.0, "B": 1.0}), {"core_einzelaktie": 0.075, "satellite_einzelaktie": 0.125})
    assert not [h for h in tief if " A " in h]


def test_drift_satellite_nur_einzelaktien_ab_12_5_prozent():
    sch = {"core_einzelaktie": 0.075, "satellite_einzelaktie": 0.125}
    j = JournalAttrappe({"s": {"A": 12, "IUSA.DE": 88}, "t": {"A": 13, "IUSA.DE": 87}}, {"s": 0.0, "t": 0.0}, {"s": {}, "t": {}})
    assert kl.drift_hinweise(_basis(j, "s", {"A": 1.0, "IUSA.DE": 1.0}, rolle="satellite"), sch) == []   # ETF 88 %: kein Hinweis
    t = kl.drift_hinweise(_basis(j, "t", {"A": 1.0, "IUSA.DE": 1.0}, rolle="satellite"), sch)
    assert len(t) == 1 and "A 13,0 %" in t[0]


def test_buch_ohne_rolle_wird_gemeldet_und_ohne_drift(journal):
    b = _basis(journal, "f", {"A": 100.0, "B": 100.0, "C": 100.0}, rolle=None)
    assert any("Rolle unbekannt" in h for h in b.hinweise)
    assert kl.drift_hinweise(b, {"core_einzelaktie": 0.075, "satellite_einzelaktie": 0.125}) == []


def test_fehlender_kurs_macht_buch_unvollstaendig(journal):
    b = _basis(journal, "f", {"A": 100.0, "B": 100.0})
    assert not b.vollstaendig and any("kein Kurs für C" in h for h in b.hinweise)
    assert "nicht möglich" in kl.buchwert_abgleich(b, 1000.0, 0.005)


def test_buchwert_abgleich_meldet_abweichung_und_gleicht_nicht_an(journal):
    b = _basis(journal, "f", {"A": 100.0, "B": 100.0, "C": 100.0})
    assert kl.buchwert_abgleich(b, 1000.0, 0.005) is None
    assert kl.buchwert_abgleich(b, 1000.004, 0.005) is None
    m = kl.buchwert_abgleich(b, 999.0, 0.005)
    assert m and "+1.00 €" in m and b.wert_eur == pytest.approx(1000.0)


def test_gesamtbloecke_getrennt_und_doppelte_titel_markiert(journal):
    betrieb = {"buecher": {"f": {"art": "skalierung", "rolle": "core"}, "g": {"art": "skalierung", "rolle": "core"},
                           "s": {"art": "real", "rolle": "core"}}}
    basen = {"f": _basis(journal, "f", {"A": 100.0, "B": 100.0, "C": 100.0}),
             "g": _basis(journal, "g", {"A": 100.0, "B": 100.0}),
             "s": _basis(journal, "s", {"IUSA.DE": 40.0, "EUNN.DE": 50.0})}
    bl = kl.bloecke(basen, betrieb)
    assert bl["real"].buecher == ("s",) and set(bl["skalierung"].buecher) == {"f", "g"}
    sk = bl["skalierung"]
    assert sk.doppelt == ("A", "B") and sk.wert_eur == pytest.approx(1300.0)
    a = next(p for p in sk.posten if p.ticker == "A")
    assert a.stueck == 7 and a.buecher == ("f", "g")
    assert kl.kennzahlen(sk)["anteile"]["titel"]["A"] == pytest.approx(700 / 1300)


def test_gesamtblock_meldet_unterschiedliche_kurse_je_buch(journal):
    basen = [_basis(journal, "f", {"A": 100.0, "B": 100.0, "C": 100.0}), _basis(journal, "g", {"A": 101.0, "B": 100.0})]
    sk = kl.gesamtblock("Skalierung", basen)
    assert any("A mit unterschiedlichen Kursen" in h for h in sk.hinweise)
    assert sk.wert_eur == pytest.approx(1000.0 + 302.0)                  # Werte je Buch summiert, nichts angeglichen


def test_buch_nur_kasse_ohne_hhi():
    j = JournalAttrappe({"k": {}}, {"k": 500.0}, {"k": {"EUR": 500.0}})
    k = kl.kennzahlen(_basis(j, "k", {}))
    assert math.isnan(k["hhi"]) and k["groesste"] is None and k["anteile"]["land"].to_dict() == {"Kasse": 1.0}


def test_rollen_aus_betriebskonfiguration():
    r = kl.rollen(lade_konfiguration("betrieb"))
    assert r == {"real": "core", "fundamental_a": "core", "fundamental_b": "core", "crossover": "satellite",
                 "momentum": "satellite", "regime": "core"}
    assert lade_konfiguration("risiko_uebersicht")["drift"] == {"core_einzelaktie": 0.075, "satellite_einzelaktie": 0.125}
