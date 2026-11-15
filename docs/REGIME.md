# Makro-/Regime-Engine

Stand der Festlegungen: 15.11.2026 (Jakob). **Alles in den Abschnitten 1–7 steht vor dem ersten Lauf fest und wird nach
einem Lauf nicht geändert.** Eine Verfehlung bleibt im Bericht stehen und wird begründet. Der Tresor (Daten ab 01.01.2025)
bleibt zu. Probeläufe zählen nie.

## 1. Entscheidung, die das Signal treibt

Neues Schattenbuch **„regime“** (10.000 €, Skalierungsbuch). Die bestehenden Bücher bleiben unverändert.

- **Zweistufig:** 100 % SPYI.DE („Risiko an“) oder 0 % SPYI.DE („Risiko aus“).
- **Defensive Anlage:** XEON.DE (Xtrackers II EUR Overnight Rate Swap), falls die Datenprüfung aus Abschnitt 6 besteht;
  sonst Kasse zu 0 %.
- **Takt:** Bewertung am letzten Xetra-Handelstag des Monats (Kalender von SPYI.DE) mit Schlusskursen, Order am nächsten
  Handelstag nach dem bestehenden Kosten- und Steuermodell des Backtests.
- **Haltepflicht:** Nach einem Wechsel am Monatsende m ist der nächste Wechsel frühestens am Monatsende m+2 möglich.
- Nicht Teil dieses Bausteins: Gewichte im Scoring verschieben.

## 2. Signale (Schwellen vorab, nicht optimiert)

| Signal | Reihe | „aus“, wenn |
| --- | --- | --- |
| **Trend** | **gehaltenes Instrument SPYI.DE in EUR** (nicht S&P 500 in USD; Jakob 15.11.2026), Monatsschlusskurse | Monatsschluss < Durchschnitt der letzten 10 Monatsschlüsse einschließlich des aktuellen (Faber 2007) |
| **Zinskurve** | T10Y3M (FRED) | Durchschnitt der Tageswerte des laufenden Monats < 0 (Estrella/Mishkin 1998) |
| **Kreditaufschlag** | BAA10Y (FRED, Moody's Baa minus 10 Jahre) | Monatsdurchschnitt > Durchschnitt der letzten 10 Monatsdurchschnitte einschließlich des aktuellen (gleiche Bauart wie der Trend, kein eigener Parameter) |
| **Arbeitsmarkt** | UNRATE (ALFRED) | Sahm-Regel in Echtzeit: 3-Monats-Mittel − Minimum der 3-Monats-Mittel der vorangegangenen 12 Monate ≥ 0,50 Pp. |

Die ICE-BofA-High-Yield-Reihen scheiden aus: FRED führt sie nur noch ab 14.11.2023 (geprüft 15.11.2026).

**Hauptvariante V1 (einzige gewertete Variante):** Risiko aus genau dann, wenn der **Trend „aus“ ist und zugleich mindestens
eines** der drei Makrosignale (Zinskurve, Kreditaufschlag, Arbeitsmarkt) „aus“ ist; sonst Risiko an. Dazu die Haltepflicht.

**Diagnosen (gezählt, nie gewertet):** D1 nur Trend, D2 nur Zinskurve, D3 nur Kreditaufschlag, D4 nur Arbeitsmarkt; jeweils
Risiko aus, wenn das Signal „aus“ ist, gleiche Haltepflicht. VIX nur als Angabe im Bericht.

## 3. Point-in-time

- **Revidierte Reihen (UNRATE):** nur ALFRED-Stände (`daten/makro.py`, `stand_am`). Ein Wert zählt ab dem **Handelstag
  nach** `realtime_start`: am Bewertungstag t gilt der Stand mit `gueltig_ab` ≤ t − 1 Tag.
- **Marktreihen (T10Y3M, BAA10Y, DGS3MO):** ALFRED führt Stände erst ab 27.01.2014 (DGS3MO ab 28.06.2005), die Historie
  reicht bis 1982/1986. Sie gelten als nicht revidiert: Wert des Tages d ab d + 1 Tag. Prüfung am 15.11.2026: Stände vom
  27.01.2014 und 28.06.2019 gegen heute – T10Y3M und BAA10Y 0 abweichende Werte; DGS3MO 1 Wert um 0,1 Pp. abweichend und
  rund 80 später ergänzte Tage.
- **Erster ALFRED-Stand:** UNRATE ab 15.03.1960. Vor dem ersten Stand einer revidierten Reihe gibt es keine Werte; ein Test
  schlägt fehl, wenn der erste Stand nach dem Beginn des Vorlaufs liegt.
- **Tresor:** Ein Wissensstand nach der Datengrenze wird nie geliefert, auch nicht für Beobachtungen aus 2024, die erst
  2025 gemeldet oder revidiert wurden.
- **Eingefrorener Datenstand:** Für jeden gewerteten Lauf liegen die verwendeten Makrotabellen mit Prüfsumme im Laufordner.

## 4. Zeitraum und Erfolgskriterien (Entwicklungsdaten)

- **Gewerteter Zeitraum:** 01.11.2012 bis 31.12.2024 (SPYI.DE-Historie ab 01.01.2012, erster 10-Monats-Durchschnitt am
  31.10.2012). Hälften: 01.11.2012–30.11.2018 und 01.12.2018–31.12.2024 (je 73 Monate).
- **Rechnung:** nach Kosten und Steuern nach den bestehenden Backtest-Regeln, für alle Vergleichsportfolios gleich; Sharpe
  wie im Backtest-Bericht.
- **Vergleichsportfolios:** (i) Kaufen und Halten SPYI.DE; (ii) statische Mischung SPYI.DE/defensive Anlage mit **demselben
  durchschnittlichen Aktienanteil** wie V1 (Anteil der Tage mit Risiko an, je Hälfte getrennt bestimmt; ein durchgehender
  Lauf, Zielgewicht wechselt an der Hälftengrenze), quartalsweise auf das Zielgewicht zurückgestellt.
- **Kriterien, jeweils in beiden Hälften, nur für V1:**
  - a) Sharpe ≥ Kaufen und Halten.
  - b) Sharpe ≥ statische Mischung mit gleichem Durchschnitts-Aktienanteil.
  - c) Maximaler Drawdown mindestens 25 % kleiner als bei Kaufen und Halten: |MDD_V1| ≤ 0,75 · |MDD_KuH| (relativ statt
    5 Pp., weil die Hälften sehr unterschiedliche Drawdowns haben; Jakob 15.11.2026).
