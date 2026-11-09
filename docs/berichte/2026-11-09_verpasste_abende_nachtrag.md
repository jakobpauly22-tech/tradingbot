# Verpasste Abende 04.–08.11.2026: Nachtrag, Absicherung, IUSM, Probelauf (09.11.2026)

## 1. Ausführungen vom 04.11. nachgetragen

- **API geprüft (nur lesend, readonly):** `reqExecutions` liefert 0 Ausführungen, auch mit Zeitfilter ab 01.11.2026. Die
  Ausführungen vom 04.11. sind über die API nicht mehr abrufbar.
- **Flex:** Ist nicht eingerichtet (kein Token in `.env`). Der Beleg kommt deshalb aus Weg (b), also den IBKR-Positionen
  mit Einstand und der gemeldeten Gebühr von 3,00 € je Order (Paper-Festpreis).

| Buch | Titel (IBKR) | Stück | Einstand IBKR (inkl. Gebühr) | − 3,00 € → Preis | Tief–Hoch 04.11. | Eröffnung 04.11. |
| --- | --- | --- | --- | --- | --- | --- |
| real | SPYI.DE (SPYI) | 42 | 11,619524 | 11,5481 | 11,536–11,716 | 11,540 |
| crossover | IUSA.DE (IUSA) | 36 | 67,473333 | 67,3900 | 67,046–68,278 | 67,046 |
| crossover | SXR1.DE (SXR1) | 11 | 218,372727 | 218,1000 | 218,00–221,45 | 218,00 |
| crossover | EUNM.DE (IEMA) | 35 | 52,653714 | 52,5680 | 52,55–53,23 | 52,552 |
| crossover | EUNN.DE (IJPA) | 30 | 70,960000 | 70,8600 | 70,79–71,94 | 70,85 |

- **Gegenprobe:** Einstand × Stück − 3 € ergibt bei vier Titeln glatte Kurse, was dafür spricht, dass die Gebühr im
  Einstand steckt. SPYI (11,5481) ist ein Durchschnitt, vermutlich aus Teilausführungen. Die Kontokasse von
  990.709,16 € entspricht auf den Cent 1.000.000,00 € minus 9.290,84 € (Summe Einstand × Stück). Die Kassenbasis liegt
  damit bei genau 1.000.000,00 €, dem Startguthaben des Paper-Kontos.
- **Gebucht** mit `tools/ausfuehrungen_nachtragen.py --buchen`: Sicherung vorher (`journal_2026-11-09_093030.sqlite`)
  und nachher (`…_093031`). Für jede Ausführung ist die Quelle in `ausfuehrungen.quelle` vermerkt und ein Ereignis
  `nachtrag` angelegt. Uhrzeit und Handelsplatz sind unbekannt und im Journal als unbekannt vermerkt (Zeit = Handelstag
  04.11.).
- **Abgleich danach:** Bestand stimmt (5 Positionen). Kasse EUR stimmt (990.709,16 €). Realbuch: Kasse 11,98 €.
  Crossover: Kasse 1.197,18 €.
- Kauftag und Stop im Technikbuch kommen aus den Kursdaten (erster Handelstag nach dem Signal, also 04.11.). Der späte
  Nachtrag verschiebt also weder Zeit-Stop noch Stop.

## 2. Dauerhaft robust (Code und Tests)

- `betrieb/nachtrag.py`, im Tageslauf vor dem Abgleich: Eine Order unterwegs, deren Handelstag vorbei ist und die bei IBKR
  nicht mehr offen ist, gilt nur dann als verfallen, wenn die IBKR-Position nicht von den Büchern abweicht. Weicht sie
  ab, wird sie mit Beleg nachgetragen und im Protokoll gemeldet. Der Beleg kommt aus der Flex-Abfrage oder, falls keine
  eingerichtet ist, aus der Position mit Einstand (nur Käufe, die die Position allein erklären; Preis höchstens Limit und
  innerhalb von Tief und Hoch). **Ohne Beleg stoppt der Lauf**, und nichts wird gebucht oder als verfallen markiert.
- **Behoben:** Die Kassenbasis wird erst festgehalten, wenn der Bestands-Abgleich stimmt. Vorher hätte sie fehlende Käufe
  verschluckt.
- **Behoben:** Das Paper-Konto meldet die Kasse als `$LEDGER-CashBalance`. Der Adapter las nur `CashBalance`, deshalb
  blieb der Kassen-Abgleich seit dem 04.11. ungeprüft.
