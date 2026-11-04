# Betrieb (Paper Trading) – Abweichungen und Festlegungen

Ablauf am Abend: `docs/BETRIEB_ABEND.md`.

## Abweichungen zum Backtest

| Seit | Abweichung | Grund | Wirkung |
| --- | --- | --- | --- |
| 03.11.2026 | **Routing über SMART** mit Xetra (IBIS2) als Primärbörse, Kontrakt per conId, statt Direktrouting an IBIS2 | Direktrouting blockieren die API-Vorsichtseinstellungen (Fehler 10311). Die Einstellungen im Gateway bleiben unverändert (Jakob). | Die Ausführung liegt nicht zwingend in der Xetra-Eröffnungsauktion, die der Backtest unterstellt (Eröffnungskurs). IBKR kann an einen anderen Platz routen, etwa gettex oder Tradegate. Der Ausführungsplatz steht je Ausführung im Journal (`ausfuehrungen.boerse`), damit sich die Abweichung messen lässt. |
| 03.11.2026 | **Kauflimit auf die gültige Kursstufe abgerundet** (reqMarketRule, gemeinsame Stufe der Regeln von SMART und Xetra) | Fehler 110: SXR1 221,34 € verletzt die Stufe 0,05 € ab 200 € | Das Limit liegt höchstens eine Kursstufe unter Vortagesschluss + 2 %, die 2-%-Grenze bleibt eingehalten. Verkaufslimits (falls künftig) werden aufgerundet. |

## Gebühren (04.11.2026)

- **Preismodell:** Das Kostenmodell (`config/backtest.yaml`, 1,25 € Minimum an EUR-Börsen) setzt das IBKR-Modell
  „Gestaffelt“ (Tiered) voraus. Das echte Konto ist seit 04.11.2026 darauf umgestellt; vorher galt Festpreis mit 3 €
  Minimum bei SMART.
- **Buchung:** Kasse und Auswertungen buchen die Gebühr laut Kostenmodell (je Order, bei Teilausführungen das Minimum
  einmal). Die tatsächliche Gebühr aus dem CommissionReport steht daneben (`ausfuehrungen.gebuehr_ibkr`). Das
  Paper-Konto rechnet offenbar kaum Gebühren, deshalb zeigt der Tageslauf je Ausführung „Gebühr IBKR …, Modell …
  (gebucht), Abweichung …“ an und korrigiert nichts.

## Kontrakte (04.11.2026)

`config/kontrakte.yaml` (`tools/kontrakte_pruefen.py`, nur lesend) ordnet 514 Werte zu: Core, Satellite, Xetra-Gold,
EUR.USD (IDEALPRO) und die S&P-500-Aktien. Nicht auflösbar, also beim Senden Veto „Kontrakt unbekannt“:
- **SXRM.DE:** Die ISIN IE00B3VWN518 ist bei IBKR nicht an Xetra handelbar, nur an der SIX (CSBGU0, USD) und der LSE.
  Ob ein Ersatz oder ein anderer Platz kommt, entscheidet Jakob. Bis dahin kann der Satellite diesen Wert nicht kaufen.
- **KVUE:** Unter SMART/USD gibt es keinen Treffer (vermutlich nach der Übernahme nicht mehr gelistet).
