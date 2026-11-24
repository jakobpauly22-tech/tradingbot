"""SEC-Aktualisierung Schritt 4 (Festlegung Jakob 23.11.2026): Zeitplan samstags 10:00, Protokolldatei, Healthchecks-Ping."""
import importlib.util

import pytest

from tradingbot.betrieb import benachrichtigung as bn
from tradingbot.konfiguration import PROJEKT_WURZEL

_spec = importlib.util.spec_from_file_location("sec_aktualisieren", PROJEKT_WURZEL / "tools" / "sec_aktualisieren.py")
werkzeug = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(werkzeug)

URL = "https://hc-ping.com/sec-test"


class Antwort:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture
def pings(monkeypatch, tmp_path):
    gesendet = []

    def oeffnen(anfrage, timeout=None):
        gesendet.append(anfrage.full_url)
        return Antwort()

    monkeypatch.setattr(bn, "sec_melder_aus_env", lambda betrieb, umgebung=None: bn.Melder([], URL, oeffnen=oeffnen))
    monkeypatch.setattr(werkzeug, "PROTOKOLL", tmp_path / "sec_aktualisierung.log")
    monkeypatch.setattr(werkzeug, "load_dotenv", lambda *a, **k: None)   # nie die echte .env laden (Flex, Telegram)
    return gesendet


@pytest.mark.parametrize("ausgang, url", [(0, URL), (1, URL + "/fail"), (3, URL + "/fail")])
def test_ping_nach_dem_lauf(pings, ausgang, url, capsys):
    assert werkzeug.main([], lauf=lambda probe: ausgang) == ausgang
    assert pings == [url]
    aus = capsys.readouterr().out
    assert "Lebenszeichen SEC an Healthchecks gesendet" in aus and URL not in aus


def test_unerwarteter_fehler_pingt_fail(pings):
    def kaputt(probe):
        raise RuntimeError("kaputt")
    assert werkzeug.main([], lauf=kaputt) == 2 and pings == [URL + "/fail"]


def test_probe_pingt_nie(pings):
    assert werkzeug.main(["--probe"], lauf=lambda probe: 0) == 0 and pings == []


def test_protokolldatei(pings, capsys):
    werkzeug.main(["--protokoll"], lauf=lambda probe: print("Lauf-Ausgabe") or 0)
    text = werkzeug.PROTOKOLL.read_text(encoding="utf-8")
    assert "=== SEC-Aktualisierung" in text and "Lauf-Ausgabe" in text and "Ausgang 0" in text
    assert capsys.readouterr().out == ""
    werkzeug.main(["--protokoll"], lauf=lambda probe: 1)              # angehängt, nicht überschrieben
    assert werkzeug.PROTOKOLL.read_text(encoding="utf-8").count("=== SEC-Aktualisierung") == 2


def test_sec_melder_eigene_url():
    betrieb = {"benachrichtigung": {"healthchecks": True, "telegram": False}}
    m = bn.sec_melder_aus_env(betrieb, {"HEALTHCHECKS_PING_URL": "https://hc-ping.com/tageslauf", "HEALTHCHECKS_SEC_PING_URL": URL})
    assert m.lebenszeichen_url == URL
    assert bn.sec_melder_aus_env(betrieb, {"HEALTHCHECKS_PING_URL": "https://hc-ping.com/tageslauf"}).lebenszeichen_url is None
    assert "nicht eingerichtet (HEALTHCHECKS_SEC_PING_URL" in bn.sec_lebenszeichen(bn.Melder([], None), True)


def test_einrichtungsskript_samstag_10_uhr():
    text = (PROJEKT_WURZEL / "tools" / "sec_aktualisierung_einrichten.ps1").read_text(encoding="utf-8")
    assert "-DaysOfWeek Saturday -At 10:00" in text and "-StartWhenAvailable" in text
    assert "-AllowStartIfOnBatteries" in text and "-DontStopIfGoingOnBatteries" in text and "--protokoll" in text
    assert "pythonw.exe" in text
