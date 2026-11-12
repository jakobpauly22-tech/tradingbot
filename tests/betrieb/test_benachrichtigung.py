"""Benachrichtigungen (Jakob 12.11.2026): Inhalte aus der Positivliste, Eurobeträge abschaltbar, keine Kontodaten,
Versand wirft nie, Wächter um 22:00, Sendeprobleme."""
import re
import urllib.parse
from datetime import date, datetime
from types import SimpleNamespace

import pytest

from tradingbot.betrieb import benachrichtigung as bn
from tradingbot.betrieb.journal import Journal
from tradingbot.betrieb.tageslauf import Laufergebnis

BETRIEB = {"buecher": {"real": {}, "crossover": {}}}
JETZT = datetime(2026, 11, 12, 18, 40)


@pytest.fixture
def journal(tmp_path):
    j = Journal(tmp_path / "journal.sqlite")
    j.buch_anlegen("real", 500.0)
    j.buch_anlegen("crossover", 10_000.0)
    j.buchwert_speichern("real", "2026-11-11", 505.0, 5.0, 506.0)
    j.buchwert_speichern("real", "2026-11-12", 512.34, 5.0, 513.10)
    j.buchwert_speichern("crossover", "2026-11-12", 9_876.5, 100.0, 9_880.0)
    yield j
    j.schliessen()


def vorschlag(buch, frei=True):
    return SimpleNamespace(vorschlag=SimpleNamespace(buch=buch)), SimpleNamespace(frei=frei)


def ergebnis(**kw):
    erg = Laufergebnis(JETZT, xetra=date(2026, 11, 12), nyse=date(2026, 11, 11))
    for k, v in kw.items():
        setattr(erg, k, v)
    return erg


# --- (a) Kurzfassung ----------------------------------------------------------------------------------------------
def test_kurzfassung_mit_eurobetraegen(journal):
    erg = ergebnis(abgleich="ok", vorschlaege=[vorschlag("real"), vorschlag("crossover"), vorschlag("crossover", frei=False)],
                   befunde={"crossover": ["SXR1.DE: Kurs fehlt"]})
    text = bn.kurzfassung(erg, journal, BETRIEB)
    assert text.startswith("✅ Tageslauf 12.11.2026 18:40")
    assert "Abgleich: ok" in text
    assert "Vorschläge: 3 (2 frei, 1 Veto)" in text and "crossover: 2 (1 frei, 1 Veto)" in text
    assert "Datenprüfung: crossover ohne Vorschläge (1 Befund)" in text
    assert "real: 512,34 € (+2,47 %), Modell 513,10 € (+2,62 %); Vortag +1,45 %" in text
    assert "crossover: 9.876,50 € (−1,23 %)" in text


def test_kurzfassung_ohne_eurobetraege_nur_prozente(journal):
    erg = ergebnis(abgleich="ok", vorschlaege=[vorschlag("real")])
    text = bn.kurzfassung(erg, journal, BETRIEB, eurobetraege=False)
    assert "€" not in text and "512" not in text and "9.876" not in text
    assert "real: +2,47 % (Modell +2,62 %); Vortag +1,45 %" in text


def test_stopp_ohne_stueckzahlen_und_kontokasse(journal):
    gestoppt = ("Abgleich mit IBKR weicht ab – Tageslauf gestoppt: SAP.DE: Bücher 3 Stück, IBKR 5 Stück; "
                "Kasse EUR: Bücher + Basis 990,709.16, IBKR 990,800.00 (Abweichung +90.84, über 10 €); Konto DU1234567")
    erg = ergebnis(abgleich="gestoppt", gestoppt=gestoppt)
    text = bn.kurzfassung(erg, journal, BETRIEB)
    assert text.startswith("⛔ Tageslauf GESTOPPT")
    assert "Abgleich mit IBKR weicht ab; betroffen: SAP.DE, Kasse EUR" in text
    for verboten in ("990", "Bücher 3", "IBKR 5", "DU1234567", "90,84", "90.84"):
        assert verboten not in text


def test_abgelehnte_und_verfallene_seit_dem_letzten_lauf(journal):
    journal.ereignis("tageslauf", "voriger Lauf", jetzt=datetime(2026, 11, 11, 22, 0))
    journal.db.executemany(
        "INSERT INTO vorschlaege (id, erstellt, signaltag, buch, ticker, art, waehrung, richtung, stueck, letzter_kurs_eur, frei, status, "
        "freigabe_bis, aktualisiert) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [("a1", "x", "2026-11-11", "crossover", "EUNK.DE", "etf", "EUR", 1, 10, 50.0, 1, "abgelehnt", "x", "2026-11-11T22:07:05"),
         ("a2", "x", "2026-11-10", "real", "SPYI.DE", "etf", "EUR", 1, 1, 50.0, 1, "abgelehnt", "x", "2026-11-10T22:07:05"),   # älter
         ("v1", "x", "2026-11-11", "crossover", "EURUSD", "fx", "EUR", 1, 100, 1.0, 1, "verfallen", "x", "2026-11-12T18:39:00")])
    erg = ergebnis(abgleich="ok")
    text = bn.kurzfassung(erg, journal, BETRIEB, seit=bn.vorheriger_lauf(journal, erg.jetzt))
    assert "Abgelehnt seit dem letzten Lauf: 1 (crossover EUNK.DE)" in text
    assert "Verfallen seit dem letzten Lauf: 1 (crossover Tausch)" in text
    assert "SPYI" not in text


