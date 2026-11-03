# Anleitung für den Abend (Paper Trading, erster Sendeabend 03.11.2026)

Freischaltung durch Jakob am 03.11.2026: `senden_freigeschaltet: true` global, je Buch nur **real** und **crossover**.
Fundamental A, Fundamental B und Momentum zeigen ihre Vorschläge, sind aber nicht freigebbar (rot markiert im Fenster).
Die übrigen Bücher schaltet Jakob erst frei, wenn er am nächsten Abend die Ausführungen und den Abgleich geprüft hat
(`config/betrieb.yaml`, `buecher.<buch>.senden_freigeschaltet`).

## Ablauf

1. **IB Gateway starten** und mit dem Paper-Konto anmelden (Port 4002, nur 127.0.0.1). **Read-Only bleibt zunächst an.**
2. **Ab 18 Uhr `Tageslauf.bat`** starten. Der Tageslauf liest die Ausführungen, gleicht die Bestände ab und rechnet die
   Vorschläge. Dafür reicht Read-Only. Im Protokoll sollten „Gateway verbunden, Konto DU…“ und „Journal gesichert: …“
   stehen. Fehlt die Sicherungszeile, ist `JOURNAL_BACKUP_DIR` in `.env` nicht gesetzt.
3. **Vorschläge prüfen:** Kurzzeile und „Details ▸“ je Vorschlag. Real: einzeln abhaken; Crossover: Sammelfreigabe.
4. **Read-Only im Gateway erst unmittelbar vor der ersten Freigabe ausschalten** (Gateway: Konfiguration → API →
   Einstellungen → „Read-Only API“ abwählen → Übernehmen). Das Fenster bleibt dabei offen. Vor dem Senden verbindet
   sich der Bot neu, liest die Ausführungen ein und gleicht erneut ab.
5. **„Freigeben und senden“** drücken und bestätigen. Das Protokoll zeigt je Order „gesendet (Order …)“ oder den Grund
   der Ablehnung.
6. **Nach dem Senden** Read-Only im Gateway wieder einschalten. Das Fenster schließen.

## Was technisch dahintersteht

- Beim Verbinden ruft der Bot Positionen, offene Orders, Kontodaten und Ausführungen ab (reqExecutions, auch unter
  Read-Only erlaubt). Den Abruf abgeschlossener Orders (ReqCompletedOrders) schaltet der Bot seit dem 03.11.2026 ab. Er
  wird nicht gebraucht, und IBKR hat ihn unter Read-Only als Schreibzugriff abgelehnt (Gateway-Hinweis 13:38). Der
  Abgleich hängt also nicht davon ab, ob Read-Only an oder aus ist. Fehlermeldungen des Gateways landen als
  „(kein Abbruch) Gateway-Meldung …“ im Protokoll.
- **Laufsperre:** Solange ein Tageslauf-Fenster offen ist, verweigert ein zweiter Start desselben Journals den Lauf
  (Sperrdatei `daten/betrieb/tageslauf.sperre`, Probe getrennt). Nach einem Absturz wird die Sperre automatisch
  übernommen, weil der eintragende Prozess nicht mehr läuft.
- **Orders unterwegs:** Gesendete, noch nicht ausgeführte Orders reservieren die Kasse (Limit plus höchstens 1 % Gebühr)
  und sperren neue Vorschläge für denselben Titel im selben Buch. Ein zweiter Tageslauf am selben Abend wiederholt
  keine Käufe. Am nächsten Abend werden sie entweder als Ausführung eingelesen oder, wenn nicht ausgeführt, als
  „verfallen“ markiert. Danach ist der Titel wieder frei.
- **1-%-Regel vom Limit:** Satellite-Käufe riskieren höchstens 1 % des Buchwerts, gemessen vom Limit als schlechtestem
  Einstiegskurs bis zum Stop. Die Stückzahl wird schon im Vorschlag entsprechend begrenzt.

## Am nächsten Abend

Ausführungen und Abgleich prüfen. Stimmt der Abgleich („Bestände aller Bücher stimmen mit IBKR überein“) und sind die
Ausführungen plausibel (Preis ≤ Limit, Gebühr), schaltet Jakob die übrigen Bücher frei.
