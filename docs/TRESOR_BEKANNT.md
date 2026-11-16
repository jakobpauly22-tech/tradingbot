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
| 2 | `config/kapitalmassnahmen_historie.yaml`, 28 Einträge mit Datum ab 2025 | Splits und Abspaltungen 2025/2026 (Ticker, Datum, Faktor) | `tools/split_ereignisse_einordnen.py` im Betriebsmodus bis 13.11.2026 (Befund 8) | Rechnerisch ohne Wirkung auf Backtests (`korrektur` durchläuft nur Ereignisse der begrenzten Kursreihe). Seit 16.11.2026 ordnet das Werkzeug nur bis zur Grenze ein. |
| 3 | `config/kapitalmassnahmen_historie.yaml`, 5 Einträge aus 2024 (SMCI, ANET, ETR, PANW, TSCO) | Einordnung über eine SEC-Einreichung aus Februar 2025 | wie Nr. 2 | Inhaltlich harmlos (der Split war am Ereignistag öffentlich), formal Wissen nach der Grenze. Ein neuer Lauf des begrenzten Werkzeugs würde sie neu einordnen (vermutlich „unklar“); nicht gelaufen, Entscheidung bei Jakob. |
| 4 | `docs/berichte/2026-11-13_split_ereignisse.md`, Abschnitt „Betrieb ab 2025 noch offen“ und Zählung | wie Nr. 2 | wie Nr. 2 | wie Nr. 2 |
| 5 | `docs/FUNDAMENTAL.md` (c2 (2): erste Abnahme, zweiter Probelauf; c3-Absicherung: Variante B) und `docs/berichte/2026-11-15_rohkurse_abnahme.md`, `2026-11-16_rohkurse_abnahme.md`, `2026-11-16_1247_rohkurse_abnahme.md` (Abschnitt „Verdeckter Faktor H ≠ 1“), `daten/cache/tiingo/roh_bis_tresor/abnahme.csv` (Spalte H, nicht in Git) | Firmen mit Split oder Abspaltung nach 2024, mit Faktor H | Abnahme der Rohreihen (Befund 9): H ist der verdeckte Faktor aus Ereignissen nach der Grenze und für die Rechnung nötig | In Regeln oder Parameter fließt H nicht ein; nur die Auswahl der Stichprobe (Firmen mit H ≠ 1) hängt daran. Ein Split ist ein Hinweis auf die Kursentwicklung danach. |
| 6 | `docs/berichte/2026-11-15_stichprobe_marktwert_roh_auswahl.md`, `docs/FUNDAMENTAL.md` (eingefrorene Auswahl) | welche Stichprobenfirmen H ≠ 1 haben | wie Nr. 5 | wie Nr. 5 |
| 7 | `docs/FUNDAMENTAL.md` (Datenkorrektur Marktwert, Musterprüfung), `docs/berichte/2026-11-13_piotroski_eq_offer_bestand.md` | einzelne Kapitalmaßnahmen 2025/2026 gehaltener oder bewerteter Titel | Betrieb (Bestand der Bücher, Quartalsstichtag 01.10.2026) | Betrieb; ohne Wirkung auf Backtests. |
| 8 | `docs/PHASE2.md`, `config/daten.yaml`, Berichte zum Phase-2-Gesamtdepot | Split der SPYI 2026 | Betrieb und Rückrechnung der Anteilspreise | Im Backtest rückgängig gemacht; ohne Kurswissen nach 2024. |
| 9 | `docs/BETRIEB.md` (Kontrakte, Universum) und `docs/berichte/2026-11-13_reihen_nach_indexabgang.md` | Indexwechsel, Übernahmen und Kursenden 2025/2026 | Betrieb und Prüfung der Kursreihen | Die Zusammensetzung des S&P 500 nach 2024 wird in Backtests nicht verwendet. |
| 10 | `docs/berichte/2026-11-16_unabhaengige_pruefung.md` | Zusammenfassung von Nr. 1, 2, 5 | Prüfbericht | wie dort |

## Ausblick

- Befund 9 bleibt offen in der Form: Der Abnahmebericht nennt Firmen mit H ≠ 1 weiterhin mit Namen und Faktor. Ob er
  künftig nur die Zahl nennt, entscheidet Jakob.
- Nr. 3: neuer Lauf des begrenzten Einordnungswerkzeugs vor c3, nur nach Jakobs Freigabe (ändert die Liste, die auch der
  Tageslauf liest).
