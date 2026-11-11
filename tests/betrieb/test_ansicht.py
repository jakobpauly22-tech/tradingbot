"""Ansichtsschicht der neuen Oberfläche (Jakob 10.11.2026): Ampel, Übersicht je Buch, Vorschlagszeilen, Meldungen."""
from datetime import date, datetime

import pandas as pd
import pytest

from tradingbot.betrieb import ansicht
from tradingbot.betrieb.buecher import BuchVorschlag
from tradingbot.betrieb.journal import Journal
from tradingbot.betrieb.tageslauf import Laufergebnis
from tradingbot.konfiguration import lade_konfiguration
from tradingbot.risiko.manager import OrderVorschlag, Urteil

READ_ONLY = {"verbunden": True, "konto": "DUR3…", "schreiben": False, "grund": "Read-Only im Gateway ist aktiv (Fehler 321 auf eine reine Abfrage)",
             "geprueft": datetime(2026, 11, 10, 19, 0)}
FREI = {**READ_ONLY, "schreiben": True, "grund": "Schreibzugriff im Gateway geprüft"}


def betrieb(alle_an=True):
    b = lade_konfiguration("betrieb")
    b["ibkr"] = {**b["ibkr"], "senden_freigeschaltet": True}
    b["buecher"] = {n: {**bk, "senden_freigeschaltet": alle_an or n == "real"} for n, bk in b["buecher"].items()}
    return b


def vorschlag(i, buch, ticker="SXR1.DE", art="etf", richtung=1, frei=True, waehrung="EUR"):
    v = OrderVorschlag(f"{buch}-{i}", pd.Timestamp("2026-11-10"), buch, ticker, richtung, 3, 100.0, art, limit=102.0, these="These eins. Zwei.")
    bv = BuchVorschlag(v, waehrung, 102.0)
    bv.kern = f"Kern {i}"
    return bv, Urteil(frei, [] if frei else ["Test-Veto"])


def erg_mit(vs=(), jetzt=datetime(2026, 11, 10, 19, 0)):
    e = Laufergebnis(jetzt, vorschlaege=list(vs), meldungen=["Test"])
    e.xetra, e.nyse = date(2026, 11, 10), date(2026, 11, 7)
    return e


@pytest.fixture
def journal(tmp_path):
    j = Journal(tmp_path / "journal.sqlite")
    for n, bk in lade_konfiguration("betrieb")["buecher"].items():
        j.buch_anlegen(n, float(bk["budget_eur"]))
    yield j
    j.schliessen()


def lampe(lampen, name):
    return next(la for la in lampen if la.name == name)


# --- Ampel -------------------------------------------------------------------------------------------------------------
def test_ampel_read_only_rot_und_senden_gesperrt(journal):
    lampen = ansicht.ampel(erg_mit(), journal, betrieb(), probe=False, gateway=READ_ONLY, jetzt=datetime(2026, 11, 10, 22, 10))
    assert lampe(lampen, "Schreibzugriff").farbe == ansicht.ROT and lampe(lampen, "Schreibzugriff").text.startswith("Read-Only an")
    assert lampe(lampen, "Gateway").farbe == ansicht.GRUEN and "DUR3…" in lampe(lampen, "Gateway").text
    assert ansicht.senden_erlaubt(READ_ONLY, False) == (False, ansicht.READ_ONLY_HINWEIS)
    assert ansicht.senden_erlaubt(FREI, False) == (True, "")
    gruen = ansicht.ampel(erg_mit(), journal, betrieb(), probe=False, gateway=FREI, jetzt=datetime(2026, 11, 10, 22, 10))
    assert lampe(gruen, "Schreibzugriff").farbe == ansicht.GRUEN


def test_ampel_ohne_gateway_probe_und_stopp(journal):
    aus = {"verbunden": False, "schreiben": None, "grund": "kein Gateway"}
    lampen = ansicht.ampel(erg_mit(), journal, betrieb(), probe=False, gateway=aus, jetzt=datetime(2026, 11, 10, 19, 0))
    assert lampe(lampen, "Gateway").farbe == ansicht.ROT and lampe(lampen, "Schreibzugriff").farbe == ansicht.GRAU
    assert not ansicht.senden_erlaubt(aus, False)[0]
    probe = ansicht.ampel(erg_mit(), journal, betrieb(), probe=True, gateway=aus, jetzt=datetime(2026, 11, 10, 10, 0))
    assert lampe(probe, "Modus").farbe == ansicht.ORANGE and lampe(probe, "Freigabefenster").text == "Probe: jederzeit"
    # Probe sperrt wie der echte Lauf (Jakob 10.11.2026), damit die Sperre testbar ist
    assert not ansicht.senden_erlaubt(aus, True)[0] and ansicht.senden_erlaubt(READ_ONLY, True) == (False, ansicht.READ_ONLY_HINWEIS)
    assert ansicht.senden_erlaubt(FREI, True) == (True, "")
    assert not ansicht.senden_erlaubt(FREI, False, gestoppt="Abgleich weicht ab")[0]


