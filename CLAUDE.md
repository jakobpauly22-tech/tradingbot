# CLAUDE.md – Trading-Bot

Diese Datei ist das Projektgedächtnis. Lies sie zu Beginn jeder Sitzung. Antworte Jakob auf Deutsch.

## Worum es geht

Regelbasierter Trading-Bot für ein kleines Privatdepot (Start 500 €): Core/Satellite-Portfolio, vier Signal-Engines, ein Risk-Manager mit Vetorecht und ein Journal. Reihenfolge immer: Backtest, dann Paper Trading bei Interactive Brokers, erst nach den Go-Live-Kriterien echtes Geld. Jakob studiert Finance & Accounting; er legt die Regeln fest, prüft die Fachlogik und entscheidet. Claude schreibt Architektur, Code, Tests und Backtests und erklärt Entscheidungen kurz.

## Maßgebliche Dateien

| Datei | Inhalt |
| --- | --- |
| `docs/ROADMAP.md` | Alle Entscheidungen, Limits, Strategien, Prioritäten und Phasen (Kopie der Roadmap im Claude-Doc). |
| `wissen/00_Uebersicht.md` | Einstieg ins Grundlagenwissen aus dem Studium; vor dem Bau eines Moduls die passende Datei lesen (z.B. `01` Bewertung, `02` Portfolio/Anleihen, `04` Risikomanagement, `08` Kostenrechnung, `09` Ökonometrie). |
| `tests/musterloesungen/` | 641 Tests aus Übungsblättern mit Musterlösung; `referenz.py` enthält die Referenzformeln. |
| `docs/BOT_ANHANG.md` | Schema des täglichen Briefing-Anhangs für die News-Engine. |
| `docs/DATENQUALITAET.md` | Regeln und Abnahmekriterien der Datenbasis (Universum, Kursreihen, Kursabdeckung, Fehlerschwelle, Gegenprobe des Index-Nachbaus). Bei Verfehlung Ursachen suchen und mit Jakob besprechen, nicht nachjustieren. |

Bei Widersprüchen gilt die neueste Entscheidung von Jakob. Weicht der Code von der Roadmap ab, Jakob fragen statt still anpassen.

## Feste Regeln (nur mit Jakobs Zustimmung ändern)

| Regel | Core (70 %) | Satellite (30 %) |
| --- | --- | --- |
| Haltedauer | Monate bis Jahre, Rebalancing quartalsweise | Tage bis ca. 3 Monate, kein Intraday |
| Positionsgröße | max. 5 % je Einzelaktie (breite ETFs ausgenommen) | 1 % Risiko pro Trade, max. 25 % je ETF-Position, max. 10 % je Einzelaktie (02.11.2026) |
| Ausstieg | These gebrochen oder fairer Wert erreicht | Stop 2 × ATR(20) plus Zeit-Stop |
| Monatslimit | keins | −10 %: Bot pausiert, Ursache prüfen |
| Notbremse | Review, wenn 12 Monate > 10 Prozentpunkte hinter MSCI ACWI IMI | −20 % vom Höchststand: Satellite stoppt |
| Freigaben | beim Rebalancing | feste Fenster morgens und abends |

