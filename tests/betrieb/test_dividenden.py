"""Bardividenden mit Quellensteuer (A0, Jakob 12.11.2026): nachgestellte Flex-Fälle, Aufteilung nach Bestand vor dem
Ex-Tag, Vormerkung über AccruedDividend am Zahltag, Frist, Abweichung, Rücknahme „vermutet“-Übernahmen, Prüfung
brutto/netto, Dividende und Zinsgutschrift am selben Tag.

Die Fälle sind nachgestellt (Beträge frei gewählt, Format wie die Flex-Bargeldtransaktionen des Paper-Kontos)."""
import copy
from datetime import date

import pytest
from test_tageslauf import KontoAttrappe, lauf, umgebung  # noqa: F401

from tradingbot.betrieb import benachrichtigung as bn
from tradingbot.betrieb import dividenden as dv
from tradingbot.betrieb.journal import Journal
from tradingbot.betrieb.tageslauf import kassenabgleich

KO, ETF = 8894, 4242
TICKER = {KO: "KO", ETF: "EXSA.DE"}
FX = {"USD": 1.16}
TOL = 0.05


@pytest.fixture
def journal(tmp_path):
    j = Journal(tmp_path / "journal.sqlite")
    for n in ("a", "b"):
        j.buch_anlegen(n, 10_000.0)
    yield j
    j.schliessen()


def kauf(j, buch, ticker, stueck, tag, waehrung="USD", preis=60.0):
    j.db.execute("INSERT INTO ausfuehrungen (exec_id, order_ref, buch, ticker, richtung, stueck, preis_eur, gebuehr_eur, zeit, waehrung, preis) "
                 "VALUES (?,?,?,?,?,?,?,?,?,?,?)", (f"{buch}-{ticker}-{tag}-{stueck}", f"{buch}:x", buch, ticker, 1, stueck,
                                                    preis / FX.get(waehrung, 1.0), 0.0, f"{tag}T15:35:00", waehrung, preis))
    j.db.commit()


def zeile(tid, typ, betrag, *, conid=KO, waehrung="USD", ex="20261114", zahl="20261201", satz="0.51", action="A1", sym="KO"):
    beschreibung = f"{sym}(US1912161007) CASH DIVIDEND {waehrung} {satz} PER SHARE" + (" - US TAX" if typ == "Withholding Tax" else
                                                                                         " (Ordinary Dividend)")
    return {"transactionID": tid, "type": typ, "amount": str(betrag), "currency": waehrung, "conid": str(conid), "symbol": sym,
            "exDate": ex if typ != "Withholding Tax" else "", "dateTime": zahl, "description": beschreibung, "actionID": action,
            "levelOfDetail": "DETAIL"}


def ko_bestand(j):
    """Buch a 10 KO, Buch b 6 KO vor dem Ex-Tag 14.11. und 4 KO am Ex-Tag (ohne Anspruch)."""
    kauf(j, "a", "KO", 10, "2026-11-10")
    kauf(j, "b", "KO", 6, "2026-11-10")
    kauf(j, "b", "KO", 4, "2026-11-14")


def buchen(j, zeilen):
    return dv.verbuchen(j, ["a", "b"], dv.belege_aus_flex(zeilen), ticker_je_conid=TICKER, fx=FX, toleranz=TOL, quelle="Flex Test")


def summe(j, buch, waehrung="USD"):
    return round(sum(z["betrag"] for z in j.kassenbuchungen("buch=? AND waehrung=?", (buch, waehrung))), 2)


# --- Buchung aus Flex ---------------------------------------------------------------------------------------------------
def test_us_dividende_mit_quellensteuer_auf_zwei_buecher_kauf_am_ex_tag_ohne_anspruch(journal):
    ko_bestand(journal)
    usd_vorher = journal.kasse_je_waehrung("b").get("USD", 0.0)
    v = buchen(journal, [zeile("T1", "Dividends", 8.16), zeile("T2", "Withholding Tax", -1.22)])
    assert v.stopp == []
    assert summe(journal, "a") == round(5.10 - 0.76, 2) and summe(journal, "b") == round(3.06 - 0.46, 2)
    assert round(summe(journal, "a") + summe(journal, "b"), 2) == round(8.16 - 1.22, 2)       # Summe stimmt auf den Cent
    b_zeilen = journal.kassenbuchungen("buch='b' AND art='dividende'")
    assert b_zeilen[0]["stueck"] == 6 and b_zeilen[0]["ex_tag"] == "2026-11-14" and b_zeilen[0]["zahltag"] == "2026-12-01"
    assert all("zu prüfen" in z["steuer"] for z in journal.kassenbuchungen())
    assert abs(journal.kasse_je_waehrung("b")["USD"] - (usd_vorher + 2.60)) < 1e-9             # Originalwährung
    assert abs(journal.kasse("a") - (10_000 - 10 * 60 / 1.16 + round(4.34 / 1.16, 2))) < 0.02  # Eurowert zum Kurs des Laufs
    assert journal.db.execute("SELECT COUNT(*) FROM ereignisse WHERE art='dividende'").fetchone()[0] == 4


