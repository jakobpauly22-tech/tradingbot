"""A4 (Jakob 13.11.2026): Abspaltung (SO) nach Bestätigung buchen.

Nachgestellt mit Versant: 1 Versant (VSNT) je 25 Comcast (CMCSA), Bruchteile bar. Kurse und Barausgleich angenommen
(die echten stehen im Flex-Beleg und in den Kursreihen). Format der IBKR-Beschreibung am ersten echten Beleg prüfen."""
from datetime import datetime

import pandas as pd
import pytest

from tradingbot.betrieb import kapitalmassnahmen as km
from tradingbot.broker.basis import Position

from test_kapitalmassnahmen_a2 import FX, JETZT, erkennen_und_buchen, j, zeile  # noqa: F401
from test_kapitalmassnahmen_a3 import kauf_usd

SO = "SPINOFF  1 FOR 25"
TAB = {800: "CMCSA", 801: "VSNT"}
MUTTER = "CMCSA(US20030N1019)"


def versant(neu, erloes="0", conid="801"):
    return [{"type": "SO", "actionID": "66", "conid": conid, "symbol": "VSNT", "isin": "US92536B1052", "currency": "USD",
             "quantity": str(neu), "proceeds": erloes, "reportDate": "20261105",
             "description": f"{MUTTER} {SO} (VSNT, VERSANT MEDIA GROUP INC, US92536B1052)", "transactionID": f"966{neu}",
             "levelOfDetail": "DETAIL"}]


def kurse(mutter=(28.0, 28.5), tochter=(45.0, 46.0), ab="2026-11-05"):
    tage = pd.bdate_range(ab, periods=2)
    reihen = {"CMCSA": pd.Series(mutter, index=tage), "VSNT": pd.Series(tochter, index=tage)}
    return lambda t, tag: reihen[t]


def test_beschreibung_lesen():
    text = f"{MUTTER} {SO} (VSNT, VERSANT MEDIA GROUP INC, US92536B1052)"
    assert km.mutter_aus_beschreibung(text) == ("CMCSA", "US20030N1019")
    assert km.abspaltung_verhaeltnis(text) == pytest.approx(0.04)
    assert km.abspaltung_verhaeltnis("XYZ(US0000000001) SPIN-OFF 3 FOR 2 (…)") == pytest.approx(1.5)


def test_erkannt_mutter_betroffen_bestaetigung_noetig(j):
    kauf_usd(j, "fundamental_a", "CMCSA", 110, 30.0)
    erg, m = erkennen_und_buchen(j, versant(4, "14.00"), [Position("DU1", "VSNT", 4, 45.0)], ticker_je_conid=TAB)
    assert erg == [] and any("Abspaltung" in x and "betroffen: fundamental_a" in x and "Bestätigung in der Oberfläche" in x for x in m)
    offen = km.bestaetigung_offen(j, "fundamental_a")
    assert [o["bestaetigbar"] for o in offen] == [True] and "Mutter CMCSA, 0.04 Tochter-Aktien je Aktie" in offen[0]["text"]
    assert j.bestand("fundamental_a") == {"CMCSA": 110}


def test_versant_gebucht_einstand_nach_schlusskursen(j):
    kauf_usd(j, "fundamental_a", "CMCSA", 60, 30.0, nr="1")
    kauf_usd(j, "fundamental_a", "CMCSA", 50, 30.0, nr="2")                     # 110 Stück, Einstand 3.300 USD
    usd = j.kasse_je_waehrung("fundamental_a").get("USD", 0.0)
    pos = [Position("DU1", "CMCSA", 110, 28.0), Position("DU1", "VSNT", 4, 45.0)]
    # 110 / 25 = 4,4 → 4 VSNT, Spitze 0,4 bar zu 35 USD = 14 USD
    erkennen_und_buchen(j, versant(4, "14.00"), pos, ticker_je_conid=TAB)
    km.bestaetigen(j, "CA:66", datetime(2026, 1, 6, 21, 0))
    m = []
    erg = km.buchen(j, ["crossover", "momentum", "fundamental_a"], pos, m, fx=FX, ticker_je_conid=TAB, jetzt=JETZT, schlusskurse=kurse())
    assert [b.ok for b in erg] == [True], m
    assert j.bestand("fundamental_a") == {"CMCSA": 110, "VSNT": 4}
    anteil = 0.04 * 45.0 / (0.04 * 45.0 + 28.0)                                     # ≈ 6,04 %
    e = j.einstaende("fundamental_a")
    assert e["CMCSA"]["w"] == pytest.approx(3300.0 * (1 - anteil))
    assert e["VSNT"]["w"] == pytest.approx(3300.0 * anteil * 4 / 4.4)              # Spitze anteilig mit dem Barausgleich ab
    assert e["VSNT"]["erst"][:10] == "2026-10-01"                                 # Anschaffungsdatum der Mutter
    assert j.kasse_je_waehrung("fundamental_a")["USD"] == pytest.approx(usd + 14.0)
    text = next(x for x in m if "gebucht (fundamental_a)" in x)
    assert "Schlusskursen am 2026-11-05" in text and "Tochter 6.04%" in text and "Kaufposten der Mutter: 2026-10-01 110 St." in text
    assert "Sachausschüttung" in text and "Wert der Tochter am 2026-11-05: 180.00 USD" in text and "Form 8937 noch nicht eingetragen" in text
    assert km.buchen(j, ["fundamental_a"], pos, [], fx=FX, ticker_je_conid=TAB, schlusskurse=kurse()) == []     # nicht doppelt


