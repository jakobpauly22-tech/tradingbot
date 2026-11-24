# Tresor: was über den Zeitraum ab 01.01.2025 bekannt ist

Angelegt am 16.11.2026 nach der unabhängigen Prüfung (`docs/berichte/2026-11-16_unabhaengige_pruefung.md`, Befunde 1, 8
und 9; Ablage nach Jakobs Hinweis vom 16.11.2026).

**Zweck.** Der Tresor (Daten ab 01.01.2025, `config/backtest.yaml`) ist technisch zu: Backtests und Auswertungen sehen
keine Kurse oder Einreichungen nach dem 31.12.2024. Über andere Wege ist aber Wissen über diesen Zeitraum ins Projekt
gelangt. Diese Datei hält fest, **was** bekannt ist und **wo** es steht, damit spätere Varianten, Neuläufe und Prüfungen
einschätzen können, wie unabhängig sie vom Tresorzeitraum sind.

**Regeln.**

- Diese Datei nennt Fundstelle und Art des Wissens, wiederholt aber keine Werte (keine Zustände, Faktoren, Kurse).
- Wer neues Wissen über den Zeitraum ab 2025 in Git schreibt (Doku, Bericht, Konfiguration), trägt es hier ein.
- Das ist **keine Tresor-Öffnung.** Öffnungen stehen allein in `docs/TRESOR_PROTOKOLL.md` und laufen nur über
  `backtest/tresor.oeffne_tresor`. Bisher wurde der Tresor nie geöffnet.
- Nichts wird nachträglich gelöscht; Git enthält die Stellen ohnehin. Ein Eintrag hier ändert keine Regel und kein Urteil.

## Grundsätzlich (unvermeidbar)

| Quelle | Was bekannt ist | Einordnung |
| --- | --- | --- |
| Allgemeines Wissen von Jakob und Claude | grober Marktverlauf 2025/2026 aus Nachrichten und Trainingsdaten | Nicht zu vermeiden. Deshalb sind die Regeln vor jedem Lauf festgelegt und werden nicht nachjustiert. |
| Paper Trading (seit November 2026) | aktuelle Kurse, Signale und Buchstände im Betrieb | Gewollt („zweiter Tresor“). Betriebsdaten liegen in einem eigenen Bereich, Backtest- und Auswertungswerkzeuge lesen ihn nicht. |
| Briefing-Archiv (ab 28.10.2026) | Nachrichten aus der Gegenwart | Gewollt; Eingang der News-Engine. |

## Konkrete Fundstellen in Git (Stand 16.11.2026)

