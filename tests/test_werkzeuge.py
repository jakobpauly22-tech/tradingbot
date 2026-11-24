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
    from tradingbot.daten.kursquellen import bekannte_namen   # seit 18.11.2026 dort (aus tools/kurse_universum.py)

    for vorgaenger in (np.array([1288776]), np.array([], dtype=np.int64), None, [1288776]):
        zeile = pd.Series({"name": "Alphabet Inc. (Class A)", "cik": 1652044, "vorgaenger_ciks": vorgaenger})
        namen = bekannte_namen(zeile, _Sec())
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


def test_split_einordnung_nur_bis_zur_tresorgrenze(monkeypatch, tmp_path):
    """Befund 8 (Jakob 16.11.2026): kein Betriebsmodus, SEC-Einreichungen nur bis zur Grenze, Einträge nach der Grenze
    werden unverändert übernommen; der Kopf der Liste behauptet keinen Datumsfilter mehr."""
    import pytest

    from tradingbot.backtest.tresor import TresorGesperrt, betriebsmodus

    w = _werkzeug("split_ereignisse_einordnen")
    grenze = pd.Timestamp("2024-12-31")
    alt = {(1, "2024-06-03"): {"cik": 1, "datum": "2024-06-03", "art": "split"},
           (2, "2025-03-03"): {"cik": 2, "datum": "2025-03-03", "art": "abspaltung", "geprueft": False}}
    bis, nach = w.teile_nach_grenze(alt, grenze)
    assert list(bis) == [(1, "2024-06-03")] and nach == [alt[(2, "2025-03-03")]]
    with betriebsmodus("Test", protokoll=tmp_path / "betriebsfreigaben.log"):
        with pytest.raises(TresorGesperrt):
            w.main([])
    # Einreichungen nach der Grenze fallen weg (Aktienfakten aus dem Cache)
    fakten = pd.DataFrame([_fakt("2023-01-01", "2023-12-31", 1e8, "2024-02-20"), _fakt("2024-01-01", "2024-12-31", 2e8, "2025-02-20")])
    monkeypatch.setattr(w, "aktienfakten", lambda roh, d, dauer: fakten)

    class _Client:
        def __init__(self, **k):
            pass

        def companyfacts_aus_cache(self, cik):
            return {}, None

    import tradingbot.daten.sec as sec
    monkeypatch.setattr(sec, "SecClient", _Client)
    assert list(w.aktienfakten_mit_quartalen([1])["filed"]) == [pd.Timestamp("2024-02-20")]
    assert "liest ALLE Einträge, ohne" in w.KOPF and "Backtests lesen nur Ereignisse bis zur Datumsgrenze" not in w.KOPF


# --- c3 Schritt 1b (Jakob 24.11.2026): Kandidatenliste, Netzsperre, Versiegelung, Übernahme, Freigaben -----------------
def _liste(pfad, eintraege):
    from io import StringIO

    from ruamel.yaml import YAML

    puffer = StringIO()
    YAML().dump({"stand": "2026-11-13T12:54:11", "ereignisse": eintraege}, puffer)
    pfad.write_text("# Kopf\n" + puffer.getvalue(), encoding="utf-8")
    return pfad


def _e(cik, ticker, datum, art="split", faktor=2.0, geprueft=False, **mehr):
    eintrag = {"cik": cik, "ticker": ticker, "datum": datum, "faktor_kursreihe": faktor, "sec_verhaeltnis": faktor,
               "sec_einreichungen": "2024-02-01 → 2025-02-01", "art": art, "split_faktor": faktor,
               "quelle": "SEC-Vergleich automatisch", "geprueft": geprueft, "bemerkung": "SEC-Verhältnis = Faktor"}
    eintrag.update(mehr)
    return eintrag


_LEER = {"ereignisse_mit_r": 0, "gleichstand": [], "r_anders": [], "art_anders": []}


def _lauf_umgebung(tmp_path, monkeypatch, einordnung):
    w = _werkzeug("split_ereignisse_einordnen")
    liste = _liste(tmp_path / "liste.yaml", [_e(1, "AAA", "2024-12-04"), _e(2, "GEP", "2016-12-02", art="unklar", geprueft=True),
                                             _e(3, "NACH", "2026-11-20", faktor=8.0)])
    cache = tmp_path / "cache"
    (cache / "sec").mkdir(parents=True)
    (cache / "sec" / "a.json").write_text("x", encoding="utf-8")
    monkeypatch.setattr(w, "einordnung", lambda grenze, bis, freigaben: einordnung(cache, bis))
    return w, liste, cache, tmp_path / "ablage"


