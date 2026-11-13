"""Benachrichtigungen des Tageslaufs (Entscheidungen Jakob 12.11.2026).

(a) Kurzfassung nach jedem echten Tageslauf: Vorschläge je Buch, Abgleich ok/gestoppt, abgelehnte und verfallene Orders
    seit dem letzten Lauf, Buchwerte.
(b) Erinnerung, wenn an einem Xetra-Handelstag bis 22:25 kein Tageslauf lief: lokal per Aufgabenplanung
    (tools/waechter.py) und extern über Healthchecks.io (Totmannschalter, funktioniert auch bei ausgeschaltetem Laptop).
(c) Sofortmeldung bei Stopp oder Fehler (Stopp im Tageslauf, Abbruch oder Ablehnung beim Senden, Ausnahme, nach dem
    Senden bei IBKR offene Order, die im Journal nicht unterwegs ist).

Kanal: Telegram (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID in .env). Lebenszeichen: HEALTHCHECKS_PING_URL in .env.

Sicherheit:
- Der Bot sendet nur. Er ruft nie Nachrichten ab (kein getUpdates, kein Webhook, kein offener Port); über Nachrichten
  lässt sich nichts auslösen.
- Nachrichten werden aus einer Positivliste gebaut (Zahlen, Buchnamen, Ticker, Status). Freitexte aus dem Tageslauf
  (etwa Kassenstände des Kontos im Stopptext) werden nie weitergereicht. `bereinigen` entfernt zusätzlich Konto-IDs und
  die Werte geheimer Variablen aus der .env.
- `benachrichtigung.eurobetraege: false` (für den Echtbetrieb): nur Prozente und Status, keine Eurobeträge.
- Ein Fehler beim Benachrichtigen bricht den Tageslauf nie ab; er steht nur im Protokoll. Probe und Kopie melden nie.
"""
from __future__ import annotations

import os
import re
import sqlite3
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, time

KONTO_MUSTER = (re.compile(r"\bDU[A-Z]?\d\w*…?"), re.compile(r"\bU\d{5,}\b"))   # Paper „DU…“/„DUR3…“, Live „U1234567“
GEHEIME_VARIABLEN = ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "HEALTHCHECKS_PING_URL", "FLEX_TOKEN", "FLEX_QUERY_ID",
                     "TIINGO_API_KEY", "FRED_API_KEY", "SEC_USER_AGENT")
MAX_LAENGE = 4000                                   # Telegram erlaubt 4096 Zeichen je Nachricht
ERINNERUNG_AB = time(22, 25)               # Abendlauf startet laut Ablauf erst nach 22:15 (Jakob 13.11.2026)
SENDEPROBLEME = (                                   # Anfang der Meldung von freigeben_und_senden → Kategorie (ohne Inhalt)
    ("Gateway nicht verbunden", "Gateway nicht verbunden – nichts gesendet"),
    ("Abgleich mit IBKR weicht ab – nichts gesendet", "Abgleich vor dem Senden weicht ab – nichts gesendet"),
    ("Read-Only im Gateway ist aktiv", "Read-Only im Gateway aktiv"),
    ("Senden abgebrochen", "Senden abgebrochen (Ausnahme)"),
    ("Abgleich der offenen Orders nach dem Senden fehlgeschlagen", "Abgleich der offenen Orders fehlgeschlagen"),
)
ORDER_OFFEN = "Order bei IBKR offen, im Journal nicht unterwegs"      # gleicher Text wie tageslauf.ORDER_OFFEN_MELDUNG
TICKER_MUSTER = re.compile(r"[A-Z0-9][A-Z0-9.\-]{0,14}")


# --- Formatierung -------------------------------------------------------------------------------------------------
def _de(x: float, stellen: int = 2) -> str:
    return f"{x:,.{stellen}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _eur(x: float) -> str:
    return f"{_de(x)} €"


def _prozent(x: float) -> str:
    return f"{'+' if x >= 0 else '−'}{_de(abs(x) * 100)} %"


