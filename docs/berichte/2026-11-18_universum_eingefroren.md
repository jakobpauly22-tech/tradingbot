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

## 3. Ergebnis (18.11.2026)

Werkzeug `tools/universum_revision_suchen.py`, 21 Kandidaten im Fenster. Die Kriterien und das Suchverfahren sind
unverändert, festgehalten in Commit 61ed4ec vor der Suche.

### Gewählte Revision

| | Wert |
| --- | --- |
| Zeitpunkt | 29.10.2026, 22:20:50 UTC |
| List of S&P 500 companies | revid 1382178819 (Stand vom 27.10.2026, 02:50 UTC) |
| Historical components of the S&P 500 | revid 1382710214 (29.10.2026, 22:20 UTC) |
| Abnahme | (a) 896 Zeilen; (b) 0 von 813 falsch; (c) 0 von 13.085 (Stichtag, CIK) falsch |

**Grund:** Es ist der früheste Kandidat, der (a) bis (c) besteht. Die Abnahme wurde am geschriebenen
`universum.parquet` wiederholt und erneut bestanden. Werte und SHA-256 stehen in `config/universum_stand.yaml`.

### Verlauf der Suche

| Kandidaten | Ergebnis |
| --- | --- |
| 14 Kandidaten vom 01.10. bis 27.10.2026 | Kein Universum: Die Korrektur „beenden FOX/Twenty-First Century Fox Class B“ aus `config/universum_korrekturen.yaml` findet 0 statt 1 Treffer. Die Änderungstabelle sah damals noch anders aus. |
| 29.10.2026, 21:35 UTC | (a) bestanden, (b) 2 falsch: UA (Zeile 626) und UAA (676) |
| 29.10.2026, 22:20 UTC | **bestanden** |

Randregel: Schon der erste Kandidat im Fenster (01.10.2026) scheitert. Ein Rückgang vor den 01.10.2026 war daher nicht
nötig.

### Gegenproben (kein Kriterium)

| Zustand | Ergebnis |
| --- | --- |
| 09.11.2026, 08:31 MEZ (Abruf laut Protokoll) | **nicht bestanden**: 897 Zeilen, (b) 3 falsch (KVUE, IR, XEC). Die Liste der heutigen Mitglieder enthielt damals schon den Wechsel KVUE → OKTA. |
| 16.11.2026, 22:18 MEZ (Abruf der Probe) | nicht bestanden: 897 Zeilen, (b) 654 falsch. Die gecachten Seiten sind tabellengleich mit den Revisionen 1384572480 und 1385951946. |

Zu 653 und 654: Am 18.11. morgens stand im Nachtrag zu Befund 19 „653 von 813“. Diese Zahl verglich nur den Ticker an
der Zeilennummer. Kriterium (b) prüft den ganzen Schlüssel und erfasst damit auch die eine verschobene Zeile, an deren
neuer Stelle zufällig derselbe Ticker steht. Das ergibt 648 + 5 + 1 = 654. Beide Zahlen stimmen, sie messen
Verschiedenes.

### Die betroffenen Fälle einzeln

| Fall | Eingefrorener Stand | Stand 16.11.2026 22:18 | Bemerkung |
| --- | --- | --- | --- |
| XEC (Cimarex, CIK 1168054) | Zeile 628, 20.06.2014 bis 02.03.2020 | Zeile 629, bis 03.03.2020 | Ende um einen Tag verschoben |
| IR (Ingersoll Rand, CIK 1699150) | Zeile 773, ab 02.03.2020 | Zeile 774, ab 03.03.2020 | Gegenstück zu XEC |
| CDAY (Ceridian, CIK 1725057) | Zeile 802, 20.09.2021 bis 01.02.2024 | Zeile 803, ohne Ende | Am 16.11. fälschlich bis heute Mitglied |
| DAY (Dayforce, CIK 1725057) | Zeile 841, 01.02.2024 bis 09.02.2026 | Zeile 120, ohne Beginn, bis 09.02.2026 | Am 16.11. hätte dieselbe CIK von 2024 bis 2026 doppelt gezählt |
| KVUE (Kenvue, CIK 1944048) | Zeile 832, ab 25.08.2023, ohne Ende | Zeile 833, bis 30.10.2026 | Echter Indexwechsel, gehört nur in den Betriebsstand (Schritt 3) |
| OKTA (Okta, CIK 1660134) | nicht enthalten | Zeile 896, ab 30.10.2026 | wie KVUE |

Ob der Wechsel XEC → IR auf den 02. oder den 03.03.2020 fällt, ist mit diesem Schritt nicht entschieden. Eingefroren
ist der Stand, auf dem `kursstatus.csv` und alle bisherigen Läufe beruhen (02.03.2020). Eine Prüfung gegen die
S&P-Mitteilung wäre ein eigener Punkt.

### Umsetzung

- **Ablage:** `daten/universum/eingefroren/` (nicht in Git) enthält beide Seiten und das daraus berechnete
  `universum.parquet`. Die Dateinamen, die `revid` und die SHA-256 stehen in `config/universum_stand.yaml`.
- **Ergänzung zum Plan:** Eingefroren ist auch das berechnete Universum, nicht nur die Seiten. Sonst könnte die
  Erneuerung des SEC-Namensverzeichnisses (spätestens alle 30 Tage) den Stand still verändern.
- **`lade_universum(stand="eingefroren")`:** Das ist jetzt der Standard für Backtest, c3 und alle Werkzeuge. Jede
  Datei wird über SHA-256 geprüft; bei Abweichung oder fehlender Datei folgt `StandPasstNicht`. Der Stand wird nie
  neu berechnet.
- **`lade_universum(stand="betrieb")`:** Diesen Weg nutzen nur `universum_aktualisieren` (Tageslauf) und
  `bewertung_am`. Er läuft unverändert über den laufenden Wikipedia-Cache. Die Sperre der Fundamental-Bewertung im
  Betrieb bleibt deshalb bestehen, bis Schritt 3 gepusht ist.
- **`tools/auswertung_eq_offer.py`:** Das Werkzeug las den Universum-Cache direkt und nutzt jetzt den eingefrorenen
  Stand.
- **Tests:** `tests/daten/test_universum_stand.py`. Der bisher rote Test `test_now_2020_bis_2022_mit_echten_daten`
  besteht wieder.