def test_1b_lauf_schreibt_nur_kandidat(tmp_path, monkeypatch):
    """Der Lauf schreibt nicht in die geltende Liste, sondern Kandidat, Vergleich und Bericht in die Ablage; Einträge nach
    der Grenze und geprüfte bleiben gleich, der Vergleich nennt die Änderung und die Versiegelung 0 Dateien."""
    def einordnung(cache, bis):
        assert (3, "2026-11-20") not in bis                       # nach der Grenze nicht neu eingeordnet
        neu = dict(bis[(1, "2024-12-04")], art="unklar", split_faktor=None, sec_verhaeltnis=None, sec_einreichungen=None,
                   bemerkung="kein Periodenbericht danach")
        return [neu, bis[(2, "2016-12-02")]], _LEER

    w, liste, cache, ablage = _lauf_umgebung(tmp_path, monkeypatch, einordnung)
    vorher = liste.read_bytes()
    kandidat = w.lauf(ablage=ablage, liste=liste, cache=cache, freigaben_pfad=tmp_path / "keine.yaml")
    assert liste.read_bytes() == vorher
    daten = w.lies_liste(kandidat)
    assert daten["grundlage_sha256"] == w.sha256(liste)
    neu = w.eintraege_nach_schluessel(daten["ereignisse"])
    assert neu[(3, "2026-11-20")] == w.eintraege_nach_schluessel(w.lies_liste(liste)["ereignisse"])[(3, "2026-11-20")]
    assert neu[(1, "2024-12-04")]["art"] == "unklar"
    vergleich = next(ablage.glob("*_vergleich.md")).read_text(encoding="utf-8")
    assert "Versiegelung daten/cache/: 0 Dateien" in vergleich and "Netzversuche: 0" in vergleich
    assert "| AAA (1) 2024-12-04 | art | split | unklar |" in vergleich
    assert "Geänderte Einträge nach der Grenze: 0" in vergleich and "Verletzungen bei geprüften Einträgen (geändert oder gestrichen): 0" in vergleich
    assert "AAA (1) 2024-12-04: Faktor Kursreihe 2.0; kein Periodenbericht danach" in vergleich
    assert list(ablage.glob("*_split_ereignisse.md"))


def test_1b_nicht_gefundene_bleiben_und_verletzung_geprueft(tmp_path, monkeypatch):
    """Jakob 24.11.2026: Einträge bis zur Grenze, die der Lauf nicht mehr findet, bleiben unverändert und werden eigens
    gezählt; gestrichene oder geänderte geprüfte Einträge zählt die Abnahme als Verletzung."""
    def einordnung(cache, bis):
        return [bis[(1, "2024-12-04")]], _LEER                      # GEP (geprüft) nicht mehr gefunden

    w, liste, cache, ablage = _lauf_umgebung(tmp_path, monkeypatch, einordnung)
    kandidat = w.lauf(ablage=ablage, liste=liste, cache=cache, freigaben_pfad=tmp_path / "keine.yaml")
    alt = w.eintraege_nach_schluessel(w.lies_liste(liste)["ereignisse"])
    neu = w.eintraege_nach_schluessel(w.lies_liste(kandidat)["ereignisse"])
    assert neu == alt
    vergleich = next(ablage.glob("*_vergleich.md")).read_text(encoding="utf-8")
    assert "unverändert behalten: 1." in vergleich and "- GEP (2) 2016-12-02 (geprüft)" in vergleich
    assert "Verletzungen bei geprüften Einträgen (geändert oder gestrichen): 0" in vergleich
    bericht = next(ablage.glob("*_split_ereignisse.md")).read_text(encoding="utf-8")
    assert "1 Einträge bis zur Grenze stehen nicht mehr" in bericht and "## Messung Gleichstand" in bericht
    # gestrichen und geändert geprüft → Verletzung
    v = w.vergleich(alt, {k: e for k, e in alt.items() if k != (2, "2016-12-02")}, pd.Timestamp("2024-12-31"))
    assert v["verletzung_geprueft"] == [(2, "2016-12-02")]
    v = w.vergleich(alt, {**alt, (2, "2016-12-02"): dict(alt[(2, "2016-12-02")], art="split")}, pd.Timestamp("2024-12-31"))
    assert v["verletzung_geprueft"] == [(2, "2016-12-02")]


