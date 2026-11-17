# Fundamental-Engine: Ergebnisse und offene Entscheidungen

Stand Sitzung 3 (02.11.2026). Code: `src/tradingbot/engines/fundamental/`; Parameter: `config/fundamental.yaml`;
Rechenwege an echten 10-K zum Nachrechnen: `docs/rechenwege/`.

## Umsetzung

- Jahresabschlüsse point-in-time (t, t−1, t−2) aus den SEC-Erstmeldungen, Vorgänger-CIKs zusammengelegt. Je Periode zählt
  unter den am Stichtag bekannten Begriffen der zuerst gemeldete Wert (Fehler gefunden und behoben: vorher wählte der
  Code den vorrangigen Begriff, auch wenn dieser erst Jahre später gemeldet wurde, z.B. Walmart, J&J).
- Abgeleitete Posten (markiert): Bruttoergebnis, Vertriebs- und Verwaltungskosten, Verbindlichkeiten, EBIT, kurzfristige
  Finanzschulden; fehlende langfristige Finanzschulden = 0. Aktualität: letztes Geschäftsjahr höchstens 15 Monate alt.
- Scores: Piotroski (ursprünglich für Value-Aktien, hier allgemeiner Qualitätsfilter), Altman Z (1968, SIC 2000–3999, X4
  mit Marktwert point-in-time) und Z'' (Buchwert) für die übrigen, Beneish (8 Variablen), Accruals-Quote.
- Multiples: E/P und EBIT/EV als Perzentil-Rang in der zweistelligen SIC-Gruppe (mindestens 5 Firmen, sonst Division),
  Kappung auf 1./99. Perzentil, negativer EV markiert. Marktwert gegen den geprüften Streubesitz plausibilisiert.

## Plausibilitätsfälle (Tests)

| Fall | Ergebnis |
| --- | --- |
| Apple GJ 2019 (Rechenweg) | Piotroski 6, Beneish −2,81 (unauffällig), Altman Z 4,53 (sicher) |
| Walmart GJ 2020 (Rechenweg) | Z'' 1,85 (grau) |
| Sears GJ 2017, acht Monate vor dem Insolvenzantrag | Z'' −4,40 (Gefahr), Piotroski 2 |
| Johnson & Johnson GJ 2019 | Altman Z 4,20 (sicher) |

## Auswertung über 33 Stichtage (Q4 2016 bis Q4 2024)

Rund 390–400 investierbare Firmen je Stichtag (Mitglied, kein Finanzwert, gültige Kurse).

| Score | Abdeckung | schließt aus |
| --- | --- | --- |
| Piotroski | 68–69 % | ≤ 3: 1–5 % |
| Altman | 88–91 % | Gefahrenzone: 20–24 % |
| Beneish | 49–58 % | > −1,78: 2–6 % |
| Marktwert / E/P-Rang | 92–96 % | – |
| EBIT/EV-Rang | 87–90 % | – |

Häufigste Lücke: Bruttoergebnis (viele Dienstleister, Versorger und Energieunternehmen melden keine Umsatzkosten), danach
Vertriebs- und Verwaltungskosten. Beide fehlen Piotroski (ΔMARGIN) bzw. Beneish (GMI, SGAI).

## Entscheidungen (Jakob, 02.11.2026)

1. **Altman.** Kein Marktwert in Z'' (die Z''-Grenzen sind auf Buchwerten geschätzt). Stattdessen:
   - SIC 2000–3999: Altman Z (1968) in der Gefahrenzone bleibt harter Ausschluss.
   - Versorger (SIC 4900–4999): kein Altman.
   - Übrige Branchen: Ausschluss nur bei Z'' in der Gefahrenzone **und** einem zweiten Signal (Piotroski ≤ 3 oder negativer
     operativer Cashflow im letzten Geschäftsjahr). Z'' allein ist nur ein Warnhinweis.
2. **Fehlende Scores.** Beneish nicht berechenbar: Filter überspringen und markieren. Piotroski: bei mindestens 7 von 9
   Signalen auf 9 Punkte hochrechnen (Punkte · 9 / Signale) und markieren, sonst Filter überspringen und markieren.
   Der hochgerechnete Wert wird kaufmännisch auf ganze Punkte gerundet, dann gilt „≤ 3 = Ausschluss“ wie im Original
   (3 von 8 → 3,375 → 3 → raus; 3 von 7 → 3,857 → 4 → bleibt). Begründung: Die Hochrechnung schätzt den
   wahrscheinlichsten ganzzahligen Wert auf der 9-Punkte-Skala; so werden Firmen mit und ohne fehlendes Signal gleich
   behandelt (Entscheidung 02.11.2026, zweiter Teil).
3. **Für Sitzung 4:** Ein fehlender Score zählt im Gesamtscore neutral (Median der Vergleichsgruppe), nie als gut.

Code: `engines/fundamental/filter.py`, Parameter: `config/fundamental.yaml` (`filter`, `score.fehlender_score`).

## Ausschlussquoten mit der neuen Regel (33 Stichtage, an allen bewertbaren Firmen, mit Rundung)

| Jahr | Piotroski ≤ 3 | Altman Z Industrie | Z'' + 2. Signal | Z'' nur Warnhinweis | Beneish > −1,78 | ausgeschlossen gesamt | Piotroski hochgerechnet | Piotroski übersprungen | Beneish übersprungen |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2016 | 7 % | 4 % | 2 % | 5 % | 3 % | **13 %** | 31 % | 1 % | 43 % |
| 2017 | 6 % | 5 % | 1 % | 6 % | 1 % | **10 %** | 30 % | 1 % | 43 % |
| 2018 | 3 % | 5 % | 0 % | 6 % | 2 % | **9 %** | 30 % | 1 % | 43 % |
| 2019 | 1 % | 5 % | 0 % | 6 % | 1 % | **7 %** | 29 % | 1 % | 42 % |
| 2020 | 3 % | 6 % | 1 % | 7 % | 3 % | **10 %** | 29 % | 1 % | 42 % |
| 2021 | 7 % | 5 % | 3 % | 7 % | 3 % | **14 %** | 30 % | 1 % | 45 % |
| 2022 | 4 % | 3 % | 2 % | 7 % | 3 % | **10 %** | 31 % | 1 % | 47 % |
| 2023 | 4 % | 4 % | 1 % | 9 % | 3 % | **11 %** | 31 % | 1 % | 49 % |
| 2024 | 5 % | 5 % | 0 % | 9 % | 1 % | **9 %** | 31 % | 1 % | 50 % |

Gesamt 10 % ausgeschlossen statt 22 % mit der alten Regel (jede Altman-Gefahrenzone raus). Z'' + zweites Signal trifft
155 Firmen-Stichtage (Divisionen B Bergbau/Energie 43, E Verkehr/Kommunikation 54, I Dienstleistungen 58); 925 bleiben als
Warnhinweis im Universum, am 01.10.2024 sind es 36 Firmen. Durch die Hochrechnung ist Piotroski jetzt für 99 % bewertbar
(vorher 68–69 %); dadurch steigt die Quote „Piotroski ≤ 3“ gegenüber der ersten Auswertung (1–5 %).
Bericht mit Tabellen je Division: `daten/fundamental/auswertung_scores.md` (`tools/auswertung_scores.py`).

Rundung: 43 Firmen-Stichtage (3 von 7 Signalen → 4) bleiben gegenüber der ungerundeten Grenze „unter 4“ im Universum;
keiner fällt zusätzlich heraus (1.342 statt 1.385 Ausschlüsse von 13.011 bewertbaren Firmen-Stichtagen).

## Sitzung 4: Entscheidungen (Jakob, 02.11.2026)

Parameter in `config/fundamental.yaml` (`score`, `schattenportfolio`, `erfolgskriterien`), vor dem ersten Lauf festgelegt.

1. **Gesamtscore:** Qualität 50 % (Ränge Piotroski und Accruals, je gleich), Bewertung 50 % (Ränge E/P und EBIT/EV, je
   gleich). Der DCF kommt später in die Bewertungshälfte. Ein fehlender Rang zählt mit dem Median der Vergleichsgruppe und
   wird markiert; EBIT/EV bei negativem EV gilt als fehlend.
2. **Branchenobergrenze:** höchstens 25 % der Positionen (5 von 20) je zweistelliger SIC. Im Bericht zusätzlich die Anteile
   je Division gegenüber dem Universum.
3. **Puffer 30:** Ein gehaltener Titel bleibt, solange er im gefilterten Universum unter den besten 30 ist. Durch Filter
   ausgeschlossene oder aus dem S&P 500 ausgeschiedene Titel werden am nächsten Stichtag immer verkauft. Freie Plätze gehen
   an die besten noch nicht gehaltenen Titel, höchstens 20 Positionen.
4. **Drift:** Gehaltene Titel nur am Stichtag zurück auf 5 %, und nur wenn sie über 7,5 % oder unter 2,5 % liegen. Die
   125-€-Regel gilt zusätzlich.
5. **Austritt aus dem S&P 500 unter dem Quartal:** halten bis zum Stichtag, außer bei Delisting. Erlöse aus Übernahmen
   bleiben bis zum Stichtag als Kasse ohne Zins.
6. **Benchmarks:** MSCI ACWI IMI Value Weighted fehlt im ersten Lauf (kein ETF; Lücke im Bericht vermerkt). Zusatzbenchmark
   US-Value: iShares S&P 500 Value (IVE, USD, in Euro), weil auf Xetra ab 10/2016 nur Small-Cap- (ZPRV) oder
   Welt-Value-ETFs (XDEV) Kurse haben. S&P 500 ohne Finanzwerte in Euro. Sharpe mit EUR-Geldmarktzins (FRED ECBDFR).
7. **Kontrollportfolio:** alle Titel des gefilterten Universums gleich gewichtet, quartalsweise, ohne Kosten und vor Steuern.
8. **Bericht:** je Stichtag, wie viele der gehaltenen Titel mindestens einen Median-Ersatz haben.

Begriffe, wie im Code umgesetzt (Claude, zur Prüfung): *Gefiltertes Universum* = Mitglied am Stichtag, kein Finanzwert,
gültige Kursreihe, aktueller Jahresabschluss (höchstens 15 Monate alt) und von keinem Filter ausgeschlossen. Die Ränge
werden innerhalb des gefilterten Universums gebildet, Vergleichsgruppe wie bei den Multiples (zweistellige SIC mit
mindestens 5 Firmen, sonst Division). *Vor Steuern* heißt auch ohne US-Quellensteuer (sie ist auf die deutsche Steuer
anrechenbar); dafür wird das Schattenportfolio ein zweites Mal mit Kosten, aber ohne Steuern simuliert. Der Lauf mit
Steuern wird auf allen drei Ebenen berichtet.

## Erfolgskriterien des ersten Laufs (vor dem Lauf festgeschrieben, 02.11.2026)

Zeitraum 01.10.2016 bis 31.12.2024 (gewerteter Backtest), Tresor bleibt zu.

| Kriterium | Bedingung |
| --- | --- |
| (a) Auswahl | Rendite p.a. nach Kosten und vor Steuern ≥ Kontrollportfolio |
| (b) Risiko | Sharpe nach Kosten ≥ Sharpe des S&P 500 ohne Finanzwerte (EUR) **und** maximaler Drawdown höchstens 5 Prozentpunkte schlechter |

- Die Rendite gegenüber SXR8 (S&P 500), SPYI (MSCI ACWI IMI) und IVE (S&P 500 Value) wird berichtet, ist aber kein Kriterium.
- Beide bestanden → die Engine geht wie geplant ins Paper Trading. Eines verfehlt → Ergebnis dokumentieren und mit Jakob
  besprechen.
- Änderungen nur bei einem Fehler oder mit theoretischer Begründung, nie weil eine Variante besser abschneidet. Jede
  getestete Variante wird im Bericht gezählt (`daten/fundamental/varianten.csv`).
- Aussagekraft: 33 Quartale; Vorsprünge unter etwa 5 Prozentpunkten p.a. sind statistisch nicht von Zufall zu unterscheiden.

## Ergebnis erster Lauf (Variante 1, 02.11.2026): beide Kriterien verfehlt

