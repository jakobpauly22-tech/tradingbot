"""Daten für die neue Oberfläche des Tageslaufs (Jakob 10.11.2026, Variante A Tkinter): Ampel, Übersicht je Buch,
Vorschlagstabelle, Einordnung der Meldungen.

Nur lesen und aufbereiten: keine Funktion hier schreibt ins Journal oder sendet etwas. Freigabe und Senden laufen
unverändert über `tageslauf.freigeben_und_senden`. Ohne Fenster testbar (tests/betrieb/test_ansicht.py).
"""
from __future__ import annotations

import gzip
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache

import pandas as pd

from tradingbot.betrieb.tageslauf import FREIGABE_VON, buch_freigeschaltet, verpasste_handelstage, zeitfenster_hinweis

GRUEN, GELB, ROT, GRAU, ORANGE = "#2e7d32", "#f9a825", "#c62828", "#757575", "#ef6c00"
READ_ONLY_HINWEIS = "Read-Only im Gateway ist aktiv – ausschalten, dann „Status prüfen“"


@dataclass
class Lampe:
    name: str
    farbe: str
    text: str


# --- Gateway-Status (beim Start und per Knopf, Jakob 10.11.2026) ----------------------------------------------------------
def gateway_status(broker) -> dict:
    """Verbindung, Konto (gekürzt) und Schreibzugriff. Der Schreibzugriff wird über eine reine Abfrage ohne Order geprüft
    (`IbkrBroker.schreibzugriff`). Fehler werden zum Status, nie zur Ausnahme."""
    from tradingbot.betrieb.journal import konto_kurz

    status = {"verbunden": False, "konto": "", "schreiben": None, "grund": "", "geprueft": datetime.now()}
    if broker is None:
        status["grund"] = "kein Gateway"
        return status
    try:
        if not broker.verbunden():
            broker.verbinden()
        status["verbunden"] = bool(broker.verbunden())
    except Exception as f:  # noqa: BLE001
        status["grund"] = f"nicht verbunden ({type(f).__name__})"
        return status
    try:
        status["konto"] = konto_kurz(broker.konto_id())
    except Exception:  # noqa: BLE001
        status["konto"] = "?"
    if hasattr(broker, "schreibzugriff"):
        try:
            status["schreiben"], status["grund"] = broker.schreibzugriff()
        except Exception as f:  # noqa: BLE001
            status["schreiben"], status["grund"] = False, f"Schreibprüfung fehlgeschlagen ({type(f).__name__})"
    return status


def senden_erlaubt(gateway: dict, probe: bool, gestoppt: str | None = None) -> tuple[bool, str]:
    """Senden-Knopf (Jakob 10.11.2026): bei Read-Only gesperrt, bis „Status prüfen“ grün zeigt. Der Probe-Modus sperrt
    genauso (damit die Sperre testbar ist), auch wenn er nie sendet. Ein gestoppter Lauf sperrt wie bisher."""
    if gestoppt:
        return False, "Tageslauf gestoppt – erst Ursache klären"
    if not gateway.get("verbunden"):
        return False, "Gateway nicht verbunden – Gateway starten, dann „Status prüfen“"
    if gateway.get("schreiben") is not True:
        return False, READ_ONLY_HINWEIS if gateway.get("schreiben") is False else "Schreibzugriff nicht geprüft – „Status prüfen“"
    return True, ""


# --- Letzter Tageslauf und Datenstand ------------------------------------------------------------------------------------
def letzter_tageslauf(journal, vor) -> tuple[str | None, pd.Timestamp | None]:
    """Zeit und Xetra-Signaltag des letzten Tageslaufs vor `vor` (Ereignis „tageslauf“ im Journal)."""
    grenze = (vor.replace(tzinfo=None) if getattr(vor, "tzinfo", None) else vor).isoformat(timespec="seconds")
    z = journal.db.execute("SELECT zeit, text FROM ereignisse WHERE art='tageslauf' AND zeit < ? ORDER BY zeit DESC LIMIT 1",
                           (grenze,)).fetchone()
    if z is None:
        return None, None
    m = re.search(r"Xetra (\d{2})\.(\d{2})\.(\d{4})", z["text"])
    return z["zeit"], (pd.Timestamp(f"{m.group(3)}-{m.group(2)}-{m.group(1)}") if m else None)


