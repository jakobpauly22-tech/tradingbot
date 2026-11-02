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
- **Plausibilität des Streubesitzes (03.11.2026):** Die SEC-Rohdaten enthalten grob falsche Werte (z.B. eBay 3·10¹⁹ USD, Werte in Tausend statt USD, Nullen bei Tochtergesellschaften); 262 von 11.297 Meldungen (2,3 %). Werte außerhalb 0,5 Mrd. bis 10 Bio. USD gelten als fehlend; es zählt der jüngste plausible, zum Stichtag bekannte Wert. Nichts wird umgerechnet. Code: `abdeckung.streubesitz_am`.
- **Schwelle:** Liegt das Gewicht der nicht kaufbaren Firmen im investierbaren Universum (ohne Finanzwerte) an einem Stichtag **über 2 %**, wird das vor dem ersten Backtest mit Jakob besprochen.
- Auswertung: `tools/auswertung_abdeckung.py` → `daten/universum/auswertung_abdeckung.md`.
- **Ergebnis und Entscheidung (03.11.2026):** Von 2012-Q1 bis 2016-Q1 lag das Gewicht an 17 von 52 Stichtagen über 2 % (3,7–6,7 %), danach immer darunter. Deshalb wird der Backtest erst ab **01.04.2016** gewertet (bis 31.12.2024); 2012 bis März 2016 läuft nur als nicht gewerteter Vorlauf für Indikatoren. WRDS/CRSP als Ersatzquelle entfällt (Lizenz nur für akademische, nicht-kommerzielle Forschung).

## Fehlerschwelle der Datenwerkzeuge

Liegt der Anteil an Lade- oder Prüffehlern **über 5 %**, bricht das Werkzeug ab (Exit-Code 1, Meldung „ABBRUCH“) und schreibt keine Status- oder Ergebnisdatei. Eine abgelehnte Kursreihe ist ein reguläres Ergebnis, kein Fehler. Die Prüfung läuft ab 40 Einträgen mit. Code: `daten/fehlerschwelle.py` (festgelegt 03.11.2026).

## Gegenprobe des Index-Nachbaus

Der Nachbau des S&P 500 aus dem point-in-time-Universum (Börsenwert-gewichtet, Total Return, ohne Ausschluss von Finanzwerten) wird gegen den offiziellen S&P 500 Total Return (`^SP500TR`) geprüft, beide in USD, an gemeinsamen Handelstagen, Zeitraum 01.04.2016 bis 31.12.2024 (gewerteter Backtest, Entscheidung 03.11.2026). Erst wenn die Gegenprobe besteht, dient derselbe Nachbau ohne Finanzwerte als Benchmark „S&P 500 ohne Finanzwerte“.

**Abnahmekriterien (festgelegt 03.11.2026):**

| Kriterium | Grenze |
| --- | --- |
| Korrelation der Tagesrenditen Nachbau vs. S&P 500 Total Return | ≥ 0,99 |
| Abweichung der Jahresrenditen, je Kalenderjahr | ≤ 1 Prozentpunkt |
| Abweichung der annualisierten Rendite 01.04.2016–31.12.2024 | ≤ 0,5 Prozentpunkte |

Code: `index_nachbau.abnahme_gegenprobe` mit den Konstanten `ABNAHME_*`. Bekannte, erwartbare Abweichungsquelle: S&P gewichtet nach Streubesitz, der Nachbau nach allen ausstehenden Aktien.

### Läufe der Gegenprobe

**Lauf 1 (03.11.2026): nicht bestanden.** Korrelation 0,966, größte Jahresabweichung 12,7 Pp. (2019), annualisiert +1,95 Pp. Ursachen (mit Jakob besprochen, nicht nachjustiert):
1. Programmierfehler: Kurse erst ab Beginn des Nachbaus geladen, der Messtag des Streubesitzes liegt aber meist im Vorjahr; bis Herbst 2016 hatten kaum Firmen ein Gewicht.
2. Programmierfehler: Kalender aus allen Werktagen statt echten Handelstagen; nach US-Feiertagen (z.B. 26.12.2018, S&P 500 +5 %) blieb der Nachbau stehen.
3. Datenfehler: Garmin meldet den Streubesitz 2015, 2017 und 2018 1.000-fach zu hoch (bis 7.753 Mrd. USD), noch unter der Grenze von 10 Bio. USD; Gewicht 2019 rund 30 %.

**Korrekturen (von Jakob freigegeben):** Kurse ab dem ersten Messtag (Vorlauf ab 2011); nur echte Handelstage (`index_nachbau.handelstage`); Streubesitz gegen den Börsenwert geprüft (`index_nachbau.streubesitz_pruefen`): mit Aktienzahl muss er zwischen 30 % und 105 % von Kurs × Aktienzahl am Messtag liegen; ohne brauchbare Aktienzahl (Kurs × Zahl selbst außerhalb 0,5 Mrd. bis 10 Bio. USD, z.B. nur eine Aktiengattung gemeldet) darf die Veränderung zum letzten gültigen Wert höchstens um Faktor 3 von der Kursveränderung abweichen. Verworfenes gilt als fehlend und wird gezählt. Tests: 26.12.2018, Messtag vor Beginn, Garmin und Nvidia mit echten Werten.