def test_zweiter_lauf_bucht_nichts_doppelt(journal):
    ko_bestand(journal)
    zeilen = [zeile("T1", "Dividends", 8.16), zeile("T2", "Withholding Tax", -1.22)]
    buchen(journal, zeilen)
    v = buchen(journal, zeilen)
    assert v.gebucht == [] and v.stopp == [] and len(journal.kassenbuchungen()) == 4


def test_storno_und_neubuchung_der_quellensteuer(journal):
    ko_bestand(journal)
    buchen(journal, [zeile("T1", "Dividends", 8.16), zeile("T2", "Withholding Tax", -1.22)])
    v = buchen(journal, [zeile("T3", "Withholding Tax", 1.22, zahl="20261205"), zeile("T4", "Withholding Tax", -1.23, zahl="20261205")])
    assert v.stopp == []                                       # Zuordnung über actionID, gleiche Stückaufteilung wie die Dividende
    assert round(summe(journal, "a") + summe(journal, "b"), 2) == round(8.16 - 1.23, 2)
    assert {z["stueck"] for z in journal.kassenbuchungen("beleg_id='T4'")} == {10, 6}


def test_probe_stimmt_nicht_keine_buchung_und_stopp(journal):
    ko_bestand(journal)
    v = buchen(journal, [zeile("T1", "Dividends", 9.00), zeile("T2", "Withholding Tax", -1.35)])
    assert journal.kassenbuchungen() == []
    assert any("Probe stimmt nicht" in s and "16 Stück × 0.51 = 8.16" in s for s in v.stopp)
    assert any("ohne gebuchte Dividende" in s for s in v.stopp)
    text = dv.stopptext(dv.Klaerung(), v.stopp)
    assert bn.stopp_kurz(text) == "Dividendenbeleg nicht verbuchbar; betroffen: KO"


def test_kein_buch_hielt_den_titel(journal):
    kauf(journal, "a", "KO", 10, "2026-11-14")                  # erst am Ex-Tag gekauft
    v = buchen(journal, [zeile("T1", "Dividends", 5.10)])
    assert v.stopp and "kein Buch hielt" in v.stopp[0] and journal.kassenbuchungen() == []


def test_ausschuettender_etf_in_eur_ohne_quellensteuer(journal):
    kauf(journal, "a", "EXSA.DE", 20, "2026-11-02", waehrung="EUR", preis=50.0)
    eur_vorher = journal.kasse_je_waehrung("a")["EUR"]
    v = buchen(journal, [zeile("E1", "Dividends", 6.00, conid=ETF, waehrung="EUR", satz="0.30", sym="EXSA", action="A9")])
    assert v.stopp == [] and summe(journal, "a", "EUR") == 6.00
    assert abs(journal.kasse_je_waehrung("a")["EUR"] - (eur_vorher + 6.00)) < 1e-9
    assert journal.kassenbuchungen()[0]["betrag_eur"] == 6.00


def test_andere_bargeldarten_bleiben_beim_kassenabgleich():
    belege = dv.belege_aus_flex([{"transactionID": "X", "type": "Deposits/Withdrawals", "amount": "1000", "currency": "EUR"},
                                 {"transactionID": "Y", "type": "Broker Interest Received", "amount": "1.5", "currency": "USD"}])
    assert belege == []


# --- Kassenabgleich am Zahltag ----------------------------------------------------------------------------------------
class Konto:
    def __init__(self, kasse, zinsen=None, dividenden=None):
        self.kasse, self.zinsen, self.dividenden = kasse, zinsen or {}, dividenden or {}

    def kasse_je_waehrung(self):
        return dict(self.kasse)

    def aufgelaufene_zinsen(self):
        return dict(self.zinsen)

    def aufgelaufene_dividenden(self):
        return dict(self.dividenden)