Lauf `daten/backtests/20261102T172824_fundamental_schatten/` (Bericht `fundamental_bericht.md`, Kopie
`daten/fundamental/backtest_bericht.md`), Git 1be7141. Getestete Varianten: 1. Ein erster Versuch brach vor der Auswertung
mit einem Fehler ab (Ausführungstag 4. Juli ohne US-Handel; Ordner `…_ABGEBROCHEN_fehler_4juli`), wurde behoben und
nicht als Variante gezählt.

| Reihe (01.10.2016–31.12.2024) | Rendite p.a. | Volatilität | Sharpe | max. Drawdown |
| --- | --- | --- | --- | --- |
| Schattenportfolio nach Kosten, vor Steuern | 10,24 % | 21,2 % | 0,44 | −41,9 % |
| Schattenportfolio nach laufenden Steuern | 8,39 % | 22,5 % | 0,34 | −44,9 % |
| Kontrollportfolio (gefiltertes Universum gleich gewichtet, ohne Kosten) | 13,03 % | 19,3 % | 0,63 | −37,3 % |
| S&P 500 ohne Finanzwerte (EUR) | 16,39 % | 19,4 % | 0,79 | −31,6 % |
| S&P 500 (SXR8) | 15,59 % | 16,1 % | 0,91 | −33,8 % |
| MSCI ACWI IMI (SPYI) | 11,23 % | 17,3 % | 0,60 | −34,6 % |
| S&P 500 Value (IVE, EUR) | 12,38 % | 18,5 % | 0,62 | −36,2 % |

- (a) verfehlt: 10,24 % < 13,03 %. (b) verfehlt: Sharpe 0,44 < 0,79; Drawdown −41,9 % schlechter als die Grenze −36,6 %.
- **Kein Simulationsfehler gefunden.** Gegenrechnung mit denselben Titeln je Quartal, gleich gewichtet und ohne Kosten
  (unabhängige Rechnung über die Kontrollportfolio-Funktion): 11,80 % p.a. Die Differenz zum Simulator (1,56 Pp.)
  entspricht den Kosten (1,51 % des Startkapitals p.a.).
- **Die Auswahl selbst liegt auch ohne Kosten 1,2 Pp. p.a. unter dem Kontrollportfolio** (11,80 % gegenüber 13,03 %).
  Schwache Jahre 2020 (−5,0 % gegenüber +6,5 %) und 2023 (+3,7 % gegenüber +11,0 %), also Wachstumsphasen; der Verlauf
  ähnelt dem Value-Index IVE (2020 −7,8 %). Das passt zu einer Value-Neigung durch E/P und EBIT/EV.
- Kosten: 340 Trades, 1.249 € (Gebühren 302 €, Währungstausch 604 €, Spread und Slippage 343 €), Umschlag 88 % p.a.
  Der Währungstausch je Order (mindestens 2 USD) ist der größte Posten.
- Branchen: Verarbeitendes Gewerbe (D) 38 % gegenüber 47 % im Universum, Handel (G) 17 % gegenüber 9 %.
- Delistings: 43 Kursreihen enden im Zeitraum (42 Übernahmen, 1 Pleite); im Portfolio betroffen nur Raytheon (Fusion 2020).
- Aussagekraft: Der Abstand zum Kontrollportfolio (2,8 Pp.) liegt unter der Schwelle von etwa 5 Pp., die man von Zufall
  unterscheiden könnte; der Abstand beim Sharpe ist deutlich.

Nächster Schritt laut Regel: mit Jakob besprechen. Keine Änderung ohne Fehler oder theoretische Begründung.

## Entscheidungen nach dem ersten Lauf (Jakob, 02.11.2026)

1. **Erkenntnis, keine Anpassung:** Der kombinierte Score geht nicht als Stockpicker ins Paper Trading. Gewichte und Score
   bleiben unverändert.
2. **Kostenmodell Währungstausch (framework-weit, Fehlerkorrektur, keine Variante):** USD-Kasse wird gehalten; getauscht
   wird nur bei Ein- und Auszahlungen bzw. für den Netto-Saldo am Ausführungstag, nicht je Order
   (`backtest/simulation.py`, `backtest/portfolio.py`). Offener Punkt im Steuermodul: Rücktausch von USD-Kasse kann ein
   privates Veräußerungsgeschäft sein (§ 23 EStG, Freigrenze 1.000 €), noch nicht modelliert.
3. **Keine Variante „nur Qualität“ auf 2016–2024** (Rückschaufehler: die Value-Schwäche des Zeitraums ist jetzt bekannt).
   Stattdessen laufen im Paper Trading zwei Schattenportfolios ohne echtes Geld vorwärts mit, sonst identische Regeln
   (20 Titel, Puffer 30, Drift-Band 2,5–7,5 %, SIC2 ≤ 25 %, Filter, quartalsweise):
   - **(A) Originalscore:** Qualität 50 % + Bewertung 50 %.
   - **(B) nur Qualitätshälfte:** Ränge Piotroski und Accruals, je gleich gewichtet.
   Beide werden ab Start des Paper Tradings getrennt ausgewiesen; erst diese Vorwärtsdaten entscheiden über eine Rückkehr
   der Engine als Stockpicker.
4. **Diagnose der Filter als Variante 2** (siehe unten): Taugen Piotroski, Altman und Beneish als Veto im Risk-Manager?
5. **DCF zurückgestellt.** Danach weiter mit der nächsten Engine laut Roadmap.

## Neuberechnung Variante 1 mit korrigiertem Kostenmodell (02.11.2026, keine neue Variante)

Lauf `daten/backtests/20261102T174450_fundamental_schatten/`, Git 4c967a7. Strategie unverändert.

| | Kosten je Order (alt) | Netto-Tausch (neu) |
| --- | --- | --- |
| Kosten gesamt | 1.249 € (1,51 % p.a.) | 668 € (0,81 % p.a.) |
| davon Währungstausch | 604 € (je Order) | 11 € (6 Tauschvorgänge) |
| Rendite p.a. nach Kosten, vor Steuern | 10,24 % | 11,17 % |
| Sharpe / max. Drawdown | 0,44 / −41,9 % | 0,48 / −41,8 % |
| nach laufenden Steuern / nach Verkauf | 8,39 % / 7,91 % | 9,12 % / 8,66 % |

Beide Kriterien bleiben verfehlt: (a) 11,17 % < 13,03 % (Kontrollportfolio); (b) Sharpe 0,48 < 0,79, Drawdown
−41,8 % schlechter als die Grenze −36,6 %. Die Entscheidung oben (keine Anpassung) bleibt.

## Diagnose der Filter (Variante 2, 02.11.2026)

`tools/diagnose_filter.py`, Bericht `daten/fundamental/diagnose_filter.md`. Gleich gewichtet, quartalsweise, ohne Kosten,
vor Steuern, 01.10.2016 bis 31.12.2024.

| Portfolio | Titel je Stichtag | Rendite p.a. | Sharpe | max. Drawdown |
| --- | --- | --- | --- | --- |
| ohne Filter (alle bewertbaren) | 394 | 12,80 % | 0,62 | −37,1 % |
| mit Filtern | 354 | 13,03 % | 0,64 | −37,3 % |
| nur ausgeschlossene | 41 | 9,86 % | 0,39 | −35,4 % |
| ausgeschlossen: Piotroski ≤ 3 | 17 | 4,84 % | 0,16 | −46,0 % |
| ausgeschlossen: Altman Z (Industrie) | 18 | 10,68 % | 0,43 | −36,3 % |
| ausgeschlossen: Z'' + zweites Signal | 4 | 5,39 % | 0,12 | −68,3 % |
| ausgeschlossen: Beneish | 9 | 17,32 % | 0,59 | −36,7 % |

Wertentwicklung je ausgeschlossenem Titel gegenüber dem Mittel aller bewertbaren (Überrendite, Mittel / Median):

| Filter | 1 Quartal | 4 Quartale | Anteil schlechter (4 Q) |
| --- | --- | --- | --- |
| alle ausgeschlossenen | −0,5 % / −1,1 % | −1,7 % / −6,6 % | 58 % |
| Piotroski ≤ 3 | −1,1 % / −2,1 % | −4,4 % / −10,7 % | 62 % |
| Altman Z (Industrie) | −0,4 % / −0,8 % | −1,8 % / −5,1 % | 58 % |
| Z'' + zweites Signal | −1,2 % / −3,2 % | −1,5 % / −19,5 % | 65 % |
| Beneish | +0,8 % / +0,1 % | +3,6 % / −0,7 % | 51 % |

Lesart (Claude, zur Entscheidung durch Jakob):
- Gesamtwirkung klein: Die Filter heben das gleich gewichtete Universum um 0,2 Pp. p.a.; in 19 von 33 Quartalen liefen
  die ausgeschlossenen schlechter, mittlerer Abstand −0,6 % je Quartal, t-Wert −0,9 (nicht signifikant).
- Piotroski ≤ 3 und Z'' mit zweitem Signal trennen am deutlichsten: niedrige Rendite, hohe Schwankung, Median der
  Überrendite über 4 Quartale −11 % bzw. −20 %. Altman Z (Industrie) wirkt schwächer, Beneish gar nicht (ausgeschlossene
  Titel liefen im Mittel besser; einzelne Totalausfälle wie SolarEdge 2023 −91 %).
- Insolvenzen kamen im Zeitraum kaum vor (1 Pleite-Delisting im ganzen Universum), daher ist der eigentliche Zweck von
  Altman hier kaum prüfbar. Die 4-Quartals-Fenster überlappen sich, die Fälle sind nicht unabhängig.

## Datenkorrektur Piotroski „keine neuen Aktien“ (Jakob 13.11.2026, festgehalten vor dem Neulauf)

Festgehalten am 13.11.2026 um 09:36, **vor** jedem Neulauf mit der Korrektur.

- **Befund:** Das Signal EQ_OFFER vergleicht die gewichtete Aktienzahl der Jahre t und t−1, beide als Erstmeldung. Liegt
  ein Split zwischen den beiden Einreichungen, steht ein Wert nach dem Split (t) gegen einen Wert vor dem Split (t−1).
  Ein Split wirkt dann wie eine Kapitalerhöhung, ein Reverse-Split wie ein Rückkauf, jeweils für einen 10-K-Zyklus.
- **Einordnung:** Datenkorrektur. Die Umsetzung wird an die Definition angeglichen (beide Jahre auf derselben
  Split-Basis). Keine neue Variante: Score, Gewichte, Filtergrenzen und Erfolgskriterien bleiben unverändert.
- **Methode (Jakob 13.11.2026):** Weg A: t−1 als Vergleichswert aus derselben Einreichung wie t (gleicher Begriff,
  Basic oder Diluted). Rückfall Weg B, wenn der Vergleichswert fehlt: Erstmeldungen beider Jahre mit den Split-Faktoren
  zwischen den Einreichungen (nur Splits bis zum Stichtag; Backtest Yahoo/Tiingo, Betrieb zusätzlich quittierte
  Flex-Verhältnisse). Gegenprobe beider Wege; Abweichungen von A zur Erstmeldung ohne Split werden getrennt ausgewiesen.
- **Die Korrektur wird unabhängig vom Ergebnis des Neulaufs übernommen.** Der Neulauf auf den Entwicklungsdaten
  (01.10.2016 bis 31.12.2024, Tresor unverändert zu) dient nur der Dokumentation der Wirkung. Ein besseres oder
  schlechteres Ergebnis ändert weder die Übernahme noch die Entscheidungen vom 02.11.2026.
- **Wirksam im Betrieb** ab dem ersten Rebalancing-Stichtag im Januar 2027 (04.01.2027), gleichzeitig für die Auswahl
  der Bücher Fundamental A und B und das Fundamental-Veto im Risk-Manager. Davor rechnet der Betrieb wie bisher.
- **Varianten-Liste:** Der Neulauf wird in `daten/fundamental/varianten.csv` als „Datenkorrektur, keine neue Variante“
  eingetragen.

### Ergebnis des Neulaufs (13.11.2026, nur Dokumentation der Wirkung)

Auswertung der Signale, der Gegenprobe und der Auswahl: `docs/berichte/2026-11-13_piotroski_eq_offer.md`; gehaltene
Titel: `docs/berichte/2026-11-13_piotroski_eq_offer_bestand.md`. Code-Stand 13b300a.

- **Signale:** 150 von 12.595 Firmen-Stichtagen ändern sich (1,2 %, 44 Firmen), 128 von 0 auf 1 (bisher fälschlich
  „neue Aktien“), 22 von 1 auf 0 (unter anderem GE nach dem Reverse-Split 1:8 und XRX nach 1:4). Weg A greift in
  12.583 Fällen, der Rückfall B in 12.