# --- Ampel -------------------------------------------------------------------------------------------------------------
def ampel(erg, journal, betrieb: dict, *, probe: bool, gateway: dict, jetzt: datetime) -> list[Lampe]:
    lampen = []
    if probe:
        lampen.append(Lampe("Modus", ORANGE, "PROBE – sendet nie, kein Messbeginn"))
    if gateway.get("verbunden"):
        lampen.append(Lampe("Gateway", GRUEN, f"verbunden, Konto {gateway.get('konto') or '?'}"))
    else:
        lampen.append(Lampe("Gateway", ROT, gateway.get("grund") or "nicht verbunden"))
    schreiben = gateway.get("schreiben")
    zeit = f" (geprüft {gateway['geprueft']:%H:%M})" if gateway.get("geprueft") else ""
    if schreiben is True:
        lampen.append(Lampe("Schreibzugriff", GRUEN, "frei – Read-Only aus" + zeit))
    elif schreiben is False:
        lampen.append(Lampe("Schreibzugriff", ROT, ("Read-Only an" if "Read-Only" in (gateway.get("grund") or "") else
                                                    gateway.get("grund") or "gesperrt") + zeit))
    else:
        lampen.append(Lampe("Schreibzugriff", GRAU, "nicht geprüft"))
    if probe:
        lampen.append(Lampe("Freigabefenster", GRUEN, "Probe: jederzeit"))
    elif jetzt.time() >= FREIGABE_VON:
        lampen.append(Lampe("Freigabefenster", GRUEN, "offen bis 24 Uhr"))
    else:
        lampen.append(Lampe("Freigabefenster", GRAU, f"öffnet um {FREIGABE_VON:%H:%M}"))
    frei = [bv.vorschlag for bv, u in erg.vorschlaege if u.frei]
    hinweise = zeitfenster_hinweis(jetzt, frei)
    us_fx = [v for v in frei if v.art == "fx" or (v.art == "aktie" and not v.ticker.endswith(".DE") and v.richtung > 0)]
    if hinweise:
        lampen.append(Lampe("Uhrzeit US/FX", GELB, "; ".join(h.replace("HINWEIS Zeitpunkt: ", "") for h in hinweise)))
    elif us_fx:
        lampen.append(Lampe("Uhrzeit US/FX", GRUEN, f"passt für {len(us_fx)} US-/FX-Orders (empfohlen 22:05–22:50)"))
    else:
        lampen.append(Lampe("Uhrzeit US/FX", GRAU, "keine US-/FX-Orders"))
    zeit_vor, tag_vor = letzter_tageslauf(journal, erg.jetzt)
    if zeit_vor is None:
        lampen.append(Lampe("Letzter Tageslauf", GRAU, "keiner vorher"))
    else:
        verpasst = verpasste_handelstage("xetra", tag_vor, erg.xetra) if (tag_vor is not None and erg.xetra is not None) else []
        text = f"{pd.Timestamp(zeit_vor):%d.%m. %H:%M} (Signaltag {tag_vor:%d.%m.})" if tag_vor is not None else f"{pd.Timestamp(zeit_vor):%d.%m. %H:%M}"
        if verpasst:
            lampen.append(Lampe("Letzter Tageslauf", GELB, f"{text} – {len(verpasst)} Handelstag(e) ohne Lauf: "
                                + ", ".join(f"{d:%d.%m.}" for d in verpasst)))
        else:
            lampen.append(Lampe("Letzter Tageslauf", GRUEN, text))
    if erg.xetra is not None:
        stand = f"Schlusskurse Xetra {pd.Timestamp(erg.xetra):%d.%m.}, NYSE {pd.Timestamp(erg.nyse):%d.%m.}"
        lampen.append(Lampe("Datenstand", GELB if erg.befunde else GRUEN,
                            stand + (f" – Datenbefund in {', '.join(sorted(erg.befunde))}" if erg.befunde else "")))
    if erg.gestoppt:
        lampen.append(Lampe("Abgleich", ROT, "GESTOPPT – " + erg.gestoppt[:160]))
    for buch in betrieb["buecher"]:
        an = buch_freigeschaltet(betrieb, buch)
        lampen.append(Lampe(f"Senden {buch}", GRAU if probe else (GRUEN if an else GRAU), "Probe" if probe else ("an" if an else "aus")))
    return lampen


