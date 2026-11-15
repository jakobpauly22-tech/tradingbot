"""Hilfsfunktionen der Werkzeuge in tools/ (die Skripte selbst brauchen Netz und Cache)."""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd


def _werkzeug(name):
    pfad = Path(__file__).parents[1] / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"werkzeug_{name}", pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


class _Sec:
    def submissions(self, cik):
        namen = {1288776: ("GOOGLE INC.", []), 1652044: ("Alphabet Inc.", [])}
        name, frueher = namen[cik]
        return {"name": name, "formerNames": [{"name": n} for n in frueher]}, None


def test_bekannte_namen_mit_vorgaengern_als_numpy_array():
    w = _werkzeug("kurse_universum")
    for vorgaenger in (np.array([1288776]), np.array([], dtype=np.int64), None, [1288776]):
        zeile = pd.Series({"name": "Alphabet Inc. (Class A)", "cik": 1652044, "vorgaenger_ciks": vorgaenger})
        namen = w._bekannte_namen(zeile, _Sec())
        assert "Alphabet Inc." in namen
        assert ("GOOGLE INC." in namen) == (vorgaenger is not None and len(vorgaenger) > 0)


# --- tools/split_ereignisse_einordnen.py (Datenkorrektur Marktwert, Teil a, Jakob 13.11.2026) ---------------------------
def _fakt(start, ende, wert, filed, form="10-K", konzept="us-gaap:WeightedAverageNumberOfSharesOutstandingBasic"):
    return {"konzept": konzept, "rang": 0, "start": pd.Timestamp(start), "ende": pd.Timestamp(ende), "wert": wert,
            "filed": pd.Timestamp(filed), "form": form, "accn": filed}


def test_split_einordnen_regeln():
    w = _werkzeug("split_ereignisse_einordnen")
    assert w.einordnen(2.0, 2.0, 2.0, 1, "")[:2] == ("split", 2.0)
    assert w.einordnen(1.841, 1.0, 1.841, 1, "")[:2] == ("abspaltung", 1.0)                 # BAX/Baxalta
    art, faktor, _ = w.einordnen(0.4873, 0.3337, 0.4873, 1, "")                               # HLT: Reverse-Split und Abspaltung
    assert art == "kombiniert" and abs(faktor - 0.3337) < 1e-9
    assert w.einordnen(2.0, None, 2.0, 1, "kein Periodenbericht danach")[:2] == ("unklar", None)
    art, _, bem = w.einordnen(2.0, 2000.0, 2.0, 1, "")                                        # OKE: Tausend statt Stück
    assert art == "unklar" and "Vorschlag: split, Split-Faktor 2" in bem
    assert w.einordnen(1.0053, 1.0, 1.0053, 1, "")[:2] == ("abspaltung", 1.0)                # HON 2016: nahe 1, eng
    assert w.einordnen(0.971, 0.9716, 0.971, 1, "")[0] == "split"                             # SLG: Aktiendividende
    assert w.einordnen(1.0017, 1.0, 1.0017, 1, "")[0] == "unklar"                             # nicht unterscheidbar


def test_split_sec_verhaeltnis_nur_periodenberichte():
    """CF 2015: das 8-K nach dem Split zeigt noch die alte Basis; maßgeblich ist der erste 10-K/10-Q danach."""
    w = _werkzeug("split_ereignisse_einordnen")
    f = pd.DataFrame([_fakt("2014-01-01", "2014-12-31", 51.2e6, "2015-02-26"),
                      _fakt("2014-01-01", "2014-12-31", 51.2e6, "2015-12-16", form="8-K"),
                      _fakt("2014-01-01", "2014-12-31", 255.9e6, "2016-02-25")])
    r, vor, nach, grund = w.sec_verhaeltnis(f, pd.Timestamp("2015-06-18"))
    assert abs(r - 255.9 / 51.2) < 1e-9 and nach == pd.Timestamp("2016-02-25") and grund == ""
    assert w.sec_verhaeltnis(f, pd.Timestamp("2016-06-01"))[3].startswith("kein Periodenbericht danach")


