# Betrieb (Paper Trading) – Abweichungen und Festlegungen

Ablauf am Abend: `docs/BETRIEB_ABEND.md`.

## Abweichungen zum Backtest

| Seit | Abweichung | Grund | Wirkung |
| --- | --- | --- | --- |
| 03.11.2026 | **Routing über SMART** mit Xetra (IBIS2) als Primärbörse, Kontrakt per conId, statt Direktrouting an IBIS2 | Direktrouting blockieren die API-Vorsichtseinstellungen (Fehler 10311). Die Einstellungen im Gateway bleiben unverändert (Jakob). | Die Ausführung liegt nicht zwingend in der Xetra-Eröffnungsauktion, die der Backtest unterstellt (Eröffnungskurs). IBKR kann an einen anderen Platz routen, etwa gettex oder Tradegate. Der Ausführungsplatz steht je Ausführung im Journal (`ausfuehrungen.boerse`), damit sich die Abweichung messen lässt. |
| 04.11.2026 | **US-Käufe als Limit-On-Open** (tif OPG) | Ausführung zur Eröffnung, unabhängig von der Freigabezeit | Nimmt IBKR OPG für ein Papier nicht an, wird die Order abgelehnt gemeldet. Ein Ersatz-Ordertyp kommt nur mit Jakobs Zustimmung. Je Ausführung stehen Zeit, Handelsplatz und Eröffnungskurs des Heimatplatzes im Journal, die Abweichung im Protokoll. |
| 04.11.2026 | **Nachkauf abgelehnter oder verfallener Käufe** | Restfall eines Aufbaus (Jakob) | Fundamental: bis zum nächsten Quartalsstichtag, mit dem Gewicht vom letzten Stichtag. Technik: solange das Signal gilt (Crossover SMA50 > SMA200, Momentum 12−1 > 0). Der Backtest kennt keine Ablehnungen. |
| 03.11.2026 | **Stückzahl der Technik-Käufe zusätzlich durch die 1-%-Regel vom Limit begrenzt** | Risiko vom schlechtesten Einstieg (Jakob) | Der Backtest begrenzt über das Gewicht (Risiko vom Schluss, Ausführung zur Eröffnung); im Betrieb können es einzelne Stücke weniger sein. Zielgewichte, Reihenfolge nach Stärke und Restkasse kommen aus derselben Funktion `SatelliteStrategie.zielgewichte` wie im Backtest. |
| 03.11.2026 | **Kauflimit auf die gültige Kursstufe abgerundet** (reqMarketRule, gemeinsame Stufe der Regeln von SMART und Xetra) | Fehler 110: SXR1 221,34 € verletzt die Stufe 0,05 € ab 200 € | Das Limit liegt höchstens eine Kursstufe unter Vortagesschluss + 2 %, die 2-%-Grenze bleibt eingehalten. Verkaufslimits (falls künftig) werden aufgerundet. |

## Gebühren (04.11.2026)

- **Preismodell:** Das Kostenmodell (`config/backtest.yaml`, 1,25 € Minimum an EUR-Börsen) setzt das IBKR-Modell
  „Gestaffelt“ (Tiered) voraus. Das echte Konto ist seit 04.11.2026 darauf umgestellt; vorher galt Festpreis mit 3 €
  Minimum bei SMART.
- **Buchung (Entscheidung Jakob 04.11.2026, ersetzt die Festlegung vom Vormittag):** Das Paper-Konto rechnet Festpreis,
  3 € je Order, und lässt sich nicht umstellen. Journal und Kasse buchen deshalb die tatsächliche IBKR-Gebühr; die Kasse
  je Währung ist Teil des Abgleichs (Toleranz 0,05, Kassenbasis einmalig festgehalten). Die Modellgebühr (Tiered,
  1,25 € Minimum) steht je Ausführung daneben (`gebuehr_modell_eur`). Der Bericht weist den Buchwert zweimal aus: „wie
  gebucht (Paper, Festpreis)“ und „mit Modellgebühr (Tiered)“. Maßgeblich für den späteren Echtbetrieb ist der zweite.
  Der Risk-Manager prüft weiter mit der Modellgebühr. Die gemeldete IBKR-Gebühr steht täglich im Protokoll, damit ein
  späterer Wechsel des Paper-Kontos auf Tiered auffällt.

## Kontrakte (04.11.2026)