def test_ohne_gateway_abgleich_nicht_geprueft(journal):
    assert "Abgleich: nicht geprüft" in bn.kurzfassung(ergebnis(), journal, BETRIEB)


# --- Sicherheit ---------------------------------------------------------------------------------------------------
def test_bereinigen_entfernt_konto_und_geheimnisse_behaelt_ticker():
    umgebung = {"TELEGRAM_BOT_TOKEN": "123456:ABC-geheim", "FLEX_TOKEN": "987654321098"}
    text = bn.bereinigen("Konto DU1234567, DUR3…, U7654321; DUK +1 %; Token 123456:ABC-geheim, Flex 987654321098", umgebung)
    assert "DU1234567" not in text and "DUR3" not in text and "U7654321" not in text
    assert "123456:ABC-geheim" not in text and "987654321098" not in text
    assert "DUK +1 %" in text


def test_nur_senden_kein_abruf():
    """Der Bot liest nie Nachrichten: kein getUpdates, kein Webhook im Code."""
    quelle = open(bn.__file__, encoding="utf-8").read()
    assert "sendMessage" in quelle
    for verboten in ("getUpdates\"", "getUpdates'", "/getUpdates", "setWebhook", "HTTPServer", "socket.bind"):
        assert verboten not in quelle


# --- Versand ------------------------------------------------------------------------------------------------------
class Antwort:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_telegram_sendet_an_sendmessage():
    aufrufe = []

    def oeffnen(anfrage, timeout):
        aufrufe.append((anfrage.full_url, urllib.parse.parse_qs(anfrage.data.decode()), timeout))
        return Antwort()

    bn.Telegram("123:ABC", "42", zeitlimit=3, oeffnen=oeffnen).senden("Hallo")
    url, daten, timeout = aufrufe[0]
    assert url == "https://api.telegram.org/bot123:ABC/sendMessage"
    assert daten["chat_id"] == ["42"] and daten["text"] == ["Hallo"] and timeout == 3


def test_melder_wirft_nie_und_verraet_kein_token():
    class Kaputt:
        def senden(self, text):
            raise OSError("https://api.telegram.org/bot123:ABC/sendMessage nicht erreichbar")

    zeile = bn.Melder([Kaputt()]).melden("Text")
    assert "fehlgeschlagen (OSError)" in zeile and "123:ABC" not in zeile


def test_melder_bereinigt_vor_dem_versand():
    gesendet = []
    melder = bn.Melder([SimpleNamespace(senden=gesendet.append)])
    melder.melden("Konto DU1234567")
    assert gesendet == ["Konto [entfernt]"]


def test_melder_aus_env_ohne_variablen_ohne_kanal():
    m = bn.melder_aus_env({"benachrichtigung": {"telegram": True, "healthchecks": True, "eurobetraege": False}}, umgebung={})
    assert m.kanaele == [] and m.lebenszeichen_url is None and m.eurobetraege is False
    assert "kein Kanal eingerichtet" in m.melden("x")
    assert "nicht eingerichtet" in m.lebenszeichen()


def test_melder_aus_env_schalter_aus():
    umgebung = {"TELEGRAM_BOT_TOKEN": "1:A", "TELEGRAM_CHAT_ID": "2", "HEALTHCHECKS_PING_URL": "https://hc-ping.com/abc"}
    m = bn.melder_aus_env({"benachrichtigung": {"telegram": False, "healthchecks": False}}, umgebung=umgebung)
    assert m.kanaele == [] and m.lebenszeichen_url is None


def test_lebenszeichen_und_fehlerping():
    urls = []

    def oeffnen(anfrage, timeout):
        urls.append(anfrage.full_url)
        return Antwort()

    m = bn.Melder(lebenszeichen_url="https://hc-ping.com/uuid", oeffnen=oeffnen)
    m.lebenszeichen()
    m.lebenszeichen(fehler=True)
    assert urls == ["https://hc-ping.com/uuid", "https://hc-ping.com/uuid/fail"]