def konfig(scharf=True, ausweis="netto"):
    return {"sicherheit": {"abgleich_kasse_toleranz": TOL, "abgleich_buchung_ohne_buchbezug_max": 10.0},
            "dividenden": {"vormerkung": scharf, "accrued_dividend_ausweis": ausweis, "vormerkung_frist_handelstage": 3},
            "buecher": {"a": {}, "b": {}}}


NETTO = round(8.16 - 1.22, 2)                                   # 6,94 USD Kassenzugang am Zahltag


def zahltag(j, b, *, zins_vorher=0.0, zins_jetzt=0.0, extra=0.0):
    """30.11. Basis mit aufgelaufener Dividende 6,94; 01.12. (Zahltag) Kasse + 6,94 (+ extra), AccruedDividend 0."""
    ko_bestand(j)
    usd = sum(j.kasse_je_waehrung(n).get("USD", 0.0) for n in ("a", "b"))
    eur = sum(j.kasse_je_waehrung(n)["EUR"] for n in ("a", "b")) - 20_000
    basis = {"EUR": 1_000_000.0 + eur, "USD": 50_000.0 + usd}
    kassenabgleich(j, ["a", "b"], Konto(basis, {"USD": zins_vorher}, {"USD": NETTO}), b, heute="2026-11-30")
    jetzt = {"EUR": basis["EUR"], "USD": basis["USD"] + NETTO + extra}
    return kassenabgleich(j, ["a", "b"], Konto(jetzt, {"USD": zins_jetzt}, {"USD": 0.0}), b, heute="2026-12-01"), jetzt


def test_vormerkung_am_zahltag_und_bestaetigung_durch_flex(journal):
    b = konfig()
    (diff, text), kasse = zahltag(journal, b)
    assert diff == [] and "Dividende vorgemerkt" in text
    assert journal.zustand("_konto")["dividende_vormerkungen"][0]["betrag"] == NETTO
    assert journal.kassenbuchungen() == []                     # kein Buchen ohne Flex-Beleg
    # Folgetag: Flex-Beleg bucht, Vormerkung aufgelöst, Kasse stimmt ohne Doppelzählung
    buchen(journal, [zeile("T1", "Dividends", 8.16), zeile("T2", "Withholding Tax", -1.22)])
    k = dv.vormerkungen_klaeren(journal, b, date(2026, 12, 2), TOL)
    assert k.stopp == {} and any("durch Flex bestätigt" in m for m in k.meldungen)
    assert journal.zustand("_konto")["dividende_vormerkungen"] == []
    diff, text = kassenabgleich(journal, ["a", "b"], Konto(kasse, {"USD": 0.0}, {"USD": 0.0}), b, heute="2026-12-02")
    assert diff == [] and "stimmt" in text


def test_vormerkung_ohne_beleg_nach_drei_handelstagen_stoppt(journal):
    b = konfig()
    zahltag(journal, b)
    k = dv.vormerkungen_klaeren(journal, b, date(2026, 12, 4), TOL)             # Mi, Do, Fr: 3 Handelstage – noch in der Frist
    assert k.stopp == {}
    k = dv.vormerkungen_klaeren(journal, b, date(2026, 12, 7), TOL)             # Mo: 4. Handelstag ohne Beleg
    text = dv.stopptext(k, [])
    assert text.startswith(dv.KAT_FRIST) and "nach 3 Handelstagen kein Flex-Beleg" in text
    assert bn.stopp_kurz(text) == "Dividende ohne Flex-Beleg nach Frist; betroffen: Kasse USD"
    assert journal.zustand("_konto")["dividende_vormerkungen"]                   # bleibt offen bis zur Klärung


def test_beleg_weicht_von_der_vormerkung_ab_stoppt(journal):
    b = konfig()
    zahltag(journal, b)
    buchen(journal, [zeile("T1", "Dividends", 8.16), zeile("T2", "Withholding Tax", -1.36)])   # netto 6,80 statt 6,94
    k = dv.vormerkungen_klaeren(journal, b, date(2026, 12, 2), TOL)
    text = dv.stopptext(k, [])
    assert text.startswith(dv.KAT_ABWEICHUNG) and "vorgemerkt 6.94" in text and "Flex netto 6.80" in text
    assert bn.stopp_kurz(text) == "Dividende weicht von der Vormerkung ab; betroffen: Kasse USD"


