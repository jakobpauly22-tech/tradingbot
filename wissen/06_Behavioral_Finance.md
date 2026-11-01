# 06 Behavioral Finance

Grundlagenwissen zu Anlegerverhalten, Anomalien und Grenzen der Arbitrage. Quellen: Vorlesung *BF1: Entscheidungen unter Risiko und Unsicherheit* (Behavioral Finance, Teil 1); Barberis/Thaler (2003), *A Survey of Behavioral Finance*; Sewell (2008), *Behavioural Finance*; Bloomfield (2006), *Behavioral Finance* (New Palgrave); ergänzend Welch Kap. 12, BFIN Hackethal (System 1/2), OFIN Teil VII.

## 1. Rationale Entscheidungstheorie als Referenz (BF1)

- **Normativ vs. positiv:** Axiome definieren rationales Entscheiden (Soll), empirische Forschung beschreibt tatsächliches Verhalten (Ist).
- **Axiome (Savage-Rahmen, „Acts“):** schwache Ordnung (vollständig, transitiv), Unabhängigkeit, Stetigkeit/Nichtverschwinden u.a. → **Repräsentationstheorem:** Präferenzen lassen sich als Erwartungsnutzen mit subjektiven Wahrscheinlichkeiten darstellen.
- **Risikonutzen:** konkave Nutzenfunktion = Risikoaversion. **Sicherheitsäquivalent** S = u⁻¹(E[u(f)]); **Risikoabschlag** ρ = E(f) − S ≈ −½ σ² · u″(E f)/u′(E f) (Arrow-Pratt).
- **Bayes-Regel:** P(X|M) = P(M|X)P(X) / [P(M|X)P(X) + P(M|Xᶜ)P(Xᶜ)]. Typischer Fehler: Basisraten und falsch Positive unterschätzen (Base Rate Neglect).
- Beispiele für Urteilsfehler: Linda-Problem (Konjunktionsfehler), Ziegenproblem (Wechseln verdoppelt die Gewinnchance von 1/3 auf 2/3, aber nur 30 bis 40 % wechseln).

## 2. Psychologie: Überzeugungen und Heuristiken

- **Zwei Systeme (Kahneman):** System 1 schnell, intuitiv, mühelos; System 2 langsam, logisch, muss aktiviert werden.
- **Overconfidence:** Overestimation (eigene Fähigkeiten), Overplacement (besser als der Durchschnitt), Overprecision (zu enge Konfidenzintervalle). Messung u.a. per **Brier Score** BS = (1/N) Σ (pᵢ − cᵢ)². Folgen: zu viel Handel, zu wenig Diversifikation.
- **Optimismus und Wunschdenken.**
- **Repräsentativität:** Urteil nach Ähnlichkeit statt Wahrscheinlichkeit; „Gesetz der kleinen Zahlen“, Überreaktion auf kurze Serien.
- **Konservatismus:** zu langsame Anpassung an neue Information → Unterreaktion.
- **Belief Perseverance, Bestätigungsfehler (Confirmation Bias).**
- **Anchoring:** Schätzungen kleben an einem Anker.
- **Verfügbarkeit (Availability):** Leicht erinnerbare Ereignisse werden überschätzt.
- **Heuristiken nach Gigerenzer:** einfache Regeln sind keine Fehler, sondern oft robuste Second-Best-Lösungen in unstrukturierten Problemen („ökologische Rationalität“). Optimieren wird überschätzt, weil es Allwissenheit und Universalität unterstellt.
- **Emotionen und Stimmung:** Sonnenschein am Börsenplatz korreliert positiv mit Kursen (Saunders 1993; Hirshleifer/Shumway). Soziale Interaktion und Herdenverhalten (Le Bon 1896).
- **Persönlichkeit und Risikoeinstellung:** Frauen halten in einigen Studien weniger riskante Anlagen (Cohn et al. 1975), oft aber nicht signifikant.