- **Gegenprobe A gegen B:** Bei 86 Firmen-Stichtagen ergeben die Wege verschiedene Signale. In allen Fällen ist A
  plausibler: Yahoo führt Abspaltungen als „Split“ (37, z. B. BAX/Baxalta 1,841, APD/Versum, RTX, IBM/Kyndryl, GE,
  DHR, J/Amentum), die Erstmeldung hat einen Skalierungsfehler (19, Tausend statt Stück: PCAR, COR, COP, GRMN, ABMD,
  OI), oder der Kursreihe fehlt ein Ereignis (30, z. B. HWM/Arconic 1:3 aus 2016, LEN-Aktiendividende).
- **A weicht ohne Split-Ereignis von der Erstmeldung ab:** 317 Firmen-Stichtage (83 Firmen, Median 0,04 %), mit
  geändertem Signal 49 (14 Firmen: 6 Skalierungsfehler, die übrigen fehlende Ereignisse oder kleine Neuausweise wie
  TMO, AWK, J, TDG).
- **Filter:** Grenze Piotroski ≤ 3 neu überschritten: HWM (2017) und GE (2022), je 4 Stichtage; nicht mehr
  ausgeschlossen: CF (2016/17), 2 Stichtage.
- **Auswahl (ohne Kurse nachgestellt):** A an 5 von 33 Stichtagen anders (5 Titelwechsel), B an 8 von 33 (9).
- **Gehaltene Titel:** keiner betroffen. Splits aus der Kursreihe bestätigt: WMT 3:1 (26.02.2024), TSCO 5:1
  (20.12.2024), ETR 2:1 (13.12.2024); bei allen liegen beide verglichenen Jahre nach dem Split.

Neulauf Fundamental A, Entwicklungsdaten 01.10.2016 bis 31.12.2024, Tresor zu. Verglichen wird mit einem Lauf der
bisherigen Rechnung auf demselben Datenstand, weil sich seit dem 02.11. Marktwerte durch spätere Kursdaten leicht
geändert haben (bisherige Rechnung heute 11,04 % statt 11,17 % p.a.).

| A, nach Kosten | bisher (`20261113T100150_fundamental_schatten_eq_bisher`) | korrigiert (`20261113T100231_fundamental_schatten_eq_offer`) |
| --- | --- | --- |
| Rendite p.a. vor Steuern | 11,04 % | 11,36 % |
| Sharpe / max. Drawdown | 0,48 / −41,7 % | 0,49 / −41,8 % |
| nach laufenden Steuern / nach Verkauf | 9,31 % / 8,80 % | 9,77 % / 9,17 % |
| Trades / Kosten | 344 / 667 € | 341 / 662 € |
| Kontrollportfolio | 13,05 % | 13,04 % |

Beide Kriterien bleiben verfehlt: (a) 11,36 % < 13,04 %; (b) Sharpe 0,49 < 0,79 und Drawdown −41,8 % schlechter als
die Grenze −36,6 %. Der Abstand von 0,3 Pp. p.a. liegt weit unter der Schwelle, die man von Zufall unterscheiden
könnte. Wie vorab festgehalten, ändert das Ergebnis nichts: Die Korrektur gilt ab 04.01.2027, die Entscheidungen vom
02.11.2026 bleiben. Beide Läufe stehen in `daten/fundamental/varianten.csv` als Neuberechnung von Variante 1
(Datenkorrektur, keine neue Variante).

Für B gibt es keinen Neulauf mit Kennzahlen: Nach der Entscheidung vom 02.11.2026 (Punkt 3, Rückschaufehler) wird
„nur Qualität“ nicht auf 2016–2024 gerechnet. Für B sind nur Signale und Auswahl ausgewiesen.

**Nebenbefund (offen, nicht geändert):** Die Kursreihen von Yahoo führen Abspaltungen als „Split“ (BAX 2015, PPL 2015,
APD 2016, RTX 2020, IBM 2021, GE 2023/2024, J 2024, CMCSA 05.01.2026 mit 1,067 vermutlich Versant). Die Marktwert-Rechnung
(`index_nachbau.aktien_splitbereinigt`, genutzt für E/P, EBIT/EV, Altman X4, den Index-Nachbau und im Betrieb) multipliziert
die SEC-Aktienzahl auch mit diesen Faktoren. Im Betrieb betrifft das aktuell CMCSA (Bestand Fundamental A). Mit Jakob
besprechen.

**Varianten-Liste (Korrektur 13.11.2026, 10:26):** Variante 1 stand dort unter zwei Schreibweisen („Regeln vom
03.11.2026“ aus dem Datumsfehler vom 02.11.2026, sonst „02.11.2026“). Die Schreibweise ist vereinheitlicht, keine Zeile
gelöscht, Korrekturvermerk in der neuen Spalte `korrektur`. Gezählt sind jetzt **2 Varianten** (Variante 1 mit drei
Neuberechnungen, Variante 2 Diagnose der Filter) statt der angezeigten 3. Die Berichte vom 13.11.2026 nennen noch 3;
sie bleiben als Ablage unverändert. Keine Bewertung ändert sich: Die Zahl der Varianten geht in kein Kriterium und
keine Schwelle ein (die Aussagekraft-Schwelle von etwa 5 Pp. p.a. ist nicht nach der Variantenzahl bereinigt); sie
macht nur sichtbar, wie oft auf denselben Daten getestet wurde.

## Datenkorrektur Marktwert: Abspaltungen als „Split“ und veraltete Aktienzahl (Jakob 13.11.2026, festgehalten vor dem Neulauf)

Festgehalten am 13.11.2026 um 10:46, **vor** jedem Neulauf mit dieser Korrektur.

- **Befund:** (1) Yahoo führt Abspaltungen als Faktor in der Spalte `split`; die Marktwert-Rechnung
  (`index_nachbau.aktien_splitbereinigt`) multipliziert damit auch die SEC-Aktienzahl, wenn sie vor der Abspaltung
  gemeldet wurde und der Stichtag danach liegt. (2) Die SEC-Aktienzahl (Deckblatt) ist bei manchen Firmen veraltet, weil
  sie je Gattung gemeldet wird (CMCSA: Stand 2009).
- **Korrektur:** Faktoren nach dem Stichtag alle (der Kurs ist damit bereinigt), zwischen Meldung und Stichtag nur echte
  Splits (Einordnung je Ereignis über das SEC-Verhältnis, Liste `config/kapitalmassnahmen_historie.yaml`, unklare Fälle
  von Jakob geprüft; im Betrieb Flex-Belege). Ist die Aktienzahl älter als 15 Monate, gilt ersatzweise die jüngste
  gewichtete Aktienzahl (Basic), markiert „Ersatz“.
- **Einordnung:** Datenkorrektur, keine neue Variante; Score, Gewichte, Filtergrenzen und Erfolgskriterien unverändert.
- **Die Korrektur wird unabhängig vom Ergebnis des Neulaufs übernommen.** Das gilt ausdrücklich auch dafür, dass Titel,
  die bisher wegen „kein Marktwert“ herausfielen, durch die Ersatz-Aktienzahl wieder gewertet werden. Der Neulauf
  (Scores, Gegenprobe des Index-Nachbaus mit unveränderten Kriterien, Fundamental A; für B nur Signale und Auswahl) dient
  nur der Dokumentation der Wirkung.
- **Wirksam im Betrieb** ab dem Rebalancing-Stichtag 04.01.2027, zusammen mit EQ_OFFER, für Auswahl und Risk-Manager-Veto.

**Prüfliste Teil a (Jakob 13.11.2026):** 20 Fälle mit Beleg aus 8-K oder Pressemitteilung in
`config/kapitalmassnahmen_historie.yaml` (Spalte `quelle`, `geprueft: true`); alle Einschätzungen von Jakob durch den
Beleg bestätigt, kein Widerspruch. EVHC 2016, FERG 2018, DELL 2018 bleiben unklar ohne Faktor.

**Neuer Befund (offen, mit Jakob besprechen): Kursreihe von E. I. du Pont (CIK 30554).** Die Mitgliedschaft bis
01.09.2017 nutzt die Tiingo-Reihe „DD“; sie läuft über den 31.08.2017 (letzter Handelstag, Umtausch 1,2820 DowDuPont je
Aktie laut 8-K12B vom 01.09.2017, accn 0001193125-17-274834) hinaus und setzt ohne Umrechnung mit DowDuPont/DuPont fort
(Sprung am 01.09.2017 von 507,98 auf 406,60, −20,0 %; DowDuPont selbst +0,8 %). Die Ereignisse 2019 und 2026 dieser Reihe
sind als `nicht_zugehoerig` markiert. Wirkung: Fundamental A hielt CIK 30554 vom 04.10.2016 bis 03.10.2017 (Gewicht
rund 4 %); der Sprung bucht dort einen Scheinverlust von grob einem Fünftel der Position (Schätzung: rund −0,9 % des
Portfolios einmalig, etwa −0,1 Pp. p.a.), in allen bisherigen Läufen von A gleich. Weil die Reihe nicht endet, greift
auch die Delisting-Regel (Übernahme zum letzten Kurs) nicht.

## Dritte Datenkorrektur: Kursreihe von E. I. du Pont gekappt (Jakob 13.11.2026, festgehalten vor dem Neulauf)

Festgehalten am 13.11.2026 um 13:08, **vor** dem Neulauf.

- **Korrektur:** Die Kursreihe von CIK 30554 (E. I. du Pont, Tiingo „DD“) endet am 31.08.2017, dem letzten Handelstag
  vor dem Umtausch in DowDuPont (1,2820 je Aktie, 8-K12B vom 01.09.2017). Danach gilt die bestehende Delisting-Regel
  (Übernahme/Fusion zum letzten Kurs).
- **Einordnung:** Datenkorrektur, keine neue Variante. **Sie wird unabhängig vom Ergebnis des Neulaufs übernommen**;
  der Neulauf (Teil c) dokumentiert nur die Wirkung, zusammen mit den beiden anderen Datenkorrekturen.

### Musterprüfung auf andere Fusionen: Kriterien (festgelegt vor der Suche, 13.11.2026 13:08)

Gesucht werden Kursreihen, die nach dem Indexabgang einer Firma weiterlaufen und dabei wahrscheinlich zu einem anderen
Unternehmen gehören.

- **Grundmenge:** alle Firmen (CIK) des Universums, deren letzte Mitgliedschaft ab 01.01.2012 endet, mit gültiger
  Kursreihe.
- **K1 – Reihe läuft weiter:** Die verwendete Kursreihe hat mehr als 10 Handelstage nach dem Indexabgang noch Kurse
  (gleiche 10-Tage-Grenze wie die Abdeckungsregel in `docs/DATENQUALITAET.md`).
- **K2 – Sprung:** Im Fenster vom 5. Handelstag vor bis zum 10. Handelstag nach dem Indexabgang gibt es eine
  Tagesänderung von mehr als ±15 % ohne Split-Ereignis an diesem Tag. (Die allgemeine Kursprüfung meldet erst ab 25 %;
  der DD-Fall hatte −20 %.)
- **K3 – Ticker gehört heute einer anderen Firma:** Das Symbol der Kursreihe ist laut SEC-Tickerliste
  (`company_tickers.json`) heute einer anderen CIK zugeordnet als der Firma oder ihren Vorgängern.
- **Treffer:** K1 und (K2 oder K3). Gemeldet werden alle Treffer mit Abgangsgrund, Kurssprung, heutigem Inhaber des
  Tickers und letztem eigenen Periodenbericht (10-K/10-Q) der CIK als Zusatzangaben. Korrigiert wird erst nach Jakobs
  Prüfung der Liste.

### Musterprüfung: Ergebnis und Entscheidung (Jakob 13.11.2026)

14 Treffer (`docs/berichte/2026-11-13_reihen_nach_indexabgang.md`). **Regel:** Korrigiert wird nur, wo die Reihe nach dem
Ende nicht mehr dem entspricht, was der Aktionär besaß (Zuordnungsfehler, wiederverwendeter Ticker wie DD). Echt
weiterlaufende Reihen bleiben: Firmen, die weiter 10-K/10-Q melden, und XRX (Holdingwechsel 1:1).

