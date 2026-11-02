# Datenqualität: Regeln und Abnahmekriterien

Alle Regeln hat Jakob festgelegt. Sie gelten vor dem ersten Backtest der Fundamental-Engine und werden nicht nachträglich angepasst, um ein Ergebnis zu verbessern. **Wird ein Kriterium verfehlt, werden zuerst die Ursachen gesucht und mit Jakob besprochen. Es wird nicht nachjustiert.**

## Universum (S&P 500, point-in-time)

| Regel | Festgelegt | Code |
| --- | --- | --- |
| Historische Zusammensetzung je Stichtag statt heutiger Mitglieder | 02.11.2026 | `daten/universum.py` |
| Zusammensetzung gilt erst ab 01.01.2012 als geprüft; frühere Stichtage nur mit ausdrücklichem Schalter | 03.11.2026 | `universum.GEPRUEFT_AB` |
| Manuelle Korrekturen nur mit Quelle; CIK-Korrekturen werden bei jedem Lauf gegen die SEC-Namen geprüft | 02.11.2026 | `config/universum_korrekturen.yaml` |
| Finanzwerte (SIC 6000–6999 inklusive REITs) fallen im ersten Lauf aus dem Universum; SIC point-in-time aus der jeweiligen SEC-Einreichung | 02.11.2026 | `universum.sic_historie` |

## Kursreihen

| Regel | Festgelegt | Code |
| --- | --- | --- |
| Eine Kursreihe zählt nur, wenn sie den Mitgliedszeitraum ab 2012 abdeckt (erster Kurs höchstens 10 Tage nach Beginn, letzter höchstens 10 Tage vor dem Indexabgang, mindestens 90 % der Werktage) **und** der Firmenname aus den Metadaten passt. Sonst keine Kurse, Rückfall-Regel, Markierung. Gilt für Tiingo und yfinance. | 03.11.2026 | `kursquellen.pruefe_kursreihe` |
| Bekannte Fälle wiederverwendeter Ticker als Test: CA, CEG, BEAM, APC, POM, BRCM, DISCA | 03.11.2026 | `tests/daten/test_kursquellen.py` |
| Rückfall-Regel bei Delisting: Übernahme oder Fusion → letzter Kurs; Pleite, Performance oder unbekannt → letzter Kurs minus 30 % (Shumway 1997); markiert und gezählt | 02.11.2026 | `daten/delisting.py` |

## Kursabdeckung je Stichtag

- **Nicht kaufbar:** Eine Firma ohne gültige Kursreihe am Rebalancing-Stichtag (für keine ihrer Aktiengattungen) kann nicht ins Portfolio.
- **Rückfall-Regel:** Eine gehaltene Aktie, die später ihre Kurse verliert, wird nach der Delisting-Regel geschlossen.
- **Gewicht:** Streubesitzwert laut SEC-Deckblatt (`dei:EntityPublicFloat`, point-in-time), je Firma, nicht je Aktiengattung.
- **Schwelle:** Liegt das Gewicht der nicht kaufbaren Firmen im investierbaren Universum (ohne Finanzwerte) an einem Stichtag **über 2 %**, wird das vor dem ersten Backtest mit Jakob besprochen.
- Auswertung: `tools/auswertung_abdeckung.py` → `daten/universum/auswertung_abdeckung.md`.

## Fehlerschwelle der Datenwerkzeuge

Liegt der Anteil an Lade- oder Prüffehlern **über 5 %**, bricht das Werkzeug ab (Exit-Code 1, Meldung „ABBRUCH“) und schreibt keine Status- oder Ergebnisdatei. Eine abgelehnte Kursreihe ist ein reguläres Ergebnis, kein Fehler. Die Prüfung läuft ab 40 Einträgen mit. Code: `daten/fehlerschwelle.py` (festgelegt 03.11.2026).

## Gegenprobe des Index-Nachbaus

Der Nachbau des S&P 500 aus dem point-in-time-Universum (Börsenwert-gewichtet, Total Return, ohne Ausschluss von Finanzwerten) wird gegen den offiziellen S&P 500 Total Return (`^SP500TR`) geprüft, beide in USD, an gemeinsamen Handelstagen, Zeitraum 2012 bis 2024. Erst wenn die Gegenprobe besteht, dient derselbe Nachbau ohne Finanzwerte als Benchmark „S&P 500 ohne Finanzwerte“.

**Abnahmekriterien (festgelegt 03.11.2026):**

| Kriterium | Grenze |
| --- | --- |
| Korrelation der Tagesrenditen Nachbau vs. S&P 500 Total Return | ≥ 0,99 |
| Abweichung der Jahresrenditen, je Kalenderjahr | ≤ 1 Prozentpunkt |
| Abweichung der annualisierten Rendite 2012–2024 | ≤ 0,5 Prozentpunkte |

Code: `index_nachbau.abnahme_gegenprobe` mit den Konstanten `ABNAHME_*`. Bekannte, erwartbare Abweichungsquelle: S&P gewichtet nach Streubesitz, der Nachbau nach allen ausstehenden Aktien.
