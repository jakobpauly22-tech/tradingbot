# Read-Only-Vorfall 09.11.2026: Abgleich, Korrektur, Absicherung (10.11.2026)

## 1. Abgleich mit IBKR (nur lesend) und Korrektur des Journals

Alle offenen Orders (`reqAllOpenOrders`) und die heutigen Ausführungen, abgeglichen mit dem Journal am 10.11. ab 09:06:

| Buch | Journal | IBKR |
| --- | --- | --- |
| fundamental_a | Tausch ausgeführt; 20 US-Käufe „gesendet“, Order 55–93 | 20 offen (OPG, PreSubmitted), permId 192793080–099 |
| fundamental_b | Tausch ausgeführt; 19 US-Käufe „gesendet“, Order 97–129, 137, 139 | 19 offen, permId 192793101–119 (WMT, WST aus dem zweiten Lauf) |
| momentum | 4 Käufe „gesendet“, Order 141–147 | heute ausgeführt: EUNM 33, EUNN 28, IUSA 34, SXR1 10 (= Stückzahl der Order) |
| crossover | Verkauf EUNN.DE (Order 49), Kauf EUNK.DE (Order 51) „unbestaetigt“, Fehler 321 | **nicht vorhanden** (weder offen noch ausgeführt) |

Es gibt keine offene Order und keine Ausführung ohne Journalbezug, und keine Duplikate.

**Korrektur** (`tools/journal_korrektur_20261110.py --buchen`, nichts storniert; Sicherungen
`journal_2026-11-10_091337.sqlite` und `…_091337_2.sqlite`, Ereignis `korrektur`):
- Die US-Orders von 22:07 standen schon richtig als „gesendet“ mit Order-ID im Journal; es war keine Änderung nötig.
- Crossover 49 und 51: von „unbestaetigt“ auf „abgelehnt“ gesetzt. Damit entfallen Reservierung und Titelsperre.
- Crossover-Strategiezustand auf den Stand nach dem Lauf vom 03.11. zurückgesetzt, weil die Orders des Laufs vom 09.11.
  nie angekommen sind. Der Tageslauf heute Abend prüft damit die Tage 04.–09.11. und schlägt den **Verkauf EUNN.DE
  („Stop 69.04 gerissen am 06.11., nachgeholt“)** neu vor. EUNK.DE kommt, wenn das Crossover-Signal am 10.11. gilt.
- Die Momentum-Ausführungen von heute liest der Tageslauf heute Abend über die API ein. Fällt der Abend aus, gilt der
  Nachtrag-Weg vom 09.11.

## 2. Absturz: Ursache und Behebung

**Ursache:** Die Windows-Ereignisanzeige meldet um 22:07:36 „Application Hang“ (AppHangB1) für pythonw.exe; Windows hat
das nicht reagierende Fenster geschlossen. Das Senden lief im Fenster-Thread, und allein die beiden Wartezeiten von je
8 s auf die Read-Only-Ablehnungen haben es eingefroren. Ein Python-Fehler lag nicht vor. Abgebrochen wurde mitten in
fundamental_b nach WMB.

**Behebung (mit Tests, `tests/betrieb/test_read_only.py`, 8 Fälle):**
- **Schreibprüfung vor jedem Senden** (`IbkrBroker.schreibzugriff`) über eine reine Abfrage ohne Order
  (`reqCompletedOrders`). Unter Read-Only antwortet das Gateway sofort mit Fehler 321. Heute Morgen live geprüft, Read-Only
  war an: „ReqCompletedOrders … Die API befindet sich im schreibgeschützten Modus“. Bei 321 oder ohne Antwort in 3 s
  ruft der Bot kein `placeOrder` auf, auch nicht für den Tausch, und meldet „Read-Only im Gateway ist aktiv – bitte
  ausschalten und Tageslauf neu starten“. Die Freigaben bleiben bis 24 Uhr gültig.
- Kommt während des Sendens doch eine 321-Ablehnung, bricht der Bot sofort ab und übergibt keine weitere Order.
  `ValidationError` zählt als „abgelehnt“.
- Das Fenster bleibt während des Sendens bedienbar (Ereignisse zwischen den Orders und beim Warten), ein zweites Senden
  ist gesperrt, und jede Ausnahme wird zur Meldung statt zum Absturz.
- **Nicht live getestet:** die Schreibprüfung bei ausgeschaltetem Read-Only (erwartet: Liste der abgeschlossenen
  Orders). Das zeigt sich heute Abend im Protokoll an der Zeile „Schreibzugriff im Gateway geprüft“.

## 3. Dokumentation

`docs/BETRIEB.md` (Abschnitt „Read-Only-Vorfall 09.11.2026“) und `docs/BETRIEB_ABEND.md` (Schritt 5). Dort steht die
Feststellung, dass das Gateway unter Read-Only blockierte Orders parkt und beim Abschalten nachsendet, und dass der Bot
deshalb vor dem Senden selbst prüft.

**Anmerkung zum Ablauf (zur Prüfung durch Jakob):** Laut Freigabeprotokoll begann die Freigabe um 22:06:48; der
Tageslauf ab 21:53 rechnete bis 22:00. Die beiden Orders mit Fehler 321 (Crossover) sind nicht nachgesendet worden. Die
angekommenen Orders hat der Bot nach seinem Journal ab 22:07:22 übergeben, und IBKR hat sie sofort bestätigt. Das spricht
eher dafür, dass Read-Only um 22:07:21 während des Sendens ausgeschaltet wurde, als für ein Parken im Gateway. Belegen
lässt sich keins von beiden. Für die Absicherung spielt das keine Rolle: Geprüft wird jetzt vor dem Senden.

## Heute Abend

1. Tageslauf nach 17:30 Uhr starten (Read-Only darf dafür an sein). Erwartet:
   - momentum: 4 Ausführungen eingelesen
   - crossover: Prüfung der Tage ab 04.11., Verkauf EUNN nachgeholt
   - fundamental: Ausführungen der US-Käufe, soweit IBKR sie zur Eröffnung (OPG) ausgeführt hat; nicht ausgeführte
     sind verfallen
   - Abgleich und Kasse stimmen
2. Read-Only ausschalten, dann freigeben. Ist Read-Only noch an, wird nichts gesendet.