def test_dividende_und_zinsgutschrift_am_selben_tag(journal):
    b = konfig()
    (diff, text), _ = zahltag(journal, b, zins_vorher=1.60, zins_jetzt=0.10, extra=1.50)
    assert diff == [], diff
    konto = journal.zustand("_konto")
    assert konto["dividende_vormerkungen"][0]["betrag"] == NETTO                 # Dividende vorgemerkt
    assert "Zinsbuchung belegt" in text and "+1.50" in text                       # Zinsregel greift für den Rest
    assert abs(konto["kassenbasis"]["USD"] - (50_000.0 + 1.50)) < 1e-6           # nur die Zinsen in die Basis
    assert konto["aufgelaufene_zinsen"] == {"USD": 0.10}


def test_zins_allein_bleibt_unveraendert_bei_vormerkung_an(journal):
    b = konfig()
    ko_bestand(journal)
    usd = sum(journal.kasse_je_waehrung(n).get("USD", 0.0) for n in "ab")
    eur = sum(journal.kasse_je_waehrung(n)["EUR"] for n in "ab") - 20_000
    k0 = {"EUR": 1_000_000.0 + eur, "USD": 50_000.0 + usd}
    kassenabgleich(journal, ["a", "b"], Konto(k0, {"USD": 1.60}, {"USD": 0.0}), b, heute="2026-11-30")
    diff, text = kassenabgleich(journal, ["a", "b"], Konto({**k0, "USD": k0["USD"] + 1.60}, {"USD": 0.0}, {"USD": 0.0}), b,
                                heute="2026-12-01")
    assert diff == [] and "Zinsbuchung belegt" in text and "vorgemerkt" not in text


def test_nicht_scharf_vermutet_dann_flex_nimmt_zurueck_und_prueft_ausweis(journal):
    b = konfig(scharf=False, ausweis="unbekannt")
    (diff, text), kasse = zahltag(journal, b)
    assert diff == [] and "Buchung ohne Buchbezug" in text and "Vormerkung nicht scharf" in text
    konto = journal.zustand("_konto")
    assert "dividende_vormerkungen" not in konto and konto["dividende_abnahmen"][0]["abnahme"] == NETTO
    basis_vorher = konto["kassenbasis"]["USD"]
    buchen(journal, [zeile("T1", "Dividends", 8.16), zeile("T2", "Withholding Tax", -1.22)])
    k = dv.vormerkungen_klaeren(journal, b, date(2026, 12, 2), TOL)
    assert k.stopp == {}
    assert any("aus der Kassenbasis zurückgenommen" in m for m in k.meldungen)
    assert any("entspricht NETTO" in m and "erst nach Jakobs Entscheidung" in m for m in k.meldungen)
    konto = journal.zustand("_konto")
    assert abs(konto["kassenbasis"]["USD"] - (basis_vorher - NETTO)) < 1e-6
    assert konto["accrued_dividend_befund"]["befund"] == "netto"
    diff, text = kassenabgleich(journal, ["a", "b"], Konto(kasse, {"USD": 0.0}, {"USD": 0.0}), b, heute="2026-12-02")
    assert diff == [] and "stimmt" in text                                       # keine Doppelzählung
    k = dv.vormerkungen_klaeren(journal, b, date(2026, 12, 3), TOL)              # kein zweites Zurücknehmen
    assert k.meldungen == []


def test_ausweis_brutto_wird_erkannt(journal):
    b = konfig(scharf=False, ausweis="unbekannt")
    ko_bestand(journal)
    usd = sum(journal.kasse_je_waehrung(n).get("USD", 0.0) for n in "ab")
    eur = sum(journal.kasse_je_waehrung(n)["EUR"] for n in "ab") - 20_000
    k0 = {"EUR": 1_000_000.0 + eur, "USD": 50_000.0 + usd}
    kassenabgleich(journal, ["a", "b"], Konto(k0, {}, {"USD": 8.16}), b, heute="2026-11-30")
    kassenabgleich(journal, ["a", "b"], Konto({**k0, "USD": k0["USD"] + NETTO}, {}, {"USD": 0.0}), b, heute="2026-12-01")
    buchen(journal, [zeile("T1", "Dividends", 8.16), zeile("T2", "Withholding Tax", -1.22)])
    k = dv.vormerkungen_klaeren(journal, b, date(2026, 12, 2), TOL)
    assert any("entspricht BRUTTO" in m for m in k.meldungen)


def test_brutto_ausweis_vormerkbar_im_quellensteuerband():
    cfg = dv.einstellungen(konfig(ausweis="brutto"))
    assert dv.vormerkbar(6.94, 8.16, cfg, TOL) == 6.94
    assert dv.vormerkbar(5.00, 8.16, cfg, TOL) is None                            # mehr als 30 % Abzug
    assert dv.einstellungen(konfig(scharf=True, ausweis="unbekannt"))["scharf"] is False


