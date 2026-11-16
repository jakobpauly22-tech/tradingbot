# Korrektur der Simulation: Steuer aus der Kasse (Befund 3 der unabhängigen Prüfung)

Festgehalten am 16.11.2026 um 09:27, **vor jeder Änderung am Code und vor jeder Nachrechnung**. Grundlage:
`docs/berichte/2026-11-16_unabhaengige_pruefung.md`, Befund 3. Entscheidungen von Jakob am 16.11.2026.

## Befund

Die Jahressteuer wird bisher erst nach dem Lauf berechnet und nur von der Reihe `wert_nach_steuern` abgezogen
(`src/tradingbot/backtest/simulation.py:503-540`, Stand 662f9f4). Die Kasse im Lauf bleibt unberührt. Ein Buch, das
Gewinne realisiert und voll reinvestiert, ist dadurch zu mehr als 100 % seines Nachsteuerwerts investiert (V1 Anfang
2024 rund 111 %); Schwankung und Drawdown der gewerteten Reihe sind verstärkt.

## Korrekturregel

Die Regel vom 01.11.2026 bleibt: Die Steuer fließt am letzten Handelstag des Jahres als eigener Abfluss ab, **ohne
Zwangsverkauf**. Neu ist nur, dass der Abfluss die Kasse im Lauf trifft:

1. **Abfluss aus der Kasse:** Am letzten Handelstag des Jahres wird die Jahressteuer der Steuergruppe berechnet, den
   Teilportfolios wie bisher nach ihrem positiven steuerpflichtigen Beitrag zugeordnet und aus der EUR-Kasse gezahlt.
2. **Fremdwährungskasse:** Reicht die EUR-Kasse nicht und liegt Fremdwährungskasse vor, wird für die Steuer
   zurückgetauscht, mit Tauschkosten (Auszahlung im Sinn der Regel vom 02.11.2026).
3. **Kasse reicht nicht:** Der Rest ist eine zinslose Steuerschuld. Sie löst nie einen Verkauf aus. Spätere Zuflüsse
   (Verkaufserlöse, Dividenden, Einzahlungen) tilgen sie zuerst.
4. **Käufe bei offener Schuld werden anteilig kleiner:** Verkäufe rechnen gegen den Depotwert ohne Abzug der Schuld,
   Käufe gegen den Depotwert minus Schuld.
   **Präzisierung von Jakobs Entscheidung 1 (16.11.2026, festgehalten 09:50 vor der Nachrechnung):** Streng anteilig.
   Reichen die Käufe eines Ausführungstags mit offener Steuerschuld nicht in die Kasse nach Tilgung der Schuld, werden
   alle Käufe dieses Tags mit demselben Faktor skaliert (bei ganzen Stücken abgerundet, der Rest bleibt Kasse), statt
   die Lücke nach der Regel „größte Lücke zuerst“ bei den letzten Käufen zu kürzen. Anlass: Bei einer Teilumschichtung
   reicht der Abzug der Schuld vom Zielwert allein nicht. Ohne offene Steuerschuld bleibt die bisherige Regel.
5. **Wertreihen:** „Nach Steuern“ = Kasse + Positionen − offene Steuerschuld (die gewertete Reihe). „Vor Steuern“ =
   Wert nach Steuern + festgesetzte Steuern; in der zeitgewichteten Rendite vor Steuern zählen Steuerzahlungen als
   Auszahlung.

Bekannte Vereinfachungen: Die Steuerschuld ist zinslos. Der Abfluss liegt am Jahresende statt beim Steuerbescheid. Der
Pfad „vor Steuern“ ist kein eigener steuerfreier Lauf mehr; er hält wegen der gezahlten Steuer etwas weniger Positionen
als ein Lauf ganz ohne Steuern.

## Zusage

**Die Korrektur wird unabhängig vom Ergebnis übernommen.** Das umfasst ausdrücklich ihre Wirkung auf Zwillinge,
Benchmarks und Vergleichsportfolios (Kaufen und Halten, statische Mischung), auf alle bisherigen Backtests und auf den
Neulauf c3.

- Kriterien, Grenzen, Signale, Parameter und Gewichte bleiben unverändert. Nach der Nachrechnung wird nichts
  nachjustiert.
- Urteile werden nicht geändert, falls sie bestehen bleiben. Kippt ein Kriterium in die eine oder andere Richtung,
  steht das im Bericht und wird mit Jakob besprochen.
