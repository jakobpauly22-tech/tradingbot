"""Broker-Schnittstelle und Sicherheitsriegel (Phase 2, Entscheidungen Jakob 31.10. und 02.11.2026).

Ein Interface für alle Broker; zuerst Interactive Brokers über das lokale IB Gateway (broker/ibkr.py). Paper und Live
unterscheidet nur die Konfiguration; bis zur Freigabe nach den Go-Live-Kriterien ist ausschließlich Paper erlaubt.

Senden nur, wenn ALLE Riegel offen sind (`pruefe_senden`):
- Senden in config/betrieb.yaml freigeschaltet (`ibkr.senden_freigeschaltet`; in Phase 6b aus: nur lesen),
- TRADING_MODE=paper (.env), Port 4002 (Live-Port 4001 ist gesperrt), Host 127.0.0.1,
- Konto-ID beginnt mit „DU“ (Paper-Konto),
- keine Not-Aus-Datei STOP im Projektordner,
- Vorschlag noch nicht gesendet und keine offene Order mit derselben Kennung (orderRef = „<Buch>:<Vorschlag-ID>“).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class SendenGesperrt(RuntimeError):
    """Ein Sicherheitsriegel verhindert das Senden."""


class VerbindungGesperrt(RuntimeError):
    """Verbindung zu einem nicht erlaubten Host oder Port (z.B. Live-Port 4001)."""


@dataclass(frozen=True)
class Position:
    konto: str
    ticker: str
    stueck: float
    einstand: float


@dataclass(frozen=True)
class OffeneOrder:
    order_ref: str               # „<Buch>:<Vorschlag-ID>“
    ticker: str
    richtung: int
    stueck: float
    limit: float | None
    status: str


@dataclass(frozen=True)
class Auftrag:
    """Freigegebener Vorschlag, bereit zum Senden. Kauf mit Limit, Verkauf ohne Limit; gültig für den nächsten Handelstag."""
    buch: str
    vorschlag_id: str
    ticker: str
    richtung: int
    stueck: int
    limit: float | None
    art: str = "etf"             # etf | etc | aktie (bestimmt die Börsenkennung)
    waehrung: str | None = None  # Handelswährung (z.B. USD für SXRM auf Xetra); ohne Angabe aus dem Ticker

    @property
    def order_ref(self) -> str:
        return f"{self.buch}:{self.vorschlag_id}"


class Broker(Protocol):
    def verbinden(self) -> None: ...
    def trennen(self) -> None: ...
    def konto_id(self) -> str: ...
    def nettowert(self) -> float: ...
    def positionen(self) -> list[Position]: ...
    def offene_orders(self) -> list[OffeneOrder]: ...
    def sende(self, auftrag: Auftrag, gesendete_refs: set[str]) -> str: ...
    def ausfuehrungen(self) -> list[dict]: ...


def pruefe_verbindung(host: str, port: int, betrieb: dict) -> None:
    """Nur lokales Gateway und nur der Paper-Port; der Live-Port ist hart gesperrt."""
    ib = betrieb["ibkr"]
    if int(port) == int(ib["port_live"]):
        raise VerbindungGesperrt(f"Port {port} ist der Live-Port und gesperrt, bis Jakob nach den Go-Live-Kriterien freigibt")
    if int(port) != int(ib["port_paper"]):
        raise VerbindungGesperrt(f"Port {port} ist nicht der Paper-Port {ib['port_paper']}")
    if host != ib["host"]:
        raise VerbindungGesperrt(f"Host {host} nicht erlaubt; nur {ib['host']} (lokales IB Gateway)")


def pruefe_senden(*, konto_id: str, port: int, modus: str | None, betrieb: dict, projekt_wurzel: Path,
                  auftrag: Auftrag, offene: list[OffeneOrder], gesendete_refs: set[str]) -> None:
    """Wirft `SendenGesperrt` mit allen Gründen, wenn auch nur ein Riegel geschlossen ist."""
    ib, gruende = betrieb["ibkr"], []
    if not ib.get("senden_freigeschaltet", False):
        gruende.append("Senden ist in config/betrieb.yaml nicht freigeschaltet (Phase 6b: nur lesen)")
    if (modus or "").strip().lower() != "paper":
        gruende.append(f"TRADING_MODE ist „{modus}“, erlaubt ist nur „paper“")
    if int(port) != int(ib["port_paper"]):
        gruende.append(f"Port {port} ist nicht der Paper-Port {ib['port_paper']}")
    if not str(konto_id).startswith(ib["konto_praefix_paper"]):
        gruende.append(f"Konto {konto_id} ist kein Paper-Konto (Präfix {ib['konto_praefix_paper']})")
    if (Path(projekt_wurzel) / betrieb["sicherheit"]["not_aus_datei"]).exists():
        gruende.append("Not-Aus: Datei STOP im Projektordner")
    if auftrag.order_ref in gesendete_refs:
        gruende.append(f"Vorschlag {auftrag.order_ref} wurde schon gesendet")
    if any(o.order_ref == auftrag.order_ref for o in offene):
        gruende.append(f"offene Order mit Kennung {auftrag.order_ref} besteht schon")
    if any(o.order_ref.split(":")[0] == auftrag.buch and o.ticker == auftrag.ticker and o.richtung == auftrag.richtung for o in offene):
        gruende.append(f"offene Order im Buch {auftrag.buch} für {auftrag.ticker} in derselben Richtung besteht schon")
    if auftrag.richtung > 0 and auftrag.limit is None and auftrag.art != "fx":
        gruende.append("Kauf ohne Limit")
    if auftrag.richtung < 0 and auftrag.limit is not None:
        gruende.append("Verkauf mit Limit (Verkäufe ohne Limit)")
    if gruende:
        raise SendenGesperrt("; ".join(gruende))