# --- Meldungen ---------------------------------------------------------------------------------------------------------
def test_kurzfassung_zeigt_dividenden_vormerkung_und_kassendifferenz(journal):
    b = konfig(scharf=False, ausweis="unbekannt")
    zahltag(journal, b)                                                           # 6,94 als „vermutet“ übernommen
    buchen(journal, [zeile("T1", "Dividends", 8.16), zeile("T2", "Withholding Tax", -1.22)])
    konto = journal.zustand("_konto")
    konto["dividende_vormerkungen"] = [{"waehrung": "USD", "betrag": 2.5, "von": "2026-12-01", "bis": "2026-12-02"}]
    journal.zustand_speichern("_konto", konto)
    mit = bn.kassenzeilen(journal, eurobetraege=True, seit="2026-01-01")
    assert "Dividende KO: a 4,34 USD netto (QSt 0,76)" in mit and "Dividende KO: b 2,60 USD netto (QSt 0,46)" in mit
    assert "Dividende vorgemerkt, Flex-Beleg folgt: USD 2,50 (seit 2026-12-02)" in mit
    assert "Kassendifferenz übernommen (Zinsen/Gebühren vermutet): USD +6,94" in mit
    ohne = bn.kassenzeilen(journal, eurobetraege=False, seit="2026-01-01")
    assert "Dividende gebucht: KO (a)" in ohne and "Kassendifferenz übernommen" in ohne
    assert not any(ch.isdigit() for z in ohne for ch in z.replace("2026-12-02", ""))   # keine Beträge
    assert bn.kassenzeilen(journal, eurobetraege=True, seit="2099-01-01") == [
        "Dividende vorgemerkt, Flex-Beleg folgt: USD 2,50 (seit 2026-12-02)"]       # offene Vormerkung bleibt sichtbar


def test_ampel_hinweis_bei_offener_vormerkung(journal):
    from types import SimpleNamespace

    from tradingbot.betrieb import ansicht
    from tradingbot.konfiguration import lade_konfiguration
    from datetime import datetime

    konto = {"dividende_vormerkungen": [{"waehrung": "USD", "betrag": 6.94, "von": "2026-11-30", "bis": "2026-12-01"}]}
    journal.zustand_speichern("_konto", konto)
    erg = SimpleNamespace(vorschlaege=[], jetzt=datetime(2026, 12, 1, 19, 0), xetra=None, nyse=None, befunde={}, gestoppt=None)
    lampen = ansicht.ampel(erg, journal, copy.deepcopy(lade_konfiguration("betrieb")), probe=False, gateway={}, jetzt=erg.jetzt)
    lampe = next(l for l in lampen if l.name == "Dividenden")
    assert lampe.farbe == ansicht.GELB and "USD 6.94" in lampe.text


def test_konfiguration_vormerkung_aus_bis_zur_pruefung():
    from tradingbot.konfiguration import lade_konfiguration

    cfg = dv.einstellungen(lade_konfiguration("betrieb"))
    assert cfg["scharf"] is False and cfg["ausweis"] == "unbekannt" and cfg["frist"] == 3


# --- Tageslauf ---------------------------------------------------------------------------------------------------------
def test_tageslauf_stoppt_bei_nicht_verbuchbarem_beleg(umgebung):
    j, rm = umgebung
    lauf(j, rm)                                                               # Bücher anlegen, ohne Bestand
    zeilen = [zeile("T1", "Dividends", 5.10)]

    def flex():
        return [], "Flex Test"
    flex.bargeld = lambda: (zeilen, "Flex Test")
    e = lauf(j, rm, broker=KontoAttrappe({"EUR": 1_000_000.0}), flex=flex)
    assert e.gestoppt and e.gestoppt.startswith(dv.KAT_NICHT_VERBUCHBAR) and "kein Buch hielt" in e.gestoppt
    assert e.abgleich == "gestoppt" and j.kassenbuchungen() == []


def test_tageslauf_ohne_dividendenbeleg_laeuft_wie_bisher(umgebung):
    j, rm = umgebung
    lauf(j, rm)

    def flex():
        return [], "Flex Test"
    flex.bargeld = lambda: ([{"transactionID": "D1", "type": "Deposits/Withdrawals", "amount": "1000", "currency": "EUR"}], "Flex Test")
    e = lauf(j, rm, broker=KontoAttrappe({"EUR": 1_000_000.0}), flex=flex)
    assert e.gestoppt is None and e.abgleich == "ok"