- **Nur zum Vergleich:** Crossover-Schatten, Diagnosen D1–D4, Rendite p. a., Zahl der Wechsel.
- **Vorbehalt:** Der Zeitraum enthält wenige Abschwünge (2018, 2020, 2022); die Beweiskraft ist gering. Deshalb Abschnitt 5.

## 5. US-Langtest 1995–2011 (zählt)

V1 muss zusätzlich **Kriterium b** im Langtest erfüllen (Jakob 15.11.2026), über den ganzen Zeitraum 01.01.1995–31.12.2011.

- Instrument: ^SP500TR in USD (Trend auf diesem Instrument); defensive Anlage: 3-Monats-Schatzwechsel (DGS3MO, Tageszins
  = letzter bekannter Wert / 360 je Kalendertag). Signale, Schwellen, Takt und Haltepflicht wie Abschnitt 1–3, Kalender des
  Index.
- Vereinfachte Kosten: 0,1 % des gehandelten Werts je Wechsel; keine Steuern, keine Währung. Sharpe mit DGS3MO als
  risikofreiem Zins. Statische Mischung: monatlich zurückgestellt, gleiche Kostenregel.
- Fehlen ALFRED-Stände dafür: dokumentieren und ohne Langtest werten. Stand 15.11.2026: UNRATE-Stände ab 1960 vorhanden,
  Marktreihen siehe Abschnitt 3 – der Langtest ist nach heutigem Stand möglich.

## 6. Datenprüfung XEON.DE (Kriterien vor dem Laden festgelegt)

XEON.DE besteht, wenn für 02.01.2012–31.12.2024 alle drei Punkte gelten; sonst Kasse zu 0 %:

1. Keine Lücke von mehr als 5 Handelstagen gegenüber dem Kalender von SPYI.DE; erster Kurs spätestens am 02.01.2012.
2. Keine Tagesänderung des Schlusskurses über ±0,25 %.
3. Jede Kalenderjahresrendite liegt höchstens 0,5 Pp. vom Jahresdurchschnitt des EZB-Einlagesatzes (ECBDFR) entfernt.

