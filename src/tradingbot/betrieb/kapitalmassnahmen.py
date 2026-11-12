"""Kapitalmaßnahmen aus Flex erkennen (A1) und Split, Reverse-Split, Tickerwechsel buchen (A2, Jakob 12.11.2026).

Quelle: Abschnitt „Corporate Actions“ der Flex-Abfrage (XML-Element `CorporateAction`). Feldnamen und Typ-Kürzel laut
IBKR Activity Flex Query Reference, Abschnitt Corporate Actions (geprüft 12.11.2026): u. a. `type` (zwei Buchstaben),
`conid`, `symbol`, `isin`, `currency`, `quantity`, `proceeds`, `value`, `amount`, `reportDate`, `dateTime`,
`description`, `transactionID`. Achtung: TC heißt „Merger“ (Übernahme), ein Tickerwechsel läuft als IC „Issue Change“.

Annahmen, am ersten echten Beleg zu prüfen (bis dahin bewusst vorsichtig):
- Die Zeilen einer Maßnahme werden über `actionID` gebündelt (in der Referenz nicht aufgeführt, in Bargeldtransaktionen
  vorhanden); fehlt es, über Typ, Stichtag und Beschreibung ohne Symbolteil.
- Barkomponente = `proceeds` (Übernahme gegen Bargeld), Stückänderung = `quantity`.

Folgen (Jakobs Entscheidungen vom 12.11.2026): Ein Buch, das einen betroffenen Titel hält oder eine Order dafür unterwegs
hat, wird gestoppt (betrieb/buchstopp.py). A2 bucht Split, Reverse-Split und Tickerwechsel bei exakt passender Probe
(Abschnitt A2 unten); Übernahme, Delisting und Abspaltung folgen in A3/A4 nach Bestätigung.
Neue Conids landen nur als Vorschlag im Journal (Tabelle `conid_vorschlaege`); config/kontrakte.yaml ändert Jakob selbst.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

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
                + f"; Steuer {STEUER[m.art]}; noch nicht gebucht"
                + ("; Bestätigung in der Oberfläche nötig" if m.art in BESTAETIGUNG else
                   "; unbekannte Art – wird nie automatisch gebucht, nach Prüfung in der Oberfläche ablehnen und quittieren"
                   if m.art == "sonstige" else ""))
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
    """Nicht gebuchte Maßnahmen (erkannt, bestätigt, abgelehnt) mit Status, Titeln, Barkomponente und betroffenen Büchern.
    Abgelehnte bleiben dabei, damit Abweichungen ihrer Titel dem Buch zugeordnet werden statt alles zu stoppen (A3)."""
    aus = []
    for k in journal.massnahmen("buch=? AND status IN (?, ?, ?)", (KONTO, *OFFEN, "abgelehnt")):
        posten = journal.massnahme_posten(k["beleg_id"])
        bar: dict[str, float] = {}
        for p in posten:
            if abs(p["betrag"] or 0.0) > 1e-9:
                bar[p["waehrung"]] = bar.get(p["waehrung"], 0.0) + float(p["betrag"])
        buecher = [r["buch"] for r in journal.massnahmen("beleg_id=? AND buch!=?", (k["beleg_id"], KONTO))]
        aus.append({"beleg_id": k["beleg_id"], "art": k["art"], "status": k["status"], "titel": {p["ticker"] for p in posten if p["ticker"]},
                    "bar": bar, "buecher": buecher})
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


# === A2 (Jakob 12.11.2026): Split, Reverse-Split, Tickerwechsel automatisch buchen ===========================================
#
# Entscheidungen: (1) nur bei exakt passender Probe (Stück ganzzahlig exakt, Kasse ± 0,05), sonst Stopp und Meldung;
# (2) Spitzen nach größtem Rest, alles im Journal; (3) Werte in Kurseinheiten ÷ r mit Journal-Ereignis, Liste unten,
# Vollständigkeit per Test; (4) Kursreihe nur im Speicher des Laufs bereinigen, Cache/Tresor/Backtest unberührt;
# Fundamental-Bücher bleiben gestoppt, solange Kurs und Kennzahlen je Aktie nicht zum selben Stand passen;
# (5) Tickerwechsel erst nach Jakobs Umstellung von config/kontrakte.yaml (ggf. technik.yaml), bis dahin Stopp.
# r = neue Stück je alte Stück („SPLIT 2 FOR 1“ → 2, „SPLIT 1 FOR 10“ → 0,1; wie die Yahoo-Spalte `split`).

BUCHBAR = ("split", "reverse_split", "tickerwechsel")
SPLITS = ("split", "reverse_split")
TOLERANZ_KASSE = 0.05
BAND_SPRUNG = 0.15                     # Sprung am Stichtag passt zum Verhältnis, wenn Schluss/Vortag · r in 1 ± 15 %
FENSTER_TAGE = (7, 3)                  # Sprung bzw. Yahoo-Split-Ereignis von Stichtag − 7 bis + 3 Kalendertage

# Alle gespeicherten Felder, eingeordnet nach Einheit (Entscheidung 3). „kurs“ = je Anteil, wird bei offenen Vorgängen
# ÷ r gerechnet; „stueck“ = × r; „historisch“ = Beleg in alten Einheiten, bleibt (Belegprinzip; die Anzeige rechnet über
# Einstand ÷ Stück); „neutral“ = keine Einheit je Anteil (Beträge gesamt, Texte, Daten, Gewichte, Ränge).
# Indikatoren (SMA, ATR, 55-Tage-Hoch, 20-Tage-Tief, RSI, ADX, 12−1) werden NICHT gespeichert, sondern bei jedem Lauf aus
# der Kursreihe gerechnet – sie passen, sobald die Reihe bereinigt ist. Trailing-Stops mit gespeichertem Hochpunkt gibt es
# nicht (Stop fest: Einstieg − 2 × ATR). test_kurseinheiten_vollstaendig prüft, dass hier nichts fehlt.
EINHEITEN: dict[str, dict[str, str]] = {
    "vorschlaege": {"limit_preis": "kurs", "letzter_kurs_eur": "kurs", "stop": "kurs", "stueck": "stueck",
                    **{s: "neutral" for s in ("id", "erstellt", "signaltag", "buch", "ticker", "art", "waehrung", "richtung", "these",
                                              "frei", "gruende", "hinweise", "status", "freigabe_bis", "order_id", "aktualisiert", "kern",
                                              "details", "meldung")}},
    "ausfuehrungen": {**{s: "historisch" for s in ("stueck", "preis_eur", "preis", "eroeffnung")},
                      **{s: "neutral" for s in ("exec_id", "order_ref", "buch", "ticker", "richtung", "gebuehr_eur", "zeit", "waehrung",
                                                "gebuehr", "gebuehr_waehrung", "boerse", "gebuehr_ibkr", "gebuehr_ibkr_waehrung",
                                                "gebuehr_modell_eur", "quelle", "gebuehr_angenommen")}},
    "dividenden": {"stueck": "historisch", **{s: "neutral" for s in ("buch", "ticker", "ex_tag", "betrag_eur")}},
    "kassenbuchungen": {"stueck": "historisch", "satz": "historisch",
                        **{s: "neutral" for s in ("beleg_id", "buch", "art", "ticker", "conid", "action_id", "ex_tag", "zahltag", "waehrung",
                                                  "betrag", "betrag_eur", "steuer", "quelle", "gebucht")}},
    "kapitalmassnahmen_posten": {"stueck": "historisch",
                                 **{s: "neutral" for s in ("beleg_id", "buch", "nr", "ticker", "conid", "symbol", "isin", "waehrung", "betrag",
                                                           "betrag_eur", "einstand", "einstand_eur", "angeschafft", "art")}},
    "kapitalmassnahmen": {s: "neutral" for s in ("beleg_id", "buch", "code", "art", "tag", "beschreibung", "status", "steuer", "quelle",
                                                 "erkannt", "aktualisiert")},
    "buecher": {s: "neutral" for s in ("buch", "startkapital", "messbeginn")},
    "ereignisse": {s: "neutral" for s in ("zeit", "art", "buch", "text")},
    "zustand": {"buch": "neutral", "json": "zustand", "aktualisiert": "neutral"},     # Inhalt: Abschnitte *_zustand unten
    "buchwerte": {s: "neutral" for s in ("buch", "tag", "wert", "kasse", "wert_modell")},
    "conid_vorschlaege": {s: "neutral" for s in ("conid", "symbol", "isin", "waehrung", "ticker_vorschlag", "beleg_id", "status", "erstellt")},
    "tausche": {s: "neutral" for s in ("exec_id", "order_ref", "buch", "von", "nach", "betrag_von", "betrag_nach", "gebuehr_eur", "zeit",
                                       "gebuehr_ibkr", "gebuehr_ibkr_waehrung", "gebuehr_modell_eur", "quelle")},
    # Strategiezustand Technik (betrieb/buecher.zustand_speichern), je Lauf als „vor“ und „nach“ gespeichert
    "technik_lauf": {"signaltag": "neutral", "vor": "technik_zustand", "nach": "technik_zustand", "vor_signaltag": "neutral"},
    "technik_zustand": {"positionen": "je_titel", "gesperrt": "je_titel", "pruefmonat": "je_titel"},
    "technik_position": {"stop": "kurs", "atr_signal": "kurs", "regel": "neutral", "signal_tag": "neutral", "kauf_tag": "neutral"},
    # Fundamental (betrieb/buecher.fundamentalbuch): Zielgewichte und Ränge je Titel, keine Kurse
    "fundamental_zustand": {"letzter_signaltag": "neutral", "ziel": "je_titel", "rang": "je_titel"},
    # Kontozustand und Buchstopps: nur Beträge gesamt, Daten, Texte
    "konto_zustand": {s: "neutral" for s in ("kassenbasis", "festgehalten", "zinsbuchungen", "letzter_kassenabgleich", "aufgelaufene_zinsen", "zinsstand_tag",
                                             "aufgelaufene_dividenden", "tageszins", "dividende_vormerkungen", "dividende_abnahmen",
                                             "accrued_dividend_befund", "buchungen_ohne_buchbezug", "kennzahlen_passend",
                                             "split_quelle_flex")},
    # Split-Verhältnis aus Flex für die Aktienzahl (Jakob 12.11.2026, SPYI-Fall): je Beleg im Kontozustand
    "split_quelle_flex": {s: "neutral" for s in ("ticker", "tag", "r", "buecher", "status", "vorgeschlagen", "quittiert")},
    "buchstopp_eintrag": {s: "neutral" for s in ("seit", "kategorie", "titel", "belege", "details", "abweichung_weg", "quittung_noetig")},
}


def verhaeltnis(beschreibung: str | None) -> float | None:
    """r aus der IBKR-Beschreibung „… SPLIT 2 FOR 1 …“ (neue Stück je alte Stück); None, wenn nicht lesbar."""
    m = re.search(r"\bSPLIT\s+(\d+(?:\.\d+)?)\s+FOR\s+(\d+(?:\.\d+)?)", str(beschreibung or ""), re.IGNORECASE)
    if not m or float(m.group(2)) <= 0 or float(m.group(1)) <= 0:
        return None
    return float(m.group(1)) / float(m.group(2))


def position_umrechnen(p: dict, r: float) -> dict:
    """Strategiezustand einer Position: alle Felder in Kurseinheiten (EINHEITEN["technik_position"]) ÷ r."""
    neu = dict(p)
    for feld, einheit in EINHEITEN["technik_position"].items():
        if einheit == "kurs" and neu.get(feld) is not None:
            neu[feld] = float(neu[feld]) / r
    return neu


def zustand_umrechnen(z: dict, alt: str, neu: str, r: float) -> tuple[dict, list[str]]:
    """Strategiezustand eines Buchs (Technik mit „vor“/„nach“ oder flach, Fundamental): Position `alt` ÷ r in Kurseinheiten,
    Schlüssel je Titel alt → neu. Gibt (neuer Zustand, Änderungen als Text) zurück."""
    aenderungen: list[str] = []

    def teil(d: dict, wo: str) -> dict:
        d = dict(d)
        pos = dict(d.get("positionen") or {})
        if alt in pos:
            vorher = pos.pop(alt)
            nachher = position_umrechnen(vorher, r)
            pos[neu] = nachher
            felder = [f for f, e in EINHEITEN["technik_position"].items() if e == "kurs" and vorher.get(f) is not None]
            aenderungen.append(f"{wo}{alt}: " + ", ".join(f"{f} {float(vorher[f]):.4f} → {float(nachher[f]):.4f}" for f in felder)
                               + (f", Schlüssel {alt} → {neu}" if neu != alt else ""))
        if "positionen" in d:
            d["positionen"] = pos
        for schluessel in ("gesperrt", "pruefmonat", "ziel", "rang"):
            if alt != neu and isinstance(d.get(schluessel), dict) and alt in d[schluessel]:
                d[schluessel] = {(neu if k == alt else k): v for k, v in d[schluessel].items()}
                aenderungen.append(f"{wo}{schluessel}: Schlüssel {alt} → {neu}")
        return d

    if "nach" in z or "vor" in z:
        z = dict(z)
        for wo in ("vor", "nach"):
            if isinstance(z.get(wo), dict):
                z[wo] = teil(z[wo], f"{wo}: ")
        return z, aenderungen
    return teil(z, ""), aenderungen


def vorschlag_umrechnen(z, r: float) -> dict:
    """Offener Vorschlag: Felder in Kurseinheiten ÷ r, Stück × r (EINHEITEN["vorschlaege"])."""
    werte = {}
    for feld, einheit in EINHEITEN["vorschlaege"].items():
        if z[feld] is None:
            continue
        if einheit == "kurs":
            werte[feld] = float(z[feld]) / r
        elif einheit == "stueck":
            s = float(z[feld]) * r
            werte[feld] = int(round(s)) if abs(s - round(s)) < 1e-9 else s
    return werte


def _tage(kurse):
    idx = pd.DatetimeIndex(kurse.index)
    return idx.tz_localize(None) if idx.tz is not None else idx


def sprung_tag(kurse, r: float, tag: str):
    """Tag des unbereinigten Sprungs in der Kursreihe: Schluss/Vortag · r ≈ 1 (± BAND_SPRUNG) im Fenster um den Stichtag.
    None = Reihe schon bereinigt (oder kein passender Sprung)."""
    if kurse is None or len(kurse) < 2 or "close" not in kurse or abs(r - 1) <= BAND_SPRUNG:
        return None
    t = pd.Timestamp(tag)
    idx = _tage(kurse)
    c = kurse["close"].to_numpy(dtype=float)
    beste = None
    for i in range(1, len(c)):
        if not (t - pd.Timedelta(days=FENSTER_TAGE[0]) <= idx[i] <= t + pd.Timedelta(days=FENSTER_TAGE[1])) or c[i - 1] <= 0:
            continue
        q = c[i] / c[i - 1] * r
        if abs(q - 1) <= BAND_SPRUNG and (beste is None or abs(q - 1) < beste[0]):
            beste = (abs(q - 1), kurse.index[i])
    return None if beste is None else beste[1]


def selbst_bereinigen(kurse, r: float, tag: str):
    """Kursreihe auf den Stand nach dem Split bringen, solange Yahoo die Historie noch nicht bereinigt hat (Entscheidung 4):
    vor dem Sprungtag Kurse und Ausschüttung ÷ r, Volumen × r. Nur eine Kopie im Speicher – der Kurs-Cache bleibt
    unverändert. Ist die Reihe schon bereinigt (kein Sprung), kommt sie unverändert zurück: keine Doppelbereinigung.
    Gibt (Reihe, Sprungtag oder None) zurück."""
    d = sprung_tag(kurse, r, tag)
    if d is None:
        return kurse, None
    k = kurse.copy()
    vor = k.index < d
    for spalte in ("open", "high", "low", "close", "dividende"):
        if spalte in k.columns:
            k.loc[vor, spalte] = k.loc[vor, spalte] / r
    if "volume" in k.columns:
        k.loc[vor, "volume"] = k.loc[vor, "volume"] * r
    k.attrs = {**kurse.attrs, "selbst_bereinigt": str(pd.Timestamp(d).date())}
    return k, d


def splits_mit_verhaeltnis(journal) -> list[dict]:
    """Splits/Reverse-Splits laut Flex (erkannt oder gebucht) mit lesbarem Verhältnis: beleg_id, art, tag, r, titel."""
    aus = []
    for k in journal.massnahmen("buch=? AND art IN (?, ?) AND status NOT IN ('abgelehnt')", (KONTO, *SPLITS)):
        r = verhaeltnis(k["beschreibung"])
        if r is None or not k["tag"]:
            continue
        titel = {p["ticker"] for p in journal.massnahme_posten(k["beleg_id"]) if p["ticker"]}
        aus.append({"beleg_id": k["beleg_id"], "art": k["art"], "tag": k["tag"], "r": r, "titel": titel})
    return aus


def kurse_mit_massnahmen(kurse_laden, journal, meldungen: list[str]):
    """Kurslader für den Lauf: Reihen von Titeln mit Split laut Flex-Beleg werden im Speicher bereinigt, solange Yahoo noch
    nicht nachgezogen hat (Meldung einmal je Titel). Ohne Split unverändert. `laden.roh` = ursprünglicher Lader."""
    massnahmen = splits_mit_verhaeltnis(journal)
    if not massnahmen:
        return kurse_laden
    gemeldet: set[str] = set()

    def laden(ticker, bis, art):
        k = kurse_laden(ticker, bis, art)
        for m in massnahmen:
            if ticker not in m["titel"]:
                continue
            k, d = selbst_bereinigen(k, m["r"], m["tag"])
            if d is not None and ticker not in gemeldet:
                gemeldet.add(ticker)
                meldungen.append(f"Kursreihe {ticker} selbst bereinigt ({NAMEN[m['art']]} {m['r']:g} am {pd.Timestamp(d):%d.%m.%Y}, "
                                 f"Beleg {m['beleg_id']}; Yahoo noch nicht nachgezogen) – nur für diesen Lauf, Kurs-Cache unverändert")
        return k
    laden.roh = kurse_laden
    return laden


FRIST_YAHOO_SPLIT = 5                  # Handelstage nach dem Flex-Beleg ohne Yahoo-Ereignis → Vorschlag „Quelle: Flex“


def kennzahlen_stand(kurse_roh, r: float, tag: str) -> str:
    """passt | unbereinigt | ohne_ereignis | keine_kurse (siehe kennzahlen_je_aktie_passend)."""
    ok, grund = kennzahlen_je_aktie_passend(kurse_roh, r, tag)
    return "passt" if ok else "unbereinigt" if "unbereinigt" in grund else "ohne_ereignis" if "nicht als Ereignis" in grund else "keine_kurse"


def flex_splits(journal, *, nur_quittiert: bool = True) -> dict[str, dict]:
    """Splits, deren Verhältnis aus dem Flex-Beleg für die Aktienzahl gilt (Kennzeichnung „Quelle: Flex“), je Beleg."""
    alle = journal.zustand("_konto").get("split_quelle_flex") or {}
    return {b: e for b, e in alle.items() if not nur_quittiert or e.get("status") == "quittiert"}


def flex_splits_je_symbol(journal) -> dict[str, list[tuple[str, float]]]:
    """Quittierte Flex-Splits je Yahoo-Symbol für die Fundamental-Bewertung (engines/fundamental/aktuell.bewertung_am)."""
    aus: dict[str, list[tuple[str, float]]] = {}
    for e in flex_splits(journal).values():
        aus.setdefault(e["ticker"], []).append((e["tag"], float(e["r"])))
    return aus


def flex_split_offen(journal, buch: str | None = None) -> dict[str, dict]:
    """Vorgeschlagene, noch nicht quittierte Übernahmen des Flex-Verhältnisses (optional nur für ein Buch)."""
    return {b: e for b, e in flex_splits(journal, nur_quittiert=False).items()
            if e.get("status") == "vorgeschlagen" and (buch is None or buch in e.get("buecher", []))}


def flex_split_quittieren(journal, beleg_id: str, jetzt: datetime | None = None) -> str:
    """Jakobs Quittung in der Oberfläche: ab jetzt gilt das Verhältnis aus dem Flex-Beleg für die Aktienzahl (Ereignis
    „flex_split_quittiert“ mit Zeitstempel). Stopps, die nur daran hingen, werden sofort aufgehoben."""
    from tradingbot.betrieb import buchstopp

    jetzt = (jetzt or datetime.now()).replace(tzinfo=None)
    konto = journal.zustand("_konto")
    e = (konto.get("split_quelle_flex") or {}).get(beleg_id)
    if e is None or e.get("status") != "vorgeschlagen":
        raise ValueError(f"Beleg {beleg_id}: kein offener Vorschlag „Quelle: Flex“")
    e.update(status="quittiert", quittiert=jetzt.isoformat(timespec="seconds"))
    konto["kennzahlen_passend"] = sorted(set(konto.get("kennzahlen_passend") or []) | {beleg_id})
    journal.zustand_speichern("_konto", konto)
    text = (f"Split-Verhältnis {float(e['r']):g} für {e['ticker']} aus Flex-Beleg {beleg_id} übernommen (Quelle: Flex), quittiert von Jakob "
            f"am {jetzt:%d.%m.%Y %H:%M:%S}")
    journal.ereignis("flex_split_quittiert", text, jetzt=jetzt)
    st = buchstopp.gestoppt(journal)
    aufgehoben = []
    for b in list(e.get("buecher", [])):
        s = st.get(b)
        if s and set(s.get("titel") or []) <= {e["ticker"]} and not s.get("quittung_noetig") and buchstopp._gedeckt(journal, b, s) \
                and not ({z["ticker"] for z in journal.unterwegs(b)} & {e["ticker"]}):
            del st[b]
            aufgehoben.append(b)
            journal.ereignis("stopp_aufgehoben", f"Stopp aufgehoben: Buch {b} (Split-Verhältnis aus Flex quittiert): {beleg_id}", b, jetzt=jetzt)
    if aufgehoben:
        journal.zustand_speichern(buchstopp.SCHLUESSEL, st)
        text += "; Stopp aufgehoben: " + ", ".join(aufgehoben)
    return text


def kennzahlen_je_aktie_passend(kurse_roh, r: float, tag: str) -> tuple[bool, str]:
    """Fundamental (Entscheidung 4): Kurs und Kennzahlen je Aktie auf demselben Stand? Die Engine rechnet den Marktwert aus
    Schluss × Aktienzahl (SEC); die Aktienzahl wird über die Yahoo-Spalte `split` auf die Kursbasis gebracht
    (daten/index_nachbau.aktien_splitbereinigt). E/P und EBIT/EV hängen am Marktwert, die Dividende je Aktie an der Reihe;
    EPS, Buchwert je Aktie und Dividende je Aktie aus SEC nutzt die Engine nicht direkt. Passt nur, wenn die Reihe im Cache
    bereinigt ist (kein Sprung) UND Yahoo den Split als Ereignis mit Faktor r führt; eine nur im Speicher bereinigte Reihe
    genügt nicht, weil die Bewertung den Cache liest."""
    if kurse_roh is None or not len(kurse_roh):
        return False, "keine Kurse"
    if sprung_tag(kurse_roh, r, tag) is not None:
        return False, "Yahoo-Reihe noch unbereinigt (Sprung am Stichtag)"
    if "split" not in kurse_roh:
        return False, "Yahoo-Reihe ohne Split-Spalte"
    t = pd.Timestamp(tag)
    idx = _tage(kurse_roh)
    fenster = (idx >= t - pd.Timedelta(days=FENSTER_TAGE[0])) & (idx <= t + pd.Timedelta(days=FENSTER_TAGE[1]))
    werte = kurse_roh["split"].to_numpy(dtype=float)[fenster]
    if any(abs(w - r) <= 1e-6 * max(r, 1.0) for w in werte if w and w > 0):
        return True, f"Yahoo führt den Split {r:g}"
    return False, f"Yahoo führt den Split {r:g} nicht als Ereignis (Aktienzahl würde nicht angepasst)"


@dataclass
class Buchung:
    beleg_id: str
    art: str
    ok: bool
    text: str
    buecher: list[str] = field(default_factory=list)
    titel: set[str] = field(default_factory=set)


def verteilen(vorher: dict[str, float], r: float, ganz_konto: int) -> dict[str, tuple[int, float]] | None:
    """Ganze Stücke je Buch nach größtem Rest (Entscheidung 2): erst jedes Buch floor(Stück · r), die übrigen Stücke einzeln
    an die Bücher mit dem größten rechnerischen Rest (bei Gleichstand nach Buchname). Gibt je Buch (ganze Stück, Spitze =
    rechnerisch − zugeteilt, negativ bei Aufrundung) zurück; None, wenn die Kontosumme so nicht erreichbar ist."""
    exakt = {b: s * r for b, s in vorher.items()}
    ganz = {b: int(math.floor(e + 1e-9)) for b, e in exakt.items()}
    rest = ganz_konto - sum(ganz.values())
    kandidaten = sorted((b for b in exakt if exakt[b] - ganz[b] > 1e-9), key=lambda b: (-(exakt[b] - ganz[b]), b))
    if rest < 0 or rest > len(kandidaten):
        return None
    for b in kandidaten[:rest]:
        ganz[b] += 1
    return {b: (ganz[b], exakt[b] - ganz[b]) for b in exakt}


def _cent_aufteilen(betraege: dict[str, float], summe: float) -> dict[str, float]:
    """Auf Cent runden; das letzte Buch (nach Name) bekommt den Rest, damit die Summe exakt dem Beleg entspricht."""
    gerundet = {b: round(x, 2) for b, x in betraege.items()}
    if gerundet:
        letzter = sorted(gerundet)[-1]
        gerundet[letzter] = round(summe - sum(v for b, v in gerundet.items() if b != letzter), 2)
    return gerundet


def buchen(journal, buecher: list[str], positionen, meldungen: list[str], *, fx: dict[str, float],
           ticker_je_conid: dict[int, str] | None = None, technik_universum=frozenset(), jetzt=None) -> list[Buchung]:
    """Split, Reverse-Split und Tickerwechsel mit Flex-Beleg je Buch buchen (A2). Nur bei exakt passender Probe:
    - Verhältnis r aus der Beschreibung (Split) bzw. aus den Stückzahlen (Tickerwechsel), gegen die Flex-Stückzahlen geprüft;
    - Bücher vor dem Stichtag · r: ganze Stück exakt laut Flex, eine Spitze nur mit Barausgleich (Kasse ± 0,05);
    - nach der Buchung Bücher = IBKR-Position, je Titel ganzzahlig exakt.
    Sonst nichts buchen: das Buch bleibt gestoppt (A1), Meldung. Im selben Schritt (eine Transaktion): Kurseinheiten ÷ r im
    Strategiezustand und in offenen Vorschlägen, Beleg an den Buchstopp hängen (Aufhebung, sobald der Abgleich sauber ist)."""
    from tradingbot.betrieb import buchstopp

    tabelle = ticker_je_conid if ticker_je_conid is not None else _ticker_je_conid()
    ist = {p.ticker: float(p.stueck) for p in positionen}
    jetzt_text = (jetzt or datetime.now()).replace(tzinfo=None).isoformat(timespec="seconds")
    ergebnisse: list[Buchung] = []
    for k in journal.massnahmen("buch=? AND art IN (?, ?, ?, ?, ?) AND status IN (?, ?)", (KONTO, *BUCHBAR, *BESTAETIGUNG, *OFFEN)):
        if k["art"] in BESTAETIGUNG:                               # A3: erst nach Jakobs Bestätigung, im nächsten Tageslauf
            if k["status"] != "bestaetigt":
                meldungen.append(f"{NAMEN[k['art']]} {k['beleg_id']}: wartet auf Bestätigung in der Oberfläche – Buch bleibt gestoppt")
                continue
            bu = _buchen_uebernahme(journal, k, buecher, ist, tabelle, fx, jetzt_text, meldungen)
            if bu is not None:
                ergebnisse.append(bu)
            continue
        beleg, art, tag = k["beleg_id"], k["art"], k["tag"]
        kopf = f"{NAMEN[art]} {beleg}"
        roh = [dict(p) for p in journal.massnahme_posten(beleg)]
        for p in roh:                                               # neue Conids, die Jakob inzwischen eingetragen hat
            if p["conid"] and p["conid"] in tabelle:
                p["ticker"] = tabelle[p["conid"]]

        def nicht(text, titel=frozenset()):
            ergebnisse.append(Buchung(beleg, art, False, f"{kopf}: nicht gebucht – {text}", titel=set(titel)))
            meldungen.append(ergebnisse[-1].text)

        stueck_je: dict[str, float] = {}
        bar: dict[str, float] = {}
        for p in roh:
            if p["ticker"] and abs(p["stueck"] or 0) > 1e-9:
                stueck_je[p["ticker"]] = stueck_je.get(p["ticker"], 0.0) + float(p["stueck"])
            if abs(p["betrag"] or 0) > 1e-9:
                bar[p["waehrung"]] = bar.get(p["waehrung"], 0.0) + float(p["betrag"])
        if not tag:
            nicht("Stichtag fehlt im Beleg")
            continue
        vorher_je = {b: journal.bestand_vor(b, tag) for b in buecher}
        titel_beleg = {p["ticker"] for p in roh if p["ticker"]}
        gehalten = {t for t in titel_beleg if any(vorher_je[b].get(t, 0) for b in buecher)}
        if not gehalten:
            journal.massnahme_status(beleg, KONTO, "ohne_buch")
            meldungen.append(f"{kopf}: kein Buch hielt {', '.join(sorted(titel_beleg)) or '–'} vor dem Stichtag – nichts zu buchen")
            continue
        if len(gehalten) != 1:
            nicht(f"mehrere gehaltene Titel im Beleg ({', '.join(sorted(gehalten))})", titel_beleg)
            continue
        alt = next(iter(gehalten))
        neue = sorted(t for t in titel_beleg if t != alt and stueck_je.get(t, 0) > 0)
        if len(neue) > 1:
            nicht(f"mehrere neue Titel im Beleg ({', '.join(neue)})", titel_beleg)
            continue
        neu = neue[0] if neue else alt
        vorher = {b: vorher_je[b].get(alt, 0.0) for b in buecher if abs(vorher_je[b].get(alt, 0.0)) > 1e-9}
        alt_konto = sum(vorher.values())
        if any(s < 0 or abs(s - round(s)) > 1e-9 for s in vorher.values()):
            nicht(f"Bestand vor dem Stichtag nicht ganzzahlig positiv ({alt})", {alt, neu})
            continue
        # Stückzahlen laut Flex: eine Zeile mit der Änderung oder −alt/+neu (auch bei gleichem Titel)
        if neu == alt:
            neu_konto = alt_konto + stueck_je.get(alt, 0.0)
        else:
            if abs(stueck_je.get(alt, 0.0) + alt_konto) > 1e-6:
                nicht(f"Abgang {alt} laut Flex {stueck_je.get(alt, 0.0):g} Stück, Bücher vor dem Stichtag {alt_konto:g} Stück", {alt, neu})
                continue
            neu_konto = stueck_je.get(neu, 0.0)
        if abs(neu_konto - round(neu_konto)) > 1e-9 or neu_konto < 0:
            nicht(f"neue Stückzahl laut Flex nicht ganzzahlig ({neu_konto:g})", {alt, neu})
            continue
        neu_konto = int(round(neu_konto))
        if art in SPLITS:
            r = verhaeltnis(k["beschreibung"])
            if r is None:
                nicht("Verhältnis in der Beschreibung nicht lesbar", {alt, neu})
                continue
        else:
            if neu == alt:
                nicht("Tickerwechsel ohne neuen Titel im Beleg", {alt})
                continue
            r = neu_konto / alt_konto
            fehlend = [p for p in roh if p["stueck"] and p["stueck"] > 0 and (not p["conid"] or p["conid"] not in tabelle)]
            if fehlend:
                nicht(f"neue Conid {fehlend[0]['conid']} ({fehlend[0]['symbol']}) steht noch nicht in config/kontrakte.yaml – Buch bleibt "
                      "gestoppt, bis Jakob sie übernommen hat (Vorschlag im Journal)", {alt, neu})
                continue
            if alt in technik_universum and neu not in technik_universum:
                nicht(f"{alt} steht im Technik-Universum, {neu} noch nicht – Buch bleibt gestoppt, bis Jakob config/technik.yaml "
                      "umgestellt hat", {alt, neu})
                continue
        exakt_konto = alt_konto * r
        if neu_konto != int(math.floor(exakt_konto + 1e-9)):
            nicht(f"Probe: Bücher {alt_konto:g} Stück × {r:g} = {exakt_konto:g}, Flex {neu_konto} ganze Stück", {alt, neu})
            continue
        spitze_konto = exakt_konto - neu_konto
        if len(bar) > 1:
            nicht(f"Barausgleich in mehreren Währungen ({', '.join(sorted(bar))})", {alt, neu})
            continue
        bar_w, bar_betrag = next(iter(bar.items())) if bar else (None, 0.0)
        if spitze_konto <= 1e-9 and abs(bar_betrag) > TOLERANZ_KASSE:
            nicht(f"Barbetrag {bar_betrag:,.2f} {bar_w} ohne Spitze", {alt, neu})
            continue
        if spitze_konto > 1e-9 and bar_betrag <= TOLERANZ_KASSE:
            nicht(f"Spitze {spitze_konto:g} Stück ohne Barausgleich im Beleg", {alt, neu})
            continue
        verteilung = verteilen(vorher, r, neu_konto)
        if verteilung is None:
            nicht(f"Spitzen nicht nach größtem Rest verteilbar ({neu_konto} Stück auf {len(vorher)} Bücher)", {alt, neu})
            continue
        preis_spitze = bar_betrag / spitze_konto if spitze_konto > 1e-9 else None
        if preis_spitze is None and any(f < -1e-9 for _, f in verteilung.values()):
            nicht("Spitzenausgleich zwischen Büchern ohne Barausgleichskurs im Beleg", {alt, neu})
            continue
        # Probe gegen IBKR: Bücher nach der Buchung = Position je Titel (ganzzahlig exakt)
        nachher: dict[str, float] = {alt: 0.0, neu: 0.0}
        for b in buecher:
            jetzt_b = journal.bestand(b)
            for t in nachher:
                nachher[t] += jetzt_b.get(t, 0.0)
        for b, s in vorher.items():
            nachher[alt] -= s
            nachher[neu] += verteilung[b][0]
        abweichend = [t for t in sorted(nachher) if abs(nachher[t] - ist.get(t, 0.0)) > 1e-6]
        if abweichend:
            nicht("Probe gegen IBKR: " + "; ".join(f"{t} Bücher danach {nachher[t]:g}, IBKR {ist.get(t, 0.0):g}" for t in abweichend), {alt, neu})
            continue

        # --- Posten je Buch ---------------------------------------------------------------------------------------------------
        bar_je = (_cent_aufteilen({b: f * preis_spitze for b, (_, f) in verteilung.items() if abs(f) > 1e-9}, bar_betrag)
                  if preis_spitze else {})
        p_alt = next((p for p in roh if p["ticker"] == alt), {})
        p_neu = next((p for p in roh if p["ticker"] == neu and (p["stueck"] or 0) > 0), p_alt)
        felder = {"code": k["code"], "tag": tag, "beschreibung": k["beschreibung"], "steuer": STEUER[art], "quelle": k["quelle"]}
        posten_je_buch, ereignisse, zeilen = {}, [], []
        for b, s in sorted(vorher.items()):
            ganz, f = verteilung[b]
            e = journal.einstaende(b, bis=tag).get(alt, {})
            w_alt, k_alt = float(e.get("w", 0.0)), float(e.get("k", 0.0))
            w_ein = e.get("waehrung") or p_alt.get("waehrung") or "EUR"
            if f >= 0:                                              # verkaufte Spitze: Einstand anteilig ab
                anteil = ganz / (s * r)
                w_neu, k_neu = w_alt * anteil, k_alt * anteil
            else:                                                   # aufgerundet: zugekaufte Spitze zum Barausgleichskurs
                w_neu = w_alt + (-f) * preis_spitze
                k_neu = k_alt + (-f) * preis_spitze / (1.0 if bar_w == "EUR" else float(fx[bar_w]))
            angeschafft = str(e.get("erst") or "")[:10] or None
            posten = [{"ticker": alt, "conid": p_alt.get("conid"), "symbol": p_alt.get("symbol"), "isin": p_alt.get("isin"), "stueck": -s,
                       "waehrung": w_ein, "einstand": -w_alt, "einstand_eur": -k_alt, "art": "bestand"}]
            if ganz:
                posten.append({"ticker": neu, "conid": p_neu.get("conid"), "symbol": p_neu.get("symbol"), "isin": p_neu.get("isin"),
                               "stueck": ganz, "waehrung": w_ein, "einstand": w_neu, "einstand_eur": k_neu, "angeschafft": angeschafft,
                               "art": "bestand"})
            if b in bar_je:
                posten.append(_barposten(bar_je[b], bar_w, fx, "spitzenausgleich"))
            posten_je_buch[b] = posten
            text = (f"{kopf} gebucht ({b}): {alt} {s:g} → {neu} {ganz} Stück (r = {r:g}), Einstand {w_alt:,.2f} → {w_neu:,.2f} {w_ein}"
                    + (f", Spitze {f:+.4f} Stück nach größtem Rest, Barausgleich {bar_je.get(b, 0.0):+,.2f} {bar_w}" if abs(f) > 1e-9 else "")
                    + f", angeschafft {angeschafft or '–'}; Steuer {STEUER[art]}")
            ereignisse.append(("kapitalmassnahme_gebucht", text, b))
            zeilen.append(text)

        zustaende = {}
        for b in buecher:
            z = journal.zustand(b)
            if not z:
                continue
            z_neu, aend = zustand_umrechnen(z, alt, neu, r)
            if aend:
                zustaende[b] = z_neu
                ereignisse.append(("kurseinheiten", f"{kopf}: Strategiezustand {b} umgerechnet (Kurseinheiten ÷ {r:g}): " + "; ".join(aend), b))
        ergebnisse.append(_abschliessen(journal, k, alt, neu, r, vorher, posten_je_buch, zustaende, ereignisse, zeilen, meldungen, jetzt_text,
                                        umrechnen=True))
    return ergebnisse


def kennzahlen_pruefen(journal, buecher: list[str], kurse_roh, je_buch: dict, tag_kurse, heute=None) -> list[str]:
    """Fundamental-Bücher (Entscheidung 4): Hält ein Fundamental-Buch einen Titel mit Split (oder hat eine Order dafür
    unterwegs) und passen Kurs und Kennzahlen je Aktie noch nicht zum selben Stand, bleibt das Buch für diesen Titel
    gestoppt (Eintrag in `je_buch` mit Beleg), bis es passt. Einmal passend → nicht erneut geprüft (Kontozustand
    `kennzahlen_passend`). Gibt Protokollzeilen zurück.

    SPYI-Fall (Jakob 12.11.2026): Ist die Reihe bereinigt, fehlt aber das Yahoo-Ereignis noch FRIST_YAHOO_SPLIT Handelstage
    nach dem Flex-Beleg, schlägt der Bot vor, das Verhältnis aus dem Flex-Beleg für die Aktienzahl zu übernehmen
    („Quelle: Flex“). Erst nach Jakobs Quittung in der Oberfläche gilt es (flex_split_quittieren)."""
    from tradingbot.betrieb import buchstopp
    from tradingbot.betrieb.dividenden import handelstage_nach

    fund = [b for b in buecher if b.startswith("fundamental")]
    if not fund:
        return []
    konto = journal.zustand("_konto")
    passend = set(konto.get("kennzahlen_passend") or [])
    flex = dict(konto.get("split_quelle_flex") or {})
    heute = heute or datetime.now().date()
    zeilen, neu_passend, geaendert = [], [], False
    for m in splits_mit_verhaeltnis(journal):
        if m["beleg_id"] in passend:
            continue
        for t in sorted(m["titel"]):
            halter = [b for b in fund if journal.bestand(b).get(t, 0) or t in {z["ticker"] for z in journal.unterwegs(b)}]
            if not halter:
                continue
            try:
                reihe = kurse_roh(t, tag_kurse, "aktie_usd")
                ok, grund = kennzahlen_je_aktie_passend(reihe, m["r"], m["tag"])
                stand = kennzahlen_stand(reihe, m["r"], m["tag"])
            except Exception as f:  # noqa: BLE001 – ohne Kurse kein Urteil: gestoppt lassen
                ok, grund, stand = False, f"Kurse nicht abrufbar ({type(f).__name__})", "keine_kurse"
            fe = flex.get(m["beleg_id"])
            if not ok and stand == "ohne_ereignis":
                if fe and fe.get("status") == "quittiert":
                    ok, grund = True, f"Quelle: Flex, Verhältnis {m['r']:g} quittiert am {fe['quittiert'][:10]}"
                elif fe is None:
                    erkannt = journal.massnahmen("beleg_id=? AND buch=?", (m["beleg_id"], KONTO))[0]["erkannt"][:10]
                    if handelstage_nach(erkannt, heute) >= FRIST_YAHOO_SPLIT:
                        fe = flex[m["beleg_id"]] = {"ticker": t, "tag": m["tag"], "r": m["r"], "buecher": halter, "status": "vorgeschlagen",
                                                    "vorgeschlagen": str(heute)}
                        geaendert = True
                        text = (f"Vorschlag: Yahoo führt den Split {m['r']:g} von {t} auch {FRIST_YAHOO_SPLIT} Handelstage nach dem Flex-Beleg "
                                f"nicht – Verhältnis aus Flex-Beleg {m['beleg_id']} für die Aktienzahl übernehmen (Quelle: Flex); gilt erst "
                                "nach Quittung in der Oberfläche")
                        journal.ereignis("flex_split_vorschlag", text)
                        zeilen.append(text)
                if fe and fe.get("status") == "vorgeschlagen":
                    grund += "; Vorschlag „Quelle: Flex“ wartet auf Quittung in der Oberfläche"
            if ok:
                neu_passend.append(m["beleg_id"])
                zeilen.append(f"{t}: Kurs und Kennzahlen je Aktie passen zum Split {m['r']:g} ({grund})")
                continue
            for b in halter:
                buchstopp.eintragen(je_buch, b, t, [m["beleg_id"]],
                                    f"{t}: Kurs und Kennzahlen je Aktie nicht auf demselben Stand ({grund}) – Buch bleibt gestoppt, bis es passt")
    if neu_passend:
        konto["kennzahlen_passend"] = sorted(passend | set(neu_passend))
    if geaendert:
        konto["split_quelle_flex"] = flex
    if neu_passend or geaendert:
        journal.zustand_speichern("_konto", konto)
    return zeilen


# === A3 (Jakob 12.11.2026): Übernahme (TC) und Delisting wertlos (DW) nach Bestätigung =======================================
#
# Entscheidungen: (1) Einstand geht voll auf die neuen Aktien über; die Barkomponente wird als eigene Posten-Art
# „Barzuzahlung (§ 20 Abs. 4a, zu prüfen)“ gebucht, getrennt von Dividenden und Veräußerungen, damit sie sich umrechnen
# lässt, falls die Vorschrift nicht greift; (2) gebucht wird erst im nächsten Tageslauf nach der Bestätigung (Probe mit
# frischen IBKR-Positionen); (3) Fremdtitel: Fundamental hält bis zum nächsten Stichtag, Technik bekommt im nächsten Lauf
# einen Ausstiegsvorschlag; (4) nach „Ablehnen“ bleibt das Buch gestoppt bis zur Quittung. Zusatz: Nur DW ist „Delisting
# wertlos“; ein Delisting mit weiterem Handel (z. B. außerbörslich) ist kein DW – ein unbekanntes Kürzel stoppt wie in A1
# und wird nie automatisch gebucht.

BESTAETIGUNG = ("uebernahme", "delisting")
POSTEN_ARTEN = {"bestand": "Stückposten (Einstand übertragen)",
                "barzuzahlung": "Barzuzahlung (§ 20 Abs. 4a, zu prüfen)",
                "barabfindung": "Barabfindung (Veräußerung § 20 Abs. 2, zu prüfen)",
                "spitzenausgleich": "Spitzenausgleich (Veräußerung des Bruchteils, zu prüfen)"}


def _barposten(betrag: float, waehrung: str, fx: dict[str, float], art: str) -> dict:
    return {"ticker": None, "stueck": 0, "waehrung": waehrung, "betrag": betrag, "art": art,
            "betrag_eur": round(betrag if waehrung == "EUR" else betrag / float(fx[waehrung]), 2)}


def konditionen(beschreibung: str | None) -> tuple[float | None, str | None, float | None]:
    """Übernahmekonditionen aus der IBKR-Beschreibung: (neue Aktien je alte Aktie, Währung, Barbetrag je Aktie).
    „… MERGED(Acquisition) WITH US4943681035 14625 FOR 100000 AND USD 3.50 (…)“ → (0,14625, USD, 3,50);
    „… MERGED(Acquisition) FOR USD 50.00 PER SHARE (…)“ → (None, USD, 50,0). Format am ersten echten Beleg prüfen."""
    t = str(beschreibung or "")
    r = None
    m = re.search(r"WITH\s+\S+\s+(\d+(?:\.\d+)?)\s+FOR\s+(\d+(?:\.\d+)?)", t, re.IGNORECASE)
    if m and float(m.group(2)) > 0:
        r = float(m.group(1)) / float(m.group(2))
    m = re.search(r"(?:AND|FOR)\s+([A-Z]{3})\s+(\d+(?:\.\d+)?)", t)
    return r, (m.group(1) if m else None), (float(m.group(2)) if m else None)


def bestaetigung_offen(journal, buch: str | None = None) -> list[dict]:
    """Erkannte Übernahmen/Delistings (Bestätigen oder Ablehnen) und unbekannte Arten (nur Ablehnen), optional je Buch, mit
    Text der Konditionen laut Flex-Beleg für die Oberfläche."""
    aus = []
    for k in journal.massnahmen("buch=? AND status='erkannt' AND art IN (?, ?, ?)", (KONTO, *BESTAETIGUNG, "sonstige")):
        buecher = [r["buch"] for r in journal.massnahmen("beleg_id=? AND buch!=?", (k["beleg_id"], KONTO))]
        if buch is not None and buch not in buecher:
            continue
        aus.append({"beleg_id": k["beleg_id"], "art": k["art"], "buecher": buecher, "bestaetigbar": k["art"] in BESTAETIGUNG,
                    "text": konditionen_text(journal, k)})
    return aus


def konditionen_text(journal, k) -> str:
    """Konditionen laut Flex-Beleg zum Vergleich mit der Pressemitteilung (nur Oberfläche, nie in Nachrichten)."""
    posten = journal.massnahme_posten(k["beleg_id"])
    r, w, bar_je = konditionen(k["beschreibung"])
    teile = [f"{NAMEN[k['art']]} {k['beleg_id']} am {k['tag'] or '?'}"]
    if r is not None:
        teile.append(f"{r:g} neue Aktien je Aktie")
    if bar_je is not None:
        teile.append(f"{bar_je:,.2f} {w} bar je Aktie")
    teile.append("Flex: " + ", ".join(f"{p['ticker'] or p['waehrung']} {p['stueck']:+g}" + (f" / {p['betrag']:+,.2f} {p['waehrung']}" if p["betrag"] else "")
                                      for p in posten))
    return "; ".join(teile)


def bestaetigen(journal, beleg_id: str, jetzt: datetime | None = None) -> str:
    """Jakob bestätigt eine Übernahme/ein Delisting in der Oberfläche (Status „bestätigt“, Ereignis mit Zeitstempel);
    gebucht wird im nächsten Tageslauf, nur bei exakt passender Probe."""
    jetzt = (jetzt or datetime.now()).replace(tzinfo=None)
    k = (journal.massnahmen("beleg_id=? AND buch=?", (beleg_id, KONTO)) or [None])[0]
    if k is None or k["status"] != "erkannt" or k["art"] not in BESTAETIGUNG:
        raise ValueError(f"Beleg {beleg_id}: nicht bestätigbar (Art {k['art'] if k else '?'}, Status {k['status'] if k else '?'})")
    for r in journal.massnahmen("beleg_id=?", (beleg_id,)):
        journal.massnahme_status(beleg_id, r["buch"], "bestaetigt")
    text = f"{NAMEN[k['art']]} {beleg_id} bestätigt von Jakob am {jetzt:%d.%m.%Y %H:%M:%S} ({konditionen_text(journal, k)}) – Buchung im nächsten Tageslauf"
    journal.ereignis("massnahme_bestaetigt", text, jetzt=jetzt)
    return text


def ablehnen(journal, beleg_id: str, jetzt: datetime | None = None) -> str:
    """Jakob lehnt ab (Konditionen passen nicht, oder unbekannte Art ohne Buchung erledigt): Status „abgelehnt“, die Bücher
    bleiben gestoppt bis zur Quittung (Entscheidung 4)."""
    from tradingbot.betrieb import buchstopp

    jetzt = (jetzt or datetime.now()).replace(tzinfo=None)
    k = (journal.massnahmen("beleg_id=? AND buch=?", (beleg_id, KONTO)) or [None])[0]
    if k is None or k["status"] not in OFFEN:
        raise ValueError(f"Beleg {beleg_id}: nicht ablehnbar (Status {k['status'] if k else '?'})")
    buecher = [r["buch"] for r in journal.massnahmen("beleg_id=? AND buch!=?", (beleg_id, KONTO))]
    for r in journal.massnahmen("beleg_id=?", (beleg_id,)):
        journal.massnahme_status(beleg_id, r["buch"], "abgelehnt")
    text = f"{NAMEN[k['art']]} {beleg_id} abgelehnt von Jakob am {jetzt:%d.%m.%Y %H:%M:%S} – Bücher {', '.join(buecher) or '–'} bleiben gestoppt bis zur Quittung"
    st = buchstopp.gestoppt(journal)
    titel = sorted({p["ticker"] for p in journal.massnahme_posten(beleg_id) if p["ticker"]})
    for b in buecher:
        e = st.setdefault(b, {"seit": jetzt.isoformat(timespec="seconds"), "kategorie": buchstopp.KAT_BELEG, "titel": [], "belege": [],
                              "details": [], "abweichung_weg": None})
        e["titel"] = sorted(set(e.get("titel") or []) | set(titel))
        e["belege"] = sorted(set(e.get("belege") or []) | {beleg_id})
        e["quittung_noetig"] = text
        e["details"] = list(e.get("details") or []) + [text]
    journal.zustand_speichern(buchstopp.SCHLUESSEL, st)
    journal.ereignis("massnahme_abgelehnt", text, jetzt=jetzt)
    return text


def zustand_entfernen(z: dict, alt: str) -> tuple[dict, list[str]]:
    """Strategiezustand ohne den untergegangenen Titel (A3): Technik-Position, Sperren, Monatsprüfung, Fundamental-Ziel und
    -Rang – sonst schlüge der Nachkauf einen delisteten Titel vor."""
    aenderungen: list[str] = []

    def teil(d: dict, wo: str) -> dict:
        d = dict(d)
        for schluessel in ("positionen", "gesperrt", "pruefmonat", "ziel", "rang"):
            if isinstance(d.get(schluessel), dict) and alt in d[schluessel]:
                d[schluessel] = {t: v for t, v in d[schluessel].items() if t != alt}
                aenderungen.append(f"{wo}{schluessel}: {alt} entfernt")
        return d

    if "nach" in z or "vor" in z:
        z = dict(z)
        for wo in ("vor", "nach"):
            if isinstance(z.get(wo), dict):
                z[wo] = teil(z[wo], f"{wo}: ")
        return z, aenderungen
    return teil(z, ""), aenderungen


def _abschliessen(journal, k, alt: str, neu: str | None, r: float, vorher: dict[str, float], posten_je_buch, zustaende, ereignisse,
                  zeilen, meldungen, jetzt_text, *, umrechnen: bool) -> Buchung:
    """Gemeinsamer Abschluss A2/A3: offene Vorschläge vor dem Stichtag (Split: umrechnen; Titel geht unter: ersetzen bzw.
    unterwegs lassen), Order über den Stichtag, Beleg an die Buchstopps, alles in einer Transaktion."""
    from tradingbot.betrieb import buchstopp

    beleg, art, tag = k["beleg_id"], k["art"], k["tag"]
    kopf = f"{NAMEN[art]} {beleg}"
    titel = {alt} | ({neu} if neu else set())
    vorschlaege, unterwegs_alt, ueber_stichtag = [], {}, {}
    for z in journal.db.execute("SELECT * FROM vorschlaege WHERE ticker=? AND art!='fx' AND signaltag < ? AND status IN "
                                "('vorgeschlagen','freigegeben','gesendet','unbestaetigt','ausgefuehrt')", (alt, tag)).fetchall():
        if z["status"] == "ausgefuehrt":                           # Order über den Stichtag ausgeführt?
            spaet = journal.db.execute("SELECT COALESCE(SUM(stueck), 0) FROM ausfuehrungen WHERE order_ref=? AND substr(zeit, 1, 10) >= ?",
                                       (f"{z['buch']}:{z['id']}", tag)).fetchone()[0]
            if spaet:
                erwartet = float(z["stueck"]) * r if umrechnen else None
                if erwartet is None or abs(float(spaet) - erwartet) > 1e-6:
                    ueber_stichtag.setdefault(z["buch"], []).append(
                        f"Order {z['id']} ({alt}) über den Stichtag ausgeführt: {float(spaet):g} Stück"
                        + (f" statt {erwartet:g} nach Umrechnung – von IBKR nicht angepasst?" if erwartet is not None else " – Titel ging am Stichtag unter")
                        + " Bitte im Client Portal prüfen und quittieren")
                else:
                    meldungen.append(f"Order {z['id']} ({alt}) über den Stichtag von IBKR angepasst ausgeführt ({float(spaet):g} Stück)")
            continue
        if (neu != alt or not umrechnen) and z["status"] in ("vorgeschlagen", "freigegeben"):
            vorschlaege.append((z["id"], {"status": "ersetzt"}))
            ereignisse.append(("kurseinheiten", f"{kopf}: Vorschlag {z['id']} ({alt}) ersetzt – " + (f"der Titel heißt jetzt {neu}" if umrechnen
                               else "der Titel ist untergegangen"), z["buch"]))
            continue
        if z["status"] in ("gesendet", "unbestaetigt"):
            unterwegs_alt.setdefault(z["buch"], []).append(z["id"])
            if neu != alt or not umrechnen:                        # Tickerwechsel/Übernahme: nicht automatisch umdeuten
                continue
        werte = vorschlag_umrechnen(z, r)
        vorschlaege.append((z["id"], werte))
        ereignisse.append(("order_an_split_angepasst" if z["status"] in ("gesendet", "unbestaetigt") else "kurseinheiten",
                           f"{kopf}: Vorschlag {z['id']} ({z['status']}) umgerechnet: "
                           + ", ".join(f"{f} {float(z[f]):g} → {v:g}" for f, v in werte.items()), z["buch"]))
    st = buchstopp.gestoppt(journal)
    for b in sorted(set(vorher) | set(unterwegs_alt) | set(ueber_stichtag)):
        if b not in st and b not in ueber_stichtag and b not in unterwegs_alt:
            continue
        e = st.setdefault(b, {"seit": jetzt_text, "kategorie": buchstopp.KAT_BELEG, "titel": [], "belege": [], "details": [],
                              "abweichung_weg": None})
        e["belege"] = sorted(set(e.get("belege") or []) | {beleg})
        e["titel"] = sorted(set(e.get("titel") or []) | titel)
        if b in ueber_stichtag:
            e["quittung_noetig"] = "; ".join(ueber_stichtag[b])
            e["details"] = list(e.get("details") or []) + ueber_stichtag[b]
        if b in unterwegs_alt:
            e["details"] = list(e.get("details") or []) + [f"Order(s) {', '.join(unterwegs_alt[b])} über den Stichtag unterwegs – "
                                                           "Stopp bleibt, bis sie abgeschlossen sind"]
    zustaende[buchstopp.SCHLUESSEL] = st
    felder = {"code": k["code"], "tag": tag, "beschreibung": k["beschreibung"], "steuer": STEUER[art], "quelle": k["quelle"]}
    journal.massnahme_buchen(beleg_id=beleg, art=art, felder=felder, posten_je_buch=posten_je_buch, zustaende=zustaende,
                             vorschlaege=vorschlaege, ereignisse=ereignisse)
    meldungen += zeilen
    meldungen += [x for b in sorted(ueber_stichtag) for x in ueber_stichtag[b]]
    return Buchung(beleg, art, True, f"Kapitalmaßnahme gebucht: {NAMEN[art]} {alt}" + (f" → {neu}" if neu and neu != alt else "")
                   + (f" (r = {r:g})" if art in SPLITS else "") + f"; Bücher {', '.join(sorted(vorher))}", sorted(vorher), titel)


def _buchen_uebernahme(journal, k, buecher, ist, tabelle, fx, jetzt_text, meldungen) -> Buchung | None:
    """Übernahme (Aktien, bar oder beides) bzw. Delisting wertlos je Buch, nur bei exakt passender Probe:
    - Abgang laut Flex = Bücher vor dem Stichtag; neue ganze Stück = floor(Stück · r) laut Flex, Verteilung nach größtem Rest;
    - Barzuzahlung = Stück · Barbetrag je Aktie (Konditionen aus der Beschreibung), der Rest des Barbetrags ist der
      Spitzenausgleich (Kurs = Rest ÷ Spitze des Kontos); ohne Spitze muss der Barbetrag auf ± 0,05 passen;
    - DW nur ohne Gegenleistung (sonst kein „Delisting wertlos“);
    - danach Bücher = IBKR-Position je Titel."""
    beleg, art, tag = k["beleg_id"], k["art"], k["tag"]
    kopf = f"{NAMEN[art]} {beleg}"
    roh = [dict(p) for p in journal.massnahme_posten(beleg)]
    for p in roh:
        if p["conid"] and p["conid"] in tabelle:
            p["ticker"] = tabelle[p["conid"]]

    def nicht(text):
        meldungen.append(f"{kopf}: nicht gebucht – {text}")
        return Buchung(beleg, art, False, meldungen[-1], titel={p["ticker"] for p in roh if p["ticker"]})

    if not tag:
        return nicht("Stichtag fehlt im Beleg")
    stueck_je: dict[str, float] = {}
    bar: dict[str, float] = {}
    for p in roh:
        if p["ticker"] and abs(p["stueck"] or 0) > 1e-9:
            stueck_je[p["ticker"]] = stueck_je.get(p["ticker"], 0.0) + float(p["stueck"])
        if abs(p["betrag"] or 0) > 1e-9:
            bar[p["waehrung"]] = bar.get(p["waehrung"], 0.0) + float(p["betrag"])
    vorher_je = {b: journal.bestand_vor(b, tag) for b in buecher}
    gehalten = {t for t in stueck_je if stueck_je[t] < 0 and any(vorher_je[b].get(t, 0) for b in buecher)}
    if not gehalten:
        journal.massnahme_status(beleg, KONTO, "ohne_buch")
        meldungen.append(f"{kopf}: kein Buch hielt den Titel vor dem Stichtag – nichts zu buchen")
        return None
    if len(gehalten) != 1:
        return nicht(f"mehrere gehaltene Titel im Beleg ({', '.join(sorted(gehalten))})")
    alt = next(iter(gehalten))
    vorher = {b: vorher_je[b].get(alt, 0.0) for b in buecher if abs(vorher_je[b].get(alt, 0.0)) > 1e-9}
    alt_konto = sum(vorher.values())
    if any(s < 0 or abs(s - round(s)) > 1e-9 for s in vorher.values()):
        return nicht(f"Bestand vor dem Stichtag nicht ganzzahlig positiv ({alt})")
    if abs(stueck_je[alt] + alt_konto) > 1e-6:
        return nicht(f"Abgang {alt} laut Flex {stueck_je[alt]:g} Stück, Bücher vor dem Stichtag {alt_konto:g} Stück")
    neue = sorted(t for t, s in stueck_je.items() if s > 0)
    if len(neue) > 1:
        return nicht(f"mehrere neue Titel im Beleg ({', '.join(neue)})")
    neu = neue[0] if neue else None
    if len(bar) > 1:
        return nicht(f"Barbetrag in mehreren Währungen ({', '.join(sorted(bar))})")
    bar_w, bar_betrag = next(iter(bar.items())) if bar else (None, 0.0)
    r, bar_je, preis_spitze = 0.0, 0.0, None
    neu_konto = 0
    if art == "delisting":
        if neu or abs(bar_betrag) > TOLERANZ_KASSE:
            return nicht("Delisting mit Gegenleistung im Beleg – kein „Delisting wertlos“ (DW); bitte prüfen")
    else:
        kr, kw, kb = konditionen(k["beschreibung"])
        if neu:
            fehlt = [p for p in roh if (p["stueck"] or 0) > 0 and (not p["conid"] or p["conid"] not in tabelle)]
            if fehlt:
                return nicht(f"neue Conid {fehlt[0]['conid']} ({fehlt[0]['symbol']}) steht noch nicht in config/kontrakte.yaml – Buch bleibt "
                             "gestoppt, bis Jakob sie übernommen hat (Vorschlag im Journal)")
            neu_konto = stueck_je[neu]
            if abs(neu_konto - round(neu_konto)) > 1e-9:
                return nicht(f"neue Stückzahl laut Flex nicht ganzzahlig ({neu_konto:g})")
            neu_konto = int(round(neu_konto))
            r = kr if kr is not None else neu_konto / alt_konto
        elif kr is not None:
            return nicht("Aktienteil laut Beschreibung fehlt im Beleg")
        if kw and bar_w and kw != bar_w:
            return nicht(f"Währung laut Beschreibung {kw}, laut Beleg {bar_w}")
        bar_w = bar_w or kw
        exakt_konto = alt_konto * r
        if neu_konto != int(math.floor(exakt_konto + 1e-9)):
            return nicht(f"Probe: Bücher {alt_konto:g} Stück × {r:g} = {exakt_konto:g}, Flex {neu_konto} ganze Stück")
        spitze_konto = exakt_konto - neu_konto
        if kb is None:
            if spitze_konto > 1e-9:
                return nicht("Barbetrag je Aktie nicht lesbar und Spitze vorhanden")
            kb = bar_betrag / alt_konto
        bar_je = kb
        bar_aktie = round(alt_konto * bar_je, 2)
        rest = bar_betrag - bar_aktie
        if spitze_konto > 1e-9:
            if rest <= TOLERANZ_KASSE:
                return nicht(f"Probe Kasse: Barbetrag {bar_betrag:,.2f} {bar_w}, Barkomponente {alt_konto:g} × {bar_je:g} = {bar_aktie:,.2f} – "
                             "kein Spitzenausgleich übrig")
            preis_spitze = rest / spitze_konto
        elif abs(rest) > TOLERANZ_KASSE:
            return nicht(f"Probe Kasse: Barbetrag {bar_betrag:,.2f} {bar_w}, erwartet {alt_konto:g} × {bar_je:g} = {bar_aktie:,.2f}")
    verteilung = verteilen(vorher, r, neu_konto) if r > 0 else {b: (0, 0.0) for b in vorher}
    if verteilung is None:
        return nicht(f"Spitzen nicht nach größtem Rest verteilbar ({neu_konto} Stück auf {len(vorher)} Bücher)")
    if preis_spitze is None and any(f < -1e-9 for _, f in verteilung.values()):
        return nicht("Spitzenausgleich zwischen Büchern ohne Barausgleichskurs im Beleg")
    nachher = {alt: 0.0, **({neu: 0.0} if neu else {})}
    for b in buecher:
        jetzt_b = journal.bestand(b)
        for t in nachher:
            nachher[t] += jetzt_b.get(t, 0.0)
    for b, s in vorher.items():
        nachher[alt] -= s
        if neu:
            nachher[neu] += verteilung[b][0]
    abweichend = [t for t in sorted(nachher) if abs(nachher[t] - ist.get(t, 0.0)) > 1e-6]
    if abweichend:
        return nicht("Probe gegen IBKR: " + "; ".join(f"{t} Bücher danach {nachher[t]:g}, IBKR {ist.get(t, 0.0):g}" for t in abweichend))

    barart = "barzuzahlung" if neu else "barabfindung"
    bar_aktie_je = _cent_aufteilen({b: s * bar_je for b, s in vorher.items()}, round(alt_konto * bar_je, 2)) if bar_je else {}
    spitze_je = (_cent_aufteilen({b: f * preis_spitze for b, (_, f) in verteilung.items() if abs(f) > 1e-9}, bar_betrag - round(alt_konto * bar_je, 2))
                 if preis_spitze else {})
    p_alt = next((p for p in roh if p["ticker"] == alt), {})
    p_neu = next((p for p in roh if p["ticker"] == neu and (p["stueck"] or 0) > 0), {}) if neu else {}
    posten_je_buch, ereignisse, zeilen = {}, [], []
    for b, s in sorted(vorher.items()):
        ganz, f = verteilung[b]
        e = journal.einstaende(b, bis=tag).get(alt, {})
        w_alt, k_alt = float(e.get("w", 0.0)), float(e.get("k", 0.0))
        w_ein = e.get("waehrung") or p_alt.get("waehrung") or "EUR"
        angeschafft = str(e.get("erst") or "")[:10] or None
        posten = [{"ticker": alt, "conid": p_alt.get("conid"), "symbol": p_alt.get("symbol"), "isin": p_alt.get("isin"), "stueck": -s,
                   "waehrung": w_ein, "einstand": -w_alt, "einstand_eur": -k_alt, "art": "bestand"}]
        w_neu = k_neu = 0.0
        if neu and ganz:
            if f >= 0:                     # Einstand voll auf die neuen Aktien (Entscheidung 1); verkaufte Spitze anteilig ab
                w_neu, k_neu = w_alt * ganz / (s * r), k_alt * ganz / (s * r)
            else:                          # aufgerundet: zugekaufte Spitze zum Spitzenausgleichskurs
                w_neu = w_alt + (-f) * preis_spitze
                k_neu = k_alt + (-f) * preis_spitze / (1.0 if bar_w == "EUR" else float(fx[bar_w]))
            posten.append({"ticker": neu, "conid": p_neu.get("conid"), "symbol": p_neu.get("symbol"), "isin": p_neu.get("isin"), "stueck": ganz,
                           "waehrung": p_neu.get("waehrung") or w_ein, "einstand": w_neu, "einstand_eur": k_neu, "angeschafft": angeschafft,
                           "art": "bestand"})
        if b in bar_aktie_je:
            posten.append(_barposten(bar_aktie_je[b], bar_w, fx, barart))
        if b in spitze_je:
            posten.append(_barposten(spitze_je[b], bar_w, fx, "spitzenausgleich"))
        posten_je_buch[b] = posten
        text = (f"{kopf} gebucht ({b}): {alt} −{s:g} Stück (Einstand {w_alt:,.2f} {w_ein})"
                + (f", {neu} +{ganz} Stück (Einstand {w_neu:,.2f}, angeschafft {angeschafft or '–'})" if neu and ganz else "")
                + (f", {POSTEN_ARTEN[barart]} {bar_aktie_je[b]:+,.2f} {bar_w}" if b in bar_aktie_je else "")
                + (f", Spitze {f:+.4f} Stück nach größtem Rest, {POSTEN_ARTEN['spitzenausgleich']} {spitze_je[b]:+,.2f} {bar_w}" if b in spitze_je else "")
                + (", Einstand ausgebucht (Verlust)" if art == "delisting" else "") + f"; Steuer {STEUER[art]}")
        ereignisse.append(("kapitalmassnahme_gebucht", text, b))
        zeilen.append(text)
    zustaende = {}
    for b in buecher:
        z = journal.zustand(b)
        if not z:
            continue
        z_neu, aend = zustand_entfernen(z, alt)
        if aend:
            zustaende[b] = z_neu
            ereignisse.append(("kurseinheiten", f"{kopf}: Strategiezustand {b}: " + "; ".join(aend), b))
    return _abschliessen(journal, k, alt, neu, r, vorher, posten_je_buch, zustaende, ereignisse, zeilen, meldungen, jetzt_text, umrechnen=False)
