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

## Offene Entscheidungen (Jakob)

1. **Altman Z'' und negatives Buch-Eigenkapital.** Z'' (Buchwert) setzt 32 % der Nicht-Industrieunternehmen in die
   Gefahrenzone, bei Versorgern und Verkehr (SIC-Division E) 60 %; Z (Marktwert) nur 11 %. Am 01.10.2024 liegen u.a.
   Verisign, Domino's, Yum!, O'Reilly, AutoZone, Starbucks und Oracle in der Gefahrenzone – gesunde Firmen mit negativem
   Eigenkapital durch Aktienrückkäufe, oft mit Piotroski 8–9. Als Ausschlussfilter würde Z'' so jede fünfte Firma
   streichen, überwiegend ohne Insolvenzrisiko.
2. **Fehlendes Bruttoergebnis und SG&A.** Piotroski und Beneish sind für rund ein Drittel bzw. knapp die Hälfte der Firmen
   nicht berechenbar. Wie mit nicht berechenbaren Scores umgehen (Firma ausschließen, Filter überspringen oder Variable
   neutral setzen)?
