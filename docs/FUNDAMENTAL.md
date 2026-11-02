# Fundamental-Engine: Ergebnisse und offene Entscheidungen

Stand Sitzung 3 (03.11.2026). Code: `src/tradingbot/engines/fundamental/`; Parameter: `config/fundamental.yaml`;
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

## Entscheidungen (Jakob, 03.11.2026)

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
   behandelt (Entscheidung 03.11.2026, zweiter Teil).
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
