# Eingefrorener Wikipedia-Stand für Backtest und c3 (Befund 19, Schritt 1)

Plan freigegeben von Jakob am 17.11.2026 (Prüfbericht `docs/berichte/2026-11-16_unabhaengige_pruefung.md`, Befund 19).
Dieser Bericht hält zuerst die Abnahmekriterien und das Suchverfahren fest. Beides ist **vor** der Suche nach der
Revision committet und wird danach nicht geändert. Ergebnis und gewählte Revision folgen unten in einem eigenen Commit.

## 1. Abnahmekriterien (festgehalten am 18.11.2026 vor der Suche)

Geprüft wird das Universum, das der unveränderte Aufbau (`lade_mitgliedschaften` → `cik_zuordnen` →
`vorgaenger_suchen` → `cik_korrekturen_anwenden`) aus einem Paar von Wikipedia-Revisionen erzeugt: „List of S&P 500
companies“ (heutige Mitglieder) und „Historical components of the S&P 500“ (Änderungen). Dabei gelten die heutige
`config/universum_korrekturen.yaml` und das gecachte SEC-Namensverzeichnis.

- **(a)** Das Universum hat genau **896 Zeilen**.
- **(b)** Alle **813 Zeilen** von `daten/universum/kursstatus.csv` passen: Die Universumszeile mit der Nummer aus
  Spalte `index` hat denselben Ticker, dasselbe `von` und dasselbe `bis` (Schlüssel). Zeilennummer **und** Schlüssel
  müssen stimmen.
- **(c)** Jede CIK (`firma`) aus dem Cache `fundamental/scores_eq_offer` (Stand 13.11.2026, 33 Stichtage vom
  03.10.2016 bis 01.10.2024) ist am jeweiligen Stichtag Mitglied, also in `mitglieder_am(universum, stichtag)` mit
  dieser CIK enthalten.

Alle drei müssen bestehen. Es gibt keine Toleranz.

## 2. Suchverfahren (festgehalten vor der Suche)

- **Kandidaten:** Ein Kandidat ist der Zustand beider Seiten zu einem Zeitpunkt T, also je Seite die letzte Revision mit
  Zeitstempel ≤ T. Die Zeitpunkte T sind die Zeitstempel aller Revisionen beider Seiten von 01.10.2026 00:00 UTC bis
  16.11.2026 21:18 UTC (22:18 MEZ, der Abruf der Probe aus Befund 19).
- **Reihenfolge:** chronologisch. Gewählt wird der **früheste** Kandidat, der (a)–(c) besteht.
- **Rand:** Besteht schon der erste Kandidat im Fenster, wird monatsweise vor den 01.10.2026 zurückgegangen, bis ein
  früherer Kandidat scheitert. Gewählt wird dann der früheste bestehende Kandidat nach diesem Scheitern.
- **Kein Treffer:** Besteht kein Kandidat, wird nichts eingefroren. Ich halte an und melde mich bei Jakob, ohne die
  Kriterien anzupassen.
- **Gegenprobe (nur berichtet, kein Kriterium):** Ergebnis für den Zustand am 09.11.2026 um 08:31 MEZ, dem
  Wikipedia-Abruf laut Protokoll (Hinweis Jakob).
- **Abruf:** Wikipedia-API (Revisionsliste) und `index.php?oldid=…` mit allgemeinem User-Agent ohne persönliche
  Angaben. Die Seiten der gewählten Revision werden unter `daten/universum/eingefroren/` abgelegt.
  `config/universum_stand.yaml` erhält je Seite `revid`, Zeitstempel und SHA-256 der abgelegten Datei.
- **Bericht:** XEC, IR, CDAY, DAY sowie KVUE/OKTA einzeln, jeweils im eingefrorenen Stand und im Stand vom
  16.11.2026 22:18.

## 3. Ergebnis

*folgt nach der Suche*