def test_ampel_freigabefenster_uhrzeit_und_senden_je_buch(journal):
    us = [vorschlag(1, "fundamental_a", "DPZ", "aktie", waehrung="USD")]
    b = betrieb(alle_an=False)
    frueh = ansicht.ampel(erg_mit(us), journal, b, probe=False, gateway=FREI, jetzt=datetime(2026, 11, 10, 17, 0))
    assert lampe(frueh, "Freigabefenster").farbe == ansicht.GRAU
    abend = ansicht.ampel(erg_mit(us), journal, b, probe=False, gateway=FREI, jetzt=datetime(2026, 11, 10, 21, 30))
    assert lampe(abend, "Freigabefenster").farbe == ansicht.GRUEN and lampe(abend, "Uhrzeit US/FX").farbe == ansicht.GELB
    spaet = ansicht.ampel(erg_mit(us), journal, b, probe=False, gateway=FREI, jetzt=datetime(2026, 11, 10, 22, 10))
    assert lampe(spaet, "Uhrzeit US/FX").farbe == ansicht.GRUEN
    assert lampe(spaet, "Senden real").text == "an" and lampe(spaet, "Senden momentum").text == "aus"
    assert lampe(spaet, "Datenstand").text.startswith("Schlusskurse Xetra 10.11., NYSE 07.11.")


def test_letzter_tageslauf_gelb_bei_verpassten_tagen(journal):
    journal.ereignis("tageslauf", "4 Vorschläge, Befunde in []; Xetra 03.11.2026, NYSE 03.11.2026", jetzt=datetime(2026, 11, 3, 22, 8))
    la = lampe(ansicht.ampel(erg_mit(), journal, betrieb(), probe=False, gateway=FREI, jetzt=datetime(2026, 11, 10, 19, 0)), "Letzter Tageslauf")
    assert la.farbe == ansicht.GELB and "4 Handelstag(e) ohne Lauf: 04.11., 05.11., 06.11., 09.11." in la.text and "03.11. 22:08" in la.text
    journal.ereignis("tageslauf", "x; Xetra 09.11.2026, NYSE 07.11.2026", jetzt=datetime(2026, 11, 9, 22, 7))
    la = lampe(ansicht.ampel(erg_mit(), journal, betrieb(), probe=False, gateway=FREI, jetzt=datetime(2026, 11, 10, 19, 0)), "Letzter Tageslauf")
    assert la.farbe == ansicht.GRUEN
    # der Lauf von heute (nach Beginn des aktuellen Laufs eingetragen) zählt nicht als „letzter“
    journal.ereignis("tageslauf", "y; Xetra 10.11.2026, NYSE 07.11.2026", jetzt=datetime(2026, 11, 10, 19, 5))
    la = lampe(ansicht.ampel(erg_mit(), journal, betrieb(), probe=False, gateway=FREI, jetzt=datetime(2026, 11, 10, 19, 6)), "Letzter Tageslauf")
    assert "09.11. 22:07" in la.text


# --- Entwicklung gegen SPYI (TWR) --------------------------------------------------------------------------------------
def test_rendite_buch_und_spyi_twr():
    einz = pd.Series({pd.Timestamp("2026-11-03"): 10_000.0})
    werte = pd.Series({pd.Timestamp("2026-11-04"): 10_100.0, pd.Timestamp("2026-11-05"): 10_200.0})
    assert ansicht.rendite_seit_messbeginn(werte, einz) == pytest.approx(0.02)
    spyi = pd.Series({pd.Timestamp("2026-11-02"): 99.0, pd.Timestamp("2026-11-03"): 100.0, pd.Timestamp("2026-11-05"): 103.0})
    assert ansicht.rendite_spyi(spyi, einz, "2026-11-05") == pytest.approx(0.03)        # ab Schluss am Messbeginn