def test_1b_versiegelung_meldet_geaenderte_cache_datei(tmp_path, monkeypatch):
    def einordnung(cache, bis):
        (cache / "sec" / "a.json").write_text("y", encoding="utf-8")   # der Lauf verändert den Cache
        return list(bis.values()), _LEER

    w, liste, cache, ablage = _lauf_umgebung(tmp_path, monkeypatch, einordnung)
    w.lauf(ablage=ablage, liste=liste, cache=cache, freigaben_pfad=tmp_path / "keine.yaml")
    vergleich = next(ablage.glob("*_vergleich.md")).read_text(encoding="utf-8")
    assert "Versiegelung daten/cache/: 1 Dateien verändert" in vergleich and "geaendert: sec/a.json" in vergleich


def test_1b_netzsperre_bricht_ab_auch_wenn_abgefangen(tmp_path, monkeypatch):
    """Fehlende Datei → Abbruch statt Abruf: Der Netzversuch ist keine Exception, die `except Exception` still zählt."""
    import socket

    import pytest

    def einordnung(cache, bis):
        try:
            socket.getaddrinfo("api.tiingo.com", 443)
        except Exception:                                          # wie die Fehlerschwelle in lade_firmendaten
            pass
        return list(bis.values()), _LEER

    w, liste, cache, ablage = _lauf_umgebung(tmp_path, monkeypatch, einordnung)
    alt = socket.getaddrinfo
    with pytest.raises(SystemExit, match="Netzzugriff gesperrt"):
        w.lauf(ablage=ablage, liste=liste, cache=cache, freigaben_pfad=tmp_path / "keine.yaml")
    assert socket.getaddrinfo is alt                               # Sperre wieder aufgehoben
    assert not list(ablage.glob("*_kandidat.yaml"))


def test_1b_uebernehmen_sichert_und_prueft_grundlage(tmp_path, monkeypatch):
    import pytest

    def einordnung(cache, bis):
        return [dict(bis[(1, "2024-12-04")], art="unklar"), bis[(2, "2016-12-02")]], _LEER

    w, liste, cache, ablage = _lauf_umgebung(tmp_path, monkeypatch, einordnung)
    kandidat = w.lauf(ablage=ablage, liste=liste, cache=cache, freigaben_pfad=tmp_path / "keine.yaml")
    vorher = liste.read_bytes()
    sicherung, berichte = tmp_path / "sicherung", tmp_path / "berichte"
    gesichert = w.uebernehmen(kandidat, liste=liste, sicherung=sicherung, berichte=berichte)
    assert gesichert.read_bytes() == vorher
    text = liste.read_text(encoding="utf-8")
    assert "grundlage_sha256" not in text and text.startswith(w.KOPF)
    assert w.lies_liste(liste)["ereignisse"] == w.lies_liste(kandidat)["ereignisse"]
    assert list(berichte.glob("*_split_ereignisse.md"))
    with pytest.raises(SystemExit, match="nicht mehr die Grundlage"):       # Liste inzwischen geändert
        w.uebernehmen(kandidat, liste=liste, sicherung=sicherung, berichte=berichte)


def test_1b_freigabe_nur_unklar_bis_grenze_mit_beleg(tmp_path):
    import pytest

    w = _werkzeug("split_ereignisse_einordnen")
    grenze = pd.Timestamp("2024-12-31")
    (tmp_path / "ANET_2024-12-04").mkdir()
    (tmp_path / "ANET_2024-12-04" / "0001596532-24-000123.txt.gz").write_bytes(b"")
    eintrag = _e(1596532, "ANET", "2024-12-04", art="unklar", faktor=4.0, split_faktor=None)
    freigabe = {"split_faktor": 4, "accn": "0001596532-24-000123", "filed": "2024-11-07", "beleg": "4-for-1, wirksam 03.12.2024",
                "freigegeben": "Jakob 24.11.2026"}
    neu = w.freigabe_anwenden(eintrag, freigabe, grenze, belege=tmp_path)
    assert neu["art"] == "split" and neu["split_faktor"] == 4.0 and neu["geprueft"] is True
    assert "0001596532-24-000123" in neu["quelle"] and "2024-11-07" in neu["quelle"] and w.REGEL_UNKLAR in neu["quelle"]
    with pytest.raises(SystemExit, match="nach der Tresorgrenze"):
        w.freigabe_anwenden(eintrag, dict(freigabe, filed="2025-02-19"), grenze, belege=tmp_path)
    with pytest.raises(SystemExit, match="nicht „unklar“"):
        w.freigabe_anwenden(dict(eintrag, art="split"), freigabe, grenze, belege=tmp_path)
    with pytest.raises(SystemExit, match="fehlt in der Belegablage"):
        w.freigabe_anwenden(eintrag, dict(freigabe, accn="0001596532-24-999999"), grenze, belege=tmp_path)