# --- Übersicht je Buch ---------------------------------------------------------------------------------------------------
@dataclass
class Position:
    ticker: str
    stueck: float
    kaufkurs: float | None          # Ø Kaufkurs in der Handelswährung (ohne Gebühren)
    waehrung: str
    kurs_eur: float | None
    wert_eur: float | None


@dataclass
class BuchKarte:
    buch: str
    art: str
    budget: float
    messbeginn: str | None
    wert: float | None              # Buchwert wie gebucht (Paper, Festpreis), letzter Tageslauf
    wert_modell: float | None       # mit Modellgebühr (Tiered)
    wert_tag: str | None
    kasse: dict[str, float]
    reserviert: dict[str, float]
    rendite: float | None           # TWR seit Messbeginn
    rendite_spyi: float | None      # SPYI Kauf und Halten, gleiche Einzahlungen, TWR
    positionen: list[Position] = field(default_factory=list)
    offene: list[dict] = field(default_factory=list)


def einzahlungen(journal, buch: str) -> pd.Series:
    """Einzahlungen des Buchs: Startkapital am Messbeginn. Weitere Einzahlungen führt das Journal (noch) nicht; sobald es
    sie führt, kommen sie hier dazu (gleiche Einzahlungen für Buch und SPYI-Vergleich, Jakob 10.11.2026)."""
    mb = journal.messbeginn(buch)
    return pd.Series(dtype=float) if mb is None else pd.Series({pd.Timestamp(mb): journal.startkapital(buch)}, dtype=float)


def rendite_seit_messbeginn(werte: pd.Series, einz: pd.Series) -> float | None:
    """TWR des Buchs seit Messbeginn (kennzahlen.performance.zeitgewichtete_rendite). Startpunkt ist die erste Einzahlung
    (Startkapital am Messbeginn); Buchwerte ab dem Tag nach dem Messbeginn."""
    from tradingbot.kennzahlen.performance import zeitgewichtete_rendite

    if not len(einz):
        return None
    start = einz.index.min()
    if len(werte):
        werte = pd.Series(werte.to_numpy(dtype=float), index=pd.to_datetime(werte.index))
        werte = werte[werte.index > start]
    reihe = pd.concat([pd.Series({start: float(einz.loc[start])}), werte]).sort_index() if len(werte) else pd.Series({start: float(einz.loc[start])})
    if len(reihe) < 2:
        return 0.0
    return float(zeitgewichtete_rendite(reihe, einz.reindex(reihe.index).fillna(0.0)).iloc[-1] - 1)


def rendite_spyi(spyi: pd.Series | None, einz: pd.Series, bis) -> float | None:
    """Vergleich (Jakob 10.11.2026): SPYI Kauf und Halten ab dem Schlusskurs am Messbeginn, ohne Kosten, Bruchstücke; jede
    Einzahlung kauft zum Schluss ihres Tages. Zeitgewichtete Rendite (TWR) wie im Phase-2-Abschluss."""
    from tradingbot.kennzahlen.performance import zeitgewichtete_rendite

    if spyi is None or not len(spyi) or not len(einz):
        return None
    kurse = spyi.sort_index()
    kurse.index = pd.to_datetime(kurse.index).tz_localize(None).normalize()
    tage = sorted(set(einz.index) | {pd.Timestamp(bis)})
    stueck, werte = 0.0, {}
    for d in tage:
        k = kurse.loc[:d]
        if not len(k):
            return None
        stueck += float(einz.get(d, 0.0)) / float(k.iloc[-1])
        werte[d] = stueck * float(k.iloc[-1])
    reihe = pd.Series(werte)
    return float(zeitgewichtete_rendite(reihe, einz.reindex(reihe.index).fillna(0.0)).iloc[-1] - 1)


def _kaufkurse(journal, buch: str) -> dict[str, tuple[float, str]]:
    zeilen = journal.db.execute("SELECT ticker, waehrung, SUM(stueck * COALESCE(preis, preis_eur)) w, SUM(stueck) s FROM ausfuehrungen "
                                "WHERE buch=? AND richtung>0 GROUP BY ticker, waehrung", (buch,)).fetchall()
    return {z["ticker"]: (z["w"] / z["s"] if z["s"] else None, z["waehrung"] or "EUR") for z in zeilen}


