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

## 7. Varianten

Jeder Lauf kommt in `daten/regime/varianten.csv` (V1, D1–D4, Langtest), auch Diagnosen und Wiederholungen nach
Datenkorrekturen. Nach einem Lauf werden weder Signale noch Schwellen noch Kriterien geändert.

## 8. Sitzungen

| Sitzung | Inhalt | Stand |
| --- | --- | --- |
| 1 | Festlegungen, neue Reihen, ALFRED-Abdeckung, Tresor- und Erstmeldungstests, XEON-Prüfung | 15.11.2026 |
| 2 | Signale, Monatslogik mit Haltepflicht, Tests | offen |
| 3 | Backtest des Buchs, Vergleichsportfolios, Bericht | offen |
| 4 | US-Langtest 1995–2011 | offen |
| 5 | Schattenbuch im Tageslauf | offen |
