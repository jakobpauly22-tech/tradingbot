"""Ersatzzahlungen ohne Satz in der Flex-Beschreibung (Fall 20.11.2026, Jakob 23.11.2026).

Nachgestellt nach dem echten Flex-Bericht: sechs „Payment In Lieu Of Dividends“ mit Beschreibung
„<SYM>(<ISIN>) PAYMENT IN LIEU OF DIVIDEND (Ordinary Dividend)“, Zahltag = Ex-Tag 12.–18.11., Gutschrift (reportDate) 19.11.
Satz je Stück nur aus Yahoo am exakt gleichen Ex-Tag; die „vermutet“-Übernahme vom 19.11. (USD +9,53 = vier der sechs
Belege) wird über die Teilsumme zurückgenommen, damit nichts doppelt in Kassenbasis und Büchern steht."""
import sys
import types
from datetime import date

import pandas as pd
import pytest

from tradingbot.betrieb import dividenden as dv
from tradingbot.betrieb.journal import Journal
from tradingbot.betrieb.tageslauf import kassenabgleich

FX = {"USD": 1.0967}
TOL = 0.05
# Symbol: (conid, Buch, Stück, Ex-Tag, Satz laut Yahoo, Flex-Betrag, ISIN, transactionID, actionID)
FAELLE = {
    "EXE": (1001, "fundamental_a", 6, "20261112", 0.575, 3.45, "US1651677353", "11154265004", "177801460"),
    "ETR": (1002, "fundamental_b", 4, "20261113", 0.68, 2.72, "US29364G1031", "11154642187", "177876832"),
    "CF": (1003, "fundamental_a", 4, "20261116", 0.60, 2.40, "US1252691001", "11157599712", "177212852"),
    "STE": (1004, "fundamental_b", 2, "20261117", 0.69, 1.38, "IE00BFY8C754", "11157850588", "177827654"),
    "VRSN": (1005, "fundamental_b", 1, "20261117", 0.81, 0.81, "US92343E1029", "11157849584", "177654842"),
    "EXPE": (1006, "fundamental_b", 2, "20261118", 0.48, 0.96, "US30212P3038", "11154790431", "178033703"),
}
TICKER = {v[0]: k for k, v in FAELLE.items()}
BUECHER = ["fundamental_a", "fundamental_b"]


def beschreibung(sym: str, umbruch: bool = False) -> str:
    isin = FAELLE[sym][6]
    return f"{sym}({isin}) PAYMENT IN LIEU OF\nDIVIDEND (Ordinary Dividend)" if umbruch else \
        f"{sym}({isin}) PAYMENT IN LIEU OF DIVIDEND (Ordinary Dividend)"


def zeile(sym: str) -> dict:
    conid, _, _, ex, _, betrag, _, tid, aid = FAELLE[sym]
    return {"type": "Payment In Lieu Of Dividends", "symbol": sym, "conid": str(conid), "transactionID": tid, "exDate": ex,
            "dateTime": ex, "settleDate": ex, "reportDate": "20261119", "amount": str(betrag), "currency": "USD",
            "levelOfDetail": "DETAIL", "actionID": aid, "description": beschreibung(sym, umbruch=sym in ("VRSN", "EXPE"))}


def yahoo(ticker, ex_tag):
    _, _, _, ex, satz, *_ = FAELLE[ticker]
    return (satz, "") if ex_tag == f"{ex[:4]}-{ex[4:6]}-{ex[6:]}" else (None, f"Yahoo: 0 Dividenden am Ex-Tag {ex_tag}")