- Der bisherige Rechenweg bleibt nur als Vergleichsmodus erhalten (`steuern.zahlung: jahresende_nur_wertreihe`) und
  wird in jedem Bericht markiert; gewertet wird nur noch mit `jahresende_aus_kasse`.

## Nachrechnung (Umfang, festgelegt vor dem Lauf)

Jeweils alter und neuer Steuermodus auf demselben Code- und Datenstand, Entwicklungsdaten bis 31.12.2024, Tresor zu.

| Lauf | Verglichen wird |
| --- | --- |
| Regime (V1, D1–D4, Kaufen und Halten, Mischung) | Kriterien a–c je Hälfte, Sharpe, maximaler Drawdown, Endwerte |
| Phase 2 Gesamtdepot | Kriterien 2 bis 4 und Prüfung 1 |
| Technik (fünf Varianten und Buy & Hold) | Sharpe und maximaler Drawdown je Hälfte |

- **Regime:** Die Nachrechnung wird als Lauf mit dem Anlass „Korrektur der Simulation: Steuer aus der Kasse
  (Befund 3)“ in `daten/regime/varianten.csv` eingetragen, nicht als neue Variante. Der neue Festlegungs-Commit betrifft
  nur die Simulation; Kriterien und Signale bleiben unverändert (`engines/regime/signale.py` wird nicht angefasst).
- **Fundamental A:** keine Nachrechnung vor c3. In c3 (ab 01.12.2026) laufen beide Steuermodi nebeneinander.
- Der Betrieb (Paper Trading) ist nicht betroffen; die Simulation läuft dort nicht.

## Umsetzung

- Commit ca95bc0: Steuer aus der Kasse, Vergleichsmodus `jahresende_nur_wertreihe`, TWR vor Steuern mit Steuer als
  Auszahlung.
- Commit f96ee50: Käufe bei offener Steuerschuld streng anteilig (Präzisierung oben).
- Commit d066bf6: Schalter `--steuermodus` in `tools/backtest_regime.py`, `tools/backtest_phase2.py` und
  `tools/backtest_technik.py`; Prüfung gegen frühere Ablagen (`--vergleich-ablage`); Festlegung der Regime-Nachrechnung
  in `docs/REGIME.md`, Abschnitt 7f.

## Ergebnis der Nachrechnung (16.11.2026, Entwicklungsdaten bis 31.12.2024, Tresor zu)

### Prüfung vorab: Der alte Steuerweg trifft die Ablagen vom 15.11.2026

`tools/backtest_regime.py --festlegung d066bf6 --steuermodus jahresende_nur_wertreihe --vergleich-ablage …` gegen alle
sechs Ablagen `daten/backtests/20261115T1428*_regime_*`:

- Geprüft: 12 Reihen (V1, D1–D4, Mischung, je mit Zwilling) an 3.085 Tagen, dazu `kriterien.csv`.
- Ergebnis: keine Abweichung. Werte (`wert`, `cash`, `steuern_kumuliert`, `wert_nach_steuern`) mit relativer Toleranz
  1e-6, Trades nach Datum, Richtung und Stückzahl sowie die Kriterien a–c stimmen genau.
- Der Datenstand von SPYI.DE ist unverändert (Cache vom 13.11.2026, wie in `meta.json` der Ablage).

Der Unterschied unten kommt also allein aus der Korrektur.

### Regime (gewerteter Lauf mit Anlass, Festlegung d066bf6)

Lauf `daten/backtests/20261116T100449_regime_V1/` und folgende, eingetragen in `daten/regime/varianten.csv` mit dem
Anlass „Korrektur der Simulation: Steuer aus der Kasse (Befund 3)“, keine neue Variante. Bericht
`docs/berichte/2026-11-16_regime_backtest.md`.

| Hälfte | Kennzahl | alter Steuerweg (15.11.) | Steuer aus der Kasse |
| --- | --- | --- | --- |
| 1 | Sharpe V1 / Kaufen und Halten / Mischung | 0,446 / 0,653 / 0,650 | 0,446 / 0,653 / 0,653 |
| 1 | max. Drawdown V1 / Kaufen und Halten | −33,29 % / −24,12 % | −33,29 % / −24,12 % |
| 1 | Kriterien a / b / c | nein / nein / nein | nein / nein / nein |
| 2 | Sharpe V1 / Kaufen und Halten / Mischung | 0,643 / 0,691 / 0,641 | 0,629 / 0,691 / 0,632 |
| 2 | max. Drawdown V1 / Kaufen und Halten | −18,18 % / −34,71 % | −17,15 % / −34,71 % |
| 2 | Kriterien a / b / c | nein / **ja** / ja | nein / **nein** / ja |