**Lauf 2 (03.11.2026): bestanden.** Korrelation 0,9997; größte Jahresabweichung 0,43 Pp. (2022); annualisiert +0,08 Pp. Abdeckung der Mitglieder mit Rendite und Gewicht: Median 95 % (2016: 92 %, ab 2021: 96 %), Minimum 90 %.

**Zur Beobachtung:** 1.925 von 10.031 Streubesitzwerten verworfen (19,2 %): 1.220 ohne Kurs am Messtag (meist Messtage vor 2011), 512 außerhalb 30–105 % des Börsenwerts, 187 außerhalb des festen Bereichs, 6 beim Vorjahresvergleich. Von den 512 liegen 246 zwischen 105 % und 130 %; das sind vermutlich überwiegend echte Werte (Streubesitz und Aktienzahl haben verschiedene Stichtage, dazwischen Rückkäufe und Kursbewegungen). Die Grenze bleibt unverändert, solange Jakob nicht anders entscheidet.

**Obergrenze 130 % (Entscheidung Jakob 03.11.2026, vorher 105 %).** Begründung: Der Streubesitz wird zum Ende des zweiten Quartals gemessen, die Aktienzahl zum Datum des Deckblatts (meist sechs bis acht Monate später). Dazwischen liegen Aktienrückkäufe, Kapitalerhöhungen und Kursbewegungen; ein Streubesitz knapp über dem Börsenwert aus Kurs am Messtag × späterer Aktienzahl ist deshalb kein Datenfehler. Code: `index_nachbau.STREUBESITZ_ANTEIL_MAX`.

**Lauf 3 (03.11.2026): bestanden**, mit Verweis auf Lauf 2 (`daten/universum/gegenprobe_index_lauf2.md`). Korrelation 0,9997; größte Jahresabweichung 0,39 Pp. (2022); annualisiert +0,06 Pp. Streubesitz: 1.671 von 10.031 Werten verworfen (16,7 %), davon 258 außerhalb 30–130 % des Börsenwerts (vorher 512). Abdeckung je Jahr (Median) 92 % (2016) bis 97 % (ab 2021).

### Kursabdeckung neu gerechnet (03.11.2026, geprüfter Streubesitz)

Firmen mit gültigen Kursen: Streubesitz gegen den Börsenwert geprüft (30–130 %). Firmen ohne gültige Kurse (die nicht kaufbaren) sind nicht prüfbar und nutzen nur den festen Bereich, sonst verschwände genau ihr Gewicht. Ergebnis: Über 2 % liegen jetzt 19 statt 17 Stichtage, darunter **01.04.2016 (2,68 %) und 01.07.2016 (2,28 %)** im bisher gewerteten Zeitraum; ab 03.10.2016 immer unter 2 %. Die frühere Auswertung lag zu niedrig, weil unplausible Streubesitzwerte innerhalb des festen Bereichs (z.B. Garmin 5.634 Mrd. USD) den Nenner aufblähten. Eine Vergleichsrechnung mit Rohwerten als Ersatz für fehlende geprüfte Werte ändert die Zahlen kaum (01.04.2016: 2,74 %). **Entscheidung (Jakob 03.11.2026): Regel statt festem Datum.** Der gewertete Backtest beginnt am ersten Rebalancing-Stichtag, ab dem alle folgenden Stichtage unter 2 % nicht kaufbarem Gewicht im investierbaren Universum liegen. Heute ergibt das den **01.10.2016** (Stichtag 03.10.2016). Code: `abdeckung.gewerteter_beginn`; das Auswertungswerkzeug meldet laut, wenn die Regel bei neuen Daten ein anderes Datum ergibt als `config/fundamental.yaml` (`backtest.gewertet_ab`). Die Gegenprobe gilt für denselben Zeitraum (01.10.2016–31.12.2024), Kriterien unverändert.

**Lauf 4 (03.11.2026): bestanden**, Zeitraum nach der Regel 01.10.2016–31.12.2024 (erster Handelstag 03.10.2016), mit Verweis auf Lauf 3 (`daten/universum/gegenprobe_index_lauf3.md`); Nachbau, Daten und Kriterien unverändert. Korrelation 0,9997; größte Jahresabweichung 0,39 Pp. (2022); annualisiert +0,08 Pp.; Abdeckung Median 96,4 %, Minimum 92,8 %. **Damit ist die Datenbasis für den gewerteten Zeitraum abgenommen.**