- `IbkrBroker(nur_lesen=True)`: verbindet readonly und verweigert das Senden. Genutzt vom Werkzeug und vom Probelauf.
- **Tests:** `tests/betrieb/test_nachtrag.py` mit 8 Fällen: Beleg aus Position, Beleg aus Flex, ohne Beleg → Stopp, Preis
  außerhalb der Tagesspanne → Stopp, Teilausführung → Stopp, ohne Abweichung → verfallen, Flex-Tausch, nächste Sitzung.
  Dazu ein Adaptertest (Ledger-Kasse, nur lesend). Volle Suite: 964 grün.

## 3. IUSM-Kontrakt

`tools/kontrakte_pruefen.py --ohne-aktien`: **IUSM.DE ist auflösbar**. Werte: conId 100292090, IBKR-Symbol BTMA, EUR,
primär AEB, Xetra-Platz IBIS2 gültig, „ISHARES USD TREASURY 7-10Y“, ISIN IE00B1FZS798. Damit entfällt das Veto
„Kontrakt unbekannt“. Die Tabelle umfasst jetzt 515 Kontrakte. Nicht auflösbar bleibt nur KVUE, und SXRM ist aus der
Liste verschwunden. Der Test `test_tabelle_deckt_universum_ab` ist auf IUSM umgestellt.

## 4. Probelauf aller Bücher (Kopie des echten Journals, Gateway nur lesend)

`tools/tageslauf.py --kopie`, 09.11.2026 09:46. Signaltag ist der 06.11. (Xetra heute noch offen); der echte Lauf heute
Abend rechnet mit dem Schluss vom 09.11.

- Abgleich: Bestände stimmen (5 Positionen), Kasse EUR stimmt (990.709,16 €).
- Kassenbasis: EUR 1.000.000,00, festgehalten 09.11.2026.

| Buch | Bestand / Kasse | Vorschläge (alle ohne Veto) |
| --- | --- | --- |
| real | SPYI 42 / 11,98 € | keine (Kasse reicht für keinen Anteil) |
| crossover | IEMA 35, IJPA 30, IUSA 36, SXR1 11 / 1.197,18 € | **VERKAUF 30 EUNN.DE (Stop 69,04 € am 06.11. gerissen, Schluss 69,02 €)**; KAUF 11 EUNK.DE (Limit 107,70 €, SMA50 2,8 % über SMA200) |
| momentum | – / 10.000 € | Aufbau: KAUF 33 EUNM, 28 EUNN, 35 IUSA, 10 SXR1 |
| fundamental_a | – / 10.000 € | Aufbau: Tausch 9.064 € → USD, 20 US-Käufe (neu ADBE und LOW; STE und TPR nicht mehr dabei) |
| fundamental_b | – / 10.000 € | Aufbau: Tausch 7.828 € → USD, 19 US-Käufe (CASY nicht kaufbar: 688 USD je Anteil) |

Alle Kontrakte wurden aufgelöst, es gibt kein Veto. Für die 39 US-Käufe gilt: Freigabe zwischen 22:05 und 22:50 Uhr.

## Offene Punkte für Jakob

1. **Verpasster Stop:** Den Stop von EUNN.DE im Crossover-Buch hat der Schluss am Freitag, 06.11., gerissen. Ohne
   Abendlauf gab es keinen Vorschlag. Heute Abend gilt der Schluss vom 09.11.: Liegt er wieder über 69,04 €, kommt kein
   Verkauf. Soll der Tageslauf Stops verpasster Tage nachholen (Schluss seit dem letzten Lauf), oder gilt „verpasster
   Abend = verpasster Trade“ auch für Stops? Ich habe das nicht geändert.
2. **Zinsen im Paper-Konto:** IBKR meldet aufgelaufene Zinsen (`AccruedCash`) von 225,74 €. Werden sie gebucht, steigt
   die Kasse um mehr als 10 €, und der Kassen-Abgleich stoppt als „unerklärte Buchung“. Vorschlag: Zinsgutschriften mit
   Beleg in die Kassenbasis übernehmen, etwa über Flex (Cash Transactions) oder bis zur Höhe des vorherigen
   `AccruedCash`. Das ist eine Entscheidung über die 10-€-Grenze, deshalb nicht umgesetzt.