def test_twr_mit_weiterer_einzahlung():
    """Realbuch (Jakob 10.11.2026): gleiche Einzahlungen wie im Buch, TWR. SPYI 100 → 110 → 121: TWR 21 %, unabhängig von
    der zweiten Einzahlung; das Buch mit derselben Entwicklung ebenfalls 21 %."""
    einz = pd.Series({pd.Timestamp("2026-11-03"): 500.0, pd.Timestamp("2026-11-05"): 500.0})
    spyi = pd.Series({pd.Timestamp("2026-11-03"): 100.0, pd.Timestamp("2026-11-05"): 110.0, pd.Timestamp("2026-11-07"): 121.0})
    assert ansicht.rendite_spyi(spyi, einz, "2026-11-07") == pytest.approx(0.21)
    werte = pd.Series({pd.Timestamp("2026-11-05"): 500 * 1.1 + 500, pd.Timestamp("2026-11-07"): (500 * 1.1 + 500) * 1.1})
    assert ansicht.rendite_seit_messbeginn(werte, einz) == pytest.approx(0.21)
    assert ansicht.rendite_spyi(None, einz, "2026-11-07") is None and ansicht.rendite_seit_messbeginn(werte, pd.Series(dtype=float)) is None


def test_buchuebersicht(journal):
    journal.messbeginn_setzen("crossover", "2026-11-03")
    journal.ausfuehrung("e1", "crossover:x1", "SXR1.DE", 1, 10, 218.10, 3.0, "2026-11-04", gebuehr_modell_eur=1.25)
    journal.ausfuehrung("e2", "crossover:x2", "IUSA.DE", 1, 36, 67.39, 3.0, "2026-11-04", gebuehr_modell_eur=1.25)
    journal.buchwert_speichern("crossover", "2026-11-05", 10_050.0, 7_384.0, 10_053.5)
    journal.vorschlag_speichern(OrderVorschlag("crossover-y", pd.Timestamp("2026-11-05"), "crossover", "EUNK.DE", 1, 11, 107.0, "etf",
                                               limit=109.0, these="t"), Urteil(True, []), waehrung="EUR", freigabe_bis="2026-11-05T23:59:59",
                                jetzt=datetime(2026, 11, 5, 22, 0))
    journal.status_setzen("crossover-y", "gesendet", order_id="51")
    e = erg_mit()
    e.xetra = date(2026, 11, 5)
    e.kurse_eur = {"SXR1.DE": 220.0, "IUSA.DE": 68.0}
    e.spyi = pd.Series({pd.Timestamp("2026-11-03"): 11.60, pd.Timestamp("2026-11-05"): 11.716})
    k = next(x for x in ansicht.buchuebersicht(journal, betrieb(), e) if x.buch == "crossover")
    assert k.wert == 10_050.0 and k.wert_modell == 10_053.5 and k.wert_tag == "2026-11-05"
    assert k.rendite == pytest.approx(0.005) and k.rendite_spyi == pytest.approx(0.01)
    assert [p.ticker for p in k.positionen] == ["IUSA.DE", "SXR1.DE"]
    sxr1 = k.positionen[1]
    assert sxr1.kaufkurs == pytest.approx(218.10) and sxr1.wert_eur == pytest.approx(2_200.0)
    assert k.offene[0]["order_id"] == "51" and k.offene[0]["art"] == "KAUF" and k.reserviert["EUR"] == pytest.approx(11 * 109.0 * 1.01)
    leer = next(x for x in ansicht.buchuebersicht(journal, betrieb(), e) if x.buch == "momentum")
    assert leer.messbeginn is None and leer.rendite is None and leer.positionen == []


# --- Vorschlagszeilen und Meldungen -----------------------------------------------------------------------------------
def test_vorschlagszeilen_waehlbar_wie_bisher():
    vs = [vorschlag(1, "real", "SPYI.DE"), vorschlag(2, "crossover"), vorschlag(3, "crossover", frei=False), vorschlag(4, "momentum")]
    z = {x.id: x for x in ansicht.vorschlagszeilen(erg_mit(vs), betrieb(alle_an=False), probe=False)}
    assert z["real-1"].waehlbar and z["real-1"].freigabe == "einzeln"
    assert not z["crossover-2"].waehlbar and z["crossover-2"].gesperrt                       # Buch nicht freigeschaltet
    assert not z["crossover-3"].waehlbar and z["crossover-3"].veto == "Test-Veto"
    z = {x.id: x for x in ansicht.vorschlagszeilen(erg_mit(vs), betrieb(alle_an=False), probe=True)}
    assert z["crossover-2"].waehlbar and z["crossover-2"].freigabe == "sammel"              # Probe: alle Bücher
    assert not z["crossover-3"].waehlbar                                                     # Veto nie
    assert "Kern: Kern 2" in z["crossover-2"].details and z["real-1"].limit == "102.00 EUR"