def bereinigen(text: str, umgebung: dict | None = None) -> str:
    """Letzte Sicherung vor dem Versand: Konto-IDs und Werte geheimer .env-Variablen entfernen."""
    umgebung = os.environ if umgebung is None else umgebung
    for muster in KONTO_MUSTER:
        text = muster.sub("[entfernt]", text)
    for name in GEHEIME_VARIABLEN:
        wert = (umgebung.get(name) or "").strip().strip('"')
        if len(wert) >= 6:
            text = text.replace(wert, "[entfernt]")
    return text[:MAX_LAENGE]


# --- Inhalte (Positivliste) ---------------------------------------------------------------------------------------
def stopp_kurz(gestoppt: str) -> str:
    """Kategorie und betroffene Titel eines Stopps, ohne Stückzahlen und Kassenstände.
    „Abgleich mit IBKR weicht ab – Tageslauf gestoppt: SAP.DE: Bücher 3 Stück, IBKR 5 Stück; Kasse EUR: …“
    → „Abgleich mit IBKR weicht ab; betroffen: SAP.DE, Kasse EUR“."""
    kategorie, _, rest = gestoppt.partition(" – ")
    _, _, liste = rest.partition(": ")
    betroffen = []
    for teil in liste.split("; "):
        kopf = teil.split(":", 1)[0].strip()
        if re.fullmatch(r"Kasse [A-Z]{3}|[A-Z0-9][A-Z0-9.\-]{0,9}", kopf) and kopf not in betroffen:
            betroffen.append(kopf)
    kategorie = kategorie.strip() if re.fullmatch(r"[\wÄÖÜäöüß \-]{3,80}", kategorie.strip()) else "Tageslauf gestoppt"
    return f"{kategorie}; betroffen: {', '.join(betroffen[:10])}" if betroffen else kategorie


def vorheriger_lauf(journal, vor: datetime) -> str | None:
    """Zeit des letzten Tageslaufs (Ereignis „tageslauf“ oder „abgleich“) vor `vor` (ISO, lokale Zeit)."""
    z = journal.db.execute("SELECT MAX(zeit) FROM ereignisse WHERE art IN ('tageslauf','abgleich') AND zeit < ?",
                           (vor.replace(tzinfo=None).isoformat(timespec="seconds"),)).fetchone()
    return z[0] if z else None


def _buchwerte(journal, buch: str) -> list[sqlite3.Row]:
    return journal.db.execute("SELECT tag, wert, wert_modell FROM buchwerte WHERE buch=? ORDER BY tag DESC LIMIT 2", (buch,)).fetchall()