- **XEC (Cimarex):** Der Sprung von −38,2 % am 09.03.2020 ist der Ölpreissturz (am selben Tag DVN −37,4 %, PXD −36,9 %,
  HES −33,7 %, MRO −46,9 %, OXY −53,4 %), kein Umtausch. Die Fusion mit Cabot (Coterra) kam erst am 01.10.2021, mit
  4,0146 Coterra je Aktie (8-K vom 01.10.2021, Item 2.01, accn 0001104659-21-122062). Die Reihe endet dort ohne Sprung:
  letzter Kurs 87,20 USD gegen 4,0146 × 21,76 USD = 87,36 USD (Coterra am 30.09.2021). Keine Korrektur.
- **CSC, TGNA:** Abspaltungen in nicht bereinigten Tiingo-Reihen, eigene Prüfung in Teil c mit vorab festgelegten Kriterien.
- **SIVB:** Prüfung der Insolvenzfälle siehe unten; Ergebnis an Jakob, noch nichts geändert.

## Datenkorrektur Marktwert, Teil b: umgesetzt (13.11.2026)

Plan von Jakob freigegeben am 13.11.2026. Code: `daten/kapitalmassnahmen_historie.py` (Einordnung, Korrekturfaktor),
`engines/fundamental/multiples.marktwert_korrigiert`, `engines/fundamental/aktienzahl.ersatz_aktienzahl`, Tests
`tests/engines/test_marktwert_korrektur.py`.

    MW_T = C_T · A_d · Π_{e>d} f_e · K(d, T),     K(d, T) = Π_{d<e≤T} s_e / f_e

- **Abspaltung nicht als Split:** f_e = Faktor der Kursreihe, s_e = Split-Faktor der Aktienzahl laut
  `config/kapitalmassnahmen_historie.yaml` (Abspaltung 1). Ereignisse nach T bleiben wie bisher (der Kurs bei T ist um sie
  bereinigt). Die Fortschreibung des Streubesitzes (Plausibilitätsprüfung, Index-Nachbau) bekommt denselben Faktor K(e, T).
- **Ungeklärte Ereignisse** (unklar, nicht_zugehoerig, nicht in der Liste): Kursfaktor bleibt, markiert (Entscheidung Jakob
  13.11.2026). Im Betrieb ordnet die Bewertung neue und ungeprüft unklare Ereignisse über das SEC-Verhältnis ein (gewichtete
  Aktienzahl mit Quartalen); was offen bleibt, meldet sie („Marktwert mit ungeklärter Kapitalmaßnahme“). Quittierte Splits
  „Quelle: Flex“ gelten als Split und haben Vorrang.
- **Ersatz-Aktienzahl:** Deckblatt-Zahl älter als 15 Monate (nach `filed`, gegen T) oder keine vorhanden → jüngste gewichtete
  Basic-Zahl (kürzeste Periode, Erstmeldung, bekannt ab dem Tag nach `filed`), Messtag `filed`, markiert „Ersatz“. Ist auch
  sie älter als 15 Monate: kein Marktwert. `config/fundamental.yaml`, `marktwert_korrektur.aktien_max_alter_monate`.
- **Kursreihe E. I. du Pont:** `config/universum_korrekturen.yaml`, `kursreihe_ende` (CIK 30554 bis 31.08.2017) und
  Delisting-Eintrag „Übernahme“ nur für CIK 30554 (Einträge mit `cik` gelten nur für diese Firma). Die Kappung gilt ab
  diesem Stand in allen Läufen. Hinweis: Das Kursniveau der Reihe bleibt um die späteren DowDuPont-Ereignisse skaliert
  (2016 rund 406 statt rund 67 USD); Renditen stimmen, der Marktwert 2016/17 bleibt wie bisher unplausibel und fehlt.
- **Schalter:** Backtest `tools/auswertung_scores.py --marktwert-korrektur` (Cache-Schlüssel mit Zusatz „_marktwert“,
  Vergleichsspalten `marktwert_alt`, `ep_alt`, `ebit_ev_alt`, Quelle, Faktor, ungeklärte Ereignisse);
  Index-Nachbau `baue_nachbau(..., marktwert_korrektur=True)`. Betrieb ab 04.01.2027 (`marktwert_korrektur.ab`); bis dahin
  rechnet die Bewertung beide Werte (`marktwert_alt_usd`, `marktwert_neu_usd`) und zeigt sie.
- **Stichprobe (Backtest-Daten):** BAX 03.10.2016 bisher ohne Marktwert (Streubesitz 183 %, Abspaltung Baxalta 2015 als
  Split), korrigiert 25,9 Mrd. USD; CMCSA mit Ersatz-Aktienzahl 150,1 statt 128,0 Mrd. USD (2016) und 189,7 statt
  172,2 Mrd. USD (2019); HON 2016 Faktor 0,995 (Abspaltung AdvanSix); LDOS unverändert (kombiniert 1:4 vor 2016).

## Vierte Datenkorrektur: eingefrorene Kurse nach einem Handelsstopp bei Insolvenz (Jakob 13.11.2026, festgehalten vor der Suche)

Festgehalten am 13.11.2026 um 14:41, **vor** der Suche und vor dem Neulauf.

- **Anlass SIVB (CIK 719739):** Tiingo füllt während des Handelsstopps vom 10.03. bis 27.03.2023 den letzten Kurs vor dem
  Stopp ein (106,04 USD); erster echter Kurs danach 0,40 USD (Schluss 28.03.2023, OTC „SIVBQ“). Im Index-Nachbau gilt für
  SIVB ab dem ersten Tag des Stopps der erste echte Kurs nach dem Stopp (0,40 USD); der Verlust fällt damit in die
  Mitgliedschaft (Abgang 15.03.2023).
- **Allgemeine Regel:** Eingefrorene Kurse nach einem Handelsstopp mit Insolvenz werden ab dem ersten eingefrorenen Tag
  durch den ersten echten Kurs nach dem Stopp ersetzt (Backtests und Index-Nachbau). Gibt es danach keinen echten Kurs,
  wird der Fall gemeldet und nicht automatisch entschieden.
- **Einordnung:** Datenkorrektur in Teil c, keine neue Variante. **Sie wird unabhängig vom Ergebnis des Neulaufs
  übernommen.** Gefundene Fälle gehen vor der Korrektur als Liste an Jakob.

### Suchkriterien (festgelegt vor der Suche)

- **Grundmenge:** alle Firmen (CIK, mit Vorgängern) des Universums mit gültiger Kursreihe und mindestens einem 8-K mit
  Item 1.03 (Bankruptcy or Receivership) in den SEC-Einreichungen; Kurse wie im Backtest (bis zur Datumsgrenze des Tresors).
- **Fenster:** vom 10. Handelstag vor bis 60 Kalendertage nach dem ersten 8-K mit Item 1.03.
- **E1 – eingefroren:** mindestens 3 aufeinanderfolgende Handelstage mit unverändertem Schlusskurs (gleich dem Vortag)
  und Umsatz 0 (oder fehlendem Umsatz).
- **Treffer:** E1 im Fenster. Gemeldet: Firma, Mitgliedschaft, Datum des 8-K, eingefrorener Zeitraum und Kurs, erster
  echter Kurs danach (erster Tag mit Umsatz > 0 und anderem Schlusskurs) oder Reihenende, ob die Firma am ersten
  eingefrorenen Tag Indexmitglied war und ob ein Backtest-Buch sie hielt.

### Änderung der Suchkriterien nach der ersten Suche (Jakob 13.11.2026, festgehalten vor der zweiten Suche)

**Änderung nach der Suche, mit Begründung:** Die erste Suche (Bericht vom 13.11.2026 14:42) fand SIVB nur zerlegt und erst ab
dem 15.03.2023, weil Tiingo an eingefrorenen Tagen Umsatz meldet (10.03.: 11,5 Mio. Stück bei Eröffnung = Hoch = Tief =
Schluss = 106,04 USD; 13.03.: 2.404; 14.03.: 6; 21.03.: 4). Die Umsatzbedingung erkennt den Handelsstopp damit nicht.
Jakob hat die Regel ohne Umsatzbedingung freigegeben; die erste Suche bleibt als Bericht stehen.

- **E1 (neu):** mindestens **n = 3** aufeinanderfolgende Handelstage mit Eröffnung = Hoch = Tief = Schluss und Schluss
  gleich dem Vortagesschluss. n bleibt bei 3 wie in der ersten Suche (festgelegt vor der zweiten Suche).
- **Erster echter Kurs danach:** erster Handelstag nach dem Lauf, der E1 nicht erfüllt (Kursspanne oder anderer Schluss).
- Grundmenge, Fenster und gemeldete Angaben unverändert.

## Teil c1: Abspaltungen in Tiingo-Reihen (Jakob 13.11.2026, festgehalten vor der Suche)

**Befund:** Tiingo bereinigt Abspaltungen nicht (Anlass CSC 30.11.2015, TGNA 01.06.2017). Hält der Backtest einen solchen
Titel über die Abspaltung, bucht er den Wert der Tochter als Verlust. **Die Korrektur bestätigter Fälle wird unabhängig vom
Ergebnis des Neulaufs übernommen** (Datenkorrektur, keine neue Variante); gefundene Fälle gehen vorher als Liste an Jakob.

**Kriterien** (Jakob 13.11.2026, Schwelle 3 % statt der geplanten 15 %: kleine Abspaltungen wie Versant ≈ 6 % des
Comcast-Werts würden sonst übersehen; S2 hält die Fehltreffer klein):

- **Grundmenge:** Firmen, deren Kursreihe im Backtest aus Tiingo kommt; Zeitraum Mitgliedschaft 2012–2024, verlängert bis
  zum nächsten Rebalancing-Stichtag nach dem Indexabgang. Kurse bis zur Datumsgrenze des Tresors.
- **S1 – Rückgang:** Schlusskurs gegen Vortagesschluss −3 % oder schlechter, an einem Tag ohne Split-Eintrag bei Tiingo.
- **S2 – SEC-Beleg:** Im Fenster 30 Kalendertage vor bis 5 nach dem Tag reicht die Firma (oder ein Vorgänger-CIK) ein 8-K
  mit Item 2.01 ein oder eine Einreichung, deren Dokumentbeschreibung „spin“, „separation“ oder „distribution“ enthält.
- **Treffer:** S1 und S2. **Zweite Liste „unklar“:** Rückgang von 15 % oder mehr ohne S2.
- **Probe (müssen gefunden werden):** CSC 30.11.2015 (CSRA plus Sonderdividende), TGNA 01.06.2017 (Cars.com) und als kleine
  Abspaltung TWX 09.06.2014 (Time Inc., 1 je 8 Time-Warner-Aktien laut 8-K vom 09.06.2014, accn 0001105705-14-000031;
  Wertanteil 4,05 % laut Anhang zum Form 8937 von Time Warner). Fehlt ein Probefall, wird das gemeldet, die Kriterien
  werden nicht selbst geändert.
- **Korrektur je bestätigtem Fall** (erst nach Jakobs Prüfung): Eintrag `abspaltungen_tiingo` in
  `config/universum_korrekturen.yaml` mit Datum, Verhältnis, Quelle und Kursfaktor nach Yahoo-Art
  Vortagesschluss / (Vortagesschluss − Verhältnis × erster Schlusskurs der Tochter); fehlt der Kurs der Tochter, wird der
  Fall gemeldet, nicht geschätzt.

### Teil c1: Änderung der Kriterien nach der ersten Suche (Jakob 13.11.2026, festgehalten vor der zweiten Suche)

**Begründung:** Die erste Suche (Bericht `docs/berichte/2026-11-13_abspaltungen_tiingo.md`, bleibt stehen) maß den reinen
Kurs. Tiingo bucht Abspaltungen aber meist als Bardividende am Ex-Tag (TGNA 01.06.2017: 8,53 USD = Wert von Cars.com;
TWX 09.06.2014: 2,935 USD = Time Inc.), und der Backtest rechnet mit der Gesamtrendite (Dividenden reinvestiert). Fehlerhaft
sind nur Fälle wie CSC (30.11.2015: Dividende 10,50 USD = nur die Sonderdividende, der Wert von CSRA fehlt, Gesamtrendite
−39 %). Außerdem lief das 8-K von TWX über Item 8.01, und Item 2.01 allein lieferte 246 Fehltreffer.

- **S1 (neu):** Gesamtrendite (Schluss plus Dividende gegen Vortagesschluss) −3 % oder schlechter an einem Tag ohne
  Split-Eintrag, oder über zwei aufeinanderfolgende Tage zusammen (Verschiebung um einen Tag wie bei TWX).