- **Nur long, ohne Hebel.** Keine Leerverkäufe, Futures, CFDs, Optionen oder Margin. Short-Signale bedeuten „nicht investiert“.
- **Währungstausch (02.11.2026):** Fremdwährungskasse wird gehalten, getauscht wird nur der Netto-Saldo am Ausführungstag und bei Ein- und Auszahlungen, nicht je Order. Offener Steuerpunkt: § 23 EStG beim Rücktausch.
- **Kosten:** Käufe und Aufstockungen nur, wenn die Gebühr höchstens 1 % des Orderwerts ausmacht (IBKR mindestens 1,25 € je Order, also ab 125 € Orderwert). Ausstiege (Stops, Zeit-Stops, These gebrochen) sind immer erlaubt, auch bei Gebühr über 1 % (Entscheidung 01.11.2026). Bruchteilsaktien gibt es über die IBKR-API nicht.
- **Kapital:** 500 €, Aufteilung 70/30, Prozentregeln skalieren mit. Bis das Kapital wächst, bildet der Core die Streuung über breite ETFs ab; die Fundamental-Engine führt parallel ein bewertetes Schattenportfolio aus Einzelaktien.
- **Satellite-Schattenbetrieb (Entscheidung 01.11.2026):** Echte Satellite-Trades erst ab 1.250 € Satellite-Kapital (10 % Position = 125 € Mindestorder). Bis dahin gehen die echten 150 € in den Core-ETF, und der Satellite läuft als Schattenportfolio mit virtuellen 1.250 € nach allen Regeln inklusive Kosten und Steuern, getrennt ausgewiesen (`config/backtest.yaml`, `kapital`).
- **Human in the loop:** Der Bot schlägt vor, Jakob gibt frei. Kein automatisches Senden von Orders ohne Freigabe.
- **Technik-Startparameter, vor jedem Backtest festgelegt, nicht nachträglich optimieren:** Two MA Crossover 50/200; Momentum 12 minus 1 Monat; Price Channel Einstieg 55-Tage-Hoch, Ausstieg 20-Tage-Tief, Stop 2 × ATR(20); RSI(2) < 10 nur über SMA200, Ausstieg bei Schluss über SMA5; ADX(14) als Regime-Schalter (> 25 starker, < 20 schwacher Trend). Tageskerzen.
- **Benchmarks:** Hauptmaßstab MSCI ACWI IMI; Vergleich mit MSCI ACWI, FTSE All-World GDP-Adjusted, MSCI ACWI IMI Value Weighted, MSCI World ex USA, MSCI World. Mischbenchmark für den Multi-Asset-Teil ist noch offen. Abgebildet über Xetra-ETFs (`config/daten.yaml`), Historie ab 01.01.2012, weil die Yahoo-Kurse von SPYI.DE 2011 fehlerhaft sind.

## Architektur

```
Daten ──► Fundamental │ Technik │ News │ Smart Money ──► Scoring + Regime ──► Risk-Manager (Veto) ──► Ausführung ──► Journal
                                   ▲                                                                              │
                                   └──────────────── Rückkopplung: Journal und Backtests kalibrieren Gewichte ◄───┘
```

- **Einheitliche Engine-Schnittstelle:** `score(stichtag, universum) -> pandas.Series` mit einem Wert je Ticker. Eine Engine darf nur Daten nutzen, die zum Stichtag öffentlich waren (Look-ahead-Schutz, Bilanzdaten ab Veröffentlichungsdatum).
- **Konfiguration statt Code:** Gewichte, Parameter und Limits stehen in `config/` (YAML), mit getrennten Abschnitten für Core und Satellite.
- **Broker-Adapter:** ein Interface, zuerst Interactive Brokers. Paper und Live unterscheidet nur ein Konfigurationsschalter; bis zur Freigabe ist ausschließlich `paper` erlaubt.
- **Anlageklassen-neutral:** Aktien, ETFs und ETCs zuerst; weitere Klassen später als Modul.

Geplante Struktur (wird mit dem Code angelegt, nicht vorab leer):

```
src/tradingbot/
  daten/      Loader und Cache: yfinance, FRED, SEC EDGAR, Briefing-Archiv
  engines/    fundamental.py, technik.py, news.py, smart_money.py
  scoring/    Zusammenführung der Scores, Regime
  risiko/     Risk-Manager, Limits, Positionsgröße
  backtest/   Simulation, Kosten, Steuern, Kennzahlen
  broker/     Adapter-Interface, ibkr.py
  journal/    Trades, Investment-Thesen, Berichte
config/       YAML-Konfiguration
tests/        pytest, darunter tests/musterloesungen/
wissen/       Grundlagenwissen (Markdown)
docs/         Roadmap, Schemas, Methodenhandbuch
daten/        lokale Daten und Caches, nicht in Git
```

## Phasen