| Nr. | Fundstelle | Art des Wissens | Herkunft | Wirkung |
| --- | --- | --- | --- | --- |
| 1 | `docs/REGIME.md`, Abschnitte 9, 9a und 9b (Betrieb, Probeläufe, Bewertung vom 30.10.2026, Datenlücke) | Zustände von V1 und Signalwerte 2025/2026, Monate der Wechsel, Ursache der Datenlücke | Inbetriebnahme des Schattenbuchs „regime“ (Befund 1) | Urteil zu V1 unberührt (steht, nicht nachjustiert). Jede spätere Regime-Variante ist an dieser Stelle nicht mehr blind für 2025/2026. |
| 2 | `config/kapitalmassnahmen_historie.yaml`, 28 Einträge mit Datum ab 2025 (Stand 13.11.2026), dazu SNDK 20.11.2026 (bestätigt über 8-K, Jakob 24.11.2026) | Splits und Abspaltungen 2025/2026 (Ticker, Datum, Faktor) | `tools/split_ereignisse_einordnen.py` im Betriebsmodus bis 13.11.2026 (Befund 8) | Rechnerisch ohne Wirkung auf Backtests (`korrektur` durchläuft nur Ereignisse der begrenzten Kursreihe). Seit 16.11.2026 ordnet das Werkzeug nur bis zur Grenze ein. |
| 3 | `config/kapitalmassnahmen_historie.yaml`, 5 Einträge aus 2024 (SMCI, ANET, ETR, PANW, TSCO) | Einordnung über eine SEC-Einreichung aus Februar 2025 | wie Nr. 2 | Inhaltlich harmlos (der Split war am Ereignistag öffentlich), formal Wissen nach der Grenze. **Erledigt 24.11.2026 (c3 Schritt 1b):** Das begrenzte Werkzeug ordnet alle fünf als „unklar“ ein. Jakob hat sie einzeln als geprüften Split freigegeben, belegt mit Vollzugs-8-K mit filed ≤ 31.12.2024. Die Einträge stützen sich nicht mehr auf Einreichungen ab 2025; frühere Fassungen bleiben in Git. Noch in der Liste: 7 Einträge bis 2024 von Firmen, die erst ab 2025/2026 im Index sind (FERG, ECHO, TTD, FLEX, WSM) oder deren Kursreihe gekappt ist (DD 30554). Sie sind unverändert behalten (Jakob 24.11.2026) und ohne Wirkung auf Backtests, weil die Ereignisse nicht in den begrenzten Kursreihen stehen. Dass es sie gibt, ist selbst Wissen über die Zusammensetzung nach 2024 (wie Nr. 9). |
| 4 | `docs/berichte/2026-11-13_split_ereignisse.md`, Abschnitt „Betrieb ab 2025 noch offen“ und Zählung | wie Nr. 2 | wie Nr. 2 | wie Nr. 2 |
| 5 | `docs/FUNDAMENTAL.md` (c2 (2): erste Abnahme, zweiter Probelauf; c3-Absicherung: Variante B) und `docs/berichte/2026-11-15_rohkurse_abnahme.md`, `2026-11-16_rohkurse_abnahme.md`, `2026-11-16_1247_rohkurse_abnahme.md` (Abschnitt „Verdeckter Faktor H ≠ 1“), `daten/cache/tiingo/roh_bis_tresor/abnahme.csv` (Spalte H, nicht in Git) | Firmen mit Split oder Abspaltung nach 2024, mit Faktor H | Abnahme der Rohreihen (Befund 9): H ist der verdeckte Faktor aus Ereignissen nach der Grenze und für die Rechnung nötig | In Regeln oder Parameter fließt H nicht ein; nur die Auswahl der Stichprobe (Firmen mit H ≠ 1) hängt daran. Ein Split ist ein Hinweis auf die Kursentwicklung danach. |
| 6 | `docs/berichte/2026-11-15_stichprobe_marktwert_roh_auswahl.md`, `docs/FUNDAMENTAL.md` (eingefrorene Auswahl) | welche Stichprobenfirmen H ≠ 1 haben | wie Nr. 5 | wie Nr. 5 |
| 7 | `docs/FUNDAMENTAL.md` (Datenkorrektur Marktwert, Musterprüfung), `docs/berichte/2026-11-13_piotroski_eq_offer_bestand.md` | einzelne Kapitalmaßnahmen 2025/2026 gehaltener oder bewerteter Titel | Betrieb (Bestand der Bücher, Quartalsstichtag 01.10.2026) | Betrieb; ohne Wirkung auf Backtests. |
| 8 | `docs/PHASE2.md`, `config/daten.yaml`, Berichte zum Phase-2-Gesamtdepot | Split der SPYI 2026 | Betrieb und Rückrechnung der Anteilspreise | Im Backtest rückgängig gemacht; ohne Kurswissen nach 2024. |
| 9 | `docs/BETRIEB.md` (Kontrakte, Universum) und `docs/berichte/2026-11-13_reihen_nach_indexabgang.md` | Indexwechsel, Übernahmen und Kursenden 2025/2026 | Betrieb und Prüfung der Kursreihen | Die Zusammensetzung des S&P 500 nach 2024 wird in Backtests nicht verwendet. |
| 10 | `docs/berichte/2026-11-16_unabhaengige_pruefung.md` | Zusammenfassung von Nr. 1, 2, 5 | Prüfbericht | wie dort |
| 11 | `docs/BETRIEB.md` (Wächter gegen ein verschobenes Universum), `docs/berichte/2026-11-16_unabhaengige_pruefung.md` (Befunde 19 und 20), Commit-Nachrichten vom 17.11.2026 | einzelne Indexwechsel 2026 und Kurs eines gehaltenen Titels am 16.11.2026 | Prüfung der Universums-Verschiebung nach dem Wikipedia-Abruf des Betriebs (17.11.2026) | Betrieb; die Zusammensetzung nach 2024 wird in Backtests nicht verwendet. |
| 12 | `docs/BETRIEB.md`, Abschnitte „Stand Schritt 2“ und „Fehlende Einreichungen in den companyfacts“ (23.11.2026) | welche Firmen 2025/2026 Einreichungen (10-Q, 10-K) abgegeben haben, die in den companyfacts fehlen, und welche nachgeliefert wurden; Zahl neuer Erstmeldungen im Probelauf | SEC-Aktualisierung des Betriebs (Probelauf und Ursachenprüfung) | Betrieb; keine Werte, nur Vollständigkeit der Daten. Backtests sehen Einreichungen ab 2025 nicht. |
| 13 | `docs/berichte/2026-11-24_sec_aktualisierung_abnahme_b.md`, `docs/FUNDAMENTAL.md` (sechste Datenkorrektur), `docs/BETRIEB.md` (Stand Schritt 3 und 5) | welche Firmen zwischen 30.10. und 18.11.2026 neue Einreichungen hatten, Art der Einreichung und welche Kennzahlen sich dadurch am 18.11.2026 ändern (Firmenliste); Aktienzahlen von INTU aus dem 10-K vom 09.09.2026; Ranglistenwechsel am 18. und 23.11.2026 im Gespräch | Erster echter Lauf der SEC-Aktualisierung und Abnahme (24.11.2026) | Betrieb. Die Messung zur sechsten Datenkorrektur lief auf Daten bis 2024 (Tresor). |

## Ausblick

- Befund 9: Jakob hat am 16.11.2026 entschieden, dass Abnahmeberichte H ≠ 1 nur noch als Anzahl nennen, ohne Namen und
  Faktor; umgesetzt am 17.11.2026 in `tools/pruefe_rohkurse.py` (auch die Tabelle „Nicht bestanden“ ohne Spalte H).
  Bestehende Berichte (Nr. 5) bleiben unverändert.
- Nr. 3: erledigt am 24.11.2026 (c3 Schritt 1b, docs/FUNDAMENTAL.md, Bericht `docs/berichte/2026-11-24_1511_split_ereignisse.md`).