`config/kontrakte.yaml` (`tools/kontrakte_pruefen.py`, nur lesend) ordnet 514 Werte zu: Core, Satellite, Xetra-Gold,
EUR.USD (IDEALPRO) und die S&P-500-Aktien. Nicht auflösbar, also beim Senden Veto „Kontrakt unbekannt“:
- **SXRM.DE:** Die ISIN IE00B3VWN518 ist bei IBKR nicht an Xetra handelbar, nur an der SIX (CSBGU0, USD) und der LSE.
  Ob ein Ersatz oder ein anderer Platz kommt, entscheidet Jakob. Bis dahin kann der Satellite diesen Wert nicht kaufen.
- **KVUE:** Unter SMART/USD gibt es keinen Treffer (vermutlich nach der Übernahme nicht mehr gelistet).

## Zusammensetzung des S&P 500 (04.11.2026)

Quelle ist Wikipedia (aktuelle Liste und Änderungstabelle), Stand 01.11.2026; die letzte erfasste Änderung ist vom
06.10.2026 (TWLO rein, WBD und CTVA raus). Kenvue (KVUE) steht dort noch als Mitglied. Der letzte Yahoo-Kurs ist aber
vom 30.10.2026, und bei IBKR gibt es keinen Kontrakt; vermutlich ist die Notierung nach der Übernahme durch Kimberly-Clark
beendet. Seitdem entfernt der Tageslauf vor der Rangliste jeden Titel, dessen letzter Kurs älter als 5 Handelstage ist
oder der in `config/kontrakte.yaml` unter `nicht_aufloesbar` steht, und meldet ihn.

## Ersatz für SXRM (offen, Entscheidung Jakob)

SXRM (IE00B3VWN518) ist bei IBKR nicht an Xetra handelbar. Kandidaten mit demselben Index (ICE US Treasury 7–10 Year)
gibt es nur bei iShares:
- **iShares $ Treasury Bond 7-10yr UCITS ETF USD (Dist), IE00B1FZS798, Xetra IUSM:** Yahoo-Historie ab 02.2009,
  ausschüttend wie IUSA. Replikation laut Quellen „optimiert/Sampling“, also physisch, aber nicht vollständig.
- **EUR-Hedged (Dist) IE00BGPP6697 und (Acc) IE000K1VI152:** Sie folgen der währungsgesicherten Variante des Index.
  Die Xetra-Historie (IBB1 ab 02.2019) reicht nicht bis 2012 zurück.
- Andere 7–10-Jahre-ETFs (Invesco, Xtrackers, Amundi, SPDR) folgen Bloomberg- oder iBoxx-Indizes, nicht dem ICE-Index.

**Entscheidung (Jakob 04.11.2026):** IUSM ersetzt SXRM (gleicher Fonds, ausschüttende Klasse, analog IUSA statt SXR8).
Ausschüttungen fließen wie bei IUSA in die Kasse; es gibt keine neue Variante. Eingetragen in `config/technik.yaml`. Den
Kontrakt trägt `tools/kontrakte_pruefen.py` nach dem Gateway-Start ein, nur wenn IBKR IUSM an Xetra in EUR führt. Bis
dahin bekommt IUSM wie zuvor SXRM ein Veto „Kontrakt unbekannt“.

## Kassenbasis und Zeitfenster (04.11.2026)

- Buchungen ohne Buchbezug (Zinsen, Kontogebühren) gehen in die Kassenbasis und werden protokolliert (Ereignis
  `kassenbasis`, Liste im Zustand `_konto`). Der Abgleich stoppt nur, wenn eine Abweichung je Währung 10 € übersteigt
  (`sicherheit.abgleich_buchung_ohne_buchbezug_max`). Ob eine Buchung bis 10 € tatsächlich Zins oder Gebühr ist, kann die
  API nicht belegen (dafür wären Flex-Abfragen nötig). Sie gilt deshalb als „vermutet“ und steht im Protokoll.
- **Zeitpunkt der Freigabe:** Für US-Käufe (Limit-On-Open) und den EUR→USD-Tausch zeigt der Tageslauf einen Hinweis, und
  bei der Freigabe erscheint eine Warnung in der Bestätigung: nicht vor 22:00 Uhr (US-Handel offen) und nicht zwischen
  22:55 und 23:15 Uhr (FX-Tagesschluss). Empfohlen sind 22:05–22:50 Uhr. Das ist ein Hinweis, keine Sperre.
- **S&P-500-Liste:** Sie wird wöchentlich erneuert (Wikipedia-Cache höchstens 7 Tage alt) und an jedem Quartalsstichtag
  zwingend neu abgerufen. Den Stand zeigt das Protokoll: Abruf der Liste und letzte erfasste Änderung.
