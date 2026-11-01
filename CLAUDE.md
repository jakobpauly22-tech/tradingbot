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

Bei Widersprüchen gilt die neueste Entscheidung von Jakob. Weicht der Code von der Roadmap ab, Jakob fragen statt still anpassen.

## Feste Regeln (nur mit Jakobs Zustimmung ändern)

| Regel | Core (70 %) | Satellite (30 %) |
| --- | --- | --- |
| Haltedauer | Monate bis Jahre, Rebalancing quartalsweise | Tage bis ca. 3 Monate, kein Intraday |
| Positionsgröße | max. 5 % je Einzelaktie (breite ETFs ausgenommen) | 1 % Risiko pro Trade, max. 10 % je Position |
| Ausstieg | These gebrochen oder fairer Wert erreicht | Stop 2 × ATR(20) plus Zeit-Stop |
| Monatslimit | keins | −10 %: Bot pausiert, Ursache prüfen |
| Notbremse | Review, wenn 12 Monate > 10 Prozentpunkte hinter MSCI ACWI IMI | −20 % vom Höchststand: Satellite stoppt |
| Freigaben | beim Rebalancing | feste Fenster morgens und abends |

- **Nur long, ohne Hebel.** Keine Leerverkäufe, Futures, CFDs, Optionen oder Margin. Short-Signale bedeuten „nicht investiert“.
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

1. **Setup** (jetzt): Python-Umgebung (`.venv`), Abhängigkeiten, pytest, Grundstruktur.
2. **Phase 1, Fundament:** Datenbasis, Backtest-Framework, Fundamental-Engine.
3. **Phase 2, Risiko:** Risk-Manager, Paper-Trading-Anbindung (IB Gateway), Investment-These pro Trade, Technik-Engine.
4. **Phase 3, News:** Briefing-Auswertung, Makro-Kalender, PEAD.
5. **Phase 4, Smart Money:** 13F-Tracking, Konsens-Score, Insider-Trades.
6. **Phase 5, Ausbau:** Regime-Erkennung, ESG, Stresstests (2008, 2020, 2022), Dashboard.

Eine Phase ist fertig, wenn ihr Backtest sauber gegen die Benchmark läuft.

## Arbeitsweise

- **Ein Feature pro Sitzung:** erst einen kurzen Plan zeigen, nach Jakobs Okay umsetzen, dann testen.
- **Formeln:** Jede Finanzformel bekommt einen Docstring mit Formel, Annahmen und Quelle (Datei und Abschnitt in `wissen/`). Gibt es die Formel in `tests/musterloesungen/referenz.py`, denselben Funktionsnamen und dieselbe Signatur verwenden oder darauf aufbauen.
- **Tests:** `pytest` muss vor jedem Commit grün sein, inklusive `tests/musterloesungen/test_uebungen.py`. Neue Logik bekommt eigene Tests.
- **Befehle:** Installation `.venv\Scripts\python -m pip install -e ".[dev]"`; Tests offline `.venv\Scripts\python -m pytest`; Tests gegen echte Quellen `... -m pytest -m netz`. Für Python 3.15 gibt es kein PyYAML, deshalb `ruamel.yaml`.
- **Tresor (01.11.2026):** Daten ab 01.01.2025 sind gesperrt; der Code verweigert den Zugriff ohne Freigabe (`backtest/tresor.py`, Protokoll `docs/TRESOR_PROTOKOLL.md`). Einmal pro Phase öffnen, erst wenn Regeln und Parameter feststehen. Bei schlechtem Ergebnis nicht nachjustieren und erneut testen: Erkenntnis notieren, zurück auf die Entwicklungsdaten, neue Prüfung ist das Paper Trading. Das Paper Trading ist der zweite, noch strengere Tresor. Den Tresor nie ohne Jakobs ausdrückliche Anweisung öffnen.
- **Steuern im Backtest** (`backtest/steuern.py`): heutiges Recht für alle Jahre (Abgeltungsteuer plus Soli, keine Kirchensteuer, Pauschbetrag 1.000 € vollständig für den Bot, Verlusttöpfe, FIFO, Teilfreistellung, Vorabpauschale mit Basiszins aus `config/backtest.yaml`). Steuer fließt am Jahresende als eigener Abfluss ab, ohne Zwangsverkauf; ausgewiesen werden vor Steuern, nach Steuern und nach fiktivem Verkauf am Ende. Der Schatten-Satellite bildet eine eigene Steuergruppe ohne Pauschbetrag (vorsichtig).
- **Backtests:** Walk-forward, kein Look-ahead- und kein Survivorship-Bias. Kosten realistisch: IBKR-Gebühren, Spread, Slippage, Währungskosten bei US-Werten, Abgeltungsteuer mit Sparer-Pauschbetrag. Ergebnisse immer gegen die Benchmark und nach Kosten. Neue Features: Backtest, dann Paper, dann live.
- **Git:** kleine Commits mit deutscher Nachricht. Vor Push und vor Änderungen an Regeln oder Limits Jakob fragen.
- **Verständlichkeit:** Code lesbar halten, Namen sprechend wählen, Fachbegriffe wie in den Vorlesungen verwenden.

## Sicherheit und Daten

- **Geheimnisse nur in `.env`** (steht in `.gitignore`); `.env.example` dokumentiert die Variablen. Nie Schlüssel in Code, Tests, Logs oder Commits.
- **IBKR:** keine Zugangsdaten im Code. Der Bot verbindet sich nur mit dem lokal laufenden IB Gateway, in der Paper-Phase ausschließlich mit dem Paper-Konto (Port 4002). Live (Port 4001) bleibt gesperrt, bis Jakob nach den Go-Live-Kriterien ausdrücklich freigibt.
- **Datenquellen kostenlos:** yfinance (inoffiziell, Werte plausibilisieren), FRED (Schlüssel in `.env`), SEC EDGAR (User-Agent mit Name und E-Mail aus `.env`, Abruflimits einhalten), EZB, Eurostat, BaFin. Abrufe lokal cachen.
- **Urheberrecht:** keine Vorlesungs-PDFs oder Newsletter-Texte ins Repository; nur eigene Zusammenfassungen.

## Briefing-Archiv (Eingang der News-Engine)

Eine geplante Aufgabe in Claude speichert täglich um 22:40 den Bot-Anhang als `JJJJ-MM-TT.json` in Google Drive unter `TradingBot/Briefing-Archiv` (Schema 1.1, siehe `docs/BOT_ANHANG.md`, Prüfung mit `tools/pruefe_bot_anhang.py`). Lokal gehören die Dateien nach `daten/briefings/`. Nachrichten erst ab `erstellt_um` verwenden. Bekannte Einschränkung: In den Dateien vom 28. bis 30.10.2026 ist `quelle` bei Einträgen aus Sammelmeldungen (item_key mit `-b`) teils falsch; ab 31.10.2026 korrigiert.

## Offene Punkte

- Mischbenchmark für den Multi-Asset-Teil festlegen.
- Vor Phase 2: IB Gateway installieren, API für das Paper-Konto freischalten (Port 4002, anfangs Read-Only, nur 127.0.0.1), Marktdaten-Freigabe fürs Paper-Konto prüfen.
- Phase 3: Briefing-Archiv anbinden (Kopie oder Google-Drive-Zugriff).
