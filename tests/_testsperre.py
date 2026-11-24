"""Testsperre für echte Zugänge (eingebunden über tests/conftest.py) (Jakob 24.11.2026; Anlass: ein Test lud die echte .env, danach lasen Tageslauf-Tests echte
Flex-Belege).

Drei Schichten, für jeden Test:
1. **Umgebung:** Zugänge zu Broker, Flex, Telegram, Healthchecks und Sicherung (`ZUGAENGE`) werden vor jedem Test aus
   `os.environ` entfernt. Die Datenschlüssel (`DATENSCHLUESSEL`: FRED, SEC, Tiingo) nur außerhalb von `-m netz`; dort
   steht für `SEC_USER_AGENT` ein Platzhalter (Code, der einen SecClient baut, aber nur den Cache liest), und sec.gov
   ist gesperrt (`NUR_NETZ_HOSTS`), damit nie mit der echten Kennung abgerufen wird.
2. **.env:** `dotenv.load_dotenv` ist umhüllt. Lädt ein Test die echte (oder eine andere) .env, werden dieselben
   Variablen danach sofort wieder entfernt; andere Variablen bleiben.
3. **Netz:** Namensauflösung und Verbindungen zu IBKR/Flex, Telegram und Healthchecks (`GESPERRTE_HOSTS`) sowie zum IB
   Gateway auf dem eigenen Rechner (`GATEWAY_PORTE`) brechen mit `NetzGesperrt` ab, auch bei `-m netz`. Jeder Versuch
   steht in `VERSUCHE`.
"""
from __future__ import annotations

import os
import socket

import dotenv
import dotenv.main

ZUGAENGE = ("FLEX_TOKEN", "FLEX_QUERY_ID", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "HEALTHCHECKS_PING_URL",
            "HEALTHCHECKS_SEC_PING_URL", "IB_HOST", "IB_PORT", "IB_CLIENT_ID", "TRADING_MODE", "JOURNAL_BACKUP_DIR")
DATENSCHLUESSEL = ("FRED_API_KEY", "SEC_USER_AGENT", "TIINGO_API_KEY")
GESPERRTE_HOSTS = ("interactivebrokers.com", "ibkr.com", "ibllc.com", "telegram.org", "hc-ping.com", "healthchecks.io")
NUR_NETZ_HOSTS = ("sec.gov",)                 # nur in Tests mit Marker netz erreichbar
SEC_PLATZHALTER = "Testlauf ohne Netz keine-adresse@example.invalid"
GATEWAY_PORTE = {4001, 4002, 7496, 7497}
LOKAL = {"127.0.0.1", "::1", "localhost", "0.0.0.0"}

VERSUCHE: list[str] = []
_ZUSTAND = {"netz": False}


class NetzGesperrt(OSError):
    """Echter Zugang im Test (IBKR, Flex, Telegram, Healthchecks, IB Gateway) – gesperrt durch tests/conftest.py."""


def entfernen() -> None:
    for name in ZUGAENGE + (() if _ZUSTAND["netz"] else DATENSCHLUESSEL):
        os.environ.pop(name, None)
    if not _ZUSTAND["netz"]:
        os.environ["SEC_USER_AGENT"] = SEC_PLATZHALTER


def _gesperrter_host(host) -> bool:
    h = (host.decode() if isinstance(host, bytes) else str(host or "")).lower().rstrip(".")
    gesperrt = GESPERRTE_HOSTS + (() if _ZUSTAND["netz"] else NUR_NETZ_HOSTS)
    return any(h == g or h.endswith("." + g) for g in gesperrt)


def _pruefen(adresse) -> None:
    if isinstance(adresse, tuple) and len(adresse) >= 2:
        host, port = adresse[0], adresse[1]
        if _gesperrter_host(host) or (str(host) in LOKAL and int(port) in GATEWAY_PORTE):
            VERSUCHE.append(f"{host}:{port}")
            raise NetzGesperrt(f"Testsperre: Verbindung zu {host}:{port} gesperrt (tests/conftest.py)")


_getaddrinfo, _connect, _connect_ex = socket.getaddrinfo, socket.socket.connect, socket.socket.connect_ex
_load_dotenv = dotenv.load_dotenv


def getaddrinfo(host, port, *a, **k):
    if _gesperrter_host(host):
        VERSUCHE.append(f"{host}:{port}")
        raise NetzGesperrt(f"Testsperre: Namensauflösung {host} gesperrt (tests/conftest.py)")
    return _getaddrinfo(host, port, *a, **k)


def connect(self, adresse):
    _pruefen(adresse)
    return _connect(self, adresse)


def connect_ex(self, adresse):
    _pruefen(adresse)
    return _connect_ex(self, adresse)


def load_dotenv(*a, **k):
    ergebnis = _load_dotenv(*a, **k)
    entfernen()
    return ergebnis


# beim Import, also vor jedem Testmodul und vor jedem `from dotenv import load_dotenv` im Projektcode
socket.getaddrinfo = getaddrinfo
socket.socket.connect = connect
socket.socket.connect_ex = connect_ex
dotenv.load_dotenv = dotenv.main.load_dotenv = load_dotenv
entfernen()