def buchuebersicht(journal, betrieb: dict, erg) -> list[BuchKarte]:
    karten = []
    for buch, bk in betrieb["buecher"].items():
        letzter = journal.db.execute("SELECT tag, wert, wert_modell FROM buchwerte WHERE buch=? ORDER BY tag DESC LIMIT 1", (buch,)).fetchone()
        einz = einzahlungen(journal, buch)
        werte = journal.buchwerte(buch)
        kasse = journal.kasse_je_waehrung(buch)
        reserviert = {w: b for w, b in journal.reserviert(buch).items() if w != "EUR_gesamt" and b > 1e-9}
        kauf = _kaufkurse(journal, buch)
        positionen = []
        for t, s in sorted(journal.bestand(buch).items()):
            k = erg.kurse_eur.get(t)
            positionen.append(Position(t, s, *(kauf.get(t, (None, "EUR"))), k, None if k is None else s * k))
        offene = [{"id": z["id"], "ticker": z["ticker"], "art": "TAUSCH" if z["art"] == "fx" else ("KAUF" if z["richtung"] > 0 else "VERKAUF"),
                   "stueck": z["stueck"], "limit": z["limit_preis"], "waehrung": z["waehrung"], "order_id": z["order_id"], "status": z["status"]}
                  for z in journal.unterwegs(buch)]
        bis = erg.xetra if erg.xetra is not None else (werte.index.max() if len(werte) else None)
        karten.append(BuchKarte(
            buch, bk["art"], float(bk["budget_eur"]), journal.messbeginn(buch),
            None if letzter is None else letzter["wert"], None if letzter is None else letzter["wert_modell"],
            None if letzter is None else letzter["tag"], kasse, reserviert,
            rendite_seit_messbeginn(werte, einz), None if bis is None else rendite_spyi(erg.spyi, einz, bis), positionen, offene))
    return karten


# --- Namen (Jakob 10.11.2026: „Domino's Pizza (DPZ)“, „iShares Core MSCI Japan (EUNN)“) ---------------------------------
_RECHTSFORM = re.compile(r"(,?\s+(Inc\.?|Incorporated|Corporation|Corp\.?|Co\.?|Company|Ltd\.?|Limited|plc|PLC|N\.V\.|S\.A\.|AG|SE))+$")
_ANTEILSKLASSE = re.compile(r"\s*\((Acc|Dist)\)$")


def kuerzel(ticker: str) -> str:
    return ticker[:-3] if ticker.endswith(".DE") else ticker


def _ohne_rechtsform(name: str) -> str:
    return _RECHTSFORM.sub("", name.strip()).strip(" ,")


@lru_cache(maxsize=1)
def _namenstabelle() -> dict[str, str]:
    """Ticker → Name aus lokalen Quellen, ohne Netz: ETF-/ETC-Namen aus config/technik.yaml und config/betrieb.yaml; US-Aktien
    aus dem Yahoo-Namenscache (daten/cache/namen, richtige Schreibweise), ersatzweise SEC company_tickers (Großbuchstaben)
    und der IBKR-Name aus config/kontrakte.yaml. Rechtsform und Anteilsklasse werden weggelassen."""
    from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration

    namen: dict[str, str] = {}
    try:
        from tradingbot.broker.ibkr import kontrakttabelle

        for t, e in kontrakttabelle().items():
            if e.get("name"):
                namen[t] = _ohne_rechtsform(str(e["name"]).title())
    except Exception:  # noqa: BLE001
        pass
    sec = PROJEKT_WURZEL / "daten" / "cache" / "sec" / "company_tickers.json.gz"
    if sec.exists():
        try:
            for e in json.loads(gzip.decompress(sec.read_bytes())).values():
                namen[str(e["ticker"]).replace(".", "-")] = _ohne_rechtsform(str(e["title"]).title())
        except Exception:  # noqa: BLE001
            pass
    yahoo = PROJEKT_WURZEL / "daten" / "cache" / "namen" / "yahoo.json"
    if yahoo.exists():
        try:
            namen.update({t: _ohne_rechtsform(n) for t, n in json.loads(yahoo.read_text(encoding="utf-8")).items() if n})
        except Exception:  # noqa: BLE001
            pass
    try:
        for e in lade_konfiguration("technik")["universum"]["etfs"]:
            namen[e["ticker"]] = _ANTEILSKLASSE.sub("", e["name"])
        core = lade_konfiguration("betrieb")["core"]
        if core.get("name"):
            namen[core["etf"]] = core["name"]
    except Exception:  # noqa: BLE001
        pass
    namen["EUR.USD"] = "Tausch Euro in US-Dollar"
    return namen