- **S2 (neu):** irgendein 8-K der Firma (oder eines Vorgänger-CIK) im Fenster 30 Kalendertage vor bis 5 nach dem Tag, dessen
  Volltext (alle Dokumente der Einreichung) „spin“, „separation“ oder „distribution“ enthält.
- **Treffer:** S1 und S2. **Unklar:** Gesamtrendite −15 % oder schlechter ohne S2.
- **Probe:** CSC 30.11.2015 muss Treffer sein; TGNA 01.06.2017 und TWX 06./09.06.2014 dürfen nicht als Treffer erscheinen.
  Zusätzlich muss S2 die in Teil a per SEC bestätigten Abspaltungen am jeweiligen Tag finden: LDOS 30.09.2013, CSC/DXC
  30.11.2015, OXY 25.02.2016, HLT 04.01.2017, DD 02.04.2019 (Dow), DD 03.06.2019 (Corteva), MTCH 01.07.2020; die kleinste
  davon ist **OXY 25.02.2016** (Kursfaktor 1,0017, Restbeteiligung California Resources, rund 0,17 % des Werts).
  Dazu eine Stichprobe von 10 Treffern (zufällig, fester Startwert) gegen die 8-K-Texte. Fehlt etwas, wird es gemeldet;
  die Kriterien werden nicht selbst geändert.

### Teil c1: zweite Änderung, nur S2 (Jakob 13.11.2026, festgehalten vor dem dritten Lauf)

**Begründung:** Der zweite Lauf brach wegen Speichermangel auf dem Rechner nach etwa 60 % der Grundmenge ab und hatte bis
dahin 1.664 Treffer. „distribution“ allein trifft Dividenden, Vertriebsverträge und Platzierungen, „separation“ allein
ebenso Allgemeines. Ein Bericht des abgebrochenen Laufs existiert nicht.

- **S2 (neu):** irgendein 8-K im Fenster 30 Kalendertage vor bis 5 nach dem Ereignis, dessen Volltext „spin-off“, „spinoff“,
  „spin off“, „separation and distribution“ oder „distribution of all“ enthält (typisch: „pro rata distribution of all of
  the outstanding shares“). „distribution“ und „separation“ allein entfallen.
- **S1 bleibt** (Gesamtrendite ≤ −3 %, auch über zwei Tage), damit kleine Abspaltungen nicht verloren gehen. Treffer,
  Unklar, Probe (CSC; TGNA/TWX kein Treffer), S2-Prüfung an den Teil-a-Fällen (kleinste OXY 25.02.2016) und Stichprobe von
  10 Treffern wie freigegeben.
- **Technik:** Das Werkzeug verarbeitet die 8-K einzeln und cacht den Text jedes 8-K komprimiert auf der Festplatte
  (`daten/cache/sec/volltext_8k_text/`), damit eine spätere Änderung der Suchwörter keinen neuen Abruf braucht.

### Teil c1: Methodenwechsel nach dem dritten Lauf – Obergrenze zuerst (Jakob 15.11.2026, festgehalten vor der Rechnung)

Festgehalten am 15.11.2026 um 09:10, **vor** der Rechnung.

**Begründung – dritter Lauf gescheitert** (Bericht `docs/berichte/2026-11-13_abspaltungen_tiingo_3.md`, bleibt stehen):
Die Stichprobe hat 0 von 10 echten Abspaltungen am Treffertag; die Treffer kommen aus Anhängen (Anleihebedingungen,
Abfindungsregeln, Definitionen) oder aus Erwähnungen früherer bzw. künftiger Abspaltungen. Die Probe TWX 06.06.2014 ist
fälschlich Treffer (die Zwei-Tage-Regel zählt den ersten Tag allein). Die Trefferquote ist gut: alle Teil-a-Fälle
einschließlich der kleinsten (OXY 25.02.2016) und CSC 30.11.2015 werden gefunden. **Die Suchwörter werden nicht weiter
geändert.** Statt die Treffer einzeln zu prüfen, wird zuerst die größtmögliche Wirkung gemessen.

**a) Obergrenze**

- **Kandidaten:** nur die Ereignisse des dritten Laufs (Treffer und „unklar“), aus dem Bericht gelesen; kein neuer
  Suchlauf, keine neuen Abrufe.
  - **Backtest A:** Ereignistage, an denen das Buch den Titel zum Vortagesschluss tatsächlich hielt und deren
    Gesamtrendite (Tag oder Zwei-Tage-Fenster) −3 % oder schlechter ist.
  - **Index-Nachbau:** Ereignistage mit Gesamtrendite −15 % oder schlechter innerhalb der Mitgliedschaft (die
    Verlängerung bis zum nächsten Stichtag zählt nicht).
- **Warum diese Menge für eine Obergrenze konservativ ist:** Die Trefferquote des dritten Laufs ist gut (alle in Teil a
  per SEC bestätigten Abspaltungen am jeweiligen Tag gefunden, auch die kleinste); große Rückgänge ohne SEC-Beleg stehen
  zusätzlich in „unklar“. Echte Abspaltungen sind damit in der Menge enthalten. Die vielen Fehltreffer aus S2 (normale
  Kursrückgänge mit einem zufälligen „spin-off“ im 8-K) werden ebenfalls als Scheinverlust gezählt; sie vergrößern die
  Grenze nur und können sie nie verkleinern.
- **Rechnung:** Jeder Kandidatentag gilt als vollständiger Scheinverlust (Tagesrendite 0 statt des gemessenen Werts).
  - Index-Nachbau: neu gebaut mit unveränderten Gewichten und Marktwerten, nur die Renditen dieser Tage auf 0; gemessen
    die Differenz der annualisierten Rendite im Abnahmezeitraum 01.10.2016–31.12.2024; je Jahr und die drei Kriterien der
    Gegenprobe nur zur Information.
  - Backtest A: Bestand aus `trades.csv` der abgelegten Läufe `20261113T100231_fundamental_schatten_eq_offer`
    (maßgeblich) und `…_eq_bisher` (Information); Tagesrendite des Buchs um Gewicht × Verlust angehoben; gemessen die
    Differenz der CAGR nach Kosten, vor Steuern. Näherung ohne Neusimulation (ohne Kosten- und Steuerwirkung und ohne
    geänderte Rebalancing-Entscheidungen).
- **Schwelle:** vernachlässigbar, wenn **beide** Differenzen unter **0,05 Prozentpunkten p. a.** liegen. Dann wird das
  Ergebnis dokumentiert und c1 geschlossen; sonst b).
- **Zusatzregel Neulauf Teil c:** Der Neulauf kann andere Titel halten. Dieselbe Rechnung (dieselben Tage, dieselbe
  Schwelle) wird am Bestand des Neulaufs wiederholt und im Bericht von Teil c ausgewiesen.
- **Werkzeug:** `tools/obergrenze_abspaltungen_tiingo.py` (nur lesend), Bericht
  `docs/berichte/2026-11-15_abspaltungen_obergrenze.md`.

**b) Gezielte Prüfung (nur, wenn a) die Schwelle verfehlt):** Buch A nur Tage mit tatsächlichem Bestand und
Gesamtrendite über das Zwei-Tage-Fenster −3 % oder schlechter; Index-Nachbau nur Tage −15 % oder schlechter während der
Mitgliedschaft. Jeder Fall wird am Hauptdokument des 8-K (ohne Anhänge) bzw. an einer Pressemitteilung geprüft; die
Liste mit Beleg geht an Jakob, bevor etwas korrigiert wird.

## Fünfte Datenkorrektur: vermischte Kursreihe DISCK/WBD (Jakob 15.11.2026, festgehalten vor der Umsetzung)

Festgehalten am 15.11.2026 um 09:46, **vor** der Umsetzung und vor der Suche.

- **Befund** (Nebenbefund der gezielten Prüfung, `docs/berichte/2026-11-15_abspaltungen_gezielt.md`): `lade_firmendaten`
  führt mehrere Reihen einer Firma mit `combine_first` zusammen, die zuerst geladene hat Vorrang. Die Tiingo-Reihe DISCK
  (CIK 1437107) läuft nach der Fusion mit WarnerMedia (letzter echter Handelstag 08.04.2022) ab dem 14.04.2022 mit
  eingefrorenem Kurs 24,42 USD und Lücken bis zum 16.09.2022 weiter; WBD füllt nur die Lücken, der Kurs springt zwischen
  beiden Reihen.
- **Korrektur:** Die Reihe DISCK endet am Fusionstag 08.04.2022 (`kursreihe_ende` mit `ticker`, gilt nur für diese
  Reihe der Firma); danach gilt nur WBD (ab 11.04.2022). **Sie wird unabhängig vom Ergebnis des Neulaufs übernommen.**
- **Technik:** Einträge in `kursreihe_ende` mit `ticker` kappen nur die Reihe dieses Tickers; ohne `ticker` wie bisher
  alle Reihen der Firma (E. I. du Pont).

### Eingefrorene Kurse in zusammengeführten Reihen: Suchkriterien (festgelegt vor der Suche)

- **Grundmenge:** alle Firmen (CIK), deren Kursreihe aus mehr als einer gültigen Reihe zusammengeführt wird
  (Mitgliedschaften 2012–2024), jede Teilreihe einzeln, Kurse wie im Backtest (bis zur Datumsgrenze des Tresors), ohne die
  Kappungen aus `kursreihe_ende` (bereits gekappte Abschnitte werden als „bereits erfasst“ markiert).
- **E1 (wie vierte Datenkorrektur, zweite Fassung):** mindestens 3 aufeinanderfolgende Handelstage mit
  Eröffnung = Hoch = Tief = Schluss und Schluss gleich dem Vortagesschluss.
- **Gemeldet:** Firma, Teilreihe (Ticker, Quelle), eingefrorener Zeitraum und Kurs, erster echter Kurs danach oder
  Reihenende, ob der Zeitraum in der Mitgliedschaft dieser Zeile liegt und ob die zusammengeführte Reihe an diesen Tagen
  den Wert dieser Teilreihe übernimmt.
- **Ergebnis:** Fundliste an Jakob, **bevor** etwas korrigiert wird.

### Teil c1: Ergebnis und Abschluss (Jakob 15.11.2026)

- **a) Obergrenze verfehlt** (Backtest A +1,71 Pp. p. a., Index-Nachbau +0,33 Pp. p. a.,
  `docs/berichte/2026-11-15_abspaltungen_obergrenze.md`), deshalb b).
- **b) Gezielte Prüfung** von 128 Fällen am Hauptdokument der 8-K und an Pressemitteilungen, Schlussprüfung der drei
  Einzelbewegungen ohne 8-K (PBCT, DISH, CTLT) am nächsten 10-Q (`docs/berichte/2026-11-15_abspaltungen_gezielt.md`):
  keine Abspaltung belegt.
- **Ergebnis: Außer CSC 30.11.2015 keine Abspaltung mit fehlendem Wert gefunden. c1 ist damit geschlossen**, offen bleibt
  nur die Korrektur CSC. CSC fehlt in b), weil die Mitgliedschaft am 01.12.2015 endet und damit vor beiden
  Messzeiträumen liegt (Nachbau ab 04.01.2016, Backtest A ab 03.10.2016); auf die gewerteten Ergebnisse wirkt CSC nicht.
- **CSC, Stand:** Der erste Schlusskurs von CSRA liegt nicht vor (Tiingo „CSRA“ ist ein anderes Unternehmen ab 2026,
  Yahoo führt CSRA nicht). Nach der Regel vom 13.11.2026 wird der Fall gemeldet, nicht geschätzt. Belegt sind: Verhältnis
  1 CSRA je CSC-Aktie, volumengewichteter Durchschnittskurs von CSRA am 30.11.2015 30,95 USD (10-Q von CSRA, eingereicht
  04.12.2015), Sonderdividende 10,50 USD (bei Tiingo als Dividende gebucht), Yahoo-Faktor der Kursreihe DXC 1,7412
  (`config/kapitalmassnahmen_historie.yaml`). Entscheidung über die Quelle: Jakob.

### Teil c1: Korrektur CSC und Kappung BMS (Jakob 15.11.2026)

