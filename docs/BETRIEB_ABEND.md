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
5. **„Freigeben und senden“** drücken und bestätigen. Vor dem Senden prüft der Bot den Schreibzugriff (seit 10.11.2026).
   Ist Read-Only noch an, wird **nichts** an IBKR übergeben, auch kein Tausch, und es erscheint „Read-Only im Gateway ist
   aktiv – bitte ausschalten und Tageslauf neu starten“. Die Freigaben bleiben bis 24 Uhr gültig. Das Protokoll zeigt je
   Order „von IBKR angenommen (Order …)“ oder den Grund der Ablehnung. Während des Sendens bleibt das Fenster bedienbar;
   **nicht schließen**, bis „Verbindung zum Gateway getrennt“ im Protokoll steht.
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

## Korrektur nach dem ersten Sendeversuch (03.11.2026)

- Der erste Versuch um 20:47 scheiterte: Die Orders 3–7 wurden mit dem Xetra-Kürzel als IBKR-Symbol gesendet (conId 0).
  IBKR führt EUNM als „IEMA“ und EUNN als „IJPA“ und lehnte mit Fehler 200 ab; das Protokoll meldete trotzdem
  „gesendet“. Das Journal ist korrigiert: Die Orders sind „abgelehnt“ und der Messbeginn ist zurückgesetzt
  (`tools/journal_korrektur_20261103.py`).
- Seitdem gilt:
  - Vor jedem Senden wird der Kontrakt qualifiziert (`config/kontrakte.yaml`, erzeugt mit `tools/kontrakte_pruefen.py`).
    Bei unbekanntem Kontrakt wird nicht gesendet, und der Vorschlag bekommt ein Veto „Kontrakt unbekannt“.
  - „Gesendet“ erst bei Annahme durch IBKR (PreSubmitted, Submitted). Eine Ablehnung wird „abgelehnt“ mit Fehlertext,
    ohne Reservierung. Bleibt nach 8 s jede Antwort aus, wird die Order „unbestätigt“: Sie reserviert die Kasse und ist
    im Gateway bzw. Client Portal zu prüfen.
  - Der Messbeginn eines Buchs beginnt erst mit seiner ersten angenommenen Order.
- Hinweis: Unter Read-Only lehnt das Gateway auch ReqOpenOrders ab (Meldung 321). Bis Read-Only aus ist, sieht der Bot
  keine offenen Orders bei IBKR. Den Schutz vor Doppelorders übernimmt dann das Journal (Orders unterwegs).

## Am nächsten Abend

Ausführungen und Abgleich prüfen. Stimmt der Abgleich („Bestände aller Bücher stimmen mit IBKR überein“) und sind die
Ausführungen plausibel (Preis ≤ Limit, Gebühr), schaltet Jakob die übrigen Bücher frei.