@pytest.mark.parametrize("text, art", [
    ("GESTOPPT: Abgleich mit IBKR weicht ab", "fehler"),
    ("crossover-1: von IBKR ABGELEHNT (Order 49) – 321", "fehler"),
    ("Read-Only im Gateway ist aktiv – bitte ausschalten und Tageslauf neu starten", "fehler"),
    ("Journal NICHT gesichert: JOURNAL_BACKUP_DIR fehlt in .env", "fehler"),
    ("Gateway nicht verbunden (ConnectionRefusedError) – Vorschläge aus dem Journal", "fehler"),
    ("(kein Abbruch) Gateway-Meldung 321: Fehler bei der Validierung", "hinweis"),
    ("HINWEIS Zeitpunkt: 39 US-Käufe mit Limit-On-Open", "hinweis"),
    ("2 nicht ausgeführte Order(s) verfallen", "hinweis"),
    ("Abgleich: Bestände aller Bücher stimmen mit IBKR überein (5 Positionen in den Büchern)", "ok"),
    ("fundamental_a-1: von IBKR angenommen (Order 55, PreSubmitted)", "ok"),
    ("Journal gesichert: journal_2026-11-10.sqlite", "ok"),
    ("real: Buchwert wie gebucht (Paper, Festpreis) 491.70 €", "info"),
])
def test_meldungsart(text, art):
    assert ansicht.meldungsart(text) == art


class GatewayAttrappe:
    def __init__(self, verbunden=True, schreiben=(False, "Read-Only im Gateway ist aktiv (Fehler 321)"), fehler=None):
        self._v, self._s, self._f = verbunden, schreiben, fehler

    def verbunden(self):
        return self._v

    def verbinden(self):
        if self._f:
            raise self._f

    def konto_id(self):
        return "DUR3123456"

    def schreibzugriff(self):
        return self._s


def test_gateway_status():
    s = ansicht.gateway_status(GatewayAttrappe())
    assert s["verbunden"] and s["konto"] == "DUR3…" and s["schreiben"] is False
    assert ansicht.gateway_status(GatewayAttrappe(schreiben=(True, "ok")))["schreiben"] is True
    s = ansicht.gateway_status(GatewayAttrappe(verbunden=False, fehler=ConnectionRefusedError()))
    assert not s["verbunden"] and "ConnectionRefusedError" in s["grund"]
    assert ansicht.gateway_status(None)["grund"] == "kein Gateway"


def test_rendite_ohne_buchwerte():
    einz = pd.Series({pd.Timestamp("2026-11-09"): 10_000.0})
    assert ansicht.rendite_seit_messbeginn(pd.Series(dtype=float), einz) == 0.0



# --- Namen und gegliederte Details (Jakob 10.11.2026) ---------------------------------------------------------------------
def test_anzeigename():
    assert ansicht.anzeigename("EUNN.DE") == "iShares Core MSCI Japan IMI (EUNN)"          # ETF-Name aus config/technik.yaml
    assert ansicht.anzeigename("SPYI.DE").endswith("(SPYI)") and ansicht.anzeigename("SPYI.DE").startswith("SPDR")
    assert ansicht.anzeigename("XYZ999") == "XYZ999"
    assert ansicht._ohne_rechtsform("Domino's Pizza, Inc.") == "Domino's Pizza"
    assert ansicht._ohne_rechtsform("Brown-Forman Corporation") == "Brown-Forman"
    assert ansicht._ohne_rechtsform("Transocean Ltd.") == "Transocean"


def _fundamental_zeile():
    return pd.Series({"gesamt": 0.81, "qualitaet": 0.9, "bewertung": 0.7, "accruals": -0.05, "ep": 0.05, "ebit_ev": 0.09,
                      "piotroski_filter": 8, "altman_zone": "grau", "altman": 2.1, "altman_variante": "Z''", "beneish": -1.5,
                      "marktwert_usd": 12e9, "sic": 5812})