1. **Setup:** Python-Umgebung (`.venv`), Abhängigkeiten, pytest, Grundstruktur.
2. **Phase 1, Fundament:** Datenbasis, Backtest-Framework, Fundamental-Engine.
3. **Phase 2, Risiko:** Risk-Manager, Paper-Trading-Anbindung (IB Gateway), Investment-These pro Trade, Technik-Engine. **Abgeschlossen am 03.11.2026** mit dokumentierter Ausnahme (Kriterium 2 verfehlt, `docs/PHASE2.md`).
4. **Phase 3, News:** Briefing-Auswertung, Makro-Kalender, PEAD.
5. **Phase 4, Smart Money:** 13F-Tracking, Konsens-Score, Insider-Trades.
6. **Phase 5, Ausbau:** Regime-Erkennung, ESG, Stresstests (2008, 2020, 2022), Dashboard.

Eine Phase ist fertig, wenn ihr Backtest sauber gegen die Benchmark läuft.

## Arbeitsweise

- **Datum:** immer per `date` vom System holen, nie aus dem Arbeitsverlauf schätzen (Fehler vom 02.11.2026: über Mitternacht und lange Downloads wurde ein „03.11.“ angenommen und in 83 Zeilen weitergetragen).
- **Ein Feature pro Sitzung:** erst einen kurzen Plan zeigen, nach Jakobs Okay umsetzen, dann testen.
- **Anzeige-Korrekturen (12.11.2026):** Reine Anzeige-Korrekturen ohne Änderung an Logik, Freigabe, Senden, Journal oder Risk-Manager dürfen direkt umgesetzt werden (mit Test). Alles andere: erst Plan zeigen.
- **Formeln:** Jede Finanzformel bekommt einen Docstring mit Formel, Annahmen und Quelle (Datei und Abschnitt in `wissen/`). Gibt es die Formel in `tests/musterloesungen/referenz.py`, denselben Funktionsnamen und dieselbe Signatur verwenden oder darauf aufbauen.
- **Tests:** `pytest` muss vor jedem Commit grün sein, inklusive `tests/musterloesungen/test_uebungen.py`. Neue Logik bekommt eigene Tests.
- **Befehle:** Installation `.venv\Scripts\python -m pip install -e ".[dev,broker]"`, danach `... -m pip install --no-deps ib_async==2.1.0` (ib_async pinnt tzdata<2026; Abhängigkeiten stehen im Extra `broker`); Tests offline `.venv\Scripts\python -m pytest`; Tests gegen echte Quellen `... -m pytest -m netz`. Backtest-Lauf mit Bericht: `tradingbot.backtest.bericht.fuehre_lauf_aus(...)` (optional mit `walk_forward_fenster(...)`), Ablage mit Konfiguration, Git- und Datenstand in `daten/backtests/<zeitstempel>_<name>/`. Für Python 3.15 gibt es kein PyYAML, deshalb `ruamel.yaml`.
- **Tresor (01.11.2026):** Daten ab 01.01.2025 sind gesperrt; der Code verweigert den Zugriff ohne Freigabe (`backtest/tresor.py`, Protokoll `docs/TRESOR_PROTOKOLL.md`). Einmal pro Phase öffnen, erst wenn Regeln und Parameter feststehen. Bei schlechtem Ergebnis nicht nachjustieren und erneut testen: Erkenntnis notieren, zurück auf die Entwicklungsdaten, neue Prüfung ist das Paper Trading. Das Paper Trading ist der zweite, noch strengere Tresor. Den Tresor nie ohne Jakobs ausdrückliche Anweisung öffnen.
- **Steuern im Backtest** (`backtest/steuern.py`): heutiges Recht für alle Jahre (Abgeltungsteuer plus Soli, keine Kirchensteuer, Pauschbetrag 1.000 € vollständig für den Bot, Verlusttöpfe, FIFO, Teilfreistellung, Vorabpauschale mit Basiszins aus `config/backtest.yaml`). Steuer fließt am Jahresende als eigener Abfluss ab, ohne Zwangsverkauf; ausgewiesen werden vor Steuern, nach Steuern und nach fiktivem Verkauf am Ende. Der Schatten-Satellite bildet eine eigene Steuergruppe ohne Pauschbetrag (vorsichtig).
- **Backtests:** Walk-forward, kein Look-ahead- und kein Survivorship-Bias. Kosten realistisch: IBKR-Gebühren, Spread, Slippage, Währungskosten bei US-Werten, Abgeltungsteuer mit Sparer-Pauschbetrag. Ergebnisse immer gegen die Benchmark und nach Kosten. Neue Features: Backtest, dann Paper, dann live. **Kriterien (Lehre aus Phase 2, 03.11.2026): Technik wird am Zwilling gemessen (gleiche Einzahlungen, Kosten, Steuern und Stückelung, ohne die zu prüfende Technik), Strategie am Index.** Grenzen werden nach dem Lauf nie geändert; eine Verfehlung bleibt im Bericht stehen und wird begründet.
- **Git:** kleine Commits mit deutscher Nachricht. Vor Push und vor Änderungen an Regeln oder Limits Jakob fragen.
- **Verständlichkeit:** Code lesbar halten, Namen sprechend wählen, Fachbegriffe wie in den Vorlesungen verwenden.

