"""Briefing-Archiv: Prüfprogramm (tools/pruefe_bot_anhang.py) und Übernahme (tools/briefing_uebernehmen.py)."""
import copy
import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"


def _werkzeug(name):
    sys.path.insert(0, str(TOOLS))
    spec = importlib.util.spec_from_file_location(f"werkzeug_{name}", TOOLS / f"{name}.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


anhang = _werkzeug("pruefe_bot_anhang")
uebernahme = _werkzeug("briefing_uebernehmen")

GUELTIG = {
    "schema_version": "1.1",
    "datum": "2026-11-10",
    "erstellt_um": "2026-11-10T21:44:00+01:00",
    "bloecke": ["2026-11-10_0700"],
    "nachrichten": [{
        "titel": "Beispiel", "anlage": "DAX", "ticker": None, "region": "Deutschland", "ereignistyp": "Politik",
        "richtung": "neutral", "staerke": 2, "wirkungsdauer": "Tage", "quelle": None, "quellen": ["Newsletter"],
        "block_id": "2026-11-10_0700", "item_key": "s0-i0", "story_id": None}],
    "makro_kalender": [{"datum": "2026-11-12", "ereignis": "EZB", "region": "Eurozone", "bedeutung": 3}],
}


def _schreibe(ordner, d, name=None):
    pfad = ordner / (name or f"{d['datum']}.json")
    pfad.write_text(json.dumps(d), encoding="utf-8")
    return pfad


# --- Prüfprogramm -------------------------------------------------------------------------------------------------
def test_pruefe_unveraendert_fuer_gueltige_datei():
    assert anhang.pruefe(copy.deepcopy(GUELTIG)) == []


def test_gueltige_datei(tmp_path):
    assert anhang.pruefe_datei(_schreibe(tmp_path, GUELTIG)) == ("gültig", [])


def test_dateiname_muss_zum_datum_passen(tmp_path):
    status, gruende = anhang.pruefe_datei(_schreibe(tmp_path, GUELTIG, "2026-11-11.json"))
    assert status == "ungültig" and "passt nicht zu datum" in gruende[0]


def test_falscher_dateiname_ist_ungueltig(tmp_path):
    status, gruende = anhang.pruefe_datei(_schreibe(tmp_path, GUELTIG, "briefing.json"))
    assert status == "ungültig" and "nicht JJJJ-MM-TT.json" in gruende[0]


@pytest.mark.parametrize("aendern, text", [
    (lambda d: d["nachrichten"][0].update(richtung="steigend"), "richtung"),
    (lambda d: d["nachrichten"][0].update(staerke=4), "staerke"),
    (lambda d: d["makro_kalender"][0].update(datum="2026-11-20"), "7 Folgetagen"),
    (lambda d: d["makro_kalender"][0].update(bedeutung=0), "bedeutung"),
    (lambda d: d.update(schema_version="1.0"), "schema_version"),
    (lambda d: d.update(erstellt_um="2026-11-09T21:00:00+01:00"), "vor dem Datum"),
    (lambda d: d.pop("bloecke"), "Feld fehlt"),
])
def test_ungueltige_inhalte(tmp_path, aendern, text):
    d = copy.deepcopy(GUELTIG)
    aendern(d)
    status, gruende = anhang.pruefe_datei(_schreibe(tmp_path, d))
    assert status == "ungültig" and any(text in g for g in gruende)


def test_kaputtes_json_und_falsches_datumsformat_sind_ungueltig_ohne_absturz(tmp_path):
    kaputt = tmp_path / "2026-11-10.json"
    kaputt.write_text("{nicht json", encoding="utf-8")
    assert anhang.pruefe_datei(kaputt)[0] == "ungültig"
    d = copy.deepcopy(GUELTIG)
    d["datum"] = "10.11.2026"
    assert anhang.pruefe_datei(_schreibe(tmp_path, d, "2026-11-10.json"))[0] == "ungültig"


def test_warnungen(tmp_path):
    spaet = copy.deepcopy(GUELTIG)
    spaet["erstellt_um"] = "2026-11-13T21:44:00+01:00"
    status, gruende = anhang.pruefe_datei(_schreibe(tmp_path, spaet))
    assert status == "Warnung" and "nachgeholt" in gruende[0]

    leer = copy.deepcopy(GUELTIG)
    leer["nachrichten"], leer["makro_kalender"] = [], []
    assert anhang.pruefe_datei(_schreibe(tmp_path, leer))[1] == ["keine Nachrichten", "kein Makro-Kalender"]

    doppelt = copy.deepcopy(GUELTIG)
    doppelt["nachrichten"].append(copy.deepcopy(doppelt["nachrichten"][0]))
    assert "doppelte item_key im selben Block: 2026-11-10_0700/s0-i0" in anhang.pruefe_datei(_schreibe(tmp_path, doppelt))[1]

    # gleicher item_key in einem anderen Block ist normal (Schlüssel gelten je Block)
    zwei_bloecke = copy.deepcopy(GUELTIG)
    zwei_bloecke["bloecke"].append("2026-11-10_1500")
    zwei_bloecke["nachrichten"].append({**zwei_bloecke["nachrichten"][0], "block_id": "2026-11-10_1500"})
    assert anhang.pruefe_datei(_schreibe(tmp_path, zwei_bloecke)) == ("gültig", [])


def test_bekannte_quelle_einschraenkung_nur_bis_30_10(tmp_path):
    alt = copy.deepcopy(GUELTIG)
    alt["datum"] = "2026-10-29"
    alt["erstellt_um"] = "2026-10-29T22:00:00+01:00"
    alt["makro_kalender"][0]["datum"] = "2026-10-31"
    alt["nachrichten"][0]["item_key"] = "s0-i0-b1"
    assert any("quelle bei Sammelmeldungen" in g for g in anhang.pruefe_datei(_schreibe(tmp_path, alt))[1])
    neu = copy.deepcopy(GUELTIG)
    neu["nachrichten"][0]["item_key"] = "s0-i0-b1"
    assert anhang.pruefe_datei(_schreibe(tmp_path, neu)) == ("gültig", [])


# --- Übernahme ----------------------------------------------------------------------------------------------------
def test_uebernehmen_neu_unveraendert_geaendert(tmp_path):
    quelle, ablage = tmp_path / "drive", tmp_path / "ablage"
    quelle.mkdir()
    _schreibe(quelle, GUELTIG)
    assert uebernahme.uebernehmen(quelle, ablage) == [("2026-11-10.json", "neu", "")]
    assert uebernahme.uebernehmen(quelle, ablage) == [("2026-11-10.json", "unverändert", "")]

    geaendert = copy.deepcopy(GUELTIG)
    geaendert["erstellt_um"] = "2026-11-10T22:00:00+01:00"
    _schreibe(quelle, geaendert)
    (name, aktion, detail), = uebernahme.uebernehmen(quelle, ablage)
    assert aktion == "geändert" and "21:44:00" in detail and "22:00:00" in detail
    assert json.loads((ablage / name).read_text(encoding="utf-8")) == geaendert


def test_uebernehmen_veraendert_die_quelle_nicht_und_kopiert_ungueltige_mit(tmp_path):
    quelle, ablage = tmp_path / "drive", tmp_path / "ablage"
    quelle.mkdir()
    (quelle / "2026-11-10.json").write_text("{kaputt", encoding="utf-8")
    (quelle / "notiz.txt").write_text("ignoriert", encoding="utf-8")
    vorher = sorted((p.name, p.read_bytes()) for p in quelle.iterdir())
    assert uebernahme.uebernehmen(quelle, ablage)[0][1] == "neu"
    assert sorted((p.name, p.read_bytes()) for p in quelle.iterdir()) == vorher
    assert [p.name for p in ablage.iterdir()] == ["2026-11-10.json"]   # kein .tmp zurückgeblieben


def test_nicht_lesbare_quelldatei_bricht_nicht_ab(tmp_path, monkeypatch):
    quelle, ablage = tmp_path / "drive", tmp_path / "ablage"
    quelle.mkdir()
    _schreibe(quelle, GUELTIG)
    original = Path.read_bytes

    def lesen(self):
        if self.parent == quelle:
            raise OSError("Platzhalter nicht geladen")
        return original(self)

    monkeypatch.setattr(Path, "read_bytes", lesen)
    assert uebernahme.uebernehmen(quelle, ablage) == [("2026-11-10.json", "nicht lesbar", "Platzhalter nicht geladen")]


# --- Lücken -------------------------------------------------------------------------------------------------------
def _tage(*iso):
    return [dt.date.fromisoformat(t) for t in iso]


def test_luecken_zusammenhaengende_bereiche_und_ende():
    vorhanden = _tage("2026-11-01", "2026-11-02", "2026-11-03", "2026-11-09", "2026-11-19")
    assert uebernahme.luecken(vorhanden, dt.date(2026, 11, 22)) == [
        (dt.date(2026, 11, 4), dt.date(2026, 11, 8)),
        (dt.date(2026, 11, 10), dt.date(2026, 11, 18)),
        (dt.date(2026, 11, 20), dt.date(2026, 11, 22)),
    ]


def test_luecken_keine_und_leer():
    assert uebernahme.luecken(_tage("2026-11-01", "2026-11-02"), dt.date(2026, 11, 2)) == []
    assert uebernahme.luecken([], dt.date(2026, 11, 2)) == []


def test_tage_der_dateien_ignoriert_fremde_namen():
    assert uebernahme.tage_der_dateien(["2026-11-02.json", "notiz.json", "2026-13-40.json"]) == _tage("2026-11-02")


def test_heute_erst_ab_export_uhrzeit_faellig():
    assert uebernahme.letzter_faelliger_tag(dt.datetime(2026, 11, 23, 12, 0), "21:41") == dt.date(2026, 11, 22)
    assert uebernahme.letzter_faelliger_tag(dt.datetime(2026, 11, 23, 21, 41), "21:41") == dt.date(2026, 11, 23)


# --- Quelle nicht erreichbar: ein erneuter Versuch nach 5 s ---------------------------------------------------------
def _main_vorbereiten(tmp_path, monkeypatch):
    quelle = tmp_path / "drive"
    monkeypatch.setattr(uebernahme, "lade_konfiguration",
                        lambda name: {"quelle": str(quelle), "ablage": "ablage", "export_uhrzeit": "21:41"})
    monkeypatch.setattr(uebernahme, "PROJEKT_WURZEL", tmp_path)
    pausen = []
    monkeypatch.setattr(uebernahme.time, "sleep", pausen.append)
    return quelle, pausen


def test_quelle_dauerhaft_nicht_erreichbar_exit_2_nach_einem_wiederholversuch(tmp_path, monkeypatch, capsys):
    _, pausen = _main_vorbereiten(tmp_path, monkeypatch)
    assert uebernahme.main([]) == 2
    assert pausen == [5]
    assert "nicht erreichbar" in capsys.readouterr().out


def test_quelle_beim_zweiten_versuch_erreichbar(tmp_path, monkeypatch):
    quelle, pausen = _main_vorbereiten(tmp_path, monkeypatch)
    monkeypatch.setattr(uebernahme.time, "sleep", lambda s: (pausen.append(s), quelle.mkdir(), _schreibe(quelle, GUELTIG)))
    assert uebernahme.main([]) == 0
    assert pausen == [5] and (tmp_path / "ablage" / "2026-11-10.json").exists()