def test_gliederung_fundamental():
    from tradingbot.betrieb.buecher import kennzahlen_fundamental
    med = pd.Series({"accruals": -0.02, "ep": 0.04, "ebit_ev": 0.10})
    bv, u = vorschlag(1, "fundamental_a", "DPZ", "aktie", waehrung="USD")
    bv.daten = kennzahlen_fundamental(_fundamental_zeile(), med, "A", 3)
    bv.details = ("Zahlen:\n  • Kurs 340 USD\nWas dagegen spricht:\n  • Median-Ersatz für: ebit_ev\nWiderlegt, wenn: Rang über 30\n"
                  "IBKR-Kontrakt: conId 29831612, Symbol DPZ, Routing SMART/NASDAQ, USD")
    u = Urteil(True, [], ["hätte gesperrt: Monatslimit"])
    g = ansicht.gliederung(bv, u)
    k = {name: (wert, median, urteil) for name, wert, median, urteil in g["kennzahlen"]}
    assert k["Accruals (niedriger besser)"][2] is True and k["KGV (niedriger besser)"] == ("20,0", "25,0", True)
    assert k["EBIT/EV (höher besser)"][2] is False
    assert {n: f for n, _, f in g["filter"]} == {"Piotroski": "gruen", "Altman": "gelb", "Beneish": "rot"}
    assert g["dagegen"] == ["Median-Ersatz für: ebit_ev", "Risk-Manager: hätte gesperrt: Monatslimit"]
    assert g["widerlegt"] == "Rang über 30" and g["technisch"][0].startswith("IBKR-Kontrakt: conId 29831612")
    assert g["art"] == "KAUF" and "fundamental_a · KAUF 3 Stück · Limit 102.00 USD" in g["kopf"]


def test_gliederung_technik():
    bv, u = vorschlag(1, "crossover", "EUNK.DE")
    bv.daten = {"typ": "technik", "kurs": 107.06, "sma50": 104.21, "sma200": 101.40, "abstand": 0.0277, "mom": 0.138, "atr": 1.12,
                "stop": 104.82, "max_verlust": 47.08, "max_verlust_anteil": 0.0047}
    bv.details = "Zahlen:\n  • Schluss 107,06 €\nWas dagegen spricht:\n  • nichts Besonderes\nWiderlegt, wenn: Schluss unter dem Stop"
    g = ansicht.gliederung(bv, u)
    k = {name: (wert, urteil) for name, wert, _, urteil in g["kennzahlen"]}
    assert k["Kurs (Schluss)"][0] == "107,06 €" and k["SMA50"][0] == "104,21 €" and k["SMA200"][0] == "101,40 €"
    assert k["Abstand SMA50 zu SMA200"] == ("+2,8%", True) and k["Stop (2 × ATR)"][0] == "104,82 €"
    assert k["Max. Verlust bis Stop"][0].startswith("47,08 €") and k["Max. Verlust bis Stop"][1] is True
    assert g["dagegen"] == [] and g["zahlen"] == []



def test_gliederung_technik_verkauf_urteil_bezogen_auf_aktion():
    """Verkauf (Jakob 11.11.2026): Auslöser mit Stop, Schluss am Auslösetag und Datum; ✓ = spricht für den Verkauf."""
    from tradingbot.betrieb.buecher import details_text
    bv, u = vorschlag(1, "crossover", "EUNN.DE", richtung=-1)
    bv.daten = {"typ": "technik", "aktion": "verkauf", "ausstieg": "stop", "grund": "Stop 69.04", "regel": "crossover",
                "ausloese_tag": "2026-11-06", "nachgeholt": True, "kurs": 70.27, "sma50": 68.5, "sma200": 66.0,
                "abstand": 0.0379, "mom": 0.12, "stop_kurs": 69.04, "schluss_ausloese": 68.80, "bestand_wert": 2108.1}
    bv.details = details_text(["Auslöser: Stop 69.04 am 06.11.2026 (nachgeholt)"],
                              ["Kurs liegt inzwischen wieder über dem Stop (70,27 > 69,04 €); Verkauf folgt der Regel "
                               "'verpasste Stops nachholen'", "Trend intakt (SMA50 > SMA200, Abstand 3,8%)"], "– (Ausstiege sind immer erlaubt)")
    g = ansicht.gliederung(bv, u)
    k = {name: (wert, urteil) for name, wert, _, urteil in g["kennzahlen"]}
    assert g["art"] == "VERKAUF" and k["Auslöser"][0] == "Stop 69.04 am 06.11.2026 (nachgeholt)"
    assert k["Stop (2 × ATR)"][0] == "69,04 €"
    assert k["Schluss am Auslösetag (06.11.2026)"] == ("68,80 €", True)        # unter dem Stop: spricht für den Verkauf
    assert k["Kurs (Schluss heute)"] == ("70,27 €", False)                     # wieder über dem Stop: spricht dagegen
    assert k["Abstand SMA50 zu SMA200"] == ("+3,8%", False) and k["Momentum 12−1"][1] is False
    assert g["dagegen"][0].startswith("Kurs liegt inzwischen wieder über dem Stop (70,27 > 69,04 €)")
    # Signalende Momentum: 12−1 ≤ 0 spricht für den Verkauf
    bv.daten = {"typ": "technik", "aktion": "verkauf", "ausstieg": "signal", "grund": "12−1 ≤ 0", "regel": "momentum",
                "ausloese_tag": "2026-12-01", "nachgeholt": False, "kurs": 50.0, "sma50": 49.0, "sma200": 51.0,
                "abstand": -0.039, "mom": -0.02}
    k = {name: (wert, urteil) for name, wert, _, urteil in ansicht.gliederung(bv, u)["kennzahlen"]}
    assert k["Momentum 12−1"] == ("-2,0%", True) and k["Abstand SMA50 zu SMA200"][1] is True and "Stop (2 × ATR)" not in k


