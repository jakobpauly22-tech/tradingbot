"""Prüft die Testsperre (tests/conftest.py, tests/_testsperre.py; Jakob 24.11.2026): keine echten Zugänge in Tests, auch nach .env-Laden."""
import os
import socket
import urllib.request

import pytest
from dotenv import load_dotenv

import _testsperre as sperre
from tradingbot.konfiguration import PROJEKT_WURZEL


def test_echte_env_laden_liefert_keine_zugaenge():
    load_dotenv(PROJEKT_WURZEL / ".env", override=True)              # wie ein Werkzeug im Test
    for name in sperre.ZUGAENGE + ("FRED_API_KEY", "TIINGO_API_KEY"):
        assert os.getenv(name) is None, name
    assert os.getenv("SEC_USER_AGENT") == sperre.SEC_PLATZHALTER        # nie die echte Kennung
    from tradingbot.betrieb.nachtrag import flex_aus_env
    assert flex_aus_env() is None                                     # keine Flex-Abfrage möglich


def test_andere_variablen_aus_env_bleiben(tmp_path):
    datei = tmp_path / ".env"
    datei.write_text("FLEX_TOKEN=geheim\nTELEGRAM_BOT_TOKEN=geheim\nTESTSPERRE_ANDERES=bleibt\n", encoding="utf-8")
    load_dotenv(datei, override=True)
    assert os.getenv("FLEX_TOKEN") is None and os.getenv("TELEGRAM_BOT_TOKEN") is None
    assert os.environ.pop("TESTSPERRE_ANDERES") == "bleibt"


def test_direkt_gesetzte_zugaenge_entfernt_der_naechste_test_teil1():
    os.environ["FLEX_TOKEN"] = "von-einem-test-gesetzt"               # ohne monkeypatch, bleibt nach dem Test stehen


def test_direkt_gesetzte_zugaenge_entfernt_der_naechste_test_teil2():
    assert os.getenv("FLEX_TOKEN") is None


@pytest.mark.parametrize("host", ["api.telegram.org", "hc-ping.com", "data.sec.gov", "www.sec.gov", "ndcdyn.interactivebrokers.com", "gdcdyn.interactivebrokers.com",
                                  "www.healthchecks.io"])
def test_namensaufloesung_gesperrt(host):
    vorher = len(sperre.VERSUCHE)
    with pytest.raises(sperre.NetzGesperrt):
        socket.getaddrinfo(host, 443)
    assert len(sperre.VERSUCHE) == vorher + 1


def test_urlopen_telegram_und_healthchecks_gesperrt():
    for url in ("https://api.telegram.org/botX/sendMessage", "https://hc-ping.com/abc/fail"):
        with pytest.raises(OSError):                                  # urllib verpackt NetzGesperrt in URLError (OSError)
            urllib.request.urlopen(urllib.request.Request(url, data=b"", method="POST"), timeout=2)


@pytest.mark.parametrize("port", sorted(sperre.GATEWAY_PORTE))
def test_ib_gateway_ports_gesperrt(port):
    with pytest.raises(sperre.NetzGesperrt):
        socket.create_connection(("127.0.0.1", port), timeout=1)
    with socket.socket() as s:
        with pytest.raises(sperre.NetzGesperrt):
            s.connect_ex(("localhost", port))


def test_melder_mit_echtem_urlopen_sendet_nicht():
    from tradingbot.betrieb.benachrichtigung import Melder, Telegram
    m = Melder([Telegram("token", "chat", zeitlimit=1)], "https://hc-ping.com/abc", zeitlimit=1)
    assert "gesendet" not in m.melden("Test") and "gesendet" not in m.lebenszeichen()