- **Kriterium b in Hälfte 2 kippt von „ja“ auf „nein“** (von Jakob am 16.11.2026 zur Kenntnis genommen):

  | Hälfte 2, Sharpe | alter Steuerweg | Steuer aus der Kasse |
  | --- | --- | --- |
  | V1 | 0,643 | 0,629 |
  | Mischung | 0,641 | 0,632 |
  | Kriterium b (V1 ≥ Mischung) | ja | nein |

  Beide Reihen verlieren an Sharpe, V1 mehr.
- **Urteil:** Kriterium a ist in beiden Hälften verfehlt; das Urteil „V1 nicht bestanden“ (`docs/REGIME.md`, 7e)
  bleibt deshalb unverändert. In Hälfte 1 sind alle drei Kriterien verfehlt.
- **Investitionsgrad V1 am 02.01.2024:** vorher 111,6 % des Nachsteuerwerts, jetzt 99,1 %. Das war der Kern von
  Befund 3.
- **Steuerschuld V1:**
  - Ende 2015 bleiben 781 € offen, weil V1 am 01.12.2015 mit dem vollen Erlös gekauft hatte. Der Verkauf am 01.02.2016
    tilgt sie, der Rückkauf am 02.05.2016 ist entsprechend kleiner (137 statt 146 Stück).
  - Ende 2020 und 2021 bleiben 84 € bzw. 85 € offen.
  - Ab 2016 hält V1 je Kauf 9 bis 17 Stück weniger als im alten Steuerweg.
- **Endwerte:**
  - V1 nach Steuern 24.412 € (vorher 25.744 €), nach fiktivem Verkauf 23.559 € (24.755 €).
  - Kaufen und Halten unverändert 38.921 € bzw. 33.720 €. Die Steuer auf die Vorabpauschalen (228 €) bleibt dort als
    Schuld offen, weil kein Zufluss sie tilgt; die Wertreihe nach Steuern ist deshalb gleich.
- **Diagnosen D1–D4:** D2 und D4 tragen längere Zeit eine Steuerschuld (höchstens 1.840 € bzw. 995 €, 930 bzw. 1.119
  Handelstage), weil sie nach einem Gewinnverkauf lange voll investiert bleiben. Sie werden nie gewertet.
- **Mischung:** 29 statt 28 Trades und eine zusätzlich verworfene Order am 03.01.2019 (1-%-Regel, Kauf von 1 Stück).
  Steuerschuld hat sie nie, sie hält immer Kasse.

### Phase 2 Gesamtdepot

Beide Steuermodi liefern identische Zahlen (`docs/berichte/2026-11-16_phase2_gesamtdepot.md` und
`…_alter_steuerweg.md`).

- Das Realbuch zahlt im Zeitraum keine laufende Steuer: Es verkauft nie, und die Vorabpauschalen bleiben unter dem
  Pauschbetrag. Die Korrektur greift deshalb nicht.
- Kriterien unverändert: 1, 3, 4, 5 bestanden; Kriterium 2 verfehlt mit −0,51 Pp. p. a., wie die dokumentierte
  Ausnahme in `docs/PHASE2.md`.

### Technik (beide Steuermodi, gerechnet nach Jakobs Datenfreigabe)

**Datensperre zuerst.** `tools/backtest_technik.py` brach im ersten Versuch in beiden Modi vor der Simulation mit der
eigenen Datensperre ab (Exit 2), unabhängig von Befund 3:

- **Befund:** IUSM.DE, 13.06.2012: Eröffnung = Hoch = Tief = 160,23, Schluss 158,98 (außerhalb der Spanne).
- **Ursache:** IUSM.DE ersetzt seit dem 04.11.2026 SXRM im Satellite-Universum (Commit 9e50ae5, Betrieb). Der
  gewertete Technik-Backtest wurde seitdem nicht neu gerechnet.
- **Entscheidung Jakob 16.11.2026:** unverändert übernommen und freigegeben wie Xetra-Gold
  (`config/technik.yaml`, `datenfreigaben`). Begründung: Der Tag liegt nur im nicht gewerteten Vorlauf (gewertet ab
  02.01.2013) und wirkt höchstens über Indikatoren wie SMA200.