def _positionen_journal(journal):
    journal.messbeginn_setzen("crossover", "2026-11-03")
    journal.ausfuehrung("c1", "crossover:a", "SXR1.DE", 1, 10, 218.10, 3.0, "2026-11-04")
    journal.ausfuehrung("c2", "crossover:b", "IUSA.DE", 1, 36, 67.39, 3.0, "2026-11-04")
    journal.zustand_speichern("crossover", {"signaltag": "2026-11-09", "nach": {"positionen": {
        "SXR1.DE": {"regel": "crossover", "signal_tag": "2026-11-03", "kauf_tag": "2026-11-04", "stop": 214.48, "atr_signal": 1.7},
        "IUSA.DE": {"regel": "crossover", "signal_tag": "2026-11-03", "kauf_tag": None, "stop": None, "atr_signal": 0.6}}}})
    journal.ausfuehrung("f1", "fundamental_a:a", "DPZ", 1, 1, 300.0, 1.0, "2026-11-10 14:30:00+00:00", waehrung="USD", preis=340.0)
    journal.ausfuehrung("f2", "fundamental_a:b", "BBY", 1, 5, 90.0, 1.0, "2026-11-10 14:30:00+00:00", waehrung="USD", preis=102.0)
    e = erg_mit()
    e.kurse_eur = {"SXR1.DE": 220.0, "IUSA.DE": 68.0, "DPZ": 310.0, "BBY": 88.0}
    e.fx = {"USD": 1.15}
    return e


def test_positionen_je_buch(journal):
    e = _positionen_journal(journal)
    karten = {k.buch: k for k in ansicht.buchuebersicht(journal, betrieb(), e)}
    c = karten["crossover"]
    assert c.technik and not karten["fundamental_a"].technik
    assert [p.ticker for p in c.positionen] == ["IUSA.DE", "SXR1.DE"]                      # Wert absteigend
    iusa, sxr1 = c.positionen
    assert iusa.name == "iShares Core S&P 500 (IUSA)" and iusa.kurs == pytest.approx(68.0) and iusa.waehrung == "EUR"
    assert iusa.einstand_eur == pytest.approx(36 * 67.39 + 3.0) and iusa.gv_eur == pytest.approx(36 * 68.0 - (36 * 67.39 + 3.0))
    assert iusa.gv_proz == pytest.approx(iusa.gv_eur / iusa.einstand_eur)
    buchwert = journal.kasse("crossover") + 36 * 68.0 + 10 * 220.0
    assert iusa.anteil == pytest.approx(36 * 68.0 / buchwert) and iusa.gekauft_am == "2026-11-04"
    assert sxr1.stop == pytest.approx(214.48) and iusa.stop is None
    dpz = next(p for p in karten["fundamental_a"].positionen if p.ticker == "DPZ")
    assert dpz.kurs == pytest.approx(310.0 * 1.15) and dpz.waehrung == "USD" and dpz.kaufkurs == pytest.approx(340.0)
    assert dpz.gv_eur == pytest.approx(9.0) and dpz.stop is None and dpz.gekauft_am == "2026-11-10"
    bby = next(p for p in karten["fundamental_a"].positionen if p.ticker == "BBY")
    assert bby.gv_eur == pytest.approx(5 * 88.0 - (5 * 90.0 + 1.0)) and bby.gv_eur < 0
