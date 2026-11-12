"""Bardividenden und Quellensteuer im Betrieb (A0, Entscheidungen Jakob 12.11.2026).

Beleg: Flex-Bargeldtransaktionen (FLEX_TOKEN, FLEX_QUERY_ID in .env) der Arten „Dividends“, „Payment In Lieu Of
Dividends“ und „Withholding Tax“. Kein Buchen ohne Flex-Beleg; gebucht wird automatisch mit Meldung, je
`transactionID` und Buch genau einmal (Storno- und Korrekturzeilen sind eigene Belege mit Vorzeichen).

Aufteilung auf die Bücher: Bestand je Buch zum Handelsschluss vor dem Ex-Tag (Kauf am Ex-Tag: kein Anspruch; Verkauf
am Ex-Tag: Anspruch bleibt). Probe: Summe der Buchstücke × Satz je Stück (aus der Flex-Beschreibung) = Brutto auf
`abgleich_kasse_toleranz`; sonst keine Buchung und Stopp. Der Betrag wird anteilig nach Stück verteilt, auf Cent
gerundet, den Rest bekommt das letzte Buch. Quellensteuer folgt der Aufteilung der zugehörigen Dividende (actionID,
sonst Conid und Zahltag). Gebucht wird in der Originalwährung (USD-Dividende in die USD-Kasse des Buchs), der Eurowert
zum Kurs des Laufs (wie bei Ausführungen: Fremdwährung zum Kurs des Vorgangs).

Zahltag ohne Beleg: Flex reicht nur bis zum Vortag. Der Kassenabgleich (betrieb/tageslauf.py) merkt einen Kassenzugang,
der zur Abnahme der aufgelaufenen Dividenden (AccruedDividend) passt, als „Beleg folgt“ vor – nur wenn
`dividenden.vormerkung` an ist und `accrued_dividend_ausweis` (netto/brutto) geprüft wurde. Hier:
- Vormerkung bestätigen: Flex-Netto (Dividende + Quellensteuer) im Zeitfenster der Vormerkung in derselben Währung
  gleich dem vorgemerkten Betrag (Toleranz) → aufgelöst. Weicht er ab → Stopp und Sofortmeldung.
- Frist: Keine Flex-Bestätigung nach `vormerkung_frist_handelstage` (3) Xetra-Handelstagen → Stopp und Sofortmeldung.
- „vermutet“-Übernahme in die Kassenbasis (bis 10 €) mit gleichem Betrag im selben Zeitfenster → aus der Kassenbasis
  zurücknehmen, weil der Betrag jetzt in den Büchern steht (keine Doppelzählung).
- Prüfung brutto/netto: Beim ersten Fall vergleicht der Lauf die festgehaltene Abnahme von AccruedDividend mit Brutto
  und Netto laut Flex und meldet das Ergebnis; scharf geschaltet wird erst nach Jakobs Entscheidung.

Steuerliche Markierungen sind Hinweise und als „zu prüfen“ gekennzeichnet.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

import pandas as pd

ARTEN = {"Dividends": "dividende", "Payment In Lieu Of Dividends": "ersatzzahlung", "Withholding Tax": "quellensteuer"}
STEUER = {
    "dividende": "zu prüfen: Kapitalertrag (§ 20 Abs. 1 Nr. 1 EStG)",
    "ersatzzahlung": "zu prüfen: Ersatzzahlung statt Dividende (Payment in Lieu), steuerlich wie Dividende?",
    "quellensteuer": "zu prüfen: ausländische Quellensteuer, Anrechnung (§ 32d Abs. 5 EStG)",
}
SATZ = re.compile(r"\b[A-Z]{3}\s+([0-9]+(?:\.[0-9]+)?)\s+PER\s+SHARE", re.I)
KAT_NICHT_VERBUCHBAR = "Dividendenbeleg nicht verbuchbar"
KAT_ABWEICHUNG = "Dividende weicht von der Vormerkung ab"
KAT_FRIST = "Dividende ohne Flex-Beleg nach Frist"


def einstellungen(b: dict) -> dict:
    """`dividenden` aus config/betrieb.yaml; scharf nur mit Schalter und geprüftem Ausweis."""
    k = b.get("dividenden", {}) or {}
    ausweis = str(k.get("accrued_dividend_ausweis", "unbekannt"))
    return {"vormerkung": bool(k.get("vormerkung", False)), "ausweis": ausweis,
            "scharf": bool(k.get("vormerkung", False)) and ausweis in ("netto", "brutto"),
            "frist": int(k.get("vormerkung_frist_handelstage", 3)), "quellensteuer_max": float(k.get("quellensteuer_max", 0.30))}


def vorgemerkt_je_waehrung(konto: dict) -> dict[str, float]:
    summe: dict[str, float] = {}
    for v in konto.get("dividende_vormerkungen", []):
        summe[v["waehrung"]] = summe.get(v["waehrung"], 0.0) + float(v["betrag"])
    return summe


def vormerkbar(d: float, abnahme: float, cfg: dict, toleranz: float) -> float | None:
    """Kassenzugang `d` passt zur Abnahme der aufgelaufenen Dividenden → vorzumerkender Betrag, sonst None.
    netto: |d − Abnahme| ≤ Toleranz. brutto: Abnahme × (1 − höchste Quellensteuer) − Toleranz ≤ d ≤ Abnahme + Toleranz."""
    if cfg["ausweis"] == "netto" and abs(d - abnahme) <= toleranz + 1e-9:
        return d
    if cfg["ausweis"] == "brutto" and abnahme * (1 - cfg["quellensteuer_max"]) - toleranz - 1e-9 <= d <= abnahme + toleranz + 1e-9:
        return d
    return None


# --- Belege ------------------------------------------------------------------------------------------------------------
@dataclass
class Beleg:
    beleg_id: str
    art: str                       # dividende | ersatzzahlung | quellensteuer
    conid: int | None
    symbol: str
    waehrung: str
    betrag: float                  # mit Vorzeichen (Quellensteuer negativ, Storno umgekehrt)
    ex_tag: str | None
    zahltag: str | None
    satz: float | None             # Dividende je Stück laut Beschreibung
    action_id: str


def _tag(text: str | None) -> str | None:
    ziffern = re.sub(r"\D", "", (text or "").split(";")[0])[:8]
    return f"{ziffern[:4]}-{ziffern[4:6]}-{ziffern[6:8]}" if len(ziffern) == 8 else None


def belege_aus_flex(zeilen: list[dict]) -> list[Beleg]:
    """Dividenden-, Ersatzzahlungs- und Quellensteuerzeilen der Flex-Bargeldtransaktionen; anderes (Einzahlungen, Zinsen,
    Gebühren) bleibt beim Kassenabgleich."""
    belege = []
    for z in zeilen:
        art = ARTEN.get((z.get("type") or "").strip())
        if not art or not z.get("transactionID") or (z.get("levelOfDetail") or "DETAIL").upper() not in ("DETAIL", ""):
            continue
        m = SATZ.search(z.get("description") or "")
        conid = z.get("conid") or ""
        belege.append(Beleg(beleg_id=str(z["transactionID"]), art=art, conid=int(conid) if conid.strip().isdigit() else None,
                            symbol=(z.get("symbol") or "").strip(), waehrung=(z.get("currency") or "").strip(),
                            betrag=float(z.get("amount") or 0.0), ex_tag=_tag(z.get("exDate")),
                            zahltag=_tag(z.get("dateTime")) or _tag(z.get("settleDate")) or _tag(z.get("reportDate")),
                            satz=float(m.group(1)) if m else None, action_id=(z.get("actionID") or "").strip()))
    return belege


def stueck_vor(journal, buch: str, ticker: str, ex_tag: str) -> float:
    """Bestand des Buchs zum Handelsschluss vor dem Ex-Tag (Ausführungen und gebuchte Kapitalmaßnahmen mit Datum vor dem Ex-Tag)."""
    z = journal.db.execute("SELECT COALESCE(SUM(richtung * stueck), 0) FROM ausfuehrungen WHERE buch=? AND ticker=? AND substr(zeit, 1, 10) < ?",
                           (buch, ticker, ex_tag)).fetchone()[0]
    km = sum(float(p["stueck"]) for p in journal.massnahmen_posten(buch, bis=ex_tag) if p["ticker"] == ticker)
    return float(z) + km


def aufteilen(betrag: float, gewichte: dict[str, float]) -> dict[str, float]:
    """Betrag anteilig nach Stück, auf Cent gerundet; das letzte Buch bekommt den Rest (Summe stimmt exakt)."""
    summe = sum(gewichte.values())
    namen = list(gewichte)
    anteile = {n: round(betrag * gewichte[n] / summe, 2) for n in namen[:-1]}
    anteile[namen[-1]] = round(betrag - sum(anteile.values()), 2)
    return anteile


def _eur(betrag: float, waehrung: str, fx: dict[str, float]) -> float:
    return betrag if waehrung == "EUR" else betrag / float(fx[waehrung])


@dataclass
class Verbuchung:
    gebucht: list[str] = field(default_factory=list)
    stopp: list[str] = field(default_factory=list)


def verbuchen(journal, buecher: list[str], belege: list[Beleg], *, ticker_je_conid: dict[int, str], fx: dict[str, float],
              toleranz: float, quelle: str) -> Verbuchung:
    """Neue Belege je Buch buchen (Dividenden vor Quellensteuer). Nicht verbuchbar → nichts von diesem Beleg, Stopp."""
    erg = Verbuchung()
    neu = [b for b in belege if not journal.beleg_gebucht(b.beleg_id)]
    for b in sorted(neu, key=lambda x: (x.art == "quellensteuer", x.zahltag or "", x.beleg_id)):
        ticker = ticker_je_conid.get(b.conid) if b.conid is not None else None
        ticker = ticker or b.symbol.replace(" ", "-")
        kopf = ticker if re.fullmatch(r"[A-Z0-9][A-Z0-9.\-]{0,9}", ticker or "") else "Beleg"
        if b.waehrung != "EUR" and b.waehrung not in fx:
            erg.stopp.append(f"{kopf}: Währung {b.waehrung or '?'} ohne Kurs im Lauf (Beleg {b.beleg_id})")
            continue
        if b.art == "quellensteuer":
            vorbild = _dividende_zu(journal, b, ticker)
            if not vorbild:
                erg.stopp.append(f"{kopf}: Quellensteuer {b.betrag:+,.2f} {b.waehrung} ohne gebuchte Dividende (Beleg {b.beleg_id}, Zahltag {b.zahltag})")
                continue
            gewichte = {z["buch"]: float(z["stueck"]) for z in vorbild}
            ex_tag, satz = vorbild[0]["ex_tag"], vorbild[0]["satz"]
        else:
            if b.ex_tag is None or b.satz is None:
                erg.stopp.append(f"{kopf}: Ex-Tag oder Satz je Stück fehlt im Beleg {b.beleg_id}")
                continue
            ex_tag, satz = b.ex_tag, b.satz
            gewichte = {n: s for n in buecher if (s := stueck_vor(journal, n, ticker, ex_tag)) > 1e-9}
            if not gewichte:
                erg.stopp.append(f"{kopf}: kein Buch hielt den Titel vor dem Ex-Tag {ex_tag} (Beleg {b.beleg_id}, {b.betrag:+,.2f} {b.waehrung})")
                continue
            probe = sum(gewichte.values()) * satz
            if abs(probe - abs(b.betrag)) > toleranz + 1e-9:
                erg.stopp.append(f"{kopf}: Probe stimmt nicht – Bücher {sum(gewichte.values()):g} Stück × {satz:g} = {probe:,.2f}, "
                                 f"Flex {abs(b.betrag):,.2f} {b.waehrung} (Ex-Tag {ex_tag}, Beleg {b.beleg_id})")
                continue
        for buch, anteil in aufteilen(b.betrag, gewichte).items():
            journal.kassenbuchung(beleg_id=b.beleg_id, buch=buch, art=b.art, ticker=ticker, conid=b.conid, action_id=b.action_id,
                                  ex_tag=ex_tag, zahltag=b.zahltag, waehrung=b.waehrung, betrag=anteil,
                                  betrag_eur=round(_eur(anteil, b.waehrung, fx), 2), stueck=gewichte[buch], satz=satz,
                                  steuer=STEUER[b.art], quelle=quelle)
            text = f"{'Quellensteuer' if b.art == 'quellensteuer' else 'Dividende'} {ticker}: {buch} {anteil:+,.2f} {b.waehrung} " \
                   f"({gewichte[buch]:g} Stück, Ex-Tag {ex_tag}, Zahltag {b.zahltag}; {STEUER[b.art]}; Beleg {quelle})"
            journal.ereignis("dividende", text, buch)
            erg.gebucht.append(text)
    return erg


def _dividende_zu(journal, b: Beleg, ticker: str) -> list:
    if b.action_id:
        z = journal.kassenbuchungen("action_id=? AND art!='quellensteuer'", (b.action_id,))
        if z:
            return _letzter_beleg(z)
    return _letzter_beleg(journal.kassenbuchungen("ticker=? AND zahltag=? AND art!='quellensteuer'", (ticker, b.zahltag)))


def _letzter_beleg(zeilen) -> list:
    """Die Buchzeilen des ersten Dividendenbelegs (bei Storno/Neubuchung gleiche Stückaufteilung)."""
    if not zeilen:
        return []
    erster = zeilen[0]["beleg_id"]
    return [z for z in zeilen if z["beleg_id"] == erster]


# --- Vormerkungen, „vermutet“-Übernahmen, Prüfung brutto/netto ----------------------------------------------------------
def flex_im_fenster(journal, waehrung: str, von: str, bis: str) -> tuple[float, float, int]:
    """Netto (alle Arten), Brutto (Dividende und Ersatzzahlung) und Zahl der Belege in `waehrung` mit Zahltag in (von, bis]."""
    zeilen = journal.kassenbuchungen("waehrung=? AND zahltag>? AND zahltag<=?", (waehrung, von, bis))
    netto = sum(float(z["betrag"]) for z in zeilen)
    brutto = sum(float(z["betrag"]) for z in zeilen if z["art"] != "quellensteuer")
    return round(netto, 2), round(brutto, 2), len({z["beleg_id"] for z in zeilen})


def handelstage_nach(tag: str, heute: date) -> int:
    """Xetra-Handelstage nach `tag` bis einschließlich `heute`."""
    from tradingbot.betrieb.kalender import ist_handelstag

    d, n = pd.Timestamp(tag).date() + timedelta(days=1), 0
    while d <= heute:
        n += ist_handelstag("xetra", d)
        d += timedelta(days=1)
    return n


@dataclass
class Klaerung:
    meldungen: list[str] = field(default_factory=list)
    stopp: dict[str, list[str]] = field(default_factory=dict)      # Kategorie → Einträge „Kopf: Text“


def vormerkungen_klaeren(journal, b: dict, heute: date, toleranz: float) -> Klaerung:
    """Vormerkungen bestätigen oder (Abweichung, Frist) stoppen; „vermutet“-Übernahmen mit Flex-Beleg zurücknehmen;
    Ausweis von AccruedDividend (brutto/netto) am ersten Fall prüfen. Speichert den Kontozustand."""
    cfg = einstellungen(b)
    k = Klaerung()
    konto = journal.zustand("_konto")
    if not konto:
        return k
    offen = []
    for v in konto.get("dividende_vormerkungen", []):
        netto, _, n = flex_im_fenster(journal, v["waehrung"], v["von"], v["bis"])
        if n:
            if abs(netto - float(v["betrag"])) <= toleranz + 1e-9:
                k.meldungen.append(f"Dividenden-Vormerkung {v['waehrung']} {float(v['betrag']):,.2f} vom {v['bis']} durch Flex bestätigt")
                journal.ereignis("dividende", k.meldungen[-1])
                continue
            k.stopp.setdefault(KAT_ABWEICHUNG, []).append(
                f"Kasse {v['waehrung']}: vorgemerkt {float(v['betrag']):,.2f} am {v['bis']}, Flex netto {netto:,.2f} ({n} Beleg(e)) – "
                "bitte im Client Portal klären")
        elif handelstage_nach(v["bis"], heute) > cfg["frist"]:
            k.stopp.setdefault(KAT_FRIST, []).append(
                f"Kasse {v['waehrung']}: vorgemerkt {float(v['betrag']):,.2f} am {v['bis']}, nach {cfg['frist']} Handelstagen kein Flex-Beleg – "
                "Flex-Abfrage und Client Portal prüfen")
        offen.append(v)
    konto["dividende_vormerkungen"] = offen

    basis = konto.get("kassenbasis") or {}
    for e in konto.get("buchungen_ohne_buchbezug", []):
        if "von" not in e:
            continue                                     # ältere Einträge ohne Zeitfenster bleiben unverändert
        for p in e.get("posten", []):
            if p["waehrung"] in e.setdefault("belegt", []):
                continue
            netto, _, n = flex_im_fenster(journal, p["waehrung"], e["von"], e["tag"])
            if n and abs(netto - float(p["betrag"])) <= toleranz + 1e-9:
                basis[p["waehrung"]] = basis.get(p["waehrung"], 0.0) - float(p["betrag"])
                e["belegt"].append(p["waehrung"])
                k.meldungen.append(f"Kassendifferenz vom {e['tag']} ({p['waehrung']} {float(p['betrag']):+,.2f}) war Dividende laut Flex: "
                                   "aus der Kassenbasis zurückgenommen, steht jetzt in den Büchern")
                journal.ereignis("kassenbasis", k.meldungen[-1])
    if basis:
        konto["kassenbasis"] = basis

    for a in konto.get("dividende_abnahmen", []):
        if a.get("ausgewertet"):
            continue
        netto, brutto, n = flex_im_fenster(journal, a["waehrung"], a["von"], a["bis"])
        if not n:
            continue
        ab = float(a["abnahme"])
        befund = "netto" if abs(ab - netto) <= toleranz + 1e-9 else "brutto" if abs(ab - brutto) <= toleranz + 1e-9 else "unklar"
        a.update(ausgewertet=True, befund=befund, flex_netto=netto, flex_brutto=brutto)
        konto["accrued_dividend_befund"] = {"waehrung": a["waehrung"], "befund": befund, "tag": a["bis"]}
        text = (f"Prüfung AccruedDividend ({a['waehrung']}, Zahltag bis {a['bis']}): Abnahme {ab:,.2f} entspricht {befund.upper()} "
                f"(Flex brutto {brutto:,.2f}, netto {netto:,.2f}; Kassenzugang {float(a['kassenzugang']):,.2f}). "
                + ("Vormerkung erst nach Jakobs Entscheidung scharf schalten (config/betrieb.yaml: dividenden)." if not cfg["scharf"]
                   else f"Eingestellt: {cfg['ausweis']}" + (" – PASST NICHT, bitte prüfen" if befund != cfg["ausweis"] else "")))
        k.meldungen.append(text)
        journal.ereignis("dividende", text)
    journal.zustand_speichern("_konto", konto)
    return k


def stopptext(k: Klaerung, nicht_verbuchbar: list[str]) -> str | None:
    """Ein Stopptext „Kategorie – Tageslauf gestoppt: Kopf: …; Kopf: …“ (Kategorie nach Vorrang)."""
    stopp = dict(k.stopp)
    if nicht_verbuchbar:
        stopp[KAT_NICHT_VERBUCHBAR] = nicht_verbuchbar
    for kat in (KAT_ABWEICHUNG, KAT_FRIST, KAT_NICHT_VERBUCHBAR):
        if kat in stopp:
            eintraege = [e for liste in stopp.values() for e in liste]
            return f"{kat} – Tageslauf gestoppt: " + "; ".join(eintraege)
    return None


def dividenden_klaeren(journal, b: dict, flex, fx: dict[str, float], heute: date, meldungen: list[str]) -> str | None:
    """Ablauf im Tageslauf vor dem Kassenabgleich: Flex-Belege buchen, Vormerkungen und Übernahmen klären. Gibt den
    Stopptext zurück oder None."""
    from tradingbot.broker.ibkr import _ticker_je_conid

    tol = float(b.get("sicherheit", {}).get("abgleich_kasse_toleranz", 0.05))
    nicht_verbuchbar: list[str] = []
    bargeld = getattr(flex, "bargeld", None) if flex is not None else None
    if bargeld is None:
        if journal.zustand("_konto").get("dividende_vormerkungen"):
            meldungen.append("Dividenden: Flex-Abfrage nicht eingerichtet – Vormerkungen bleiben offen")
    else:
        try:
            zeilen, quelle = bargeld()
        except Exception as f:  # noqa: BLE001 – Flex nicht erreichbar: nichts buchen, Frist läuft weiter
            meldungen.append(f"Dividenden: Flex-Abfrage fehlgeschlagen ({type(f).__name__}) – nichts gebucht, Frist der Vormerkungen läuft")
        else:
            v = verbuchen(journal, list(b["buecher"]), belege_aus_flex(zeilen), ticker_je_conid=_ticker_je_conid(), fx=fx,
                          toleranz=tol, quelle=quelle)
            meldungen.extend(v.gebucht)
            nicht_verbuchbar = v.stopp
    k = vormerkungen_klaeren(journal, b, heute, tol)
    meldungen.extend(k.meldungen)
    return stopptext(k, nicht_verbuchbar)
