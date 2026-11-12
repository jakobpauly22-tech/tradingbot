"""Kapitalmaßnahmen aus Flex erkennen (A1, Jakob 12.11.2026) – in A1 nur erkennen, festhalten und melden, nie buchen.

Quelle: Abschnitt „Corporate Actions“ der Flex-Abfrage (XML-Element `CorporateAction`). Feldnamen und Typ-Kürzel laut
IBKR Activity Flex Query Reference, Abschnitt Corporate Actions (geprüft 12.11.2026): u. a. `type` (zwei Buchstaben),
`conid`, `symbol`, `isin`, `currency`, `quantity`, `proceeds`, `value`, `amount`, `reportDate`, `dateTime`,
`description`, `transactionID`. Achtung: TC heißt „Merger“ (Übernahme), ein Tickerwechsel läuft als IC „Issue Change“.

Annahmen, am ersten echten Beleg zu prüfen (bis dahin bewusst vorsichtig):
- Die Zeilen einer Maßnahme werden über `actionID` gebündelt (in der Referenz nicht aufgeführt, in Bargeldtransaktionen
  vorhanden); fehlt es, über Typ, Stichtag und Beschreibung ohne Symbolteil.
- Barkomponente = `proceeds` (Übernahme gegen Bargeld), Stückänderung = `quantity`.

Folgen (Jakobs Entscheidungen vom 12.11.2026): Ein Buch, das einen betroffenen Titel hält oder eine Order dafür unterwegs
hat, wird gestoppt (betrieb/buchstopp.py). Gebucht wird erst ab A2 (Split, Tickerwechsel) bzw. A3/A4 nach Bestätigung.
Neue Conids landen nur als Vorschlag im Journal (Tabelle `conid_vorschlaege`); config/kontrakte.yaml ändert Jakob selbst.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Typ-Kürzel laut IBKR-Referenz (Auszug) → Art im Journal; alles andere: „sonstige“ (erkannt, nicht zuordenbar)
ARTEN = {"FS": "split", "FI": "split", "RS": "reverse_split", "IC": "tickerwechsel", "TC": "uebernahme", "SO": "abspaltung",
         "DW": "delisting"}
NAMEN = {"split": "Aktiensplit", "reverse_split": "Reverse-Split", "tickerwechsel": "Tickerwechsel/Issue Change",
         "uebernahme": "Übernahme (Merger)", "abspaltung": "Abspaltung", "delisting": "Delisting (wertlos)", "sonstige": "Kapitalmaßnahme"}
# steuerliche Markierung immer „zu prüfen“ (Jakob 12.11.2026)
STEUER = {"split": "zu prüfen: Split steuerneutral, Anschaffungsdaten übertragen",
          "reverse_split": "zu prüfen: Reverse-Split steuerneutral, Barausgleich für Bruchteile als Veräußerung",
          "tickerwechsel": "zu prüfen: reiner Tickerwechsel steuerneutral",
          "uebernahme": "zu prüfen: Barabfindung Veräußerung (§ 20 Abs. 2 EStG), Aktientausch ggf. § 20 Abs. 4a EStG",
          "abspaltung": "zu prüfen: Abspaltung § 20 Abs. 4a Satz 7 EStG, Einstand nach Kursverhältnis",
          "delisting": "zu prüfen: wertlose Ausbuchung, Verlustverrechnung",
          "sonstige": "zu prüfen"}
OFFEN = ("erkannt", "bestaetigt")
KONTO = "_konto"


@dataclass
class Massnahme:
    beleg_id: str
    code: str
    art: str
    tag: str | None
    beschreibung: str
    posten: list[dict] = field(default_factory=list)   # je Zeile: conid, symbol, isin, waehrung, stueck, betrag

    @property
    def bar(self) -> dict[str, float]:
        """Barkomponente je Währung (proceeds)."""
        aus: dict[str, float] = {}
        for p in self.posten:
            if abs(p["betrag"]) > 1e-9:
                aus[p["waehrung"]] = aus.get(p["waehrung"], 0.0) + p["betrag"]
        return aus


def _zahl(text) -> float:
    try:
        return float(str(text).replace(",", "")) if str(text or "").strip() else 0.0
    except ValueError:
        return 0.0


def _tag(text) -> str | None:
    t = re.sub(r"[^0-9]", "", str(text or "").partition(";")[0])
    return f"{t[:4]}-{t[4:6]}-{t[6:8]}" if len(t) >= 8 else None


def ticker_fuer(conid: int | None, symbol: str, waehrung: str, ticker_je_conid: dict[int, str]) -> str:
    """Conid → Yahoo-Ticker über config/kontrakte.yaml; sonst wie broker/ibkr.ticker_aus: EUR → „.DE“, Leerzeichen → „-“."""
    if conid and conid in ticker_je_conid:
        return ticker_je_conid[conid]
    return f"{symbol}.DE" if waehrung == "EUR" else symbol.replace(" ", "-")


def belege_aus_flex(zeilen: list[dict]) -> list[Massnahme]:
    """CorporateAction-Zeilen (Attribute als Text) → Maßnahmen, gebündelt über actionID (sonst Typ, Stichtag, Beschreibung)."""
    gruppen: dict[str, list[dict]] = {}
    for z in zeilen:
        if (z.get("levelOfDetail") or "DETAIL").upper() not in ("DETAIL", ""):
            continue                                                  # Summenzeilen nicht doppelt zählen
        aid = (z.get("actionID") or "").strip()
        tag = _tag(z.get("reportDate")) or _tag(z.get("dateTime"))
        sym = (z.get("symbol") or "").strip()
        rest = (z.get("description") or "").replace(sym, "").strip() if sym else (z.get("description") or "")
        schluessel = f"CA:{aid}" if aid else f"CA:{(z.get('type') or '').strip()}:{tag}:{rest[:60]}"
        gruppen.setdefault(schluessel, []).append(z)
    aus = []
    for schluessel, gz in gruppen.items():
        code = (gz[0].get("type") or "").strip().upper()
        if schluessel.count(":") > 1:                                 # ohne actionID: Belegnummer aus der kleinsten transactionID
            ids = sorted(str(z.get("transactionID") or "") for z in gz)
            schluessel = f"CA:{code}:{ids[0]}" if ids and ids[0] else schluessel
        posten = []
        for z in gz:
            cid = str(z.get("conid") or "").strip()
            posten.append({"conid": int(float(cid)) if cid.replace(".", "", 1).isdigit() else None, "symbol": (z.get("symbol") or "").strip(),
                           "isin": (z.get("isin") or z.get("securityID") or "").strip() or None,
                           "waehrung": (z.get("currency") or "").strip() or "EUR",
                           "stueck": _zahl(z.get("quantity")), "betrag": _zahl(z.get("proceeds"))})
        tage = [t for t in (_tag(z.get("reportDate")) or _tag(z.get("dateTime")) for z in gz) if t]
        aus.append(Massnahme(beleg_id=schluessel, code=code, art=ARTEN.get(code, "sonstige"), tag=min(tage) if tage else None,
                             beschreibung=(gz[0].get("actionDescription") or gz[0].get("description") or "").strip()[:300],
                             posten=posten))
    return sorted(aus, key=lambda m: (m.tag or "", m.beleg_id))


def _ticker_je_conid() -> dict[int, str]:
    try:
        from tradingbot.broker.ibkr import _ticker_je_conid as tabelle
        return tabelle()
    except Exception:  # noqa: BLE001 – ohne Kontrakttabelle: Symbolregel
        return {}


def erkennen(journal, buecher: list[str], flex, meldungen: list[str], *, ticker_je_conid: dict[int, str] | None = None) -> list[str]:
    """Neue Kapitalmaßnahmen aus Flex festhalten (Status „erkannt“, kein Buchen) und melden. Betroffen sind die Bücher, die
    einen Titel der Maßnahme halten oder eine Order dafür unterwegs haben. Gibt die Beleg-IDs der neu erkannten zurück."""
    laden = getattr(flex, "kapitalmassnahmen", None) if flex is not None else None
    if laden is None:
        return []
    try:
        zeilen, quelle = laden()
    except Exception as f:  # noqa: BLE001 – Flex nicht erreichbar: nichts erkannt, Abgleich entscheidet
        meldungen.append(f"Kapitalmaßnahmen: Flex nicht abrufbar ({type(f).__name__}) – nicht geprüft")
        return []
    tabelle = ticker_je_conid if ticker_je_conid is not None else _ticker_je_conid()
    neu = []
    for m in belege_aus_flex(zeilen):
        for p in m.posten:
            p["ticker"] = ticker_fuer(p["conid"], p["symbol"], p["waehrung"], tabelle)
        titel = {p["ticker"] for p in m.posten}
        betroffen = [b for b in buecher if titel & set(journal.bestand(b)) or titel & {z["ticker"] for z in journal.unterwegs(b)}]
        felder = {"code": m.code, "tag": m.tag, "beschreibung": m.beschreibung, "steuer": STEUER[m.art], "quelle": quelle}
        konto_posten = [{k: p[k] for k in ("ticker", "conid", "symbol", "isin", "stueck", "waehrung", "betrag")} for p in m.posten]
        if not journal.massnahme(beleg_id=m.beleg_id, buch=KONTO, art=m.art, posten=konto_posten, **felder):
            continue                                                      # schon erkannt (Flex liefert 30 Tage)
        for b in betroffen:
            journal.massnahme(beleg_id=m.beleg_id, buch=b, art=m.art, **felder)
        neu.append(m.beleg_id)
        text = (f"Kapitalmaßnahme erkannt: {NAMEN[m.art]} ({m.code or '?'}) am {m.tag or '?'}, Titel {', '.join(sorted(titel))}; "
                + (f"betroffen: {', '.join(betroffen)} – Buch gestoppt bis zur Buchung" if betroffen else "kein Buch betroffen")
                + f"; Steuer {STEUER[m.art]}; noch nicht gebucht")
        journal.ereignis("kapitalmassnahme", text)
        meldungen.append(text)
        for p in m.posten:                                                # neue Conids nur als Vorschlag
            if p["conid"] and p["stueck"] > 0 and p["conid"] not in tabelle:
                if journal.conid_vorschlag(p["conid"], symbol=p["symbol"], isin=p["isin"], waehrung=p["waehrung"],
                                           ticker_vorschlag=p["ticker"], beleg_id=m.beleg_id):
                    meldungen.append(f"Neue Conid aus Beleg {m.beleg_id}: IBKR-Symbol {p['symbol']}, ISIN {p['isin'] or '–'} → Vorschlag "
                                     f"Yahoo-Ticker {p['ticker']}; config/kontrakte.yaml bitte selbst ergänzen (nicht automatisch)")
    return neu


def offene(journal) -> list[dict]:
    """Erkannte, noch nicht gebuchte Maßnahmen mit Titeln, Barkomponente und betroffenen Büchern."""
    aus = []
    for k in journal.massnahmen("buch=? AND status IN (?, ?)", (KONTO, *OFFEN)):
        posten = journal.massnahme_posten(k["beleg_id"])
        bar: dict[str, float] = {}
        for p in posten:
            if abs(p["betrag"] or 0.0) > 1e-9:
                bar[p["waehrung"]] = bar.get(p["waehrung"], 0.0) + float(p["betrag"])
        buecher = [r["buch"] for r in journal.massnahmen("beleg_id=? AND buch!=?", (k["beleg_id"], KONTO))]
        aus.append({"beleg_id": k["beleg_id"], "art": k["art"], "titel": {p["ticker"] for p in posten if p["ticker"]}, "bar": bar,
                    "buecher": buecher})
    return aus


def bar_passend(offen: list[dict], waehrung: str, d: float, toleranz: float) -> list[dict]:
    """Kassendifferenz passt in Währung und Betrag (± Toleranz) zur Barkomponente erkannter Maßnahmen laut Flex-Beleg
    (Jakob 12.11.2026): einzeln oder alle offenen dieser Währung zusammen. Leere Liste = passt nicht."""
    mit_bar = [m for m in offen if waehrung in m["bar"]]
    for m in mit_bar:
        if abs(m["bar"][waehrung] - d) <= toleranz + 1e-9:
            return [m]
    if len(mit_bar) > 1 and abs(sum(m["bar"][waehrung] for m in mit_bar) - d) <= toleranz + 1e-9:
        return mit_bar
    return []