## Sicherheit und Daten

- **Geheimnisse nur in `.env`** (steht in `.gitignore`); `.env.example` dokumentiert die Variablen. Nie Schlüssel in Code, Tests, Logs oder Commits.
- **IBKR:** keine Zugangsdaten im Code. Der Bot verbindet sich nur mit dem lokal laufenden IB Gateway, in der Paper-Phase ausschließlich mit dem Paper-Konto (Port 4002). Live (Port 4001) bleibt gesperrt, bis Jakob nach den Go-Live-Kriterien ausdrücklich freigibt.
- **Datenquellen kostenlos:** yfinance (inoffiziell, Werte plausibilisieren), FRED (Schlüssel in `.env`), SEC EDGAR (User-Agent mit Name und E-Mail aus `.env`, Abruflimits einhalten), EZB, Eurostat, BaFin. Abrufe lokal cachen.
- **Urheberrecht:** keine Vorlesungs-PDFs oder Newsletter-Texte ins Repository; nur eigene Zusammenfassungen.

## Fundamental-Engine (Entscheidungen 02.11.2026)

Parameter in `config/fundamental.yaml`, vor dem ersten Backtest festgelegt, nicht nachträglich optimieren. Details in `docs/ROADMAP.md`, Abschnitt Fundamental-Engine.