- **CSC 30.11.2015 (Abspaltung CSRA):** Quelle Yahoo-Faktor 1,7412 (Entscheidung Jakob). Eintrag `abspaltungen_tiingo`
  in `config/universum_korrekturen.yaml`; gebucht als zusätzliche Ausschüttung am Ex-Tag
  D = Vortagesschluss · (1 − 1/1,7412) ≈ 29,21 USD neben der Sonderdividende 10,50 USD (Gesamtrendite am Ex-Tag rund
  +3,5 % statt −39 %). Schlusskurse und Marktwert bleiben unverändert (`sp500_nachbau.buche_abspaltungen`, angewendet in
  `lade_firmendaten`). Der Fall liegt vor beiden Messzeiträumen (Mitgliedschaft bis 01.12.2015; Index-Nachbau ab
  04.01.2016, Backtest A ab 03.10.2016) und wirkt nicht auf gewertete Ergebnisse.
- **BMS (Bemis, CIK 11199):** Reihe am letzten echten Handelstag vor der Übernahme durch Amcor gekappt (10.06.2019,
  `kursreihe_ende` mit `ticker_einzeln`), danach Delisting-Regel (Übernahme, 8-K Item 2.01 vom 11.06.2019). Datenkorrektur
  unter der Zusage der fünften Datenkorrektur. Verschiebt nur den Zeitpunkt des Delistings (Fund der Suche
  `docs/berichte/2026-11-15_eingefrorene_zusammengefuehrt.md`), praktisch ohne Wirkung.

## Teil c: Gliederung bis zum Neulauf (Jakob 15.11.2026, festgehalten 15.11.2026 10:42)

- **c1 – Abspaltungen in Tiingo-Reihen:** abgeschlossen (siehe oben; CSC korrigiert, DISCK und BMS gekappt).
- **c2 – Vorbereitung des Neulaufs:** (1) vierte Datenkorrektur SIVB umsetzen (eingefrorene Kurse nach Handelsstopp bei
  Insolvenz), (2) Marktwert aus unbereinigten Tiingo-Rohkursen (Weg A: Rohkurs × SEC-Aktienzahl × Splits zwischen Meldung
  und Stichtag; Ablage `daten/cache/tiingo/roh_bis_tresor/`).
- **c3 – Neulauf** nach dem Nachladen der restlichen Rohkurse ab 01.12.2026: Scores mit allen Datenkorrekturen,
  Gegenprobe Index-Nachbau mit unveränderten Kriterien, Backtest A (B nur Signale), dazu die Zusatzregel aus c1
  (Obergrenze der Scheinverluste am Bestand des Neulaufs).

### c2 (1): vierte Datenkorrektur umgesetzt (15.11.2026)

- `config/universum_korrekturen.yaml`, Abschnitt `eingefrorene_kurse`: SIVB (CIK 719739) vom 10.03. bis 27.03.2023 mit
  dem ersten echten Kurs 0,40 USD (28.03.2023) statt eingefrorener 106,04 USD; Verlust damit am 10.03.2023 in der
  Mitgliedschaft (Abgang 15.03.2023). Angewendet in `sp500_nachbau.lade_firmendaten` (`ersetze_eingefrorene`), wirkt in
  Index-Nachbau und Backtests.
- Nur gelistete Fälle, keine automatische Ersetzung. Schutz: Passt die Reihe nicht mehr (erster echter Kurs anders oder
  Zeitraum nicht eingefroren), bricht das Laden mit `DatenkorrekturPasstNicht` ab, statt still zu ersetzen oder den Fall
  als Ladefehler zu zählen.
- Wirkung nur in der Gegenprobe des Index-Nachbaus (SIVB ist Finanzwert, im Fundamental-Universum und im Nachbau ohne
  Finanzwerte ausgeschlossen; Buch A hielt ihn nie). Gemessen in c3.

### c2 (2): Marktwert aus Rohkursen – Abnahme und Stichprobe (Jakob 15.11.2026, festgehalten 15.11.2026 11:10 vor jedem Lauf)

**Formel:** MW_T = Roh_T · A_d · Π_{d<e≤T} s_e (Roh_T unbereinigter Schluss bis T, A_d SEC-Aktienzahl mit derselben
Auswahl wie in Teil b, s_e Tiingo-Splitfaktoren der Rohreihe). Plausibilität gegen den Streubesitz wie bisher (dessen
Fortschreibung nutzt Kursverhältnisse der bereinigten Reihe). Nur über den Schalter `--marktwert-rohkurse` in
`tools/auswertung_scores.py`; Tageslauf und Betriebsbewertung lesen keine Rohkurse. ~~Der Index-Nachbau braucht keine
Rohkurse (Gewichte aus dem fortgeschriebenen Streubesitz, nur Kursverhältnisse).~~ **Korrigiert 15.11.2026:** Die
Fortschreibung braucht nur Kursverhältnisse, die **Prüfung der Streubesitzwerte** aber den Börsenwert am Messtag und hat
mit bereinigten Kursen den verdeckten Faktor H; sie wird deshalb ebenfalls auf Rohkurse umgestellt (Abschnitt
„c2 (3)“ unten), und damit ändern sich die Gewichte des Index-Nachbaus.

**Abnahme jeder Rohreihe** (`tools/pruefe_rohkurse.py`, Ergebnis `daten/cache/tiingo/roh_bis_tresor/abnahme.csv`):

- Vergleich ausschließlich gegen eine **nur splitbereinigte** Reihe (Yahoo `close` mit auto_adjust=False bzw. Tiingo
  `close` nach `normalisieren`), nie gegen dividendenbereinigte Kurse (Adj Close, adjClose): Deren Verhältnis zum
  Rohkurs driftet mit jeder Ausschüttung. Im Code abgesichert (Reihe muss die Spalte `dividende` getrennt führen und
  darf keine Spalte „adj…“ haben); ein Test zeigt, dass eine dividendenbereinigte Reihe durchfällt.
- Verhältnis v_t = Roh_t / C_t; erwartet v_t = H · Π_{t<e≤Tresorgrenze} s_e. H = Median von v_t / Π s_e (verdeckter
  Faktor aus Splits nach der Tresorgrenze, die in C enthalten sind; 1 ohne solche Splits).
- **Bestanden:** mindestens 250 gemeinsame Handelstage ab 2011 und |v_t / (H · Π s_e) − 1| ≤ 1 % an mindestens 99 % davon.
  H ≠ 1 und Tiingo-Name ungleich Name im Universum werden gemeldet, sind aber kein Ausschluss.
- Nicht bestanden oder Rohreihe fehlt: Die Firma nutzt die bisherige Rechnung (Datenkorrektur Marktwert Teil b),
  markiert und gezählt. Mehr als 5 % solcher Reihen: Fehlerschwelle, laut melden, nicht anpassen.
- **Sperre c3:** Der gewertete Neulauf mit `--marktwert-rohkurse` startet nur, wenn jede Yahoo-Reihe des Universums eine
  Rohreihe mit Abnahme hat oder im Nachlader als dauerhaft nicht verfügbar geführt wird; sonst Abbruch mit Liste.
  `--probe` erlaubt Läufe mit Teilabdeckung, die nie als c3 zählen.

**Unabhängige Stichprobe** (`tools/stichprobe_marktwert_roh.py`, läuft nach dem Nachladen ab 01.12.2026 und vor c3):

- **Unabhängige Quelle:** Streubesitz vom Deckblatt des 10-K (dei:EntityPublicFloat), von der Firma selbst mit eigenem
  Kurs und eigener Aktienzahl am Messtag (letzter Handelstag des zweiten Quartals) gerechnet. `tools/pruefe_boersenwerte.py`
  ist nicht unabhängig (gleiche Yahoo-Kurse und SEC-Aktienzahl, ohne Splits nach 2024).
- **Einheiten:** 20 Firmen-Messtage, Messtag 2016–2024, Firmen des Fundamental-Universums (ohne Finanzwerte), Startwert
  15112026. Fest dabei: MA, UPS, GOOGL (Alphabet) mit je einem zufälligen Messtag. Dazu mindestens 3 Firmen mit
  H ≠ 1 (Split nach 2024). Der Rest zufällig; über alle 20 jedes Jahr 2016–2024 mindestens einmal.
- **Vergleich:** q = Streubesitz / MW_Roh am Messtag (MW_Roh ohne Plausibilitätsfilter), zur Information auch
  q_bisher = Streubesitz / Marktwert nach Teil b.
- **Kriterium:** 0,70 ≤ q ≤ 1,05 (Streubesitz ohne verbundene Aktionäre, daher höchstens rund 1; bis 5 % darüber wegen
  verschiedener Zähltage der Aktien; mehr als 30 % verbundene Aktionäre ist selten). Abweichungen gehen an Jakob, es wird
  nichts angepasst.

### c2 (2): umgesetzt; Präzisierung und eingefrorene Auswahl der Stichprobe (festgehalten 15.11.2026 11:23, vor dem gewerteten Lauf)

- **Code:** `daten/rohkurse_marktwert.py` (Rohreihe, Abnahme, Sperre c3), `multiples.marktwert_rohkurs` und
  `aktienzahl_waehlen` (dieselbe Auswahl wie Teil b), `lade_firmendaten(rohkurse=True)` (Rohreihe je Firma nur, wenn
  jede Teilreihe abgenommen ist; Kappungen wie bei den bereinigten Reihen), `tools/auswertung_scores.py
  --marktwert-rohkurse [--probe]` (Cache-Schlüssel `scores_marktwert_roh[_probe]`, Vergleichsspalten
  `marktwert_teil_b`, `marktwert_kurs`, `marktwert_splitfaktor_roh`, `marktwert_rohkurs`; Bericht je Schalter unter
  `daten/fundamental/auswertung_<schlüssel>.md`, der Basisbericht bleibt unberührt).
- **Erste Abnahme** (`docs/berichte/2026-11-15_rohkurse_abnahme.md`): 563 Rohreihen, 556 bestanden, 7 nicht (HWM, BX,
  MTCH, DD (Yahoo) wegen Abweichungen; GEV, AMTM, BXLT zu kurz) → Rückfall auf Teil b. Verdeckter Faktor H ≠ 1 bei 22
  Reihen (z. B. ORLY 15, BKNG 25, NFLX 10, KLAC 10, NKTR 1/15, Abspaltungen nach 2024 wie FTV 1,327, FDX 1,241). Für
  c3 offen: 158 Reihen (Nachladen ab 01.12.2026, dann Abnahme erneut).
- **Präzisierung der Stichprobe** (nach der ersten Auswahl, vor jeder Marktwert-Rechnung; die erste Auswahl enthielt CEG
  2021 mit Streubesitz 0 vor dem Börsengang und DD als Firma mit H ≠ 1 ohne nutzbare Rohreihe): Kandidat nur mit
  Streubesitz > 0 und Messtag in der Indexmitgliedschaft; Firmen mit H ≠ 1 nur, wenn sie die Rohreihe nutzen, Zuordnung
  über die Kursreihe, nicht den Ticker.
- **Eingefrorene Auswahl** (die Zufallsauswahl hängt über H ≠ 1 vom Stand der Abnahme ab und würde sich nach dem
  Nachladen verschieben; der gewertete Lauf nutzt genau diese 20, `FESTE_AUSWAHL` im Werkzeug): MA 30.06.2020,
  UPS 30.06.2021, GOOGL 29.06.2018, J 29.03.2019 (H), LEN 31.05.2017 (H), AMCR 31.12.2023 (H), ANDV 30.06.2016,
  CF 30.06.2022, PANW 31.01.2024, FISV 30.06.2021, KMX 31.08.2016, WAT 01.10.2016, FANG 30.06.2023, EIX 30.06.2016,
  FLR 29.06.2018, FBHS 30.06.2020, SNA 28.06.2019, NOV 30.06.2017, HAS 24.06.2016, KLAC 31.12.2020 (H). UPS, WAT
  und SNA brauchen die Rohreihen aus dem Dezember.
- **Korrektur nach dem ersten Probelauf (15.11.2026):** Die Annahme „Tiingo führt Abspaltungen nicht als Split“ war
  falsch: Manche Abspaltungen stehen auch bei Tiingo als splitFactor (MRK/Organon 2021: 1,048; IBM/Kyndryl 2021: 1,046).
  Die Formel rechnet deshalb s_e = Tiingo-Splitfaktor mit K(d, T) aus Teil b (Abspaltungen der Liste: s_e = 1); Faktoren
  außerhalb der Liste bleiben und werden als ungeklärt gemeldet (Spalte `marktwert_ungeklaert_roh`). Der Probelauf zählt
  nicht als c3 (Cache-Schlüssel `scores_marktwert_roh_probe`).