def kurzfassung(erg, journal, betrieb: dict, *, eurobetraege: bool = True, seit: str | None = None) -> str:
    """(a) Kurzfassung eines Tageslaufs; bei Stopp mit Kopfzeile „GESTOPPT“ (zugleich Sofortmeldung c)."""
    jetzt = erg.jetzt
    buchstopps = getattr(erg, "buchstopps", None) or {}
    kopf = (f"⛔ Tageslauf GESTOPPT {jetzt:%d.%m.%Y %H:%M}" if erg.gestoppt else
            f"⚠️ Tageslauf {jetzt:%d.%m.%Y %H:%M} – gestoppt: {', '.join(sorted(buchstopps))}" if buchstopps else
            f"✅ Tageslauf {jetzt:%d.%m.%Y %H:%M}")
    zeilen = [kopf]
    if erg.xetra is not None and erg.nyse is not None:
        zeilen.append(f"Signaltag Xetra {erg.xetra:%d.%m.}, NYSE {erg.nyse:%d.%m.}")
    abgleich = getattr(erg, "abgleich", "nicht_geprueft")
    if erg.gestoppt:
        zeilen.append(f"Abgleich: GESTOPPT – {stopp_kurz(erg.gestoppt)}. Keine Vorschläge; Details im Protokoll am Laptop.")
    elif abgleich == "ok":
        zeilen.append("Abgleich: ok")
    elif abgleich == "teilweise":
        zeilen.append("Abgleich: ok außer in gestoppten Büchern")
    else:
        zeilen.append("Abgleich: nicht geprüft (Gateway nicht verbunden), wird vor dem Senden nachgeholt")

    je_buch: dict[str, list[int]] = {}
    for bv, u in erg.vorschlaege:
        z = je_buch.setdefault(bv.vorschlag.buch, [0, 0])
        z[0 if u.frei else 1] += 1
    if not erg.gestoppt:
        if je_buch:
            n_frei, n_veto = sum(z[0] for z in je_buch.values()), sum(z[1] for z in je_buch.values())
            zeilen.append(f"Vorschläge: {n_frei + n_veto} ({n_frei} frei, {n_veto} Veto)")
            zeilen += [f"  {b}: {f + v} ({f} frei" + (f", {v} Veto)" if v else ")") for b, (f, v) in sorted(je_buch.items())]
        else:
            zeilen.append("Vorschläge: keine")
    if not erg.gestoppt:                             # A1: Stopp je Buch – Kategorie und Titel, ohne Stück und Beträge
        from tradingbot.betrieb.buchstopp import kurz
        zeilen += [kurz(b, e) + " – keine Vorschläge" for b, e in sorted(buchstopps.items())]
    for b, befunde in sorted(erg.befunde.items()):
        zeilen.append(f"Datenprüfung: {b} ohne Vorschläge ({len(befunde)} Befund{'e' if len(befunde) != 1 else ''})")

    zeilen += kassenzeilen(journal, eurobetraege=eurobetraege, seit=seit)
    if seit:
        for status, wort in (("abgelehnt", "Abgelehnt"), ("verfallen", "Verfallen")):
            rows = journal.db.execute("SELECT buch, ticker, art FROM vorschlaege WHERE status=? AND aktualisiert>=? ORDER BY buch, ticker",
                                      (status, seit)).fetchall()
            if rows:
                titel = ", ".join(f"{r['buch']} {'Tausch' if r['art'] == 'fx' else r['ticker']}" for r in rows[:15])
                zeilen.append(f"{wort} seit dem letzten Lauf: {len(rows)} ({titel}{', …' if len(rows) > 15 else ''})")

    zeilen.append("Buchwerte:" if eurobetraege else "Buchwerte (gegenüber Startkapital):")
    for buch in betrieb["buecher"]:
        rows = _buchwerte(journal, buch)
        if not rows:
            zeilen.append(f"  {buch}: noch kein Buchwert")
            continue
        start = journal.startkapital(buch)
        w, wm = float(rows[0]["wert"]), rows[0]["wert_modell"]
        stand = "" if erg.xetra is None or rows[0]["tag"] >= str(erg.xetra) else f" (Stand {datetime.fromisoformat(rows[0]['tag']):%d.%m.})"
        modell = ""
        if wm is not None:
            modell = f", Modell {_eur(float(wm))} ({_prozent(float(wm) / start - 1)})" if eurobetraege else f" (Modell {_prozent(float(wm) / start - 1)})"
        vortag = f"; Vortag {_prozent(w / float(rows[1]['wert']) - 1)}" if len(rows) > 1 and rows[1]["wert"] else ""
        if eurobetraege:
            zeilen.append(f"  {buch}: {_eur(w)} ({_prozent(w / start - 1)}){modell}{vortag}{stand}")
        else:
            zeilen.append(f"  {buch}: {_prozent(w / start - 1)}{modell}{vortag}{stand}")
    return "\n".join(zeilen)