- **Point-in-Time:** SEC-Werte erst ab dem Handelstag nach `filed`; bei Restatements gilt der zuerst gemeldete Wert. SEC-Abrufe höchstens 10 pro Sekunde, alles lokal cachen.
- **Universum:** S&P 500 mit historischer Zusammensetzung je Stichtag. Kurse nicht mehr gelisteter Titel über Tiingo (Schlüssel `TIINGO_API_KEY` in `.env`); Rückfall: Übernahme/Fusion zum letzten Kurs, Pleite/Performance/unbekannt letzter Kurs minus 30 % (Shumway 1997), beides markiert und gezählt im Bericht.
- **Schattenportfolio:** 20 Titel, gleich gewichtet, quartalsweise, virtuell 10.000 €, getrennt vom echten Core; gemessen gegen MSCI ACWI IMI und S&P 500 in Euro.
- **Backtest-Zeitraum (Regel, 02.11.2026):** Der gewertete Backtest beginnt am ersten Rebalancing-Stichtag, ab dem alle folgenden Stichtage unter 2 % nicht kaufbarem Gewicht im investierbaren Universum liegen; heute 01.10.2016 bis 31.12.2024. Davor ab 2012 nur nicht gewerteter Vorlauf für Indikatoren. Die Regel steht in `config/fundamental.yaml` (`backtest`) und wird von `tools/auswertung_abdeckung.py` geprüft; ein anderes Ergebnis wird laut gemeldet, nie still übernommen. WRDS/CRSP entfällt (nur akademische Nutzung erlaubt). Die Gegenprobe des Index-Nachbaus gilt für denselben Zeitraum, Kriterien unverändert (`docs/DATENQUALITAET.md`).
- **Finanzwerte (02.11.2026):** SIC 6000–6999 (inklusive REITs) fallen im ersten Lauf ganz aus dem Universum; SIC point-in-time aus dem Kopf der jeweiligen SEC-Einreichung. Der Bericht vergleicht zusätzlich mit dem S&P 500 ohne Finanzwerte, damit der Sektoreffekt sichtbar bleibt.
- **Filter:** Piotroski ≤ 3 raus; Altman 1968 für Industrie, Z'' für übrige; Beneish > −1,78 raus; Banken und Versicherungen ohne Altman und Beneish.
- **Reihenfolge:** erster Lauf mit Qualität und Multiples, DCF erst danach (MRP 5 %, g = 2 % < Kapitalkosten, Wachstum aus historischem Umsatz mit Deckel 10 %, r_f = 10-jährige US-Rendite point-in-time, Beta per Regression).
- **DAX:** vorerst nur US; später über ESEF, getrennt ausgewiesen.
- **Erster Lauf (02.11.2026):** beide Erfolgskriterien verfehlt (Ergebnis und Diagnose in `docs/FUNDAMENTAL.md`). Der kombinierte Score geht nicht als Stockpicker ins Paper Trading; Score und Gewichte bleiben unverändert. Im Paper Trading laufen zwei Schattenportfolios vorwärts mit: (A) Originalscore, (B) nur Qualitätshälfte. DCF zurückgestellt. Gezählte Varianten: `daten/fundamental/varianten.csv`.
- **Datenkorrektur Piotroski EQ_OFFER (13.11.2026):** Aktienzahl t−1 aus derselben Einreichung wie t (Rückfall Split-Faktoren), übernommen unabhängig vom Neulauf, wirksam im Betrieb ab 04.01.2027 (`config/fundamental.yaml` `piotroski_eq_offer`). Offener Nebenbefund: Yahoo führt Abspaltungen als Split, das verzerrt die Marktwerte (`docs/FUNDAMENTAL.md`).

## Technik-Engine und Risk-Manager (Entscheidungen 02.11.2026)

Parameter in `config/technik.yaml`, Veto in `config/risiko.yaml`. Details in `docs/ROADMAP.md`, Abschnitt Technik-Engine.

- **Fundamental-Veto:** Piotroski ≤ 3, Z'' mit zweitem Signal und Altman Z (Industrie) sind Veto im Risk-Manager für alle Einzelaktien-Trades; Beneish nur Warnhinweis. Bei einem reinen ETF-Universum ruht das Veto vorerst.
- **Satellite-Universum:** 11 Xetra-ETFs/-ETCs nach der Regel „je Anlageklasse der größte physisch replizierende UCITS-ETF mit Xetra-Notierung seit spätestens 2012“ (Liste in `config/technik.yaml`). Gewerteter Backtest ab dem Tag, an dem alle 12 Monate Historie haben, bis 31.12.2024.
- **Strategien:** Crossover 50/200, Momentum 12−1 (Zeitreihe, monatlich, Vergabe nach Stärke), Price Channel 55/20, RSI(2) < 10 über SMA200, ADX-Regime (über 25 Trend und Ausbruch, unter 20 nur RSI(2), dazwischen alle). Zeit-Stops: RSI(2) 10, Price Channel 63 Handelstage; Crossover und Momentum nach 63 Tagen nur, wenn das Signal nicht mehr gilt.
- **Erfolgskriterien je Variante** (fünf Varianten, nach Kosten, 1.250 €): Sharpe ≥ Buy & Hold (alle ETFs gleich gewichtet, quartalsweise, gleiche Kosten) und maximaler Drawdown nicht schlechter als −20 %, beides in beiden Hälften.
- **Ergebnis (02.11.2026), Zweig a) des Entscheidungsbaums (`docs/TECHNIK.md`):** Ohne Kosten erreichen weder Crossover noch Momentum den Sharpe von Buy & Hold in beiden Hälften. Die Technik-Engine ist kein Renditebaustein; echtes Geld bleibt im Core, Crossover und Momentum laufen im Paper Trading als Schatten vorwärts mit. RSI(2) und Price Channel sind für den Satellite raus. Ohne Kosten senken Crossover und Momentum den maximalen Drawdown aber deutlich (Crossover −12,4 % gegen −17,1 % bei Buy & Hold); sie bleiben als mögliche Risikosignale für den Gesamt-Score erhalten.
- **Berichte** zusätzlich als Datei unter `docs/berichte/`.