3. **Flex-Abfrage einrichten** (empfohlen, liefert vollwertige Belege mit Ausführungs-ID, Zeit und Platz): Im Client
   Portal des Paper-Kontos unter „Performance & Reports → Flex Queries“ eine Activity-Flex-Query mit dem Abschnitt Trades
   anlegen (Felder unter anderem Order Reference, IB Execution ID, Trade Price, IB Commission, Date/Time, Exchange,
   Conid, Buy/Sell, Quantity, Asset Category, Zeitraum mindestens „Last 30 Days“, damit die Nachträge vom 04.11. beim ersten Abruf noch enthalten sind). Dann den Flex Web Service aktivieren und
   `FLEX_TOKEN` sowie `FLEX_QUERY_ID` in die `.env` eintragen. Ob Flex für Paper-Konten freigeschaltet ist,
   habe ich nicht geprüft.
4. Für den Weg über die Position stand zunächst pauschal `nachtrag.gebuehr_je_order: 3.0` in `config/betrieb.yaml`. Am
   selben Tag ersetzt durch die Gebühr je Markt und Währung (siehe Nachtrag unten).

## Nachtrag: Entscheidungen Jakob 09.11.2026, umgesetzt

Alle Punkte mit Tests (`tests/betrieb/test_nachtrag.py`, jetzt 15 Fälle). Volle Suite: 971 grün. Details in
`docs/BETRIEB.md`, Abschnitt „Entscheidungen Jakob 09.11.2026“.

1. **Verpasste Tage:** Das Technikbuch prüft die Schlusskurse seit dem letzten Lauf der Reihe nach. Ausstiege werden
   nachgeholt und im Vorschlag vermerkt (Beispiel: „Stop … gerissen am 04.11., nachgeholt“). Einstiege verpasster Tage
   werden verworfen; die Monatsprüfung von Momentum läuft am aktuellen Tag. Heute Abend (Signaltag 09.11.) prüft das
   Crossover-Buch die Tage 04.–06.11. Der Stop von EUNN.DE vom 06.11. wird damit nachgeholt, egal wo der Schluss am 09.11.
   liegt.
2. **Zinsen:** Eine Kassenerhöhung gilt als belegte Zinsbuchung, wenn die aufgelaufenen Zinsen (`AccruedCash`) um
   denselben Betrag gefallen sind. Sie geht dann in die Kassenbasis, ohne Stopp und ohne Zinsen in den Büchern. Den
   Vergleichsstand hält jeder stimmende Abgleich fest, erstmals beim Tageslauf heute Abend (zurzeit 225,74 €).
   Einschränkung: Laufen zwischen dem letzten Abgleich und der Gutschrift schon neue Zinsen auf, ist die Abnahme kleiner
   als die Gutschrift, und der Lauf stoppt. Das ist sicher, aber dann ist eine Klärung nötig.
3. **Flex:** Die Variablen heißen jetzt `FLEX_TOKEN` und `FLEX_QUERY_ID` (`.env.example` ergänzt). Die Anleitung steht
   oben unter „Offene Punkte“, Punkt 3.
4. **Nachtragsgebühr je Markt und Währung** (`nachtrag.gebuehr`):
   - Xetra: 3,00 € je Order.
   - US-Aktien nach IBKR Pro Fixed: 0,005 USD je Aktie, mindestens 1,00 USD, höchstens 1 % des Orderwerts. Quelle:
     interactivebrokers.com/en/pricing/commissions-stocks.php, geprüft 09.11.2026.
   - Die Gebühr ist als „angenommen“ markiert, auch bei den fünf Nachträgen vom 04.11. Beim nächsten Flex-Abruf wird
     sie abgeglichen: Die abgeleitete Zeile wird durch die Flex-Ausführungen ersetzt (Ereignis `nachtrag_abgleich`). Bei
     abweichender Stückzahl stoppt der Lauf.

**Probelauf (nur lesend) 09.11.2026 10:05** auf einer Kopie des Journals, Signaltag 06.11.:
- Bestand und Kasse stimmen (EUR 990.709,16), Kassenbasis EUR 1.000.000,00.
- Crossover hat die verpassten Tage 04. und 05.11. geprüft.
- Vorschläge wie am Vormittag: Crossover verkauft EUNN (Stop, hier am aktuellen Tag 06.11.) und kauft EUNK; Momentum
  baut 4 Positionen auf; Fundamental A und B bauen 20 bzw. 19 Positionen auf, jeweils mit Tausch EUR→USD.
- Kein Veto, alle Kontrakte aufgelöst.