def anzeigename(ticker: str) -> str:
    """„Vollständiger Name (Kürzel)“; ohne bekannten Namen nur das Kürzel."""
    name = _namenstabelle().get(ticker)
    return f"{name} ({kuerzel(ticker)})" if name else kuerzel(ticker)


# --- Gegliederte Details (Jakob 10.11.2026) --------------------------------------------------------------------------------
def _abschnitte(details: str) -> tuple[list[str], list[str], str, list[str]]:
    """Zerlegt den Detailtext (betrieb/buecher.details_text) in Zahlen, Dagegen, Widerlegt und Technisches (z. B. IBKR-Kontrakt)."""
    zahlen, dagegen, widerlegt, technik, teil = [], [], "", [], None
    for zeile in (details or "").splitlines():
        s = zeile.strip()
        if s == "Zahlen:":
            teil = "zahlen"
        elif s == "Was dagegen spricht:":
            teil = "dagegen"
        elif s.startswith("Widerlegt, wenn:"):
            widerlegt, teil = s.removeprefix("Widerlegt, wenn:").strip(), None
        elif s.startswith("•") and teil == "zahlen":
            zahlen.append(s.lstrip("• ").strip())
        elif s.startswith("•") and teil == "dagegen":
            d = s.lstrip("• ").strip()
            if d != "nichts Besonderes":
                dagegen.append(d)
        elif s:
            technik.append(s)
    return zahlen, dagegen, widerlegt, technik


def _eur(x, n=2) -> str:
    return "–" if x is None else f"{x:,.{n}f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def _proz(x) -> str:
    return "–" if x is None else f"{x:+.1%}".replace(".", ",")


def gliederung(bv, u, *, gesperrt: bool = False) -> dict:
    """Detailbereich: Kopf, Warum, Kennzahlen (Kennzahl | Wert | Branchenmedian | Urteil), Filter-Ampel, Was dagegen spricht,
    Widerlegt, wenn, Technisches (eingeklappt). Technik-Vorschläge: Kurs, SMA50, SMA200, Abstand, Stop, max. Verlust in €."""
    v = bv.vorschlag
    art = "TAUSCH" if v.art == "fx" else ("KAUF" if v.richtung > 0 else "VERKAUF")
    zahlen, dagegen, widerlegt, technik = _abschnitte(bv.details)
    daten = getattr(bv, "daten", None) or {}
    limit = f"Limit {bv.limit_order:,.2f} {bv.waehrung}" if bv.limit_order else "ohne Limit"
    kopf = f"{v.buch} · {art} {v.stueck:g} {'EUR' if v.art == 'fx' else 'Stück'} · {limit} · ≈ {_eur(float(v.orderwert))}"
    saetze = [s.strip() for s in re.split(r"(?<=[.!?])\s+", v.these or "") if s.strip()]
    warum = bv.kern or (saetze[0] if saetze else "")
    if saetze and saetze[0] not in warum and len(saetze[0]) < 220:
        warum = f"{warum} {saetze[0]}".strip()
    kennzahlen: list[tuple[str, str, str, bool | None]] = []
    filter_: list[tuple[str, str, str | None]] = []
    if daten.get("typ") == "fundamental":
        kennzahlen = list(daten["kennzahlen"])
        filter_ = [(n, t, f) for n, (t, f) in daten["filter"].items()]
    elif daten.get("typ") == "technik":
        kennzahlen = [("Kurs (Schluss)", _eur(daten.get("kurs")), "", None),
                      ("SMA50", _eur(daten.get("sma50")), "", None),
                      ("SMA200", _eur(daten.get("sma200")), "", None),
                      ("Abstand SMA50 zu SMA200", _proz(daten.get("abstand")), "", None if daten.get("abstand") is None else daten["abstand"] > 0)]
        if "mom" in daten:
            kennzahlen.append(("Momentum 12−1", _proz(daten.get("mom")), "", None if daten.get("mom") is None else daten["mom"] > 0))
        if "stop" in daten:
            kennzahlen += [("Stop (2 × ATR)", _eur(daten.get("stop")), "", None),
                           ("Max. Verlust bis Stop", f"{_eur(daten.get('max_verlust'))} ({daten.get('max_verlust_anteil', 0):.2%} des Buchs)".replace(".", ","), "",
                            None if daten.get("max_verlust_anteil") is None else daten["max_verlust_anteil"] <= 0.0101)]
        if "bestand_wert" in daten:
            kennzahlen.append(("Bestand (Wert)", _eur(daten.get("bestand_wert")), "", None))
        zahlen = []
    hinweise = [f"Risk-Manager: {h}" for h in (u.hinweise or [])]
    return {"titel": anzeigename(v.ticker), "art": art, "kopf": kopf, "veto": [] if u.frei else list(u.gruende),
            "gesperrt": gesperrt, "warum": warum, "kennzahlen": kennzahlen, "zahlen": zahlen, "filter": filter_,
            "dagegen": dagegen + hinweise, "widerlegt": widerlegt, "technisch": technik + ([f"These: {v.these}"] if v.these else [])}