# --- tools/pruefe_abspaltungen_tiingo.py (Teil c1, S2 nach der zweiten Änderung, Jakob 13.11.2026) ------------------------
def test_abspaltung_suchwoerter_s2():
    w = _werkzeug("pruefe_abspaltungen_tiingo")
    treffer = ["completed the spin-off of CSRA", "the Spinoff", "a tax-free spin off", "the separation and distribution",
               "a pro rata distribution of all of the outstanding shares of Time Inc."]
    kein = ["quarterly cash distribution to unitholders", "distribution agreement with McKesson", "separation agreement with the CEO",
            "secondary distribution of shares"]
    assert all(w.WORTE.search(x) for x in treffer)
    assert not any(w.WORTE.search(x) for x in kein)


def test_abspaltung_text_nur_lesbare_dokumente():
    w = _werkzeug("pruefe_abspaltungen_tiingo")
    roh = ("<SEC-DOCUMENT><DOCUMENT><TYPE>8-K<TEXT><html><p>Time&#160;Warner completed the <b>spin-off</b></p></html></TEXT></DOCUMENT>"
           "<DOCUMENT><TYPE>GRAPHIC<TEXT>begin 644 bild.jpg spin-off M89PNG</TEXT></DOCUMENT>"
           "<DOCUMENT><TYPE>EX-99.1<TEXT>Press release: pro rata distribution of all shares</TEXT></DOCUMENT></SEC-DOCUMENT>")
    text = w.text_aus_einreichung(roh)
    assert "completed the spin-off" in text and "distribution of all" in text and "bild.jpg" not in text and "<" not in text


def test_abspaltung_volltext_nutzt_wiederholung_und_meldet_fehler(tmp_path, monkeypatch):
    """8-K-Abruf über SecClient.text_holen (Wiederholung mit Wartezeit, Jakob 15.11.2026); 404 wird gemeldet, ein
    dauerhafter Netzausfall hält den Lauf an statt still weiterzumachen."""
    import pytest

    from tradingbot.daten.abruf import DatenFehler, VoruebergehenderFehler

    w = _werkzeug("pruefe_abspaltungen_tiingo")
    monkeypatch.setattr(w, "VOLLTEXT", tmp_path)
    monkeypatch.setattr(w, "ABRUFFEHLER", [])

    class _Client:
        def __init__(self, ergebnis):
            self.ergebnis, self.urls = ergebnis, []

        def text_holen(self, url):
            self.urls.append(url)
            if isinstance(self.ergebnis, Exception):
                raise self.ergebnis
            return self.ergebnis

    ok = _Client("<DOCUMENT><TYPE>8-K<TEXT>the spin-off of Cars.com</TEXT></DOCUMENT>")
    assert "spin-off" in w.volltext(ok, 39899, "0000039899-17-000001")
    assert ok.urls == ["https://www.sec.gov/Archives/edgar/data/39899/000003989917000001/0000039899-17-000001.txt"]
    assert w.volltext(_Client(RuntimeError("nie")), 39899, "0000039899-17-000001").strip().endswith("Cars.com")   # aus dem Cache
    assert w.volltext(_Client(DatenFehler("SEC HTTP 404")), 1, "0000000001-17-000002") is None
    assert w.ABRUFFEHLER == ["8-K 0000000001-17-000002: SEC HTTP 404"]
    with pytest.raises(VoruebergehenderFehler):
        w.volltext(_Client(VoruebergehenderFehler("nach 7 Versuchen")), 1, "0000000001-17-000003")