- **Zweiter Probelauf (15.11.2026, mit K):** Bei 10.043 Firmen-Stichtagen mit Rohkurs weichen 460 um mehr als 1 % von
  Teil b ab, genau die 16 Firmen mit verdecktem Faktor H ≠ 1 (Verhältnis = H, z. B. ORLY 15, BKNG 25, KLAC 10, NKTR
  1/15); keine ungeklärten Tiingo-Faktoren. Bei NFLX, CRWD, BDX und DD liefert nur der Rohkurs einen plausiblen Wert
  (Teil b um H zu klein).
- **Rückfall ergänzt:** Gibt es bis zum Stichtag keinen Rohkurs (LIN: Tiingo-Rohreihe erst ab 31.10.2018), gilt Teil b,
  markiert „Rohkurs erst nach dem Stichtag (Teil b)“ (`auswertung_scores.marktwert_wahl`).
- **Offener Befund (Jakob entscheidet, nichts geändert):** Die Prüfung der Streubesitzwerte (`streubesitz_pruefen` in
  `lade_firmendaten`) rechnet mit dem bereinigten Kurs × SEC-Aktienzahl und hat damit denselben verdeckten Faktor H. Bei
  H-Firmen verwirft sie richtige Streubesitzwerte und behält unpassende. Folge 1: Der richtige Rohkurs-Marktwert fällt
  durch die Plausibilitätsprüfung (NOW 2020–2022: rund 54 Mrd. USD, „Streubesitz 16 %“), während Teil b (um H = 5 zu
  klein) durchkommt. Folge 2: Der Index-Nachbau gewichtet H-Firmen mit diesen Streubesitzwerten; die Aussage oben, der
  Index-Nachbau brauche keine Rohkurse, gilt deshalb nur für die Fortschreibung, nicht für die Prüfung der Streubesitzwerte.

### c2 (3): Prüfung der Streubesitzwerte mit Rohkursen (Jakob 15.11.2026, festgehalten 15.11.2026 12:02 vor der Umsetzung)

- **Befund:** `streubesitz_pruefen` vergleicht den Streubesitz F_e mit C_e · A_e (bereinigter Kurs × SEC-Aktienzahl auf
  der Split-Basis der Kursreihe). Bei Firmen mit verdecktem Faktor H ist C_e · A_e um H falsch; richtige Streubesitzwerte
  werden verworfen, unpassende behalten (NOW 2020–2022). Davon hängen die Plausibilitätsprüfung des Marktwerts und die
  **Gewichte im Index-Nachbau** ab.
- **Korrektur:** Für Firmen mit abgenommener Rohreihe prüft `streubesitz_pruefen` gegen den Rohkurs auf der Split-Basis
  der Tresorgrenze (Roh / Π Tiingo-Splits danach bis zur Grenze) und die SEC-Aktienzahl auf derselben Basis (Tiingo-
  Splits); ohne abgenommene Rohreihe wie bisher. Schalter `lade_firmendaten(rohkurse=True)`; in c3 nutzen ihn alle
  Werkzeuge des Neulaufs (Scores, Gegenprobe, Nachbau ohne Finanzwerte, Obergrenze c1). Tageslauf und Betrieb unverändert
  (dort enthält der Kurs keine späteren Splits).
- **Zusage: Die Korrektur wird unabhängig vom Ergebnis übernommen. Das umfasst ausdrücklich auch ihre Wirkung auf den
  Index-Nachbau (Gegenprobe gegen den S&P 500 TR) und auf den Benchmark „S&P 500 ohne Finanzwerte“.** Die Kriterien der
  Gegenprobe bleiben unverändert (Korrelation ≥ 0,99, Jahresabweichung ≤ 1 Pp., annualisiert ≤ 0,5 Pp.); wird eines
  verfehlt, gilt die Regel aus docs/DATENQUALITAET.md (Ursachen suchen, mit Jakob besprechen, nicht nachjustieren).
- **Test:** NOW (CIK 1373715) 2020–2022 als Fall: Mit Rohkurs werden die richtigen Streubesitzwerte angenommen, der
  Rohkurs-Marktwert besteht die Plausibilitätsprüfung.

### c2 (3): umgesetzt (15.11.2026)

- `sp500_nachbau.pruefbasis` und `lade_firmendaten(rohkurse=True)`: Für Firmen mit abgenommener Rohreihe prüft
  `streubesitz_pruefen` gegen Roh / Π Tiingo-Splits bis zur Grenze und die SEC-Aktienzahl auf derselben Basis; sonst wie
  bisher. NOW (CIK 1373715): ohne Rohkurse alle Streubesitzwerte 2017–2023 verworfen (348–384 % „des Börsenwerts“), mit
  Rohkursen alle angenommen; der Rohkurs-Marktwert 2020–2022 besteht die Plausibilitätsprüfung (Test mit echten Daten,
  übersprungen ohne lokalen Cache).
- **Schalter `--c3` / `--probe`** in `tools/gegenprobe_index.py`, `tools/nachbau_sp500_ohne_finanzwerte.py` und
  `tools/obergrenze_abspaltungen_tiingo.py` (dort zusätzlich `--backtest <Ordner>`): `--c3` schaltet alle Datenkorrekturen
  ein (Rohkurse in `lade_firmendaten`, `baue_nachbau(marktwert_korrektur=True)` für die Fortschreibung nach Teil b) und
  prüft die Sperre; `--probe` erlaubt Teilabdeckung mit eigenen Ausgaben (Zusatz „_probe“) und zählt nie als c3. Ohne
  Schalter rechnen die Werkzeuge wie bisher. Befund dabei: Die Gegenprobe rief `baue_nachbau` bisher ohne
  `marktwert_korrektur=True` auf; mit `--c3` ist die Korrektur aus Teil b im Index-Nachbau eingeschaltet.
- Kappungen DD/DISCK/BMS, SIVB und CSC wirken in `lade_firmendaten` immer (ohne Schalter).

### c3-Absicherung nach der unabhängigen Prüfung: Befunde 10, 11, 14 (Jakob 16.11.2026, festgehalten 16.11.2026 11:21 vor Umsetzung und Lauf)

Anlass: `docs/berichte/2026-11-16_unabhaengige_pruefung.md`, Befunde 10, 11 und 14. Freigegeben von Jakob am 16.11.2026
(Befund 10 mit ±1 Handelstag und ±1 %, Befund 11 Variante B, Befund 14 harte Sperre). Festgehalten, bevor eine Abnahme mit
dem neuen Kriterium gelaufen ist; das Kriterium wird danach nicht geändert.

**Befund 10: zweites Abnahmekriterium „Splitspalte“** (nur Yahoo-Reihen mit Tiingo-Rohreihe; bei Tiingo-Reihen stammen
Rohreihe und Vergleichsreihe aus derselben Quelle, das Kriterium entfällt dort).

- Grund: Die erste Abnahme vergleicht den Rohkurs mit der Yahoo-Reihe und deren Faktoren. Gerechnet wird danach mit den
  **Tiingo-Splitfaktoren** (Marktwert und Prüfung der Streubesitzwerte). Fehlt bei Tiingo ein Split oder steht er an
  einem anderen Tag, ist die Aktienzahl um den Faktor falsch; die erste Abnahme sieht das nicht.
- Ereignisse: Split-Einträge (Faktor ≠ 1) beider Reihen ab 01.01.2011 bis zur Tresorgrenze. Paarung eines Yahoo-Ereignisses
  mit einem Tiingo-Ereignis, wenn das Tiingo-Datum höchstens **1 Handelstag** (der Yahoo-Reihe) vom Yahoo-Datum abweicht;
  jedes Ereignis höchstens einmal gepaart. Einordnung aus `config/kapitalmassnahmen_historie.yaml` über die CIKs der
  Universumszeilen, die die Reihe nutzen, am Datum des Yahoo-Ereignisses (±1 Handelstag).
- Je Yahoo-Ereignis, nach der Art in der Liste:

  | Art in der Liste | Erwartung an Tiingo | sonst |
  | --- | --- | --- |
  | split | Partner mit Faktor innerhalb **±1 %** des Yahoo-Faktors | nicht bestanden |
  | kombiniert | Partner mit Faktor innerhalb ±1 % des geprüften `split_faktor` | nicht bestanden |
  | abspaltung, nicht_zugehoerig | kein Partner (Aktienzahl ändert sich nicht) | nicht bestanden |
  | unklar | – | immer nicht bestanden (nicht eingeordnet) |
  | nicht in der Liste | Partner mit Faktor innerhalb ±1 % des Yahoo-Faktors (beide Quellen führen denselben Split) | nicht bestanden |

- Jedes Tiingo-Ereignis ohne Yahoo-Partner: nicht bestanden.
- Warum auch ein Tiingo-Faktor an einem Abspaltungstag scheitert, obwohl die Marktwert-Formel ihn über K(d, T) mit s_e = 1
  neutralisiert: Die Prüfung der Streubesitzwerte rechnet ohne K (Befund 12), und K greift nur bei gleichem Datum. Eine
  strenge Regel ist einfacher zu prüfen; der Rückfall auf Teil b ist für Firmen ohne verdeckten Faktor unschädlich.
- Gesamturteil der Reihe: bestanden nur, wenn erstes Kriterium (Rohkurs gegen Yahoo, unverändert) **und** Splitspalte
  bestanden sind. Gründe stehen getrennt in `abnahme.csv` (Spalte `split_abgleich`) und im Abnahmebericht. Nicht bestanden
  heißt wie bisher: Rückfall auf Teil b, gemeldet und gezählt; die Fehlerschwelle (5 %) zählt beide Kriterien zusammen.

**Befund 11: Rückfall auf Teil b sichtbar machen, Variante B.**

- Firmen, deren Reihe die Abnahme nicht besteht **und** deren H-Schätzung um mehr als 0,5 % von 1 abweicht (|H − 1| > 0,005),
  bekommen **keinen Marktwert** (Teil b enthielte den verdeckten Faktor, der Wert kann um den Faktor falsch sein; ein
  fehlender Wert ist besser als ein falscher). Sie fallen bei den Multiples heraus und werden gezählt, Grund
  „Abnahme nicht bestanden, H ≠ 1“. Ohne H-Schätzung (keine gemeinsamen Tage, Rohreihe fehlt) bleibt Teil b.
- Im Index-Nachbau (Gewichte, Prüfung der Streubesitzwerte) bleibt für diese Firmen Teil b, mit Meldung.
- Bericht (Scores, Gegenprobe, Backtest A): Liste der Firmen mit Rückfall auf Teil b mit Reihe, Grund, H-Schätzung, Zahl der
  Firmen-Stichtage und Gewicht (Scores: Firmen-Stichtage und betroffene Marktwerte; Gegenprobe: mittleres Gewicht im
  Nachbau; Backtest A: Zahl der Haltetage im Buch).

**Befund 14: harte Sperre.** `sperre_c3()` sperrt zusätzlich, wenn in `abnahme.csv` mehr als 5 % der Reihen mit Rohreihe
nicht bestanden haben (dieselbe Schwelle wie die Fehlerschwelle der Abnahme). Damit starten die c3-Werkzeuge nach einer
überschrittenen Schwelle auch technisch nicht; `--probe` bleibt möglich und zählt nie als c3.

**Änderung des Kriteriums „Splitspalte“ nach dem ersten Lauf (Jakob 16.11.2026, festgehalten 16.11.2026 12:45 vor dem
zweiten Lauf).** Erster Lauf: 44 von 563 Reihen nicht bestanden (7,8 %), davon 26 nur, weil Tiingo eine Abspaltung der
Liste als Split führt (`docs/berichte/2026-11-16_rohkurse_abnahme.md`, Ursachen).

- **Neu:** Ein Tiingo-Faktor **genau am Datum** (gleicher Tag, nicht ±1 Handelstag) eines Ereignisses mit Art
  `abspaltung` in `config/kapitalmassnahmen_historie.yaml` gilt als bestanden; er wird im Bericht als Hinweis aufgeführt.
- **Begründung (Jakob):** Ein Tiingo-Faktor genau am Datum einer per SEC belegten Abspaltung ist kein Datenfehler. Die
  Marktwert-Formel behandelt ihn über K (s_e = 1), die Prüfung der Streubesitzwerte nach Befund 12 ebenfalls.