# --- Vorschlagstabelle ---------------------------------------------------------------------------------------------------
@dataclass
class Zeile:
    id: str
    buch: str
    art: str
    stueck: int
    titel: str
    limit: str
    wert: float
    kurz: str
    veto: str
    waehlbar: bool
    gesperrt: bool                  # Buch nicht zum Senden freigeschaltet
    freigabe: str                   # einzeln | sammel
    details: str
    gliederung: dict = field(default_factory=dict)


def vorschlagszeilen(erg, betrieb: dict, *, probe: bool) -> list[Zeile]:
    """Wie die alte Oberfläche: wählbar nur ohne Veto und (außer im Probe-Modus) in freigeschalteten Büchern; Freigabe im
    Realbuch einzeln, in Skalierungsbüchern als Sammelfreigabe je Buch."""
    zeilen = []
    for bv, u in erg.vorschlaege:
        v = bv.vorschlag
        bk = betrieb["buecher"].get(v.buch, {})
        gesperrt = not probe and not buch_freigeschaltet(betrieb, v.buch)
        art = "TAUSCH" if v.art == "fx" else ("KAUF" if v.richtung > 0 else "VERKAUF")
        limit = f"{bv.limit_order:,.2f} {bv.waehrung}" if bv.limit_order else "ohne"
        kern = bv.kern or v.these.split(". ")[0]
        teile = [f"{v.buch} – {art} {v.stueck} × {v.ticker}", "", f"Kern: {kern}", "", f"These: {v.these}"]
        if bv.details:
            teile += ["", bv.details]
        if u.hinweise:
            teile += ["", "Hinweise des Risk-Managers: " + "; ".join(u.hinweise)]
        if not u.frei:
            teile += ["", "VETO: " + "; ".join(u.gruende)]
        if gesperrt:
            teile += ["", "Buch zum Senden nicht freigeschaltet – nicht freigebbar"]
        zeilen.append(Zeile(v.id, v.buch, art, v.stueck, anzeigename(v.ticker), limit, float(v.orderwert), kern,
                            "; ".join(u.gruende) if not u.frei else "", u.frei and not gesperrt, gesperrt,
                            bk.get("freigabe", "einzeln"), "\n".join(teile), gliederung(bv, u, gesperrt=gesperrt)))
    return zeilen


# --- Meldungen -----------------------------------------------------------------------------------------------------------
_FEHLER = ("GESTOPPT", "gestoppt", "ABGELEHNT", "VETO", "Veto", "abgebrochen", "fehlgeschlagen", "weicht ab", "nicht verbunden",
           "Read-Only im Gateway ist aktiv", "NICHT gesichert", "ohne Beleg", "unerklärte", "Fehler")
_HINWEIS = ("(kein Abbruch)", "HINWEIS", "Hinweis", "Zeitpunkt", "nicht vorschlagbar", "verfallen", "Nachtrag", "nachgeholt",
            "vermutet", "UNBESTÄTIGT", "Datenprüfung", "nicht eingelesen", "nicht möglich", "erstmals", "nicht kaufbar",
            "Aufbau wie beim ersten Lauf", "ohne Lauf")
_OK = ("stimmen", "stimmt", "angenommen", "gesichert", "verbunden", "geprüft", "eingelesen", "belegt")


def meldungsart(text: str) -> str:
    """ok | hinweis | fehler | info – für die farbige Darstellung im Protokoll."""
    if text.startswith("(kein Abbruch)"):
        return "hinweis"
    if any(m in text for m in _FEHLER):
        return "fehler"
    if any(m in text for m in _HINWEIS):
        return "hinweis"
    if any(m in text for m in _OK):
        return "ok"
    return "info"