def test_ohne_gemeinsamen_kurs_wartet_die_buchung(j):
    kauf_usd(j, "fundamental_a", "CMCSA", 100, 30.0)
    pos = [Position("DU1", "CMCSA", 100, 28.0), Position("DU1", "VSNT", 4, 45.0)]
    erkennen_und_buchen(j, versant(4), pos, ticker_je_conid=TAB)
    km.bestaetigen(j, "CA:66")
    m = []
    erg = km.buchen(j, ["fundamental_a"], pos, m, fx=FX, ticker_je_conid=TAB, schlusskurse=kurse(ab="2025-12-01"))
    assert not erg[0].ok and "Buchung wartet" in erg[0].text and j.bestand("fundamental_a") == {"CMCSA": 100}


@pytest.mark.parametrize("neu, erloes, grund", [(5, "0", "Probe: Bücher"), (4, "0", "ohne Barausgleich"), (4, "14.00", "Probe gegen IBKR")])
def test_probe_scheitert_nichts_gebucht(j, neu, erloes, grund):
    kauf_usd(j, "fundamental_a", "CMCSA", 110, 30.0)
    ibkr = 3 if grund == "Probe gegen IBKR" else neu
    pos = [Position("DU1", "CMCSA", 110, 28.0), Position("DU1", "VSNT", ibkr, 45.0)]
    erkennen_und_buchen(j, versant(neu, erloes), pos, ticker_je_conid=TAB)
    km.bestaetigen(j, "CA:66")
    erg = km.buchen(j, ["fundamental_a"], pos, [], fx=FX, ticker_je_conid=TAB, schlusskurse=kurse())
    assert not erg[0].ok and grund in erg[0].text and j.bestand("fundamental_a") == {"CMCSA": 110}


def test_abgelehnt_bleibt_gestoppt(j):
    kauf_usd(j, "fundamental_a", "CMCSA", 100, 30.0)
    erkennen_und_buchen(j, versant(4), [], ticker_je_conid=TAB)
    text = km.ablehnen(j, "CA:66", datetime(2026, 1, 6, 21, 0))
    assert "abgelehnt" in text and "bleiben gestoppt" in text
    assert km.buchen(j, ["fundamental_a"], [], [], fx=FX, ticker_je_conid=TAB, schlusskurse=kurse()) == []


def test_tochter_ohne_conid_nur_gemeldet_und_gekennzeichnet(j):
    kauf_usd(j, "fundamental_a", "CMCSA", 100, 30.0)
    pos = [Position("DU1", "CMCSA", 100, 28.0), Position("DU1", "VSNT", 4, 45.0)]
    tab = {800: "CMCSA"}                                                         # Conid 801 noch nicht in kontrakte.yaml
    erkennen_und_buchen(j, versant(4), pos, ticker_je_conid=tab)
    km.bestaetigen(j, "CA:66")
    m = []
    erg = km.buchen(j, ["fundamental_a"], pos, m, fx=FX, ticker_je_conid=tab, schlusskurse=kurse())
    assert erg[0].ok and any("noch nicht in config/kontrakte.yaml – Buch läuft weiter" in x for x in m)
    assert km.tochter_ohne_conid(j, "fundamental_a", tab) == {"VSNT"}
    assert km.tochter_ohne_conid(j, "fundamental_a", TAB) == set()


def test_form8937_vor_und_nach_der_buchung(j):
    kauf_usd(j, "fundamental_a", "CMCSA", 100, 30.0)
    pos = [Position("DU1", "CMCSA", 100, 28.0), Position("DU1", "VSNT", 4, 45.0)]
    erkennen_und_buchen(j, versant(4), pos, ticker_je_conid=TAB)
    assert [o["beleg_id"] for o in km.form8937_offen(j, "fundamental_a")] == ["CA:66"]
    with pytest.raises(ValueError):
        km.form8937_eintragen(j, "CA:66", "120", "x")
    text = km.form8937_eintragen(j, "CA:66", "93,5", "Comcast Form 8937 vom 15.01.2026")
    assert "Mutter 93.50 %, Tochter 6.50 %" in text and "noch nicht gebucht" in text and km.form8937_offen(j) == []
    km.bestaetigen(j, "CA:66")
    m = []
    km.buchen(j, ["fundamental_a"], pos, m, fx=FX, ticker_je_conid=TAB, schlusskurse=kurse())
    assert any("Form 8937 (Comcast Form 8937 vom 15.01.2026): Tochter 6.50 %" in x for x in m)
    text = km.form8937_eintragen(j, "CA:66", "94", "Korrektur")
    assert "gebucht nach Schlusskursen am 2026-11-05" in text and "Differenz Tochter" in text and "Buchung bleibt" in text