## 3. Präferenzen: Prospect Theory und mehr

- **Prospect Theory (Kahneman/Tversky 1979, 1992):** Bewertung von Gewinnen und Verlusten relativ zu einem **Referenzpunkt**; Wertfunktion konkav bei Gewinnen, konvex bei Verlusten, steiler bei Verlusten (**Verlustaversion**, Faktor etwa 2 bis 2,5); **Wahrscheinlichkeitsgewichtung:** kleine Wahrscheinlichkeiten werden übergewichtet (Lotterien, Versicherungen).
- **Mental Accounting / Narrow Framing:** getrennte Konten je Wertpapier, Bewertung bei Schließung.
- **Ambiguitätsaversion (Ellsberg):** Abneigung gegen unbekannte Wahrscheinlichkeiten.
- **Endowment-Effekt:** Willingness to Accept > Willingness to Pay.
- **Hyperbolisches Diskontieren:** Zeitinkonsistenz (heute 100 € statt 110 € in einer Woche, aber in einem Jahr lieber 110 € eine Woche später). Folge: geringere Sparquote, Prokrastination.
- **Soziale Präferenzen:** Reziprozität, Vertrauen, Reputation (Public Good Game).

## 4. Anlegerverhalten (BF1, Barberis/Thaler)

- **Dispositionseffekt (Shefrin/Statman 1985; Odean 1998):** Gewinner zu früh verkaufen, Verlierer zu lange halten. Messung: DE = PGR − PLR mit PGR = realisierte Gewinne / (realisierte + Buchgewinne) und PLR analog für Verluste. Erklärung: Prospect Theory, Mental Accounting, Glaube an Mean Reversion.
- **Home Bias:** heimische Aktien übergewichtet (French/Poterba 1991). Messung z.B. HB = tatsächliches − optimales Heimatgewicht laut Weltmarktportfolio. Rationale Gründe (Kosten, Steuern, Absicherung) erklären ihn nur teilweise, psychologische Gründe: Vertrautheit, Optimismus.
- **Naive Diversifikation (1/n-Regel):** Vermögen gleich auf verfügbare Optionen verteilen (Benartzi/Thaler 2001). Bewertung: einfach und oft robust gegenüber Schätzfehlern (DeMiguel et al. 2009), aber abhängig von der Menüauswahl.
- **Zu viel Handel:** Privatanleger mit hohem Umschlag erzielen niedrigere Nettorenditen (Barber/Odean 2000); Männer handeln mehr als Frauen.
- **Kaufverhalten:** Aufmerksamkeitsgetrieben (Aktien in den Nachrichten, mit hohem Volumen oder Extremrenditen).
- Privatanleger machen teure Fehler bei Kosten, Diversifikation und Timing (BFIN Hackethal).

## 5. Grenzen der Arbitrage (Barberis/Thaler, Bloomfield)

- Fehlbewertungen bleiben bestehen, wenn Arbitrage riskant oder teuer ist:
  - **Fundamentalrisiko:** Das Ersatzpapier ist kein perfektes Substitut.
  - **Noise-Trader-Risiko (De Long et al. 1990):** Fehlbewertung kann sich vorher verschärfen; Arbitrageure mit kurzem Horizont oder Fremdkapital werden ausgestoppt (Shleifer/Vishny 1997).
  - **Implementierungskosten:** Transaktionskosten, Leerverkaufsbeschränkungen, Suche nach Fehlbewertung.
- Beispiele: Royal Dutch/Shell (Zwillingsaktien mit dauerhaften Preisabweichungen), Indexaufnahmen, 3Com/Palm-Carve-out.
- Bloomfield: Behavioral Finance hat zwei Stränge, psychologische Fehler und ökonomische Grenzen der Ausnutzung. Akzeptanz hängt davon ab, ob sie Abweichungen ohne zu viele Ad-hoc-Annahmen vorhersagt.

## 6. Anomalien und Erklärungen