def test_1b_gleichstand_nur_gemessen():
    """Zwei Werte derselben Periode mit gleichem filed: gemeldet; r bei umgekehrter Zeilenfolge wird mitgemessen."""
    w = _werkzeug("split_ereignisse_einordnen")
    f = pd.DataFrame([_fakt("2023-01-01", "2023-12-31", 100e6, "2024-02-20"),
                      _fakt("2023-01-01", "2023-12-31", 101e6, "2024-02-20"),
                      _fakt("2023-01-01", "2023-12-31", 200e6, "2024-08-01", form="10-Q")])
    g = w.gleichstand(f, pd.Timestamp("2024-06-03"))
    assert g["gleichstand"] is True and g["r_umgekehrt"] is not None
    ohne = w.gleichstand(f.iloc[[0, 2]].reset_index(drop=True), pd.Timestamp("2024-06-03"))
    assert ohne["gleichstand"] is False and abs(ohne["r_umgekehrt"] - 2.0) < 1e-9


def test_1b_belege_nur_in_ablage_und_bis_grenze(tmp_path):
    import gzip

    w = _werkzeug("split_ereignisse_einordnen")
    kandidat = _liste(tmp_path / "kandidat.yaml", [_e(1596532, "ANET", "2024-12-04", art="unklar", split_faktor=None),
                                                   _e(9, "SPL", "2024-06-03")])

    class _Lesen:
        cache_wurzel = tmp_path / "devcache"

        def _cache_lesen(self, datei):
            return {"filings": {"recent": {"form": ["8-K", "8-K", "10-Q", "8-K"],
                                           "filingDate": ["2024-11-07", "2025-01-05", "2024-11-01", "2024-01-02"],
                                           "accessionNumber": ["0001-24-1", "0001-25-1", "0001-24-2", "0001-24-0"],
                                           "items": ["2.02,9.01", "8.01", "", "8.01"]}}}, None

    class _Client:
        def __init__(self):
            self.urls = []

        def text_holen(self, url):
            self.urls.append(url)
            return "4-for-1 stock split"

    client, belege = _Client(), tmp_path / "belege"
    w.belege_holen(kandidat, belege=belege, client=client, lesen=_Lesen())
    assert client.urls == ["https://www.sec.gov/Archives/edgar/data/1596532/0001241/0001-24-1.txt"]   # nur 8-K im Fenster ≤ Grenze
    with gzip.open(belege / "ANET_2024-12-04" / "0001-24-1.txt.gz", "rt", encoding="utf-8") as f:
        assert "stock split" in f.read()
    assert not (tmp_path / "devcache").exists()


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


# --- tools/pruefe_rohkurse.py und stichprobe_marktwert_roh.py (c2 (2), Jakob 15.11.2026) -----------------------------------
def test_rohkurse_namenspruefung():
    w = _werkzeug("pruefe_rohkurse")
    assert w.name_passt("LKQ Corp", "LKQ Corporation") and w.name_passt("Conoco Phillips", "ConocoPhillips")
    assert w.name_passt("F5 Inc", "F5, Inc.") and not w.name_passt("Fleetcor Technologies Inc", "Corpay, Inc.")


def test_stichprobe_auswahl_deterministisch_mit_festen_firmen_und_jahren():
    import pandas as pd

    w = _werkzeug("stichprobe_marktwert_roh")
    kand = pd.DataFrame([{"firma": f, "messtag": pd.Timestamp(f"{j}-06-30"), "jahr": j, "streubesitz": 1e9}
                         for f in range(1, 40) for j in range(2016, 2025)])
    a = w.auswahl(kand, {"X": 5, "Y": 7}, {11, 12, 13, 14})
    b = w.auswahl(kand, {"X": 5, "Y": 7}, {11, 12, 13, 14})
    assert a.equals(b) and len(a) == 20 and a["firma"].is_unique
    assert {5, 7} <= set(a["firma"]) and len(set(a["firma"]) & {11, 12, 13, 14}) >= 3
    assert set(range(2016, 2025)) <= set(a["jahr"])