@pytest.fixture
def journal(tmp_path):
    j = Journal(tmp_path / "journal.sqlite")
    for n in BUECHER:
        j.buch_anlegen(n, 10_000.0)
    for sym, (_, buch, stueck, *_rest) in FAELLE.items():
        j.db.execute("INSERT INTO ausfuehrungen (exec_id, order_ref, buch, ticker, richtung, stueck, preis_eur, gebuehr_eur, zeit, "
                     "waehrung, preis) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                     (f"e-{sym}", f"{buch}:x", buch, sym, 1, stueck, 100 / FX["USD"], 0.0, "2026-11-10 14:30:03+00:00", "USD", 100.0))
    j.db.commit()
    yield j
    j.schliessen()


def buchen(j, zeilen, satz_quelle=yahoo):
    return dv.verbuchen(j, BUECHER, dv.belege_aus_flex(zeilen), ticker_je_conid=TICKER, fx=FX, toleranz=TOL, quelle="Flex Test",
                        satz_quelle=satz_quelle)


class Konto:
    def __init__(self, kasse):
        self.kasse = kasse

    def kasse_je_waehrung(self):
        return dict(self.kasse)

    def aufgelaufene_zinsen(self):
        return {"EUR": 0.0}

    def aufgelaufene_dividenden(self):
        return {"EUR": 0.0}


B = {"sicherheit": {"abgleich_kasse_toleranz": TOL, "abgleich_buchung_ohne_buchbezug_max": 10.0},
     "dividenden": {"vormerkung": False, "accrued_dividend_ausweis": "unbekannt"}, "buecher": {n: {} for n in BUECHER}}


# --- Satz ---------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("umbruch", [False, True])
def test_echte_ersatzzahlungs_beschreibung_hat_keinen_satz(umbruch):
    for sym in FAELLE:
        assert dv.SATZ.search(beschreibung(sym, umbruch)) is None
    (b,) = dv.belege_aus_flex([zeile("VRSN")])
    assert b.art == "ersatzzahlung" and b.satz is None and b.ex_tag == "2026-11-17" and b.zahltag == "2026-11-17"
    assert b.gutschrift == "2026-11-19"


def test_satz_aus_flex_beschreibung_auch_mit_zeilenumbruch():
    assert float(dv.SATZ.search("KO(US1912161007) CASH DIVIDEND USD\n0.51 PER SHARE (Ordinary Dividend)").group(1)) == 0.51


def test_sechs_ersatzzahlungen_mit_satz_aus_yahoo(journal):
    v = buchen(journal, [zeile(s) for s in FAELLE])
    assert v.stopp == []
    zeilen = journal.kassenbuchungen()
    assert len(zeilen) == 6 and {z["satz_quelle"] for z in zeilen} == {"Yahoo (gleicher Ex-Tag)"}
    exe = journal.kassenbuchungen("ticker='EXE'")[0]
    assert (exe["buch"], exe["stueck"], exe["satz"], exe["betrag"], exe["art"]) == ("fundamental_a", 6, 0.575, 3.45, "ersatzzahlung")
    assert exe["zahltag"] == "2026-11-12" and exe["gutschrift"] == "2026-11-19"
    assert any(t.startswith("Ersatzzahlung EXE: fundamental_a +3.45 USD (6 Stück × 0.575 laut Yahoo (gleicher Ex-Tag), Ex-Tag 2026-11-12")
               and "Beleg 11154265004" in t for t in v.gebucht)


def test_yahoo_ohne_dividende_am_ex_tag_stoppt(journal):
    v = buchen(journal, [zeile("CF")], satz_quelle=lambda t, e: (None, f"Yahoo: 0 Dividenden am Ex-Tag {e}"))
    assert journal.kassenbuchungen() == []
    assert v.stopp == ["CF: Satz je Stück fehlt im Beleg 11157599712 (nicht in der Flex-Beschreibung; Yahoo: 0 Dividenden am Ex-Tag 2026-11-16)"]


def test_yahoo_mit_anderem_satz_probe_stoppt(journal):
    v = buchen(journal, [zeile("CF")], satz_quelle=lambda t, e: (0.50, ""))
    assert journal.kassenbuchungen() == []
    assert len(v.stopp) == 1 and "Probe stimmt nicht" in v.stopp[0] and "4 Stück × 0.5 (Yahoo (gleicher Ex-Tag)) = 2.00" in v.stopp[0]


def test_satz_yahoo_nur_am_exakt_gleichen_ex_tag(monkeypatch):
    reihe = pd.Series([0.60, 0.60], index=pd.DatetimeIndex(["2026-08-14 09:30", "2026-11-16 09:30"]).tz_localize("America/New_York"))
    monkeypatch.setitem(sys.modules, "yfinance", types.SimpleNamespace(Ticker=lambda t: types.SimpleNamespace(dividends=reihe)))
    assert dv.satz_yahoo("CF", "2026-11-16") == (0.60, "")
    satz, grund = dv.satz_yahoo("CF", "2026-11-17")
    assert satz is None and "0 Dividenden am Ex-Tag 2026-11-17" in grund


def test_satz_yahoo_fehler_gibt_keinen_satz(monkeypatch):
    def kaputt(t):
        raise OSError("keine Verbindung")
    monkeypatch.setitem(sys.modules, "yfinance", types.SimpleNamespace(Ticker=kaputt))
    assert dv.satz_yahoo("CF", "2026-11-16") == (None, "Yahoo nicht erreichbar (OSError)")


# --- Rücknahme der „vermutet“-Übernahme über die Teilsumme ---------------------------------------------------------------
def ablauf_bis_uebernahme(j):
    """18.11. Basis festhalten; 19.11. IBKR-Kasse USD +9,53 (EXE+ETR+CF+EXPE) → „vermutet“ in die Kassenbasis."""
    bot_usd = sum(j.kasse_je_waehrung(n).get("USD", 0.0) for n in BUECHER)
    kasse = {"EUR": 1_000_000.0, "USD": 5_000.0 + bot_usd}
    kassenabgleich(j, BUECHER, Konto(kasse), B, heute="2026-11-18")
    kasse = {**kasse, "USD": kasse["USD"] + 9.53}
    diff, _ = kassenabgleich(j, BUECHER, Konto(kasse), B, heute="2026-11-19")
    assert diff == [] and j.zustand("_konto")["buchungen_ohne_buchbezug"][0]["posten"] == [{"waehrung": "USD", "betrag": 9.53}]
    return kasse


def test_ruecknahme_ueber_gutschriftstag_und_teilsumme_vier_von_sechs(journal):
    kasse = ablauf_bis_uebernahme(journal)
    basis_vorher = journal.zustand("_konto")["kassenbasis"]["USD"]
    assert buchen(journal, [zeile(s) for s in FAELLE]).stopp == []
    k = dv.vormerkungen_klaeren(journal, B, date(2026, 11, 23), TOL)
    assert k.stopp == {}
    konto = journal.zustand("_konto")
    assert abs(konto["kassenbasis"]["USD"] - (basis_vorher - 9.53)) < 1e-9
    e = konto["buchungen_ohne_buchbezug"][0]
    assert e["belegt"] == ["USD"] and sorted(e["belege"]["USD"]) == sorted(FAELLE[s][7] for s in ("EXE", "ETR", "CF", "EXPE"))
    (text,) = k.meldungen
    assert "Kassendifferenz vom 2026-11-19 (USD +9.53)" in text and "mehrdeutig" not in text
    for s in ("EXE", "ETR", "CF", "EXPE"):
        assert FAELLE[s][7] in text
    ereignisse = [z["text"] for z in journal.db.execute("SELECT text FROM ereignisse WHERE art='kassenbasis'")]
    assert ereignisse[-1] == text
    # VRSN + STE (2,19) kamen erst nach dem 19.11. in die IBKR-Kasse: Abgleich stimmt ohne neue Übernahme
    diff, text = kassenabgleich(journal, BUECHER, Konto({**kasse, "USD": kasse["USD"] + 2.19}), B, heute="2026-11-23")
    assert diff == [] and "stimmt" in text
    assert len(journal.zustand("_konto")["buchungen_ohne_buchbezug"]) == 1
    assert dv.vormerkungen_klaeren(journal, B, date(2026, 11, 24), TOL).meldungen == []       # kein zweites Zurücknehmen


def test_vor_der_uebernahme_gebuchter_beleg_zaehlt_nicht(journal):
    journal.kassenbuchung(beleg_id="ALT", buch="fundamental_a", art="dividende", ticker="EXE", conid=1001, action_id="X", ex_tag="2026-11-12",
                          zahltag="2026-11-19", waehrung="USD", betrag=9.53, betrag_eur=8.69, stueck=1, satz=9.53, steuer="", quelle="t",
                          gutschrift="2026-11-19", gebucht="2026-11-19T10:00:00")
    ablauf_bis_uebernahme(journal)                    # ALT stand schon in den Büchern; die 9,53 sind etwas anderes
    k = dv.vormerkungen_klaeren(journal, B, date(2026, 11, 23), TOL)
    assert k.meldungen == [] and journal.zustand("_konto")["buchungen_ohne_buchbezug"][0]["belegt"] == []


def test_teilsummen_genaueste_und_kleinste_zuerst():
    e = [{"netto": 1.0, "belege": ["a"]}, {"netto": 2.0, "belege": ["b"]}, {"netto": 3.0, "belege": ["c"]}]
    loes = dv.teilsummen(e, 3.0, TOL)
    assert [[x["belege"][0] for x in k] for k in loes] == [["c"], ["a", "b"]]
    assert dv.teilsummen(e, 7.0, TOL) == []