| Phänomen | Beobachtung | Behaviorale Erklärung |
| --- | --- | --- |
| Equity Premium Puzzle | Aktienprämie zu hoch für plausible Risikoaversion (Mehra/Prescott 1985) | kurzsichtige Verlustaversion (Benartzi/Thaler 1995) |
| Volatilitätsrätsel | Kurse schwanken stärker als Dividenden rechtfertigen (Shiller 1981) | Stimmung, extrapolative Erwartungen |
| Vorhersagbarkeit | Hohe Bewertungen (niedrige D/P) sagen niedrigere Renditen voraus | Überreaktion und spätere Korrektur |
| Size und Value | Kleine und günstige Aktien rentieren besser | Überextrapolation vergangenen Wachstums (Lakonishok/Shleifer/Vishny 1994) |
| Momentum (3–12 Monate) | Gewinner schlagen Verlierer weiter (Jegadeesh/Titman 1993) | Unterreaktion, Konservatismus, Dispositionseffekt |
| Langfrist-Umkehr (3–5 Jahre) | Langfristige Verlierer schlagen Gewinner (De Bondt/Thaler 1985) | Überreaktion, Repräsentativität |
| Post-Earnings-Announcement-Drift | Kurse laufen nach Überraschungen weiter (Bernard/Thomas) | Unterreaktion auf Gewinnmeldungen |
| Event-Effekte | Drift nach IPOs, SEOs (negativ), Rückkäufen und Dividendeninitiierungen (positiv) | Unterreaktion, Management-Timing |
| Closed-end-Fund-Puzzle | Abschläge auf den Nettoinventarwert schwanken mit der Stimmung | Noise-Trader-Sentiment (Lee/Shleifer/Thaler 1991) |
| Comovement | Aktien im gleichen Index oder Stil bewegen sich gemeinsam stärker als fundamental gerechtfertigt | Kategorisierung, Habitate |

- Unternehmensfinanzierung: Manager emittieren bei Überbewertung (Market Timing), Overconfidence von CEOs führt zu Überinvestition und schlechten Übernahmen.

## 7. Wichtige Werke (Sewell 2008)

Le Bon (1896, The Crowd), Simon (1955, Bounded Rationality), Tversky/Kahneman (1974, Heuristiken; 1979, Prospect Theory), Shiller (1981, Excess Volatility; 2000, Irrational Exuberance), De Bondt/Thaler (1985), Shefrin/Statman (1985), De Long et al. (1990), Jegadeesh/Titman (1993), Shleifer (2000, Inefficient Markets), Barberis/Thaler (2003). Gegenposition: Fama (1998), Anomalien seien Methodenartefakte oder Risikoprämien.

## Bezug zum Trading-Bot

| Konzept | Einsatz im Bot |
| --- | --- |
| Momentum, PEAD, Value, Umkehr | Begründung der Strategie-Bibliothek: Signale mit Verhaltens- und Risikoerklärung |
| Dispositionseffekt, Verlustaversion | Feste Ausstiegsregeln (Stops, Zeit-Stop), damit Verlierer nicht zu lange gehalten werden |
| Overconfidence, Brier Score | Journal: Prognosesicherheit der Thesen messen und kalibrieren |
| Zu viel Handel | Mindestordergröße und Gebührenregel, Tages- statt Intraday-Signale |
| Home Bias | Weltweites Universum, ACWI IMI als Benchmark |
| 1/n-Regel | Robuste Alternative zur Markowitz-Optimierung im Vergleichstest |
| Grenzen der Arbitrage, Noise-Trader-Risiko | Fehlbewertungen können länger dauern: Positionsgröße und Zeit-Stop |
| Stimmung, Herdenverhalten | News-Engine: Sentiment als Kontext, nicht als alleiniger Auslöser |
| Hyperbolisches Diskontieren | Regelbasiertes Sparen über Daueraufträge (Bot und Notgroschen parallel) |