## Paper Trading (Phase 2, Entscheidungen 02.11.2026)

Parameter in `config/betrieb.yaml`. Realbuch: Core 500 € in SPYI (ganze Stücke), Strategien nur als Schatten. Skalierungsbücher mit je 10.000 € (Fundamental A und B, Crossover, Momentum) handeln im Paper-Konto, um Signalqualität ohne Kostenverzerrung zu messen; sie begründen nie echte Trades mit kleinerem Kapital. Tageslauf abends, Freigabe 18–24 Uhr, Senden sofort (Limit = Vortagesschluss + 2 %, gültig für den nächsten Handelstag). Senden nur bei Konto „DU…“, Port 4002, `TRADING_MODE=paper` und ohne Datei `STOP`. Betriebsdaten ab 2025 liegen in einem eigenen Bereich, den Backtest- und Auswertungswerkzeuge nicht lesen können. Fremdwährung: Tausch EUR→USD je Buch vor den Käufen, keine Währung darf negativ werden. `Tageslauf_Probe.bat`: Probe-Journal, jederzeit bedienbar, sendet nie; Freigaben im Probe-Modus oder bei ausgeschaltetem Senden zählen nie als Messbeginn (03.11.2026).

- **Freischaltung je Buch (03.11.2026):** `senden_freigeschaltet` global an, je Buch zusätzlich `buecher.<buch>.senden_freigeschaltet`; zunächst nur real und crossover. Gesperrte Bücher zeigen Vorschläge, sind aber nicht freigebbar. Read-Only im Gateway erst unmittelbar vor der ersten Freigabe ausschalten (`docs/BETRIEB_ABEND.md`).
- **Sicherungen im Betrieb (03.11.2026):** 1-%-Regel vom Limit bis Stop; gesendete, nicht ausgeführte Orders („unterwegs“) reservieren Kasse und sperren den Titel im Buch; Laufsperre gegen zwei gleichzeitige Tagesläufe (`betrieb/sperre.py`); ReqCompletedOrders wird beim Verbinden nicht abgerufen.

## Briefing-Archiv (Eingang der News-Engine)

Eine geplante Aufgabe in Claude speichert täglich um 22:40 den Bot-Anhang als `JJJJ-MM-TT.json` in Google Drive unter `TradingBot/Briefing-Archiv` (Schema 1.1, siehe `docs/BOT_ANHANG.md`, Prüfung mit `tools/pruefe_bot_anhang.py`). Lokal gehören die Dateien nach `daten/briefings/`. Nachrichten erst ab `erstellt_um` verwenden. Bekannte Einschränkung: In den Dateien vom 28. bis 30.10.2026 ist `quelle` bei Einträgen aus Sammelmeldungen (item_key mit `-b`) teils falsch; ab 31.10.2026 korrigiert.

## Offene Punkte

- Mischbenchmark für den Multi-Asset-Teil festlegen.
- Vor Phase 2: IB Gateway installieren, API für das Paper-Konto freischalten (Port 4002, anfangs Read-Only, nur 127.0.0.1), Marktdaten-Freigabe fürs Paper-Konto prüfen.
- Phase 3: Briefing-Archiv anbinden (Kopie oder Google-Drive-Zugriff).