**Einordnung der Läufe.**

- Dies ist der **erste Technik-Lauf mit IUSM** statt SXRM.
- Er dokumentiert **nur die Wirkung von Befund 3**. Die Technik-Entscheidung vom 02.11.2026 (Zweig a, `docs/TECHNIK.md`)
  bleibt bestehen.
- Gewertet wird nur der Vergleich alt gegen neu auf demselben Universum und demselben Code. Der Abstand zum Lauf vom
  02.11.2026 mischt den Wechsel auf IUSM mit allen Änderungen an der Simulation seit dem 02.11. und wird hier nicht
  ausgewertet.
- Läufe:
  - alter Steuerweg: Bericht `docs/berichte/2026-11-16_1110_technik_satellite_alter_steuerweg.md`, Kriterien
    `daten/technik/kriterien_alter_steuerweg.csv`, ohne Ablage und ohne Eintrag in `varianten.csv`;
  - Steuer aus der Kasse: Bericht `docs/berichte/2026-11-16_1112_technik_satellite.md`, Ablage
    `daten/backtests/20261116T111112_technik_crossover/` und folgende, in `daten/technik/varianten.csv` mit dem Anlass
    „Korrektur der Simulation: Steuer aus der Kasse (Befund 3)“, keine neue Variante.
  - Beide Läufe liefen auf Commit 3c44de0 mit der noch nicht eingecheckten Datenfreigabe für IUSM in
    `config/technik.yaml`; diese hebt nur die Sperre auf und ändert keine Zahl. Sie ist im Commit nach den Läufen
    enthalten.

**Ergebnis, nach Kosten, Sharpe und maximaler Drawdown (alter Steuerweg → Steuer aus der Kasse):**

| Variante | Hälfte 1 Sharpe | Hälfte 1 max. DD | Hälfte 2 Sharpe | Hälfte 2 max. DD | Kriterien |
| --- | --- | --- | --- | --- | --- |
| Crossover | 0,14 → 0,11 | −20,41 % → −21,56 % | 0,55 → 0,45 | −16,30 % → −16,53 % | unverändert verfehlt |
| Momentum | 0,18 → 0,18 | −14,30 % → −14,30 % | 0,37 → 0,37 | −17,59 % → −16,82 % | unverändert verfehlt (Sharpe) |
| Price Channel | −0,70 → −0,70 | −27,96 % → −27,96 % | −0,90 → −0,90 | −32,85 % → −32,85 % | identisch |
| RSI(2) | −3,35 → −3,35 | −58,57 % → −58,57 % | −2,35 → −2,35 | −3,78 % → −3,78 % | identisch |
| Regime | −0,03 → −0,03 | −23,40 % → −23,40 % | 0,05 → 0,05 | −24,45 % → −24,45 % | identisch |
| Buy & Hold (Maßstab) | 0,50 → 0,50 | −15,35 % → −15,27 % | 0,67 → 0,67 | −18,83 % → −18,41 % | – |

- **Kein Kriterium kippt.** Alle fünf Varianten bleiben nach Kosten verfehlt, auch die Zeilen „ohne Kosten“ und der
  Entscheidungsbaum sind gleich (Zweig a).
- **Price Channel, RSI(2) und Regime** zahlen im Zeitraum keine laufende Steuer; ihre Zahlen sind in beiden Modi
  identisch.
- **Crossover** verliert am meisten: Sharpe −0,03 bzw. −0,10, Rendite p. a. gesamt 3,16 % → 2,57 %. Die Steuer ist klein
  (Ende 2015 33 €, danach 1 bis 12 € je Jahr; eine Steuerschuld entsteht nie), aber sie fließt jetzt aus der Kasse.
  Bei 1.250 € und Stückpreisen bis gut 300 € reicht die Kasse danach öfter nicht mehr für ein ganzes Stück: Die an
  der 125-€-Regel gescheiterten Käufe steigen von 710 auf 871. Der Pfad wird damit ein anderer. Das ist genau die
  Wirkung, die der alte Steuerweg verdeckt hat.
- **Momentum** bleibt fast gleich; Buy & Hold verliert 0,11 Pp. Rendite p. a. (5,26 % → 5,14 %) bei gleichem Sharpe.

### Fundamental A

Nicht nachgerechnet; im Neulauf c3 laufen beide Steuermodi nebeneinander (Entscheidung 5).