def kassenzeilen(journal, *, eurobetraege: bool = True, seit: str | None = None) -> list[str]:
    """Dividenden seit dem letzten Lauf (je Titel und Buch, netto mit Quellensteuer), offene Dividenden-Vormerkungen und
    „vermutet“-Übernahmen in die Kassenbasis (A0, Jakob 12.11.2026). Ohne Eurobeträge nur Titel, Buch und Status."""
    zeilen = []
    grenze = seit or ""
    rows = journal.db.execute(
        "SELECT ticker, buch, waehrung, SUM(betrag) AS netto, SUM(CASE WHEN art='quellensteuer' THEN betrag ELSE 0 END) AS qst "
        "FROM kassenbuchungen WHERE gebucht>=? GROUP BY ticker, buch, waehrung ORDER BY ticker, buch", (grenze,)).fetchall()
    for r in rows[:15]:
        if eurobetraege:
            qst = f" (QSt {_de(-float(r['qst']))})" if abs(float(r["qst"])) > 1e-9 else ""
            zeilen.append(f"Dividende {r['ticker']}: {r['buch']} {_de(float(r['netto']))} {r['waehrung']} netto{qst}")
        else:
            zeilen.append(f"Dividende gebucht: {r['ticker']} ({r['buch']})")
    konto = journal.zustand("_konto")
    for v in konto.get("dividende_vormerkungen", []):
        zeilen.append(f"Dividende vorgemerkt, Flex-Beleg folgt: {v['waehrung']} {_de(float(v['betrag']))} (seit {v['bis']})" if eurobetraege
                      else f"Dividende vorgemerkt, Flex-Beleg folgt ({v['waehrung']}, seit {v['bis']})")
    for e in konto.get("buchungen_ohne_buchbezug", []):
        zeit = e.get("zeit") or e.get("tag", "")
        if seit and zeit < seit:
            continue
        if eurobetraege:
            posten = e.get("posten") or []
            betraege = ", ".join(f"{p['waehrung']} {'+' if float(p['betrag']) >= 0 else '−'}{_de(abs(float(p['betrag'])))}" for p in posten)
            zeilen.append("Kassendifferenz übernommen (Zinsen/Gebühren vermutet)" + (f": {betraege}" if betraege else ""))
        else:
            zeilen.append("Kassendifferenz übernommen")
    return zeilen


def fehlermeldung(was: str, ausnahme: BaseException, jetzt: datetime) -> str:
    """(c) Ausnahme: nur der Typ, nie der Text (er kann Beträge oder Pfade enthalten)."""
    return f"❌ {was} fehlgeschlagen {jetzt:%d.%m.%Y %H:%M}: {type(ausnahme).__name__}. Details im Fenster bzw. Protokoll am Laptop."


def sendeprobleme(journal, ids: list[str], seit: str, meldungen: list[str], jetzt: datetime) -> str | None:
    """(c) Probleme beim Senden: abgelehnte oder unbestätigte Orders, Veto bei der zweiten Prüfung, Abbruch, bei IBKR offene
    Orders, die im Journal nicht unterwegs sind (nur die Kürzel). None = alles gut."""
    kategorien = []
    for m in meldungen:
        for anfang, kategorie in SENDEPROBLEME:
            if anfang in m and kategorie not in kategorien:
                kategorien.append(kategorie)
        if m.startswith(ORDER_OFFEN + ": "):                # Positivliste: nur Kürzel, keine Freitexte (Jakob 13.11.2026)
            titel = [t for t in m[len(ORDER_OFFEN) + 2:].split(" – ")[0].split(", ") if TICKER_MUSTER.fullmatch(t)]
            kategorien.append(f"{ORDER_OFFEN}: {', '.join(titel) or 'Titel unbekannt'} (nichts storniert)")
    zeilen = []
    if ids:
        platz = ",".join("?" * len(ids))
        for status, wort in (("abgelehnt", "abgelehnt"), ("unbestaetigt", "unbestätigt (im Gateway prüfen)"), ("veto", "Veto bei der zweiten Prüfung")):
            rows = journal.db.execute(f"SELECT buch, ticker, art FROM vorschlaege WHERE id IN ({platz}) AND status=? AND aktualisiert>=? "
                                      "ORDER BY buch, ticker", (*ids, status, seit)).fetchall()
            if rows:
                zeilen.append(f"{len(rows)} {wort}: " + ", ".join(f"{r['buch']} {'Tausch' if r['art'] == 'fx' else r['ticker']}" for r in rows[:15]))
    if not kategorien and not zeilen:
        return None
    return "\n".join([f"⚠️ Senden {jetzt:%d.%m.%Y %H:%M}: Problem"] + kategorien + zeilen + ["Details im Protokoll am Laptop."])