def test_nach_tageslauf_meldet_und_protokolliert(journal):
    gesendet = []
    melder = bn.Melder([SimpleNamespace(senden=gesendet.append)])
    zeilen = bn.nach_tageslauf(ergebnis(abgleich="ok"), journal, BETRIEB, melder)
    assert len(gesendet) == 1 and gesendet[0].startswith("✅ Tageslauf")
    assert zeilen[0] == "Benachrichtigung: SimpleNamespace gesendet"
    assert journal.db.execute("SELECT COUNT(*) FROM ereignisse WHERE art='benachrichtigung'").fetchone()[0] == 1


def test_fehlermeldung_nur_typ():
    text = bn.fehlermeldung("Tageslauf", ValueError("Kasse 990.709,16 € auf DU1234567"), JETZT)
    assert "ValueError" in text and "990" not in text and "DU" not in text


# --- (c) Senden ---------------------------------------------------------------------------------------------------
def test_sendeprobleme(journal):
    journal.db.executemany(
        "INSERT INTO vorschlaege (id, erstellt, signaltag, buch, ticker, art, waehrung, richtung, stueck, letzter_kurs_eur, frei, status, "
        "freigabe_bis, aktualisiert) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [("s1", "x", "2026-11-12", "crossover", "EUNK.DE", "etf", "EUR", 1, 10, 50.0, 1, "abgelehnt", "x", "2026-11-12T22:07:05"),
         ("s2", "x", "2026-11-12", "crossover", "EUNN.DE", "etf", "EUR", -1, 10, 50.0, 1, "gesendet", "x", "2026-11-12T22:07:06+01:00")])
    text = bn.sendeprobleme(journal, ["s1", "s2"], "2026-11-12T22:07:00", ["s1: von IBKR ABGELEHNT – Fehler 201 …"], JETZT)
    assert text.startswith("⚠️ Senden") and "1 abgelehnt: crossover EUNK.DE" in text and "EUNN" not in text
    assert "Fehler 201" not in text
    assert bn.sendeprobleme(journal, ["s2"], "2026-11-12T22:07:00", ["s2: von IBKR angenommen"], JETZT) is None
    ro = bn.sendeprobleme(journal, [], "2026-11-12T22:07:00",
                          ["Read-Only im Gateway ist aktiv – bitte ausschalten und Tageslauf neu starten (321). Nichts gesendet"], JETZT)
    assert "Read-Only im Gateway aktiv" in ro


# --- (b) Wächter --------------------------------------------------------------------------------------------------
class Zaehler(bn.Melder):
    def __init__(self):
        super().__init__([SimpleNamespace(senden=lambda t: None)])
        self.texte, self.pings = [], 0

    def melden(self, text):
        self.texte.append(text)
        return "gemeldet"

    def lebenszeichen(self, fehler=False):
        self.pings += 1
        return "ping"


def test_waechter_erinnert_ohne_lauf(journal):
    m = Zaehler()
    bn.waechter(datetime(2026, 11, 12, 22, 0), journal.datei, m)
    assert len(m.texte) == 1 and "12.11.2026" in m.texte[0] and "kein Tageslauf" in m.texte[0]


def test_waechter_still_nach_lauf_auch_gestoppt(journal):
    journal.ereignis("abgleich", "Abgleich mit IBKR weicht ab – Tageslauf gestoppt", jetzt=datetime(2026, 11, 12, 18, 30))
    m = Zaehler()
    assert "lief heute" in bn.waechter(datetime(2026, 11, 12, 22, 0), journal.datei, m)
    assert m.texte == []


def test_waechter_lauf_vom_vortag_zaehlt_nicht(journal):
    journal.ereignis("tageslauf", "x", jetzt=datetime(2026, 11, 11, 23, 59))
    m = Zaehler()
    bn.waechter(datetime(2026, 11, 12, 22, 5), journal.datei, m)
    assert len(m.texte) == 1


def test_waechter_feiertag_wochenende_und_zu_frueh(journal):
    m = Zaehler()
    bn.waechter(datetime(2026, 12, 24, 22, 0), journal.datei, m)        # Xetra-Feiertag, Donnerstag
    assert m.texte == [] and m.pings == 1
    bn.waechter(datetime(2026, 11, 14, 22, 0), journal.datei, m)        # Samstag
    bn.waechter(datetime(2026, 11, 12, 21, 59), journal.datei, m)       # vor 22:00
    assert m.texte == [] and m.pings == 1


def test_lauf_heute_liest_nur(journal):
    journal.ereignis("tageslauf", "x", jetzt=datetime(2026, 11, 12, 18, 0))
    assert bn.lauf_heute(journal.datei, date(2026, 11, 12))
    assert not bn.lauf_heute(journal.datei, date(2026, 11, 13))


def test_eurobetraege_schalter_in_konfiguration():
    from tradingbot.konfiguration import lade_konfiguration

    k = lade_konfiguration("betrieb")["benachrichtigung"]
    assert set(k) >= {"telegram", "healthchecks", "eurobetraege"}
    assert re.fullmatch(r"\d+", str(k["zeitlimit_s"]))
