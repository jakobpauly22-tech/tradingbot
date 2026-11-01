# Trading-Bot: Ideen und Roadmap

Stand: 01.11.2026. Kopie der Roadmap aus dem Claude-Doc „Trading-Bot: Ideen und Roadmap“ (https://claude.ai/artifact/QMxAbDr3aaaf48muuS1a5B). Neue Entscheidungen trifft Jakob; diese Datei wird dann nachgezogen.

## Grundprinzip und Architektur

Keine Einzelstrategie, sondern vier unabhängige Signal-Engines, die in einem Score zusammenlaufen. Jede Engine lässt sich einzeln bauen, testen und gewichten.

```
Daten: Kurse, Bilanzen, Makro (FRED), Briefing-Archiv, 13F/Insider
   │
   ├──► Fundamental-Engine ──┐
   ├──► Technik-Engine ──────┤
   ├──► News-Engine ─────────┼──► Scoring + Regime ──► Risk-Manager (Veto) ──► Ausführung (Paper zuerst) ──► Journal
   └──► Smart-Money-Engine ──┘                                                                               │
              ▲                                                                                              │
              └──────────── Rückkopplung: Journal und Backtests kalibrieren die Gewichte ◄────────────────────┘
```

Jede Engine liefert pro Aktie einen Score. Der Risk-Manager kann jeden Trade blockieren, und das Journal kalibriert die Gewichte zurück.

**Realistische Erwartung:** Die meisten aktiven Strategien schlagen den Index nach Kosten nicht, auch professionelle. Deshalb zählt jede Engine nur, wenn sie im Backtest gegen die Benchmark besteht. Zusatznutzen: Sauber dokumentiert auf GitHub ist der Bot ein starkes Projekt für Bewerbungen im Asset Management.

## Anlagehorizont: Core und Satellite

Entschieden am 31.10.2026: Der Großteil wird langfristig angelegt, ein kleinerer Teil kurzfristig gehandelt, um zusätzliche Überrendite zu suchen. Aufteilung: 70 % Core, 30 % Satellite.

| Merkmal | Core (langfristig) | Satellite (kurzfristig) |
| --- | --- | --- |
| Anteil am Kapital | 70 % | 30 % |
| Haltedauer | Monate bis Jahre | Tage bis ca. 3 Monate |
| Haupt-Signale | Fundamental-Engine, Smart Money (13F-Verzögerung stört hier kaum) | News, Earnings Surprise und PEAD, Momentum, Regime |
| Risikoregeln | Diversifikation, Rebalancing in festen Abständen | kleine Positionen, enge Stops, eigenes Verlustlimit |
| Erfolgsmessung | MSCI ACWI IMI plus Vergleichsindizes (siehe Benchmarks) | Rendite nach Kosten gegen Core und MSCI ACWI IMI |

Beide Teile bekommen ein getrenntes Risikobudget, Verluste im Satellite dürfen den Core nie berühren. Liefert der Satellite nach Kosten keine Überrendite, wird sein Anteil reduziert.

### Benchmarks für den Core

Hauptmaßstab ist der MSCI ACWI IMI statt des MSCI World, weil er den investierbaren Weltmarkt inklusive Schwellenländern und Nebenwerten abbildet. Vier Vergleichsindizes zeigen, woher eine Über- oder Unterrendite kommt.

| Index | Was er abbildet | US-Anteil | Rolle im Bot |
| --- | --- | --- | --- |
| [MSCI ACWI IMI](https://www.msci.com/documents/10199/255599/msci-acwi-imi-net.pdf) | Large, Mid und Small Caps aus 23 Industrie- und 24 Schwellenländern | – | Hauptbenchmark Core |
| [MSCI ACWI](https://www.msci.com/documents/10199/255599/msci-acwi-net.pdf) | Large und Mid Caps aus denselben 47 Ländern, rund 85 % des investierbaren Weltmarkts | 64,2 % | Alternative, falls der Core keine Nebenwerte kauft |
| [FTSE All-World GDP-Adjusted](https://extraetf.com/de/etf-profile/IE000KCKFHE8) | FTSE All-World, nach Bruttoinlandsprodukt statt Börsenwert gewichtet | – | Welt nach Wirtschaftskraft |
| [MSCI ACWI IMI Value Weighted](https://www.msci.com/documents/10199/b662d248-2e88-4f88-9e61-f6daaf461da4) | ACWI IMI, gewichtet nach Umsatz, Buchwert, Gewinn und Cash Earnings | 46,6 % | Messlatte für die Fundamental-Engine |
| [MSCI World ex USA](https://zendepot.de/etf/msci-world-ex-usa-etf) | Industrieländer ohne USA | 0 % | Zeigt, ob Rendite nur aus US-Aktien kommt |
| [MSCI World](https://www.finanztip.de/daily/top-5-die-groessten-laender-im-msci-world/) | 23 Industrieländer | 71,9 % | Bekannte Referenz, nicht mehr Hauptmaßstab |

US-Anteile: MSCI ACWI und Value Weighted per 30.09.2026 laut MSCI-Factsheets, MSCI World per 30.04.2026 laut MSCI über Finanztip. Hohe Hürde: Die Value-Weighted-Variante kam seit 1994 auf 9,47 % p.a. gegenüber 8,76 % für den ACWI IMI (vor 2011 zurückgerechnet). Die Fundamental-Engine muss also mehr leisten als eine simple fundamentale Gewichtung.

## Risikoprofil und Limits

Die Limits richten sich nach der Risikotragfähigkeit, weil sie niedriger ist als die Risikobereitschaft.

**Profil aus dem Fragebogen vom 31.10.2026:**

- **Risikobereitschaft eher hoch:** Belastung im Satellite erst ab ca. 30 % Verlust, im Crash halten, beim Satellite zählt maximale Rendite.
- **Reaktion auf Verluste rational:** bei minus 20 % im Monat pausieren und prüfen.
- **Risikotragfähigkeit eingeschränkt:** noch kein Notgroschen, Geld eventuell teilweise in den nächsten 5 Jahren benötigt, bisher nur ETF-Sparplan ohne erlebten Crash.
- **Zeit:** Freigaben mehrmals täglich möglich.

| Regel | Core (70 %) | Satellite (30 %) |
| --- | --- | --- |
| Haltedauer | Monate bis Jahre, Rebalancing quartalsweise | Tage bis ca. 3 Monate je nach Signal, kein Intraday-Handel |
| Positionsgröße | max. 5 % je Aktie | 1 % Risiko pro Trade, max. 10 % je Position |
| Ausstieg | These gebrochen oder fairer Wert erreicht | Stop bei 2 × ATR plus Zeit-Stop, wenn das Signal abgelaufen ist |
| Monatslimit | keins, Marktschwankungen werden ausgehalten | minus 10 %: Bot pausiert, Ursache prüfen |
| Notbremse | Review, wenn der Core 12 Monate lang mehr als 10 Prozentpunkte hinter dem ACWI IMI liegt | minus 20 % vom Höchststand: Satellite stoppt, komplette Überprüfung |
| Freigaben | beim Rebalancing | feste Zeitfenster: morgens mit dem Briefing und abends |

Die Notbremse liegt bewusst unter der gefühlten Schmerzgrenze von 30 %, weil die Toleranz ohne Crash-Erfahrung meist überschätzt wird. Alle Werte sind Startwerte für Paper Trading und werden im Backtest überprüft. Vor echtem Geld: Notgroschen aufbauen, und Geld, das in den nächsten Jahren gebraucht werden könnte, kommt nicht in den Satellite.

### Startkapital 500 € in Euro

Vorläufig festgelegt am 31.10.2026: 500 € Startkapital, gilt schon fürs Paper Trading. Die Prozentregeln bleiben gleich, die Euro-Beträge wachsen mit dem Kapital.

| Größe | Core (70 %) | Satellite (30 %) |
| --- | --- | --- |
| Kapital | 350 € | 150 € |
| Größte Position | 17,50 € je Aktie (5 %) | 15 € je Position (10 %) |
| Risiko pro Trade | kein Stop, lange Haltedauer | 1,50 € (1 %) |
| Monatslimit | keins | 15 € (10 %) |
| Notbremse | Review bei Unterperformance | 30 € (20 % vom Höchststand) |

Folge für die Broker-Wahl: möglichst Bruchteilsaktien und niedrige Mindestgebühren, siehe Broker. Grundregel: eine Order nur, wenn die Gebühr höchstens 1 % des Orderwerts ausmacht. Bei 1 € pro Order kosten Kauf und Verkauf einer 15-€-Position bereits über 13 %.

**Entschieden am 01.11.2026: Satellite im Schattenbetrieb.** Der erste Backtest hat gezeigt, dass der Satellite mit 150 € keinen Trade machen kann: 10 % Position sind 15 €, die Gebührenregel verlangt aber 125 € je Order. Deshalb:

- **Echte Satellite-Trades erst ab 1.250 € Satellite-Kapital,** dann ist eine 10-%-Position 125 € groß.
- **Bis dahin gehen die echten 150 € in den Core-ETF.** Das Depot besteht also anfangs aus 500 € Core.
- **Der Satellite läuft als Schattenportfolio mit virtuellen 1.250 €** nach allen Regeln inklusive Kosten und Steuern und wird getrennt ausgewiesen. So entsteht die Erfolgsbilanz für Go-Live-Kriterium 4, ohne echtes Geld in zu kleinen Positionen zu verbrennen.
- **Ausstiege sind immer erlaubt:** Stops, Zeit-Stops und gebrochene Thesen werden auch dann ausgeführt, wenn die Gebühr über 1 % liegt. Die Gebührenregel gilt nur für Käufe und Aufstockungen.

**Kopplung an den Notgroschen:** Das Kapital im Bot steigt über 500 € nur, wenn der Notgroschen um denselben Betrag mitwächst, bis etwa eine Monatsausgabe erreicht ist. Geld, das im Studium absehbar gebraucht wird, kommt nicht in den Bot. Grundsatz: Es darf nie einen Verkaufszwang geben, nur weil Geld gebraucht wird, während Positionen im Minus liegen.

### Was Risiko im Bot bedeutet

Im Alltag heißt Risiko: Geld verlieren. In der Finanztheorie heißt es: Unsicherheit, wie stark Ergebnisse vom Erwartungswert abweichen, nach oben wie nach unten. Der Bot nutzt beide Sichten, und jede Kennzahl hat eine eigene Aufgabe.

| Kennzahl | Was sie misst | Aufgabe im Bot |
| --- | --- | --- |
| Drawdown | Verlust vom letzten Höchststand, das Risiko im Alltagssinn | Monatslimit und Notbremse |
| Volatilität | Schwankungsbreite der Renditen (Standardabweichung) | Positionsgröße, Stops über ATR |
| Beta | Abhängigkeit vom Gesamtmarkt, laut CAPM das einzige vergütete Risiko | Marktabhängigkeit des Core steuern |
| VaR und CVaR | Verlust, der mit 95 % Wahrscheinlichkeit nicht überschritten wird, und der Durchschnitt der schlimmsten 5 % | Stresstests und Extremrisiko |
| Klumpenrisiko | Konzentration auf einzelne Aktien, Branchen, Länder oder Währungen | Positions-, Sektor- und Länderlimits |
| Modell- und Betriebsrisiko | Überanpassung im Backtest, Programm- oder Datenfehler | Paper Trading, Tests, Notbremse |

Die Antworten aus dem Fragebogen sind in Drawdown-Grenzen übersetzt. Die übrigen Kennzahlen setzt der Bot technisch um.

## Paper Trading wie im echten Handel

Entschieden am 31.10.2026: Der Bot läuft zuerst mehrere Monate im Paper Trading, parallel wird der Notgroschen aufgebaut. Das Paper Trading bildet den echten Handel so genau wie möglich ab, mit allen Regeln aus diesem Doc und allem, was später hinzukommt.

**Realismus-Regeln:**

- **Kapital:** Startkapital und Aufteilung 70/30 wie später im echten Depot, kein Fantasiebetrag.
- **Kosten:** Ordergebühren des gewählten Brokers, Spread, Slippage und Währungskosten bei US-Aktien werden eingerechnet.
- **Steuern:** Abgeltungsteuer auf realisierte Gewinne inklusive Sparer-Pauschbetrag wird simuliert, damit kurzfristiger Handel nicht zu gut aussieht.
- **Abläufe:** Freigaben nur in den festen Zeitfenstern. Verpasste Freigaben gelten als verpasste Trades.
- **Handelbarkeit:** gleiches Aktienuniversum und gleiche Handelsplätze wie beim echten Broker, Ordergrößen passend zur Liquidität.
- **Technik:** Paper- und Live-Konto laufen über dieselbe Broker-Schnittstelle. Der Wechsel ist nur ein Schalter in der Konfiguration.
- **Erweiterungen:** Jedes neue Feature durchläuft denselben Weg: Backtest, dann Paper Trading, erst dann live.

**Go-Live-Kriterien (vorab festgelegt, damit sie später nicht nach Ergebnis angepasst werden):**

1. Mindestens 6 Monate Paper Trading.
2. Notgroschen-Ziel erreicht, zum Start 500 €.
3. Alle Limits eingehalten; eine ausgelöste Notbremse ist analysiert und die Ursache behoben.
4. Satellite nach Kosten und Steuern mindestens gleichauf mit dem Core, sonst wird sein Anteil reduziert.
5. Ergebnisse weichen nicht stark vom Backtest ab. Große Abweichungen deuten auf ein überangepasstes Modell hin.
6. Stufenweiser Start: zuerst etwa ein Viertel des geplanten Kapitals, der Rest nach weiteren 3 Monaten ohne Auffälligkeiten.

6 Monate decken meist nur eine Marktphase ab. Deshalb zählen zusätzlich die Backtests und Stresstests über 2008, 2020 und 2022.

## Anlageuniversum, Broker und Daten

### Anlageuniversum: weltweit und Multi-Asset

Entschieden am 31.10.2026: weltweit gestreut über Aktien, Anleihen, Rohstoffe und Währungen. Umgesetzt wird das zunächst über Einzelaktien, ETFs und ETCs ohne Hebel.

- **Aktien:** Einzelwerte weltweit und Aktien-ETFs. Als EU-Privatanleger sind meist nur UCITS-ETFs handelbar.
- **Anleihen:** über Anleihe-ETFs, Signale aus Zinsumfeld, Laufzeit und Kreditrisiko.
- **Rohstoffe:** über ETCs, z.B. Gold, Signale vor allem aus Trend und Makro.
- **Währungen:** zunächst indirekt über Anlagen in Fremdwährung. Das Währungsrisiko wird gemessen und begrenzt.
- **Vorerst nicht:** Futures, CFDs und Devisenhandel auf Margin. Sie brauchen ein Margin-Konto, der Hebel widerspricht dem Risikoprofil, und die Kontraktgrößen passen nicht zu 500 €.
- **Architektur:** anlageklassen-neutral, damit Futures oder Devisen später als Modul andocken können. Die Benchmark wird zu einem Mischindex passend zur tatsächlichen Aufteilung.

### Broker

Kein Broker erfüllt alle Kriterien perfekt. Empfehlung: Interactive Brokers für Paper und Live, mit drei Anpassungen.

| Broker | Verfügbarkeit | Paper Trading über API | Kosten | Haken |
| --- | --- | --- | --- | --- |
| [Interactive Brokers](https://rankia.de/interactive-brokers-gebuehren-erfahrungen-kosten) | in Deutschland verfügbar | kostenlos und unbegrenzt, Marktdaten 10 bis 15 Minuten verzögert | EU-Aktien und ETFs ab 0,05 %, mindestens 1,25 €; US-Aktien mindestens 1 USD | [Bruchteilsaktien nicht über die API](https://brokerchooser.com/de/broker-reviews/interactive-brokers-review/fractional-share-trading), nicht steuereinfach, Margin-Konto erst ab 2.000 USD |
| [Alpaca](https://alpaca.markets/learn/account-eligibility/) | Live-Konto für Nicht-US-Bürger laut Alpaca bisher nur per Einladung | kostenlos | provisionsfrei für US-Aktien | Einzahlung nur in USD, [Europa-Angebot vor allem für Partner-Plattformen](https://www.financemagnates.com/forex/alpaca-opens-access-to-german-stocks-as-xetra-goes-live-for-broker-partners/) |
| [Saxo](https://developer.saxo/openapi/learn/environments) | in Deutschland verfügbar | Simulation mit virtuellen 100.000 USD | noch zu prüfen | Live-Zugang zur API muss beim Saxo-Team beantragt werden |

**Anpassungen für Interactive Brokers:**

1. **Mindestordergröße:** Ein Kauf nur, wenn die Gebühr höchstens 1 % ausmacht. Bei 1,25 € Mindestgebühr heißt das ab 125 € Orderwert. Mit 500 € sind das wenige, größere Positionen. Ausstiege sind immer erlaubt; der Satellite läuft bis 1.250 € als Schattenportfolio (siehe Startkapital).
2. **Core über ETFs, Einzelaktien im Schattenportfolio:** Bis das Kapital wächst, bildet der Core die Streuung über breite ETFs ab. Die Fundamental-Engine führt parallel ein virtuelles Einzelaktien-Portfolio, das wie echt bewertet wird. Die 5-%-Grenze gilt für Einzelaktien, nicht für breite ETFs.
3. **Steuern:** Interactive Brokers führt keine Abgeltungsteuer ab. Der Bot erstellt aus dem Journal die Zahlen für die Anlage KAP.

Dank Broker-Adapter ist ein späterer Wechsel, z.B. zu Alpaca, nur ein Modul.

### Datenquellen

Start kostenlos. Kostenpflichtige Daten erst, wenn die Go-Live-Kriterien erfüllt sind und die Kosten unter etwa 1 % des Kapitals pro Jahr liegen.

| Bereich | Quelle | Was du tun musst |
| --- | --- | --- |
| Kurse und Indikatoren | Broker-API, yfinance für die Historie | nichts; yfinance ist inoffiziell und ohne Garantie |
| Fundamentaldaten USA | SEC EDGAR, offiziell und kostenlos | nichts |
| Fundamentaldaten weltweit | yfinance, Geschäftsberichte | nichts; Schwachstelle, später eventuell kostenpflichtig |
| Makrodaten | FRED, EZB-Datenportal, Eurostat | kostenlosen FRED-API-Schlüssel anlegen |
| 13F-Filings und Form 4 | SEC EDGAR | nichts |
| Directors' Dealings Deutschland | BaFin-Datenbank | nichts |
| News | Tagesbriefing, RSS-Feeds | Briefing-Anhang, siehe News-Engine |

Der Code holt alle Daten selbst. Du legst nur Konten und Schlüssel an und hinterlegst sie lokal in der .env-Datei.

## Fundamental-Engine

Kern des Bots: Bewertung und Bilanzqualität aus dem Studium entscheiden, welche Aktien überhaupt infrage kommen.

- **Bewertung:** DCF und Multiples (KGV, EV/EBITDA) im Peer-Vergleich. Der Abstand zwischen innerem Wert und Kurs ist das Signal (Margin of Safety).
- **Bilanz-Scores:** Piotroski F-Score für Qualität, Altman Z-Score für Insolvenzrisiko, Beneish M-Score für Bilanzmanipulation. Ideal als Ausschlussfilter.
- **Faktormodelle:** CAPM, Fama-French (Value, Size, Profitability, Investment) plus Momentum nach Carhart. Zeigt, ob der Bot echtes Alpha erzeugt oder nur Faktorprämien einsammelt.
- **Portfolio:** Markowitz oder Risk Parity für die Gewichtung, Sharpe Ratio und Beta als Steuerungsgrößen.

### Wissen aus dem Studium

- **Unterlagen:** Vorlesungsskripte, Formelsammlungen und Übungsblätter bleiben als PDF im Ordner `Wissen` auf dem Rechner. Ins Repository kommen nur die eigenen Zusammenfassungen (`wissen/`) und die Tests aus den Musterlösungen.
- **Übersetzung:** Claude setzt jedes Modell als eigene Funktion um, mit Formel, Annahmen und Quelle im Kommentar.
- **Übungen als Tests:** Eine Übungsaufgabe mit Musterlösung wird zum automatischen Test. Der Code muss genau das Ergebnis der Musterlösung liefern.
- **Methodenhandbuch:** Zu jedem Modell ein kurzer Eintrag, was es misst und wann es versagt. Hilft zugleich bei der Klausurvorbereitung.

**Stand 31.10.2026: Grundlagenwissen eingepflegt.** Alle 75 PDFs aus dem Ordner `Wissen` (Accounting, Corporate Finance, Finanzen und Investment, Mikroökonomik, Ökonometrie) sind in zehn Wissensdateien verdichtet, jeweils mit Kernkonzepten, Formeln und Bezug zum Bot. Ablage: `Wissen/Grundlagenwissen` auf dem Rechner (Markdown plus Gesamt-PDF, 38 Seiten) und als Projektdokumente im TradingBot-Projekt.

| Datei | Wichtig für |
| --- | --- |
| 01 Bewertung und Corporate Finance | Fundamental-Engine, Risk-Manager |
| 02 Kapitalmarkttheorie, Portfolio und Anleihen | Portfolio-Konstruktion, Anleiheteil |
| 03 Derivate | Signale, spätere Absicherung |
| 04 Finanzielles Risikomanagement | Risk-Manager |
| 05 Asset Management und Hedgefonds | Technik-Engine, Strategie-Bibliothek, Smart Money |
| 06 Behavioral Finance | Begründung der Signale, Journal |
| 07 Banken und Finanzintermediation | Makro- und Stresssignale |
| 08 Rechnungslegung und Kostenrechnung | Bilanzqualität |
| 09 Ökonometrie | Backtests, Faktorregressionen, Ereignisstudien |
| 10 Mikroökonomik | Branchenanalyse, News-Einordnung |

Die CLAUDE.md des Repositorys verweist später auf diesen Ordner. Neue Folien kommen in den passenden Unterordner und werden dann ergänzt.

**Stand 31.10.2026: Übungen als Tests.** Aus den 8 Übungsblättern mit Musterlösung (Bonds 1 und 2, Futures und Forwards 1 und 2, Optionen, BFIN-Übungssammlung, OFIN-Übung, Accounting 1) sind 641 automatische Testfälle entstanden; alle bestehen gegen die Referenzformeln. Ablage: `Wissen/Grundlagenwissen/11_Testkatalog_Uebungen.md` und Ordner `Tests` (Testdaten, Referenzformeln, Testlauf mit pytest). Accounting 1 (264 Tests, Kosten- und Erlösrechnung): Die Lösung stammt aus dem WiSe 2026/27, die Aufgaben aus dem SoSe 2026. 28 von 35 Aufgaben passen und sind erfasst; für 7 SoSe-Aufgaben fehlt eine passende Lösung (2.1, 3.4, 4.3, 5.5, 6.1, 7.2, 9.1).

## News-Engine

Das Tagesbriefing wird zu strukturierten Daten und liefert Kontext und Risikofilter, keine Hochfrequenz-Signale.

- **Briefing als Input:** Claude extrahiert pro Nachricht Ticker, Ereignistyp (Earnings, M&A, Zinsentscheid, Regulierung), Richtung und Relevanz.
- **Makro-Kalender:** Vor EZB- und Fed-Sitzungen, Inflationsdaten und Earnings keine neuen oder nur kleinere Positionen.
- **Earnings Surprise und PEAD:** Post-Earnings-Announcement-Drift ist eine gut belegte Anomalie und verbindet News mit Fundamentaldaten.
- **Regime-Erkennung:** Zinsumfeld, VIX und Konjunkturphase verschieben die Gewichte, z.B. in Krisen mehr Gewicht auf Qualität.
- **Grenze:** Beim Tempo gewinnt der Hochfrequenzhandel. News dienen hier als Kontext, nicht als Kaufauslöser.

### Schnittstelle zum Tagesbriefing

Die Briefing-Aufgaben in Claude und der Bot sehen sich nicht direkt. Die Brücke ist eine Datei mit festem Aufbau.

- **Zwei Teile:** Das Briefing bleibt Lesetext für dich; eine Export-Aufgabe erzeugt daraus täglich einen maschinenlesbaren Anhang im JSON-Format.
- **Felder pro Nachricht:** Datum, betroffene Anlage oder Region, Ereignistyp, Richtung (positiv, negativ, neutral), Stärke 1 bis 3, erwartete Wirkungsdauer, Quelle.
- **Makro-Kalender:** wichtige Termine der nächsten Tage mit erwarteter Bedeutung.
- **Übergabe:** Die geplante Aufgabe „Briefing-Export Bot-Anhang“ legt den Anhang täglich um 22:40 als JJJJ-MM-TT.json in Google Drive unter TradingBot/Briefing-Archiv ab. Sobald das Repository steht, liest der Bot von dort.
- **Was du tust:** im Alltag nichts. Beim Aufbau des Repositorys den Zugriff auf das Archiv bestätigen.

### Anleitung: Tagesbriefing einbinden

Das Tagesbriefing läuft als zwei geplante Aufgaben („Newsletter-Briefing“ Mo–Fr um 7, 12, 19 und 22 Uhr, „Briefing Wochenende“ um 12 und 22 Uhr) und speichert jeden Lauf als Block in der Briefing-Seite. Diese Aufgaben lesen keine Projektanweisungen, deshalb entsteht der Anhang in einer eigenen Export-Aufgabe.

**Stufe 1: läuft seit 31.10.2026**

1. **Export-Aufgabe:** „Briefing-Export Bot-Anhang“ startet täglich um 22:40, liest die Briefing-Blöcke des Tages und speichert den Anhang als `JJJJ-MM-TT.json` in Google Drive unter `TradingBot/Briefing-Archiv`. Verpasste Tage holt sie bis zu 3 Tage rückwirkend nach.
2. **Prüfen:** Gelegentlich eine Datei öffnen und mit dem Briefing vergleichen. Fehler fließen als Korrektur in den Prompt der Export-Aufgabe.
3. **Archiv wächst:** Bis zum Start des Bots entsteht so die Testgrundlage für die News-Engine.

**Stufe 2: sobald das Repository steht**

4. **Ordner anlegen:** Claude legt im Repository den Ordner `daten/briefings/` an, dazu ein Prüfprogramm, das jede Datei gegen das Schema testet.
5. **Archiv übernehmen:** Die Dateien aus dem Briefing-Archiv in diesen Ordner holen, einmalig und danach täglich (Kopie oder Google-Drive-Zugriff).
6. **Anschluss an den Bot:** Die News-Engine liest die Datei vor deinem morgendlichen Freigabefenster ein.

**Qualitätsregeln:**

- **Zeitstempel:** Der Bot nutzt eine Nachricht erst ab ihrem Erstellungszeitpunkt. Das verhindert Look-ahead-Bias im Backtest.
- **Keine Empfehlungen:** Der Anhang beschreibt nur Ereignisse. Kauf- und Verkaufsentscheidungen trifft der Bot mit seinen Regeln.
- **Ticker nur, wenn eindeutig:** Im Zweifel bleibt das Feld leer.

**Schema und Regeln des Bot-Anhangs (Version 1.1, so in der Export-Aufgabe hinterlegt):**

```
{
  "schema_version": "1.1",
  "datum": "JJJJ-MM-TT",
  "erstellt_um": "Zeitpunkt mit Zeitzone, z.B. 2026-11-02T22:40:12+01:00",
  "bloecke": ["IDs der verwendeten Briefing-Blöcke, z.B. 2026-11-02_0700"],
  "nachrichten": [
    {
      "titel": "kurze Beschreibung, höchstens 15 Wörter",
      "anlage": "betroffene Anlage oder Anlageklasse, z.B. Aktie Nvidia, Halbleiter, DAX, Staatsanleihen USA, Gold, EUR/USD",
      "ticker": "Kürzel oder null",
      "region": "USA | Eurozone | Deutschland | UK | China | Japan | Schwellenländer | Welt",
      "ereignistyp": "Earnings | M&A | Zinsentscheid | Konjunkturdaten | Regulierung | Politik | Rohstoffe | Sonstiges",
      "richtung": "positiv | negativ | neutral",
      "staerke": 1,
      "wirkungsdauer": "Tage | Wochen | Monate",
      "quelle": "URL des Artikels oder null",
      "quellen": ["Newsletter-Namen wie im Briefing"],
      "block_id": "Briefing-Block der Nachricht",
      "item_key": "Position im Block, z.B. s0-i2",
      "story_id": "verfolgte Story oder null"
    }
  ],
  "makro_kalender": [
    {"datum": "JJJJ-MM-TT", "ereignis": "Beschreibung", "region": "Region", "bedeutung": 1}
  ]
}

Regeln: Nur marktrelevante Nachrichten; Wiederholungen eines Tages werden zusammengefasst. Richtung aus Sicht der betroffenen Anlage. Stärke und Bedeutung von 1 (gering) bis 3 (hoch). Ticker nur, wenn eindeutig, sonst null. Quelle ist die erste Artikel-URL aus dem Briefing; Meldungen ohne Link haben quelle null und nennen die Newsletter in quellen. Keine Kursprognosen und keine Kauf- oder Verkaufsempfehlungen. Der Makro-Kalender enthält datierte Termine der 7 Folgetage, nur mit einem Datum aus einer Quelle.
```

## Smart-Money-Engine

Positionen großer Investoren liefern Ideen und Bestätigung, wegen der Meldeverzögerung aber kein Timing.

- **13F-Filings (SEC):** Große US-Fonds melden quartalsweise, bis zu 45 Tage nach Quartalsende. Ausgewertet werden neue Positionen und starke Aufstockungen.
- **Konsens-Score:** Wie viele Top-Investoren steigen gleichzeitig neu in dieselbe Aktie ein?
- **Insider-Trades:** Form 4 in den USA, Directors' Dealings in Europa. Käufe sind aussagekräftiger als Verkäufe.
- **Crowding-Warnung:** Halten zu viele Fonds dieselbe Aktie, steigt das Risiko eines gemeinsamen Ausverkaufs.

## Technik-Engine

Technische Indikatoren wie bei TradingView werden selbst in Python berechnet und fließen als vierte Engine in den Score. Fundamentale Kennzahlen aus TradingView gehören in die Fundamental-Engine.

- **Trend:** gleitende Durchschnitte, z.B. 50 und 200 Tage, und Zeitreihen-Momentum.
- **Momentum:** Rendite der letzten 3 bis 12 Monate, RSI, MACD.
- **Volatilität:** ATR und Bollinger-Bänder, sie steuern Positionsgröße und Stops.
- **Volumen:** On-Balance-Volume und Volumen-Ausreißer als Bestätigung.
- **Rolle:** Hauptsignal im Satellite, Timing-Filter im Core, z.B. keine Neukäufe im starken Abwärtstrend.
- **Disziplin:** wenige Indikatoren statt vieler. Jeder muss im Backtest einzeln Mehrwert zeigen, sonst droht Überanpassung.

**Warum selbst berechnen statt TradingView anbinden:**

- Die Indikatorformeln sind offen und in Python schnell umgesetzt: kostenlos, backtestbar und nachvollziehbar.
- [TradingView-Webhooks gibt es nur in Bezahlplänen und mit Zwei-Faktor-Anmeldung](https://crosstrade.io/blog/tradingview-plan-for-webhook-alerts). Die Signale kämen dann von TradingView statt aus dem eigenen Score.
- Fürs Auge: [TradingViews Bibliothek Lightweight Charts ist Open Source unter Apache 2.0](https://in.tradingview.com/free-charting-libraries) und zeigt im eigenen Dashboard Kerzencharts mit den Signalen des Bots. Bedingung ist ein Hinweis auf TradingView.
- TradingView bleibt dein manuelles Cockpit zum Gegenprüfen. Eine Community-Strategie mit offenem Quellcode kann als Beschreibung oder Pine-Script übergeben und in Python nachgebaut werden.

## Strategie-Bibliothek

Jede Strategie wird ein eigenes Modul mit Idee, Datenbedarf, Haltedauer und Backtest. Das Scoring gewichtet sie nach Backtest-Ergebnis. Neue Strategien, z.B. aus TradingView oder Vorlesungen, kommen zuerst hierher.

| Strategie | Idee | Engine | Teil | Evidenz |
| --- | --- | --- | --- | --- |
| Value | günstig bewertete Aktien kaufen | Fundamental | Core | langfristig belegt, mit langen Schwächephasen |
| Quality | profitable, solide finanzierte Unternehmen | Fundamental | Core | gut belegt |
| Low Volatility | schwankungsarme Aktien bevorzugen | Technik | Core | belegte Anomalie |
| Momentum | Gewinner der letzten 3 bis 12 Monate kaufen | Technik | beide | gut belegt, Crash-Risiko bei Trendwenden |
| Trendfolge | Anlageklassen im Aufwärtstrend halten | Technik | Satellite | über viele Anlageklassen belegt |
| Event-Driven | Reaktion auf Gewinnüberraschungen (PEAD) | News | Satellite | belegt, über die Jahre schwächer |
| Kurzfrist-Umkehr | kurzfristige Übertreibungen handeln | Technik | Satellite | belegt, aber kostenintensiv |
| Carry | höher verzinste Anlagen halten | News | Satellite | belegt, Crash-Risiko |
| Risk Parity | Kapital nach Risiko statt Betrag auf Anlageklassen verteilen | Portfolio | Core | Allokationsmethode, kein Renditesignal |
| Smart Money folgen | 13F-Konsens und Insider-Käufe | Smart Money | Core | Insider-Käufe belegt, 13F-Nachbau gemischt |

### TradingView-Strategien

Die 23 eingebauten Strategien sind fast alle Varianten von vier Grundideen. Ihre Standardparameter sind Beispiele, keine getesteten Einstellungen.

| Familie | TradingView-Strategien | Idee | Einschätzung | Im Bot |
| --- | --- | --- | --- | --- |
| Trendfolge und Momentum | Momentum, MACD, Moving Average Crossover, Two Moving Averages Crossover, Supertrend, Parabolic SAR | mit dem Trend gehen, aussteigen, wenn er kippt | am besten belegt, vor allem über mehrere Anlageklassen; verliert in Seitwärtsphasen | Two MA Crossover und Momentum als Trendfilter für Core und Satellite |
| Ausbruch | Price Channel, Channel Breakout, Keltner Channels, Volatility Expansion Close, Rob Booker ADX Breakout, Pivot Reversal | kaufen, wenn der Kurs eine Spanne nach oben verlässt | Verwandter der Trendfolge, viele Fehlausbrüche | Price Channel mit ATR-Stop im Satellite |
| Mean Reversion | RSI, Stochastic Slow, Bollinger Bands, Bollinger Bands Directed, Pivot Extension | kaufen, wenn der Kurs kurzfristig übertrieben gefallen ist | kurzfristig belegt, aber kostenintensiv und gefährlich im starken Abwärtstrend | RSI oder Bollinger im Satellite, nur wenn der langfristige Trend steigt |
| Kerzenmuster | Inside Bar, Outside Bar, Bar Up/Down, Consecutive Up/Down | Muster einzelner Kerzen als Signal | schwach belegt, sehr viele Trades | vorerst nicht |
| Sonderfälle | Technical Ratings, Greedy | Gesamturteil aus vielen Indikatoren; Kurslücken mit bis zu 100 Nachkäufen | Ratings ähnelt unserem Score; Greedy widerspricht den Risikoregeln | Ratings als Gegenprobe, Greedy nicht |

**Regeln für die Übernahme:**

1. **Nur Long:** Leerverkäufe brauchen ein Margin-Konto. Short-Signale bedeuten im Bot „nicht investiert“.
2. **Tages- und Wochenkerzen:** wenige Trades, damit die Mindestgebühren nicht die Rendite fressen.
3. **Eine Strategie pro Familie:** Regeln und Parameter werden vor dem Backtest festgelegt. 23 Strategien mit vielen Parametern durchzuprobieren, findet fast immer zufällige Gewinner.
4. **ADX als Regime-Schalter:** Bei starkem Trend bekommen Trend- und Ausbruchsstrategien mehr Gewicht, bei schwachem Trend Mean Reversion.
5. **Gegenprobe mit TradingView:** Dieselbe Regel muss im eigenen Backtest und im Strategy Tester von TradingView ähnliche Ergebnisse liefern. Und der Bot-Score muss die Technical Ratings schlagen, sonst lohnt sich der Aufwand nicht.

**Startauswahl und Parameter (festgelegt am 31.10.2026, vor jedem Backtest):** Klassische Werte aus der Literatur, alle auf Tageskerzen und nur Long.

| Strategie | Familie | Regel | Parameter |
| --- | --- | --- | --- |
| Two MA Crossover | Trendfolge | investiert, solange der schnelle über dem langsamen Durchschnitt liegt | 50 und 200 Tage |
| Momentum | Trendfolge | Rendite der letzten 12 Monate ohne den letzten Monat, monatlich neu bewertet | 12 minus 1 Monat |
| Price Channel | Ausbruch | Einstieg beim Hoch der letzten 55 Tage, Ausstieg beim Tief der letzten 20 Tage | 55 und 20 Tage, Stop bei 2 × ATR über 20 Tage |
| RSI | Mean Reversion | Einstieg bei stark überverkauftem RSI, nur über dem 200-Tage-Durchschnitt; Ausstieg, wenn der Kurs über dem 5-Tage-Durchschnitt schließt | RSI über 2 Tage unter 10 |
| ADX | Regime-Schalter | Trend und Ausbruch bekommen mehr Gewicht bei starkem Trend, Mean Reversion bei schwachem | 14 Tage; über 25 starker Trend, unter 20 schwacher Trend |

Bollinger-Bänder (20 Tage, 2 Standardabweichungen) bleiben die Alternative zum RSI, falls der RSI im Backtest scheitert. Parameter werden nicht nachträglich optimiert. Eine Änderung braucht eine neue Begründung und einen neuen Test auf noch nicht genutzten Daten.

## Qualität und Risiko

Sauberes Testen und harte Risikoregeln entscheiden mehr über das Ergebnis als jedes einzelne Signal.

- **Backtesting:** Walk-forward-Tests, kein Look-ahead-Bias (Bilanzdaten erst ab Veröffentlichungsdatum), kein Survivorship Bias, Transaktionskosten eingerechnet.
- **Benchmark:** Der Core wird am MSCI ACWI IMI und den Vergleichsindizes gemessen, der Satellite zusätzlich am Core (siehe Anlagehorizont).
- **Risk-Manager mit Vetorecht:** maximale Positionsgröße, Sektorlimits, maximaler Drawdown, Sizing z.B. mit halbem Kelly.
- **Paper Trading:** mehrere Monate ohne echtes Geld, bevor echtes Kapital fließt.
- **Erklärbarkeit:** Zu jedem Trade eine kurze Investment-These, inklusive dem, was sie widerlegen würde. Ergibt automatisch ein Trading-Journal.
- **Human in the Loop:** Anfangs schlägt der Bot nur vor, die Freigabe erfolgt manuell. Research-Copilot statt Autopilot.

## Weitere Module

- **ESG-Score:** als Ausschlussfilter oder eigener Faktor im Scoring.
- **Stresstests:** Wie hätte das Portfolio 2008, 2020 und 2022 abgeschnitten?
- **Wochenreport:** Performance gegen Benchmark, offene Positionen, Check der Investment-Thesen.
- **Dashboard:** Scores, Positionen und Risiko auf einen Blick.

## Priorisierung

Vorschlag: zuerst Datenbasis, Backtest und Fundamental-Engine, danach Risiko, News und Smart Money. Priorität und Status sind per Dropdown änderbar.

| Feature | Engine | Phase | Priorität | Status |
| --- | --- | --- | --- | --- |
| Datenbasis (Kurse, Bilanzdaten) | Basis | 1 | Hoch | Idee |
| Backtest-Framework | Qualität | 1 | Hoch | Idee |
| Bewertung: DCF und Multiples | Fundamental | 1 | Hoch | Idee |
| Bilanz-Scores (Piotroski, Altman, Beneish) | Fundamental | 1 | Hoch | Idee |
| Strategie-Bibliothek | Basis | 1 | Mittel | Idee |
| Risk-Manager mit Vetorecht | Qualität | 2 | Hoch | Idee |
| Paper Trading | Ausführung | 2 | Hoch | Idee |
| Faktormodelle (Fama-French, Momentum) | Fundamental | 2 | Mittel | Idee |
| Investment-These pro Trade | Qualität | 2 | Mittel | Idee |
| Technik-Engine (Trend, Momentum, Volatilität) | Technik | 2 | Hoch | Idee |
| Broker-Adapter Interactive Brokers | Ausführung | 2 | Hoch | Idee |
| Schattenportfolio Einzelaktien | Fundamental | 2 | Mittel | Idee |
| Briefing-Auswertung | News | 3 | Mittel | Idee |
| Makro-Kalender | News | 3 | Mittel | Idee |
| Earnings Surprise und PEAD | News | 3 | Mittel | Idee |
| Briefing-Anhang (JSON) | News | 3 | Mittel | In Arbeit |
| 13F-Tracking und Konsens-Score | Smart Money | 4 | Mittel | Idee |
| Insider-Trades | Smart Money | 4 | Mittel | Idee |
| Regime-Erkennung | Scoring | 5 | Niedrig | Idee |
| ESG-Score | Weitere | 5 | Niedrig | Idee |
| Stresstests | Weitere | 5 | Niedrig | Idee |
| Dashboard und Wochenreport | Weitere | 5 | Niedrig | Idee |
| Kerzencharts im Dashboard (Lightweight Charts) | Weitere | 5 | Niedrig | Idee |

## Umsetzung mit Claude Code

Der Bot entsteht Modul für Modul. Eine Phase gilt erst als fertig, wenn ihr Backtest sauber gegen die Benchmark läuft.

1. **Setup:** Python, Git und GitHub-Account, Claude Code. Repository mit Grundstruktur und einer CLAUDE.md anlegen, die Ziele, Regeln und Architektur festhält.
2. **Phase 1, Fundament:** Datenbasis, Backtest-Framework, Fundamental-Engine.
3. **Phase 2, Risiko:** Risk-Manager, Paper-Trading-Anbindung, Investment-These pro Trade, Technik-Engine.
4. **Phase 3, News:** Briefing-Auswertung, Makro-Kalender, PEAD.
5. **Phase 4, Smart Money:** 13F-Tracking, Konsens-Score, Insider-Trades.
6. **Phase 5, Ausbau:** Regime-Erkennung, ESG, Stresstests, Dashboard.

**Meine Aufgaben:** Regeln festlegen (Anlagehorizont, Aktienuniversum, Risikolimits), Accounts und API-Schlüssel anlegen, Fachlogik prüfen, Ergebnisse bewerten und entscheiden.

**Claudes Aufgaben:** Architektur, Code und Tests schreiben, Backtests ausführen und auswerten, Code erklären, CLAUDE.md und Doku aktuell halten.

**Ablauf pro Feature:** Idee hier im Doc, Priorität setzen, in Claude Code erst planen lassen, dann umsetzen mit Tests, Backtest vorher gegen nachher vergleichen, committen.

**So bleibt der Bot erweiterbar:**

1. Einheitliche Schnittstelle für alle Engines: Datum und Aktienliste rein, Score pro Aktie raus. Eine neue Idee ist ein neues Modul, das andockt.
2. Gewichte und Parameter stehen in einer Konfigurationsdatei statt im Code. Core und Satellite bekommen je eigene Einstellungen.
3. Die CLAUDE.md ist das Projektgedächtnis mit Zielen, Regeln und Architektur. Claude Code liest sie zu Beginn jeder Sitzung.
4. Ein Feature pro Sitzung: erst planen, dann umsetzen. Nur was im Backtest besteht, kommt rein.
5. Das Tagesbriefing landet täglich als Datei im Projektordner, die News-Engine liest es automatisch ein.
6. API-Schlüssel liegen nur lokal in einer .env-Datei, nie im Code oder auf GitHub.

## Ideen-Backlog und offene Fragen

Neue Ideen landen zuerst hier und wandern bei Bedarf in die Priorisierungstabelle.

- [x] Anlagehorizont: Großteil langfristig (Monate bis Jahre), kleinerer Teil kurzfristig, siehe Core und Satellite
- [x] Aufteilung Core zu Satellite: 70/30
- [x] Benchmark Core: MSCI ACWI IMI plus Vergleichsindizes statt nur MSCI World
- [x] Haltedauer und Verlustlimits festgelegt, siehe Risikoprofil und Limits
- [x] Testphase: mehrere Monate Paper Trading wie im echten Handel
- [x] Startkapital: 500 € (vorläufig, anpassbar), gilt schon fürs Paper Trading
- [x] Satellite-Schattenbetrieb bis 1.250 € Satellite-Kapital, Ausstiege immer erlaubt (01.11.2026)
- [x] Tresor: Daten ab 01.01.2025 gesperrt, einmal pro Phase öffnen, Paper Trading als zweiter Tresor (01.11.2026)
- [x] Go-Live-Kriterien bestätigen
- [x] Anlageuniversum: weltweit, Multi-Asset über Aktien, ETFs und ETCs ohne Hebel
- [x] Datenquellen: kostenlos starten, siehe Datenquellen
- [x] Strategien aus TradingView gesichtet, siehe TradingView-Strategien
- [x] Startauswahl und Parameter der Technik-Strategien festgelegt: Two MA Crossover, Momentum, Price Channel, RSI, ADX als Regime-Schalter
- [x] Notgroschen während der Paper-Trading-Phase aufbauen: erstes Ziel 500 € (vorläufig), Vorschlag fürs Studium rund 1.500 € (eine Monatsausgabe), 3 bis 6 Monatsausgaben erst mit festem Einkommen
- [x] Broker: Interactive Brokers bestätigt, Live-Konto und separates Paper-Trading-Konto eröffnet (01.11.2026)
- [ ] Entwicklungsumgebung: Python, Git, privates GitHub-Repository und Claude Code einrichten (Setup vor Phase 1)
- [ ] IBKR für den Bot vorbereiten (vor Phase 2): IB Gateway installieren, API für das Paper-Konto freischalten (Port 4002, anfangs Read-Only, nur 127.0.0.1), Marktdaten-Freigabe fürs Paper-Konto prüfen
- [x] Kostenlosen FRED-API-Schlüssel anlegen
- [x] Briefing-Anhang (JSON) bestätigen: Export-Aufgabe läuft täglich um 22:40, Archiv in Google Drive (TradingBot/Briefing-Archiv)
- [ ] Briefing-Archiv ans Repository anbinden (Stufe 2, beim Aufbau des Repositorys)
- [ ] Mischbenchmark für Multi-Asset festlegen, passend zur tatsächlichen Aufteilung
- [x] Vorlesungsunterlagen eingepflegt (Grundlagenwissen, 10 Dateien); Übungen mit Musterlösung als 641 automatische Tests erfasst, davon 264 aus Accounting 1 (11 Testkatalog)
