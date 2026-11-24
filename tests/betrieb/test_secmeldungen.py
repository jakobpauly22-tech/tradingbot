"""SEC-Aktualisierung Schritt 3: Meldungen im Tageslauf (Festlegung Jakob 23.11.2026, Gruppe „bekannt“ 24.11.2026)."""
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from tradingbot.betrieb import secmeldungen as sm
from tradingbot.konfiguration import lade_konfiguration

BERLIN = ZoneInfo("Europe/Berlin")
JETZT = datetime(2026, 12, 7, 22, 30, tzinfo=BERLIN)
KONFIG = {"stand_max_tage": 9, "meldung_max_alter_tage": 120, "bekannt": {936340: "DTE Energy", 34088: "Exxon Mobil (alte CIK)"}}


def _stand(erfolgreich=True, letzter_erfolg="2026-12-05T10:14:03+01:00", **kw):
    return {"lauf_beginn": "2026-12-05T10:00:00+01:00", "lauf_ende": "2026-12-05T10:14:03+01:00", "erfolgreich": erfolgreich,
            "letzter_erfolg": letzter_erfolg, "abbruch": None, "zusammenfassung": {"ciks": 515, "Fehler": 0}, **kw}


def test_stand_aktuell_nur_protokoll():
    zeilen, sofort = sm.stand_meldungen(lambda: _stand(), JETZT, KONFIG)
    assert zeilen == ["SEC-Stand vom 05.12.2026 10:14 (letzter erfolgreicher Lauf)"] and sofort == []


def test_stand_aelter_als_neun_tage_sofort():
    zeilen, sofort = sm.stand_meldungen(lambda: _stand(letzter_erfolg="2026-11-28T10:14:03+01:00"), JETZT, KONFIG)
    assert zeilen == ["SEC-Stand vom 28.11.2026 10:14 (letzter erfolgreicher Lauf)"]
    assert sofort == ["SEC-Stand vom 28.11.2026 ist 10 Tage alt (Grenze 9 Tage) – Bewertung läuft mit dem vorhandenen Betriebs-Cache weiter"]
    # genau 9 Tage: noch keine Sofortmeldung („mehr als 9 Tage“)
    assert sm.stand_meldungen(lambda: _stand(letzter_erfolg="2026-11-28T22:30:00+01:00"), JETZT, KONFIG)[1] == []


def test_letzter_lauf_nicht_erfolgreich_mit_fehlerzahl():
    s = _stand(erfolgreich=False, lauf_ende="2026-12-12T10:20:00+01:00", abbruch="Fehlerschwelle überschritten",
               zusammenfassung={"ciks": 515, "Fehler": 31})
    zeilen, sofort = sm.stand_meldungen(lambda: s, datetime(2026, 12, 12, 22, 0, tzinfo=BERLIN), KONFIG)
    assert zeilen == ["SEC-Stand vom 05.12.2026 10:14 (letzter erfolgreicher Lauf); letzter Lauf 12.12.2026 10:20 nicht erfolgreich, "
                      "31 Fehler (Fehlerschwelle überschritten)"]
    assert sofort == []                                   # 7 Tage – Stand noch innerhalb der Grenze


def test_ohne_erfolg_fehlend_oder_unlesbar_sofort():
    _, sofort = sm.stand_meldungen(lambda: _stand(erfolgreich=False, letzter_erfolg=None), JETZT, KONFIG)
    assert len(sofort) == 1 and "kein erfolgreicher Lauf" in sofort[0]

    def fehlt():
        raise FileNotFoundError("STAND.json")
    zeilen, sofort = sm.stand_meldungen(fehlt, JETZT, KONFIG)
    assert zeilen == sofort and "STAND.json fehlt" in sofort[0] and "vorhandenen Betriebs-Cache" in sofort[0]
    _, sofort = sm.stand_meldungen(lambda: json.loads("{kaputt"), JETZT, KONFIG)
    assert "unlesbar (JSONDecodeError)" in sofort[0]


def test_stand_lesen_aus_wurzel(tmp_path):
    (tmp_path / "STAND.json").write_text(json.dumps(_stand()), encoding="utf-8")
    assert sm.stand_lesen(tmp_path)["letzter_erfolg"].startswith("2026-12-05")


def test_firmen_alt_bekannt_und_veraltet():
    tag = pd.Timestamp("2026-12-07")
    sec = {"firmen": [{"firma": 1, "symbol": "AAA", "ciks": [1], "neueste": tag - pd.Timedelta(days=121)},
                      {"firma": 2, "symbol": "BBB", "ciks": [2], "neueste": tag - pd.Timedelta(days=120)},       # genau 120: nein
                      {"firma": 3, "symbol": "CCC", "ciks": [3], "neueste": None},
                      {"firma": 4, "symbol": "DTE", "ciks": [936340], "neueste": tag - pd.Timedelta(days=180)},
                      {"firma": 5, "symbol": "XOM", "ciks": [2115436, 34088], "neueste": tag - pd.Timedelta(days=130)},
                      {"firma": 6, "symbol": "NEU", "ciks": [6], "neueste": tag - pd.Timedelta(days=3)}],
           "veraltet": ["CCC", "ZZZ"]}
    zeilen = sm.firmen_meldungen(sec, tag, KONFIG)
    assert zeilen == [
        "SEC: 2 Firma(en) mit neuester Meldung älter als 120 Tage (Bewertungstag 07.12.2026): CCC ohne Meldung, AAA 121 Tage",
        "SEC bekannt (unvollständige SEC-Daten, Befund A2 vom 23.11.2026): 2 Firma(en) älter als 120 Tage: DTE 180 Tage, XOM 130 Tage",
        "SEC: 2 Firma(en) wegen veraltetem Abschluss nicht bewertet (CCC, ZZZ)"]
    # ohne alte Firmen: nur die Zeile zu veraltet (immer)
    assert sm.firmen_meldungen({"firmen": [], "veraltet": []}, tag, KONFIG) == ["SEC: 0 Firma(en) wegen veraltetem Abschluss nicht bewertet"]
    assert sm.firmen_meldungen(None, tag, KONFIG) == []


def test_konfiguration_19_bekannte_ciks():
    k = lade_konfiguration("betrieb")["sec_meldungen"]
    assert k["stand_max_tage"] == 9 and k["meldung_max_alter_tage"] == 120
    assert len(k["bekannt"]) == 19 and 34088 in k["bekannt"] and 936340 in k["bekannt"]


def test_neueste_meldung():
    assert sm.neueste_meldung(pd.DataFrame({"filed": pd.to_datetime(["2026-05-01", "2026-08-03"])})) == pd.Timestamp("2026-08-03")
    assert sm.neueste_meldung(pd.DataFrame()) is None and sm.neueste_meldung(None) is None