def erinnerung(tag: date) -> str:
    """(b) lokale Erinnerung (tools/waechter.py)."""
    return (f"⏰ Heute ({tag:%d.%m.%Y}, Xetra-Handelstag) lief bis 22:25 kein Tageslauf. "
            "Freigabe ist bis 24 Uhr möglich (US-Käufe und Tausch empfohlen 22:05–22:50).")


# --- Versand ------------------------------------------------------------------------------------------------------
class Telegram:
    """Nur Senden (sendMessage). Ruft nie getUpdates auf: Nachrichten an den Bot werden nie gelesen."""

    def __init__(self, token: str, chat_id: str, *, zeitlimit: float = 8.0, oeffnen=urllib.request.urlopen):
        self.token, self.chat_id, self.zeitlimit, self._oeffnen = token, chat_id, zeitlimit, oeffnen

    def senden(self, text: str) -> None:
        daten = urllib.parse.urlencode({"chat_id": self.chat_id, "text": text, "disable_web_page_preview": "true"}).encode()
        anfrage = urllib.request.Request(f"https://api.telegram.org/bot{self.token}/sendMessage", data=daten, method="POST")
        with self._oeffnen(anfrage, timeout=self.zeitlimit) as antwort:
            if getattr(antwort, "status", 200) != 200:
                raise RuntimeError(f"Telegram antwortet mit Status {antwort.status}")


@dataclass
class Melder:
    """Versand mit Protokollzeile als Ergebnis; wirft nie. `kanaele`: Objekte mit `senden(text)`."""
    kanaele: list = field(default_factory=list)
    lebenszeichen_url: str | None = None
    eurobetraege: bool = True
    zeitlimit: float = 8.0
    oeffnen: object = urllib.request.urlopen

    def melden(self, text: str) -> str:
        if not self.kanaele:
            return "Benachrichtigung: kein Kanal eingerichtet (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID in .env)"
        text = bereinigen(text)
        ergebnis = []
        for k in self.kanaele:
            try:
                k.senden(text)
                ergebnis.append(f"{type(k).__name__} gesendet")
            except Exception as f:  # noqa: BLE001 – Benachrichtigung bricht nie den Lauf ab
                ergebnis.append(f"{type(k).__name__} fehlgeschlagen ({bereinigen(type(f).__name__)})")
        return "Benachrichtigung: " + ", ".join(ergebnis)

    def lebenszeichen(self, fehler: bool = False, *, nur_protokoll: bool = False) -> str:
        """Ping an Healthchecks.io (ohne Inhalt); `fehler` meldet den Lauf als fehlgeschlagen (…/fail).

        `nur_protokoll` (…/log): Eintrag im Healthchecks-Protokoll ohne Statuswechsel – für den Verbindungstest, damit ein
        Testping am Abend keinen ausgefallenen Tageslauf überdeckt.
        """
        if not self.lebenszeichen_url:
            return "Lebenszeichen: nicht eingerichtet (HEALTHCHECKS_PING_URL in .env)"
        url = self.lebenszeichen_url.rstrip("/") + ("/fail" if fehler else "/log" if nur_protokoll else "")
        try:
            with self.oeffnen(urllib.request.Request(url, data=b"", method="POST"), timeout=self.zeitlimit):
                pass
            zusatz = " (Fehler)" if fehler else " (nur Protokoll)" if nur_protokoll else ""
            return "Lebenszeichen an Healthchecks gesendet" + zusatz
        except Exception as f:  # noqa: BLE001
            return f"Lebenszeichen fehlgeschlagen ({type(f).__name__})"