- Unverändert: ±1 Handelstag bei der Paarung, ±1 % beim Faktor, alle übrigen Regeln (auch `nicht_zugehoerig` mit
  Tiingo-Faktor bleibt nicht bestanden, weil K das Ereignis dort als ungeklärt führt) und das Zeitfenster ab 01.01.2011.
- **Nicht gewählt:** Ereignisse erst ab 2012 (Beginn der Liste) zu zählen. Für die Schwelle ist das nicht nötig.
- Die übrigen Reihen, die nicht bestehen, stehen vollständig mit Ursache je Reihe im Bericht des zweiten Laufs.

**Befund 12: Prüfung der Streubesitzwerte mit K (Plan freigegeben von Jakob 16.11.2026).** `streubesitz_pruefen` rechnet
die Aktienzahl vom Messtag d auf die Kursbasis des Streubesitz-Messtags e mit demselben Faktor wie die Marktwert-Formel:
A_d · Π_{x>d} f_x · K(d, e) für d < e und A_d · Π_{x>d} f_x / K(e, d) für d > e (f = Faktoren der Prüfreihe, Tiingo
bei Rohreihen, sonst Yahoo; K aus der Liste, Abspaltung s = 1). Das gilt für Roh- und Yahoo-Reihen. Wie c2 (3) nur mit
`lade_firmendaten(rohkurse=True)`, also in c3; ohne Schalter rechnen die Werkzeuge wie bisher.

**Umsetzung (16.11.2026):**

- `daten/rohkurse_marktwert.py`: `splitabgleich` (Befund 10), `schwelle_der_abnahme` und `sperre_c3`/`sperrtext`
  (Befund 14), `unsichere_reihen` (Befund 11). `tools/auswertung_scores.py` nutzt jetzt dieselbe Sperre wie die übrigen
  c3-Werkzeuge (vorher eigene Prüfung nur auf fehlende Reihen).
- `tools/pruefe_rohkurse.py`: zweites Kriterium für Yahoo-Reihen, Spalte `split_abgleich` in `abnahme.csv`, Zahl der nur
  an der Splitspalte gescheiterten Reihen und Stand der Fehlerschwelle im Bericht. Die Fehlerschwelle wird erst am Ende
  geprüft (vorher konnte sie mitten im Lauf abbrechen, bevor `abnahme.csv` geschrieben war); die Sperre liest sie aus
  `abnahme.csv`.
- `lade_firmendaten(rohkurse=True)` führt `rohkurse_unsicher`; `tools/auswertung_scores.py` rechnet dafür keinen Marktwert
  (Grund „Abnahme nicht bestanden, H ≠ 1“). Rückfall-Listen: Scores-Bericht, Gegenprobe mit `--c3` (Gewicht im Nachbau,
  `sp500_nachbau.rueckfall_gewichte`), Backtest-Bericht (Stichtage und Haltetage im Buch).
- Tests: `tests/daten/test_c3_absicherung.py`.
- Befund 12: `sp500_nachbau.aktienkorrektur` und `streubesitz_pruefen(..., korrektur_aktien)`, nur mit
  `lade_firmendaten(rohkurse=True)`.

**Abnahme, zweiter Lauf (16.11.2026 12:47, nach der Änderung):** 18 von 563 Reihen nicht bestanden (3,2 %), Fehlerschwelle
nicht überschritten, c3 nicht gesperrt (offen bleiben nur die 158 Reihen zum Nachladen). 26 Reihen bestehen mit einem
Tiingo-Faktor an einer Abspaltung der Liste (Hinweis). Ohne Marktwert nach Variante B: MTCH, DD. Ursache je Reihe:
`docs/berichte/2026-11-16_1247_rohkurse_abnahme.md`.

### c3-Absicherung: Befunde 13, 15 und Delisting-Grund BMS (Jakob 16.11.2026, Plan freigegeben)

- **Befund 13, EQ_OFFER Weg B:** Zwischen den beiden Einreichungen zählen nur echte Splits (Π s_e statt Π f_e; Abspaltung
  der Liste s = 1, ungeklärte Ereignisse s = f wie bisher). `aktienzahl.eq_offer_vergleich(..., ereignisse=,
  fakten_quartale=)`. Scores: nur mit der Datenkorrektur Marktwert, also in c3. **Betriebsweg angeglichen:**
  `engines/fundamental/aktuell.py` nutzt dieselben Ereignisse wie beim Marktwert (Liste, Flex-Splits, automatische
  Einordnung mit Quartalsfakten). Bis 04.01.2027 ändert das nur die Anzeige (`eq_offer_neu`); danach gilt es für Auswahl
  und Veto. Weg A unverändert.
- **Befund 15, CSC:** Fehlt der Ex-Tag einer gebuchten Abspaltung innerhalb der geladenen Reihe, bricht
  `buche_abspaltungen` laut ab (`DatenkorrekturPasstNicht`, wie SIVB). Außerhalb der geladenen Reihe bleibt sie unverändert.
- **Delisting-Grund BMS:** geprüft. Nach der Kappung auf den 10.06.2019 (und mit dem alten Ende 28.06.2019) findet die
  Regel die 8-K Item 2.01 vom 11.06.2019, also „Übernahme“, ohne manuellen Eintrag. Test mit lokalem SEC-Cache.

## Checkliste c3: Neulauf ab 01.12.2026 (festgehalten 15.11.2026)

Für eine neue Sitzung ohne Verlauf. Reihenfolge einhalten; jeder Schritt erst, wenn der vorige sauber ist. Tresor bleibt
zu. Ergebnisse werden dokumentiert, **nichts nachjustiert**; alle Datenkorrekturen gelten „unabhängig vom Ergebnis
übernommen“ (inklusive Wirkung auf Index-Nachbau und Benchmark). Kriterien der Gegenprobe unverändert.

0. **Vorbereitung:** Datum per `date`; `git status` sauber, `git pull`; volle Testsuite grün
   (`.venv\Scripts\python -m pytest`). Nicht parallel zum Tageslauf rechnen.
1. **Rohkurse nachladen:** `.venv\Scripts\python tools\tiingo_rohkurse_nachladen.py` (wiederaufnehmbar; hält an Tages-,
   Monats- oder Netzgrenze an, dann einfach erneut starten). Fertig, wenn „noch offen 0“ meldet oder nur Symbole bleiben,
   die der Nachlader als dauerhaft nicht verfügbar führt. META muss geladen sein (Metadaten-404 ist kein Hindernis);
   Fehler stehen in `daten/cache/tiingo/roh_bis_tresor/stand.json`.
1b. **Einordnung der Split-Ereignisse, nur bis zur Tresorgrenze** (ergänzt 17.11.2026, Entscheidung Jakob 16.11.2026):
   Voraussetzung: Universum und `kursstatus.csv` passen zusammen (Wächter `pruefe_zuordnung`; seit dem 17.11.2026
   verschoben, Behebung nach eigenem Plan). Erst `config/kapitalmassnahmen_historie.yaml` sichern
   (`daten/fundamental/sicherung/kapitalmassnahmen_historie_<Zeit>.yaml`; das Werkzeug schreibt die Liste direkt), dann
   `.venv\Scripts\python tools\split_ereignisse_einordnen.py`. **Ergebnis zu den fünf Ereignissen aus 2024 (SMCI, ANET,
   ETR, PANW, TSCO) mit dem Unterschied zur gesicherten Liste an Jakob, bevor die Liste übernommen wird;** bis dahin die
   gesicherte Liste zurückspielen. Grund: docs/TRESOR_BEKANNT.md, Nr. 3.
2. **Abnahme der Rohreihen:** `.venv\Scripts\python tools\pruefe_rohkurse.py` → `docs/berichte/<Datum>_rohkurse_abnahme.md`.
   Erwartet: „Für c3 noch offen: 0“. Seit 16.11.2026 mit dem zweiten Kriterium „Splitspalte“ (Befund 10, Spalte
   `split_abgleich`). Der Bericht nennt H ≠ 1 nur als Anzahl, ohne Namen und Faktor (Jakob 16.11.2026). Nicht bestandene
   Reihen nutzen Teil b (gemeldet), bei |H − 1| > 0,5 % ohne Marktwert (Befund 11,
   Variante B); mehr als 5 % nicht bestanden → Fehlerschwelle, **alle c3-Werkzeuge sperren technisch** (Befund 14), mit
   Jakob besprechen. Namensmeldungen kurz prüfen (Umbenennungen sind in Ordnung).
3. **Unabhängige Stichprobe:** `.venv\Scripts\python tools\stichprobe_marktwert_roh.py` (eingefrorene 20 Einheiten,
   Kriterium 0,70 ≤ q ≤ 1,05) → `docs/berichte/<Datum>_stichprobe_marktwert_roh.md`, Titel muss „gewertet“ lauten.
   **Ergebnis an Jakob, bevor es weitergeht;** Abweichungen nicht anpassen.
4. **Scores:** `.venv\Scripts\python tools\auswertung_scores.py --eq-offer-splitbereinigt --marktwert-rohkurse`
   (ohne `--probe`; bricht ab, solange Rohreihen ohne Abnahme sind) → Cache `fundamental/scores_eq_offer_marktwert_roh`,
   Bericht `daten/fundamental/auswertung_scores_eq_offer_marktwert_roh.md`. Vergleichsspalten zu Teil b prüfen
   (`marktwert_teil_b`, `marktwert_kurs`, `marktwert_ungeklaert_roh`).
5. **Gegenprobe Index-Nachbau (Lauf 5):** `.venv\Scripts\python tools\gegenprobe_index.py --c3` →
   `daten/universum/gegenprobe_index.md` (Lauf 4 wird als `…_lauf4` gesichert). Kriterien unverändert; Verfehlung →
   docs/DATENQUALITAET.md (Ursachen suchen, mit Jakob besprechen, nicht nachjustieren) und **vor Schritt 6 anhalten**.
6. **Benchmark S&P 500 ohne Finanzwerte:** `.venv\Scripts\python tools\nachbau_sp500_ohne_finanzwerte.py --c3`
   (überschreibt den Cache `benchmarks/SP500_ohne_finanzwerte`; Kontrolle `daten/benchmarks/sp500_ohne_finanzwerte.md`).
7. **Backtest A:** `.venv\Scripts\python tools\backtest_fundamental.py --scores scores_eq_offer_marktwert_roh --name
   fundamental_schatten_c3 --anlass "Neulauf c3: alle Datenkorrekturen (Jakob)" --kopie backtest_bericht_c3.md
   --auch-alter-steuerweg` (beide Steuermodi nebeneinander, Befund 3, Jakob 16.11.2026; gewertet wird „Steuer aus der
   Kasse“; die Kriterien a und b rechnen ohnehin auf dem Lauf vor Steuern, nur die Zeile „nach laufenden Steuern“ ändert sich)
   → `daten/backtests/<Zeitstempel>_fundamental_schatten_c3/`; Eintrag in `daten/fundamental/varianten.csv` als
   Datenkorrektur, keine neue Variante. Vergleich mit dem Lauf vom 13.11.2026 (eq_offer). B: nur Signale und Auswahl wie
   beim Neulauf vom 13.11.2026 (Entscheidung 02.11.2026, kein Kennzahlen-Neulauf).
8. **Zusatzregel c1 (Obergrenze am neuen Bestand):** `.venv\Scripts\python tools\obergrenze_abspaltungen_tiingo.py --c3
   --backtest <Ordner aus 7>` → `docs/berichte/<Datum>_abspaltungen_obergrenze_c3.md`; Schwelle < 0,05 Pp. p. a. für
   Backtest A und Index-Nachbau. Verfehlt: gezielte Prüfung der neuen Fälle wie c1 b), Liste an Jakob.
9. **Bericht c3:** `docs/berichte/<Datum>_neulauf_c3.md` und Abschnitt in dieser Datei mit Wirkung je Datenkorrektur
   (Scores, Gegenprobe, Benchmark, Backtest A); Verfehlungen bleiben stehen und werden begründet. Danach Teil d (A4,
   bereits umgesetzt) und A5 (Pflicht vor Echtgeld). Im Betrieb gelten EQ_OFFER und Marktwert-Korrektur ab 04.01.2027
   (`config/fundamental.yaml`); der Betrieb braucht keine Rohkurse.
10. Volle Testsuite, committen, mit Jakob abstimmen, pushen.