**Ergebnis 15.11.2026 (`tools/pruefe_regime_daten.py`, Bericht `docs/berichte/2026-11-15_regime_daten.md`): nicht
bestanden.** Kriterium 1 (keine Lücke) und 3 (Abstand zum Einlagesatz höchstens 0,12 Pp.) bestanden; Kriterium 2 verfehlt
durch drei Tage: 16.03.2020 +0,53 %, 17.03.2020 −0,47 %, 21.04.2020 −0,31 %. **Damit ist die defensive Anlage Kasse zu
0 %** (Jakob 15.11.2026: „sonst Kasse zu 0 %“). Die Kriterien werden nicht angepasst. Folge für Kriterium b: Die statische
Mischung hält ihren defensiven Teil ebenfalls als Kasse zu 0 %.

**Bekannte Verzerrung (Jakob 15.11.2026, gehört in jeden Bericht):** In den Negativzins-Jahren 2015–2022 ist Kasse zu 0 %
in „Risiko aus“-Phasen günstiger als die Realität (Geldmarkt rund −0,4 % p. a.). Das begünstigt V1 gegenüber Kaufen und
Halten leicht; gegenüber der statischen Mischung wirkt es auf beide Seiten.

## 6a. Ergebnis der Abdeckungsprüfung (15.11.2026)

UNRATE: erster ALFRED-Stand 15.03.1960. T10Y3M ab 1982, BAA10Y ab 1986, DGS3MO ab 1981 (Marktreihen, nicht revidiert).
^SP500TR ab 04.01.1988. **Der Langtest 1995–2011 ist möglich.** Neue Reihen in `config/daten.yaml`: T10Y3M, BAA10Y.
Tresor-Lücke geschlossen: `makro_am_stichtag` lieferte für einen Stichtag nach der Grenze den 2025 revidierten Stand von
Beobachtungen aus 2024; jetzt höchstens der Wissensstand der Grenze (Test in `tests/daten/test_makro.py`). Bisher nutzte
kein Backtest einen solchen Stichtag.

## 7. Varianten

Jeder Lauf kommt in `daten/regime/varianten.csv` (V1, D1–D4, Langtest), auch Diagnosen und Wiederholungen nach
Datenkorrekturen. Nach einem Lauf werden weder Signale noch Schwellen noch Kriterien geändert.

## 7a. Bestätigung und Präzisierungen vor Sitzung 2 (15.11.2026)

Jakob hat am 15.11.2026 bestätigt: Schwellen für Kreditaufschlag und Zinskurve (Abschnitt 2), Zeitraum und Hälftengrenze,
statische Mischung je Hälfte (Abschnitt 4), Regeln des Langtests (Abschnitt 5), Kasse zu 0 % auch in der Mischung.

Präzisierungen der Rechnung (vor jedem Lauf, Code in `engines/regime/signale.py`):

- **Monatsende:** letzter Handelstag des Instruments in einem Kalendermonat; gewertet werden nur abgeschlossene Monate.
- **Marktreihen am Bewertungstag t:** Tageswerte bis t − 1 (Wert des Tages d gilt ab d + 1). „Laufender Monat“ sind die
  bis dahin bekannten Tageswerte des Monats von t; frühere Monate zählen ganz.
- **Sahm-Regel:** alle Monatswerte aus dem ALFRED-Stand von t − 1 Tag (auch die zurückliegenden, wie sie damals bekannt
  waren). 3-Monats-Mittel des jüngsten bekannten Monats minus Minimum der 3-Monats-Mittel der 12 Monate davor (ohne den
  jüngsten); „aus“ bei ≥ 0,50 Pp.
- **Fehlende Historie:** Hat ein Signal am Bewertungstag zu wenig Historie, gibt es für diesen Monat keinen Zustand (kein
  stilles „an“).
- **Erste Bewertung:** setzt den Zustand frei und zählt als Wechsel für die Haltepflicht (nächster Wechsel frühestens
  zwei Monatsenden später).
- **Sitzung 2 rechnet keinen Verlauf von V1 über den gewerteten Zeitraum aus.** Tests an echten Daten prüfen nur einzelne
  bekannte Ankerpunkte der Einzelsignale (z. B. Sahm-Regel im April 2020).

Jakob hat die Präzisierungen (erste Bewertung, Sahm-Regel, Stand der Marktreihen) am 15.11.2026 bestätigt.

## 7b. Regeln für die gewerteten Läufe (Jakob 15.11.2026)