def melder_aus_env(betrieb: dict, umgebung: dict | None = None) -> Melder:
    """Melder laut config/betrieb.yaml (`benachrichtigung`) und .env; fehlende Variablen = Kanal aus."""
    umgebung = os.environ if umgebung is None else umgebung
    k = betrieb.get("benachrichtigung", {}) or {}
    zeitlimit = float(k.get("zeitlimit_s", 8))
    kanaele = []
    token, chat = (umgebung.get("TELEGRAM_BOT_TOKEN") or "").strip(), (umgebung.get("TELEGRAM_CHAT_ID") or "").strip()
    if k.get("telegram", False) and token and chat:
        kanaele.append(Telegram(token, chat, zeitlimit=zeitlimit))
    url = (umgebung.get("HEALTHCHECKS_PING_URL") or "").strip() if k.get("healthchecks", False) else ""
    return Melder(kanaele, url or None, bool(k.get("eurobetraege", True)), zeitlimit)


VERBINDUNG_OK = "Verbindung ok"


def verbindungstest(melder: Melder) -> list[str]:
    """Testnachricht „Verbindung ok“ (fester Text, keine Kontodaten) und ein Healthchecks-Ping ohne Statuswechsel."""
    return [melder.melden(VERBINDUNG_OK), melder.lebenszeichen(nur_protokoll=True)]


# --- Abläufe ------------------------------------------------------------------------------------------------------
def nach_tageslauf(erg, journal, betrieb: dict, melder: Melder) -> list[str]:
    """Nach jedem echten Tageslauf: Kurzfassung (bei Stopp als Sofortmeldung) und Lebenszeichen. Gibt Protokollzeilen zurück."""
    try:
        text = kurzfassung(erg, journal, betrieb, eurobetraege=melder.eurobetraege, seit=vorheriger_lauf(journal, erg.jetzt))
        zeilen = [melder.melden(text)]
    except Exception as f:  # noqa: BLE001
        zeilen = [f"Benachrichtigung: Kurzfassung nicht erstellt ({type(f).__name__})"]
    sofort = getattr(erg, "sofort", None) or []
    if sofort:                                       # A1: Buchstopp, Stop gerissen im gestoppten Buch, Aufhebung
        zeilen.append(melder.melden("⛔ Sofortmeldung\n" + "\n".join(sofort[:15])))
    zeilen.append(melder.lebenszeichen())
    try:
        journal.ereignis("benachrichtigung", "; ".join(zeilen))
    except Exception:  # noqa: BLE001
        pass
    return zeilen


def lauf_heute(journal_datei, tag: date) -> bool:
    """Lief am `tag` ein echter Tageslauf (Ereignis „tageslauf“ oder „abgleich“, auch gestoppte Läufe)? Nur lesend."""
    db = sqlite3.connect(f"file:{journal_datei}?mode=ro", uri=True)
    try:
        return db.execute("SELECT 1 FROM ereignisse WHERE art IN ('tageslauf','abgleich') AND zeit >= ? AND zeit < ? LIMIT 1",
                          (tag.isoformat(), f"{tag.isoformat()}T99")).fetchone() is not None
    finally:
        db.close()


def waechter(jetzt: datetime, journal_datei, melder: Melder) -> str:
    """(b) Lokale Prüfung um 22:25 (Aufgabenplanung). Handelstag ohne Lauf → Erinnerung. An Xetra-Feiertagen unter der Woche
    ein Lebenszeichen, damit Healthchecks keinen Fehlalarm gibt. Gestartet nach Mitternacht (Laptop war aus) → nichts."""
    from tradingbot.betrieb.kalender import ist_handelstag

    tag = jetzt.date()
    if jetzt.time() < ERINNERUNG_AB:
        return f"vor {ERINNERUNG_AB:%H:%M} – nichts geprüft"
    if not ist_handelstag("xetra", tag):
        if tag.weekday() < 5:
            return "Xetra-Feiertag – " + melder.lebenszeichen()
        return "Wochenende – nichts zu tun"
    if lauf_heute(journal_datei, tag):
        return "Tageslauf lief heute – keine Erinnerung"
    return melder.melden(erinnerung(tag))
