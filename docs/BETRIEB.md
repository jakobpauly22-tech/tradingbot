# Betrieb (Paper Trading) – Abweichungen und Festlegungen

Ablauf am Abend: `docs/BETRIEB_ABEND.md`.

## Abweichungen zum Backtest

| Seit | Abweichung | Grund | Wirkung |
| --- | --- | --- | --- |
| 03.11.2026 | **Routing über SMART** mit Xetra (IBIS2) als Primärbörse, Kontrakt per conId, statt Direktrouting an IBIS2 | Direktrouting blockieren die API-Vorsichtseinstellungen (Fehler 10311). Die Einstellungen im Gateway bleiben unverändert (Jakob). | Die Ausführung liegt nicht zwingend in der Xetra-Eröffnungsauktion, die der Backtest unterstellt (Eröffnungskurs). IBKR kann an einen anderen Platz routen, etwa gettex oder Tradegate. Der Ausführungsplatz steht je Ausführung im Journal (`ausfuehrungen.boerse`), damit sich die Abweichung messen lässt. |
| 03.11.2026 | **Kauflimit auf die gültige Kursstufe abgerundet** (reqMarketRule, gemeinsame Stufe der Regeln von SMART und Xetra) | Fehler 110: SXR1 221,34 € verletzt die Stufe 0,05 € ab 200 € | Das Limit liegt höchstens eine Kursstufe unter Vortagesschluss + 2 %, die 2-%-Grenze bleibt eingehalten. Verkaufslimits (falls künftig) werden aufgerundet. |