# --- tools/pruefe_abspaltungen_gezielt.py (Teil c1 b), Jakob 15.11.2026) ------------------------------------------------
def test_gezielt_nur_hauptdokument_und_pressemitteilung():
    w = _werkzeug("pruefe_abspaltungen_gezielt")
    roh = ("<SEC-DOCUMENT><DOCUMENT><TYPE>8-K<TEXT><p>Item 8.01 The Board approved the spin-off of NewCo.</p></TEXT></DOCUMENT>"
           "<DOCUMENT><TYPE>EX-4.1<TEXT>Indenture: Spin-Off shall have the meaning in Section 13.04</TEXT></DOCUMENT>"
           "<DOCUMENT><TYPE>EX-99.1<TEXT>Press release: distribution of all of the outstanding shares</TEXT></DOCUMENT></SEC-DOCUMENT>")
    doks = w.haupt_und_pressemitteilungen(roh)
    assert [d["typ"] for d in doks] == ["8-K", "EX-99.1"]
    funde = w.fundstellen(doks)
    assert [(f["typ"], f["wort"].lower()) for f in funde] == [("8-K", "spin-off"), ("EX-99.1", "distribution of all")]
    assert all("Indenture" not in f["ausschnitt"] for f in funde)


def test_gezielt_faelle_aus_obergrenze():
    import pandas as pd

    from tradingbot.backtest.obergrenze_scheinverluste import lies_ereignisse

    w = _werkzeug("pruefe_abspaltungen_gezielt")
    lauf3 = ("## Treffer\n| RTN (1047122) | Raytheon | 2020-03-05 bis 2020-03-23 | -16.8% | 8-K |\n"
             "## Unklar (≤ −15 % ohne SEC-Beleg)\n| MRO (101778) | Marathon Oil | 2020-03-03 bis 2020-03-23 | -46.9% |\n")
    obergrenze = ("## Backtest A: Kandidatentage mit Bestand (2)\n| Ticker | Tag | x | y | z |\n| MRO | 2020-03-09 | -46.85% | 2.49% | +1.165 Pp. |\n"
                  "| MRO | 2020-03-16 | -11.70% | 1.93% | +0.226 Pp. |\n"
                  "## Index-Nachbau: Ereignisse ≤ −15 % während der Mitgliedschaft (2)\n"
                  "| RTN (1047122) | 2020-03-05 bis 2020-03-23 | -16.8% | treffer | 2020-03-05 |\n"
                  "| MRO (101778) | 2020-03-03 bis 2020-03-23 | -46.9% | unklar | 2020-03-09 |\n## Ereignisse ohne Kursreihe\n")
    f = w.faelle_aus_obergrenze(obergrenze, lies_ereignisse(lauf3))
    assert list(zip(f["ticker"], f["A"], f["Index"])) == [("MRO", True, True), ("RTN", False, True)]
    assert f.iloc[0]["bis"] == pd.Timestamp("2020-03-23")


# --- tools/pruefe_eingefrorene_zusammengefuehrt.py und pruefe_abspaltungen_schluss.py (Jakob 15.11.2026) --------------------
def test_zusammengefuehrt_uebernommene_tage():
    import pandas as pd

    w = _werkzeug("pruefe_eingefrorene_zusammengefuehrt")
    tage = pd.bdate_range("2022-04-11", periods=5)
    erste = pd.DataFrame({"close": 1.0}, index=tage[[0, 2]])
    zweite = pd.DataFrame({"close": 2.0}, index=tage)
    assert w.uebernommen([("A", erste), ("B", zweite)], 1, tage) == 3       # nur die Lücken der ersten Reihe
    assert w.uebernommen([("A", erste), ("B", zweite)], 0, tage) == 2


def test_schluss_naechster_bericht():
    import pandas as pd

    w = _werkzeug("pruefe_abspaltungen_schluss")
    subs = {"filings": {"recent": {"form": ["8-K", "10-Q", "10-Q/A", "10-K"], "filingDate": ["2023-06-20", "2023-08-08", "2023-08-01", "2024-02-29"],
                                   "accessionNumber": ["a", "b", "c", "d"], "primaryDocument": ["x", "y", "z", "w"],
                                   "reportDate": ["", "2023-06-30", "2023-06-30", "2023-12-31"]}}}
    assert w.naechster_bericht(subs, pd.Timestamp("2023-06-15"))["accessionNumber"] == "b"
    assert w.naechster_bericht(subs, pd.Timestamp("2024-03-01")) is None