def test_vorschlag_der_mutter_bleibt_mit_hinweis(j):
    kauf_usd(j, "fundamental_a", "CMCSA", 100, 30.0)
    j.db.execute("INSERT INTO vorschlaege (id, erstellt, signaltag, buch, ticker, art, waehrung, richtung, stueck, limit_preis, "
                 "letzter_kurs_eur, frei, status, freigabe_bis) VALUES ('v1', '2026-11-02', '2026-11-02', 'fundamental_a', 'CMCSA', "
                 "'aktie', 'USD', -1, 100, 29.0, 26.0, 1, 'vorgeschlagen', '2026-11-02T23:59:59')")
    j.db.commit()
    pos = [Position("DU1", "CMCSA", 100, 28.0), Position("DU1", "VSNT", 4, 45.0)]
    erkennen_und_buchen(j, versant(4), pos, ticker_je_conid=TAB)
    km.bestaetigen(j, "CA:66")
    m = []
    km.buchen(j, ["fundamental_a"], pos, m, fx=FX, ticker_je_conid=TAB, schlusskurse=kurse())
    assert j.db.execute("SELECT status FROM vorschlaege WHERE id='v1'").fetchone()[0] == "vorgeschlagen"
    assert any("Vorschlag v1 (CMCSA, vorgeschlagen) stammt von vor der Abspaltung – Limit prüfen" in x for x in m)


# --- Tageslauf: Tochter ohne Conid (Entscheidung 3) ------------------------------------------------------------------------
def test_stichtag_sperrt_nur_den_verkauf_der_tochter():
    from tradingbot.betrieb.tageslauf import verkauf_gesperrt_merken
    z = {"ziel": {"AAA": 0.05}}
    assert verkauf_gesperrt_merken(z, {"VSNT"}, {"VSNT": 4, "AAA": 3}, "kein Quartalsstichtag") == z
    assert verkauf_gesperrt_merken(z, {"VSNT"}, {"VSNT": 4}, "Quartalsstichtag")["verkauf_gesperrt"] == ["VSNT"]
    assert "verkauf_gesperrt" not in verkauf_gesperrt_merken({"ziel": {"VSNT": 0.05}}, {"VSNT"}, {"VSNT": 4}, "Quartalsstichtag")


class _Erg:
    def __init__(self):
        self.meldungen, self.sofort = [], []


def _gebuchte_tochter(j, tab):
    kauf_usd(j, "fundamental_a", "CMCSA", 100, 30.0)
    pos = [Position("DU1", "CMCSA", 100, 28.0), Position("DU1", "VSNT", 4, 45.0)]
    erkennen_und_buchen(j, versant(4), pos, ticker_je_conid=tab)
    km.bestaetigen(j, "CA:66")
    assert km.buchen(j, ["fundamental_a"], pos, [], fx=FX, ticker_je_conid=tab, schlusskurse=kurse())[0].ok


def test_erinnerung_bis_zur_conid_dann_verkauf_nachgeholt(j, monkeypatch):
    from tradingbot.betrieb.tageslauf import _tochter_ohne_conid_pruefen
    _gebuchte_tochter(j, {800: "CMCSA"})
    j.zustand_speichern("fundamental_a", {"ziel": {}, "verkauf_gesperrt": ["VSNT"]})
    laden = lambda t, tag, art: pd.DataFrame({"close": [46.0]}, index=[pd.Timestamp("2026-11-12")])  # noqa: E731
    monkeypatch.setattr(km, "_ticker_je_conid", lambda: {800: "CMCSA"})
    erg = _Erg()
    assert _tochter_ohne_conid_pruefen(j, "fundamental_a", pd.Timestamp("2026-11-12"), laden, 1.10, erg) == []
    assert any("Verkauf der Tochter VSNT steht an" in x and "Erinnerung" in x for x in erg.sofort)
    assert any("ohne Conid in config/kontrakte.yaml" in x and "Buch läuft weiter" in x for x in erg.meldungen)
    monkeypatch.setattr(km, "_ticker_je_conid", lambda: TAB)                    # Jakob hat die Conid übernommen
    erg = _Erg()
    v = _tochter_ohne_conid_pruefen(j, "fundamental_a", pd.Timestamp("2026-11-13"), laden, 1.10, erg)
    assert len(v) == 1 and v[0].vorschlag.ticker == "VSNT" and v[0].vorschlag.richtung < 0 and v[0].vorschlag.stueck == 4
    assert erg.sofort == [] and "Verkauf nachgeholt" in v[0].vorschlag.these