- Vor dem ersten gewerteten Lauf werden alle Festlegungen dieser Datei in einem eigenen Commit eingefroren; der Bericht
  nennt den Commit-Hash. Nach dem Lauf werden weder Schwellen noch Signale geändert.
- Der Bericht von Sitzung 3 enthält **kein Gesamturteil**, nur die Ergebnisse je Hälfte. Das Urteil fällt erst nach dem
  US-Langtest (Sitzung 4), weil er mitzählt.

## 7c. Präzisierungen für den Backtest des Buchs (15.11.2026, vor dem ersten Lauf)

Code: `engines/regime/buch.py`, `tools/backtest_regime.py`. Bisher wurde kein Verlauf und kein Backtest von V1 auf echten
Daten gerechnet.

1. **Kapital und Ausführung:** 10.000 € je Portfolio, ganze Stücke zu echten Anteilspreisen (Split von SPYI.DE 2026
   zurückgerechnet), Kosten und Gebührenregel nach `config/backtest.yaml` (Xetra-Plan, Spread, Slippage).
2. **Steuern:** V1, Kaufen und Halten, Mischung und jede Diagnose bilden je eine eigene Steuergruppe **ohne
   Pauschbetrag** (Regel der Schattenbücher), sonst heutiges Recht wie im Backtest (Vorabpauschale, Teilfreistellung 30 %).
3. **Wertreihe der Kriterien:** Depotwert **nach laufend gezahlten Steuern** (`wert_nach_steuern`). Die latente Steuer auf
   nicht realisierte Gewinne ist darin nicht abgezogen; der Wert nach fiktivem Verkauf am Ende steht nur zur Einordnung im
   Bericht.
4. **Beginn:** erste Bewertung am 31.10.2012 mit dem Startkapital in Kasse, Orders am 01.11.2012. Kaufen und Halten und
   die Mischung kaufen am selben Tag. Liefert die Rechnung eine andere erste Bewertung, bricht das Werkzeug laut ab.
5. **Kennzahlen je Hälfte:** Wertreihe der Hälfte mit dem letzten Wert davor als Basis; Sharpe wie
   `kennzahlen/performance.kennzahlen` mit dem EZB-Einlagesatz als risikofreiem Zins; Vergleiche mit Rundungstoleranz
   1e-9. Ist ein Sharpe nicht bestimmbar (keine Schwankung), gilt das betroffene Kriterium als nicht erfüllt.
6. **Durchschnitts-Aktienanteil:** Anteil der Handelstage der Hälfte, an denen V1 nach seinem Zustand Aktien halten soll
   (Zustand des letzten Monatsendes vor dem Tag). Die Mischung bekommt das Gewicht der zweiten Hälfte mit Signal am
   letzten Handelstag der ersten Hälfte und wird sonst am ersten Handelstag jedes Quartals zurückgestellt.
7. **Gescheiterte Orders** (kein Handel am Ausführungstag) werden am nächsten Tag wiederholt.
8. **Crossover-Schatten:** wird nicht neu gerechnet (anderes Universum und Kapital); Vergleich über die Diagnose D1.
9. **Datenhinweise SPYI.DE (15.11.2026):** bis 2016 dünn gehandelt (Tage mit Eröffnung = Hoch = Tief = Schluss: 2012 176,
   2013 147, 2014 120, 2015 101, 2016 86; insgesamt 498 Tage ohne Umsatz), ein Befund am 13.06.2012 (Hoch unter Tief, vor
   dem gewerteten Zeitraum). Die Reihe wird unverändert genutzt; beides steht im Bericht.
10. **Festlegungs-Commit:** Das Werkzeug verlangt den Commit und bricht ab, wenn diese Datei oder der Code unter
    `src/tradingbot/engines/regime` seitdem geändert wurde.

## 8. Sitzungen

| Sitzung | Inhalt | Stand |
| --- | --- | --- |
| 1 | Festlegungen, neue Reihen, ALFRED-Abdeckung, Tresor- und Erstmeldungstests, XEON-Prüfung | 15.11.2026 |
| 2 | Signale, Monatslogik mit Haltepflicht, Tests | 15.11.2026 |
| 3 | Backtest des Buchs, Vergleichsportfolios, Bericht | offen |
| 4 | US-Langtest 1995–2011 | offen |
| 5 | Schattenbuch im Tageslauf | offen |
