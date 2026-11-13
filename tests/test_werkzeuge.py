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
