# IB Gateway: Verbindungstest (nur lesend), 02.11.2026

`tools/broker_verbindungstest.py`, Paper-Konto, Port 4002, Gateway mit Read-Only-API, nur 127.0.0.1.

```
Verbinde mit 127.0.0.1:4002 (Client-ID 1, Modus paper) …
Konto: DUR3… → Paper-Konto
Nettowert: 1,000,000.00 EUR
Positionen: 0
Offene Orders: 0
Marktdaten SPYI.DE: keine Daten – Marktdaten-Freigabe im Paper-Konto prüfen
```

- Verbindung, Paper-Konto (DU…), Kontowerte, Positionen und offene Orders: in Ordnung.
- Kontrakt: Der erste Lauf fand SPYI nicht, weil der Adapter Xetra-ETFs unter „IBIS“ suchte. IBKR führt sie unter
  **IBIS2** (Aktien unter IBIS). Behoben; Kontrakt SPYI, IBIS2, EUR, conId 89384965, ISIN IE00B3YLTY66 (Treffer auch
  über die ISIN-Suche). Orders gehen direkt an IBIS2, nicht über SMART, damit sie in die Xetra-Eröffnungsauktion gehen.
- Marktdaten: „No market data permissions for IBIS2 STK“. Das Paper-Konto hat keine Xetra-Marktdaten. Für Signale und
  Limits nutzt der Bot ohnehin Yahoo (Vortagesschluss); IBKR-Marktdaten wären nur eine Gegenprobe. Entscheidung offen.