def test_stichprobe_eingefrorene_auswahl():
    w = _werkzeug("stichprobe_marktwert_roh")
    assert len(w.FESTE_AUSWAHL) == 20 and len({f for _, f, _ in w.FESTE_AUSWAHL}) == 20
    assert {"MA", "UPS", "GOOGL"} <= {t for t, _, _ in w.FESTE_AUSWAHL}
    assert {int(m[:4]) for _, _, m in w.FESTE_AUSWAHL} == set(range(2016, 2025))


def test_scores_marktwert_wahl_rueckfall_ohne_rohkurs_bis_zum_stichtag():
    w = _werkzeug("auswertung_scores")
    assert w.marktwert_wahl({"marktwert": None, "grund": "kein Rohkurs bis zum Stichtag"}, 3.4e10, None) == (
        3.4e10, None, "Rohkurs erst nach dem Stichtag (Teil b)")
    assert w.marktwert_wahl({"marktwert": 5.4e10, "grund": None}, 1.06e10, None) == (5.4e10, None, "roh")
    assert w.marktwert_wahl({"marktwert": None, "grund": "Streubesitz 16% des Marktwerts"}, 1.06e10, None)[0] is None


def _geldmarkt(tage, zins_pa=0.0):
    return pd.Series(100 * (1 + zins_pa / 365) ** np.arange(len(tage)), index=tage)


def test_geldmarkt_etf_kriterien_aus_regime_md():
    w = _werkzeug("pruefe_regime_daten")
    tage = pd.bdate_range("2012-01-02", "2013-12-31")
    satz = pd.Series([0.0], index=[pd.Timestamp("2011-06-01")])
    assert w.pruefe_geldmarkt_etf(_geldmarkt(tage), tage, satz)["bestanden"]

    sprung = _geldmarkt(tage)
    sprung.iloc[300] *= 1.005                                   # ein Ausreißertag: +0,5 % und zurück
    e = w.pruefe_geldmarkt_etf(sprung, tage, satz)
    assert not e["bestanden"] and e["kriterien"] == {"1 Lücken": True, "2 Tagesänderung": False, "3 Jahresrendite": True}
    assert len(e["spruenge"]) == 2

    luecke = _geldmarkt(tage).drop(tage[100:106])               # 6 Handelstage fehlen
    assert w.pruefe_geldmarkt_etf(luecke, tage, satz)["kriterien"]["1 Lücken"] is False
    assert w.pruefe_geldmarkt_etf(_geldmarkt(tage).drop(tage[100:105]), tage, satz)["kriterien"]["1 Lücken"] is True
    assert w.pruefe_geldmarkt_etf(_geldmarkt(tage)[5:], tage, satz)["kriterien"]["1 Lücken"] is False     # beginnt zu spät

    e = w.pruefe_geldmarkt_etf(_geldmarkt(tage, 0.02), tage, satz)                                       # 2 % p. a. gegen Satz 0 %
    assert e["kriterien"]["3 Jahresrendite"] is False and e["kriterien"]["2 Tagesänderung"] is True


def test_rohkurse_bericht_nennt_h_ungleich_1_nur_als_anzahl():
    """Jakob 16.11.2026: Abnahmeberichte nennen H ≠ 1 nur als Anzahl, ohne Namen und Faktor (Tresor)."""
    import pandas as pd

    w = _werkzeug("pruefe_rohkurse")
    t = pd.DataFrame([{"quelle": "yfinance", "symbol": "AAA", "tage": 3000, "H": 15.0, "anteil_ok": 1.0, "max_abw": 0.001, "bestanden": True, "grund": ""},
                      {"quelle": "yfinance", "symbol": "BBB", "tage": 3000, "H": 1.0, "anteil_ok": 1.0, "max_abw": 0.001, "bestanden": True, "grund": ""},
                      {"quelle": "tiingo", "symbol": "CCC", "tage": 900, "H": 0.0666, "anteil_ok": 0.9, "max_abw": 0.2, "bestanden": False,
                       "grund": "nur 90.0% der Tage innerhalb 1 %"}])
    verdeckt = "\n".join(w.abschnitt_verdeckt(t))
    assert ": 1 Reihen" in verdeckt and "AAA" not in verdeckt and "15" not in verdeckt
    nicht = "\n".join(w.abschnitt_nicht_bestanden(t[~t["bestanden"]]))
    assert "davon mit H ≠ 1: 1" in nicht and "CCC" in nicht and "0.0666" not in nicht and "0,0666" not in nicht and "| H |" not in nicht
