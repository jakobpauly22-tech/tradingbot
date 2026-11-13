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
