# 02 Kapitalmarkttheorie, Portfolio und Anleihen

Grundlagenwissen für Portfolio-Konstruktion, Kapitalkosten und den Anleiheteil. Quellen: *Finanzen I (OFIN)*, Teile I bis VII; *Finanzen 2 (BFIN)*, Skript Hackethal (Portfolio Selection, CAPM, APT, Aktien- und Anleihebewertung, Zinsstruktur) und Skript Maurer (Zinsänderungsrisiko, Duration, Konvexität, Ausfallrisiko, CDS); *BFIN Exkurs CDS*.

## 1. Bewertung bei Sicherheit (OFIN Teil II)

- **Grundprinzipien:** Arbitragefreiheit und Gesetz des einheitlichen Preises; Bewertung durch Duplikation (Replikation der Zahlungen).
- **Drei Regeln:** Zahlungen zum selben Zeitpunkt addieren; Endwert FV = C₀ · (1 + r)ᵗ; Barwert PV = Cₜ / (1 + r)ᵗ. Bei Zinsstruktur gilt je Laufzeit der eigene Zins rₜ.
- **Kapitalwert und interner Zins:** NPV-Regel ist der IRR-Regel überlegen (mehrere oder keine Nullstellen möglich).
- **Anleihen:** Nennwert, Kupon, Laufzeit; Preis = Barwert der Kupons und der Tilgung. Steigt der Marktzins, fällt der Kurs. Replikation der Cashflows zeigt Arbitragegrenzen.
- **Annuitäten:** nachschüssig PV = C/r · [1 − (1+r)⁻ᵀ]; vorschüssig = nachschüssig · (1 + r); ewige Rente C/r.
- **Aktien:** konstante Dividende P = D/r, also P/D = 1/r; mit Wachstum P = D₁/(r − g). Historische US-Daten: Kurs-Dividenden-Verhältnis und Dividendenrendite schwanken stark über die Zeit.
- **Fisher-Separation:** Mit Kapitalmarkt sind Investitionsentscheidung (NPV maximieren) und Konsumentscheidung (Zeitpräferenz) trennbar. Alle Eigentümer sind sich über die Investition einig, unabhängig von ihren Präferenzen.

## 2. Risiko, Rendite und Diversifikation (OFIN Teil III, BFIN Hackethal Kap. 7)

- **Portfoliorendite:** r_P = Σ wᵢ rᵢ; E[r_P] = Σ wᵢ E[rᵢ].
- **Portfoliovarianz (zwei Wertpapiere):** σ²_P = w₁²σ₁² + w₂²σ₂² + 2w₁w₂ρ₁₂σ₁σ₂.
- **n Wertpapiere:** σ²_P = Σᵢ Σⱼ wᵢwⱼσᵢⱼ. Bei gleichgewichtetem Portfolio: σ²_P = σ̄²/n + (1 − 1/n) · Cov̄. Das spezifische Risiko verschwindet mit wachsendem n, das systematische (durchschnittliche Kovarianz) bleibt.
- **Korrelation:** ρ = Cov/(σ₁σ₂) zwischen −1 und +1. Bei ρ = −1 ist ein risikofreies Portfolio möglich; bei ρ = +1 kein Diversifikationseffekt.
- **Minimum-Varianz-Portfolio (zwei Wertpapiere):** w₁* = (σ₂² − σ₁₂) / (σ₁² + σ₂² − 2σ₁₂).
- **Effizienter Rand:** Portfolios mit maximaler erwarteter Rendite je Risiko, oberhalb des MVP. Leerverkäufe erweitern den Rand.
- **Mit risikofreier Anlage:** Kapitalallokationslinie E[r_q] = r_f + (E[r_p] − r_f)/σ_p · σ_q. Steilste Linie berührt den Rand im **Tangentialportfolio** T, das das Sharpe Ratio (E[r_T] − r_f)/σ_T maximiert.
- **Tobin-Separation:** Jeder Anleger hält eine Mischung aus risikofreier Anlage und T; nur der Mischungsanteil hängt von der Risikoaversion ab. Optimaler Anteil im riskanten Portfolio: y* = (E[r_T] − r_f) / (A · σ_T²).
- **Praxis Robo-Advisor (Wealthfront):** Anlageklassen wählen, Renditen, Volatilitäten und Korrelationen schätzen, Risikotoleranz bestimmen, Markowitz-Optimierung (maximiere r_P − σ²_P/(2T) mit Toleranzparameter T), Umsetzung mit günstigen ETFs, regelmäßiges Rebalancing.

## 3. CAPM (OFIN Teil III, BFIN Hackethal Kap. 9)

- **Annahmen:** Erwartungsnutzen-Maximierer mit μ-σ-Präferenzen, homogene Erwartungen, eine Periode, risikoloses Leihen und Anlegen, keine Steuern und Kosten, alle Anlagen handelbar.
- **Gleichgewicht:** Alle halten das Marktportfolio; die CML ist E[r] = r_f + (E[r_M] − r_f)/σ_M · σ.
- **Wertpapiermarktlinie (SML):** E[rᵢ] = r_f + βᵢ (E[r_M] − r_f) mit βᵢ = Cov(rᵢ, r_M)/σ²_M. Portfolio-Beta = gewichteter Durchschnitt der Betas.
- **„Preis-Leistungsverhältnis“:** Marktrisikoprämie / Marktvarianz muss für jedes Wertpapier gelten. Historisch: Equity Risk Premium ca. 4 %, Volatilität ca. 16 % (Varianz 2,6 %), Verhältnis ca. 1,5.
- Der „Markt“ umfasst laut CAPM alle handelbaren Anlagen: Aktien, Anleihen, Immobilien, Rohstoffe.
- **Beta-Schätzung** per Regression der Überrenditen: rᵢ − r_f = αᵢ + βᵢ (r_M − r_f) + εᵢ. Systematischer Risikoanteil = R² = β²σ²_M / σ²ᵢ. Betas unterscheiden sich stark nach Branche.
- **Empirie:** Die SML ist flacher als vorhergesagt; Evidenz uneindeutig. Kritik am CAPM ist aus dem Modell heraus nicht möglich (Roll-Kritik: wahres Marktportfolio nicht beobachtbar).

## 4. APT und Faktormodelle (BFIN Hackethal)

- **Idee:** Renditen folgen linear K Risikofaktoren: rᵢ = E[rᵢ] + Σ βᵢₖ Fₖ + εᵢ. Ohne Arbitrage gilt E[rᵢ] = r_f + Σ βᵢₖ λₖ (λₖ = Faktorprämie).
- **Annahmen:** intensiver Wettbewerb, Vermögensmehrung als Ziel, lineares Faktormodell. Schwächer als beim CAPM.
- **Vorgehen:** Faktoren wählen, reine Faktorportfolios bilden (Faktorbeta 1), Prämien schätzen, Sensitivitäten der Aktie per Regression schätzen.
- **Fama-French-Dreifaktormodell (1992):** Markt, **SMB** (Small minus Big), **HML** (High minus Low Book-to-Market). Kleine Firmen erzielten bei gleichem CAPM-Beta höhere Renditen. Die Value-Prämie schwankt international und über die Zeit stark (23 Länder, 1975 bis 2018).
- **Fazit:** CAPM und APT führen zum selben linearen Zusammenhang; Mehrfaktormodelle sind präziser, aber die Faktorwahl ist offen und teils datengetrieben.

## 5. Aktienbewertung (BFIN Hackethal Kap. 18)

- **Fundamentalanalyse:** innerer Wert aus diskontierten Dividenden oder Cashflows im Vergleich zum Kurs.
- **Allgemeines DDM:** P₀ = Σ Dₜ/(1 + k)ᵗ. Mit konstantem Wachstum: P₀ = D₁/(k − g).
- **Zweistufiges DDM:** Phase hohen Wachstums explizit, danach Gordon-Endwert (Beispiel Honda).
- **Wachstumsrate:** g = ROE · b (Thesaurierungsquote b = 1 − Ausschüttungsquote).
- **PVGO:** P₀ = E₁/k + PVGO. Wachstum schafft nur Wert, wenn ROE > k.
- Grenzen des DDM: Firmen ohne Dividende, Sensitivität gegenüber k − g.
- **Free Cash Flows:** FCFF = EBIT(1 − t) + Abschreibungen − Capex − ΔNWC; FCFE = FCFF − Zinsen(1 − t) + Nettoneuverschuldung. FCFE mit k_E, FCFF mit WACC diskontieren.
- **Multiples:** KGV = Kurs/Gewinn; aus Gordon: P/E = (1 − b)/(k − g). Zyklisch adjustiertes KGV (Shiller-CAPE) für den S&P 500. KGVs erlauben Interpretationen, aber keine Bewertung im strengen Sinn.

## 6. Anleihen und Zinsstruktur (BFIN Hackethal Kap. 14–15)

- **Anleihearten:** Staats- und Unternehmensanleihen (mit Ausfallrisiko), inflationsindexierte Anleihen (TIPS), Nullkuponanleihen.
- **Preis:** P = Σ C/(1 + y)ᵗ + N/(1 + y)ᵀ. **Rendite bis Fälligkeit (YTM)** ist der interne Zins. YTM entspricht nur dann der realisierten Rendite, wenn Kupons zur YTM reinvestiert werden und bis Fälligkeit gehalten wird.
- Preispfad: Über pari notierte Anleihen nähern sich zum Laufzeitende dem Nennwert („pull to par“).
- **Dirty Price = Clean Price + Stückzinsen.**
- **Spot Rates und Bootstrapping:** Kuponanleihen als Bündel von Nullkuponanleihen; Spot Rates schrittweise aus Anleihepreisen ermitteln. Die Renditestrukturkurve (YTM) unterscheidet sich von der Zinsstrukturkurve (Spot).
- **Forward Rates:** (1 + s_n)ⁿ = (1 + s_{n−1})^{n−1} · (1 + f_n). Heute vereinbarter Zins für eine künftige Periode.
- **Theorien zur Kurvenform:** Erwartungshypothese (Forwards = erwartete künftige Zinsen) und Liquiditätspräferenz (Laufzeitprämie für lange Bindung). „Risikofreie“ langfristige Staatsanleihen tragen erhebliches Zinsänderungsrisiko (Beispiel 10-jährige AAA-Renditen im Euroraum).

## 7. Zinsänderungsrisiko: Duration und Konvexität (BFIN Maurer)

- Zinssensitivität steigt mit längerer Laufzeit, niedrigerem Kupon und niedrigerem Zinsniveau; Preis-Zins-Kurve ist konvex.
- **Macaulay-Duration:** D = Σ t · PV(CFₜ) / P, durchschnittliche Kapitalbindungsdauer. Nullkuponanleihe: D = Laufzeit.
- **Modifizierte Duration:** D_mod = D / (1 + y). Näherung: ΔP/P ≈ −D_mod · Δy. **Absolute Duration (Dollar-Duration):** ΔP ≈ −D_mod · P · Δy.
- **Portfolioduration** = wertgewichteter Durchschnitt der Durationen.
- **Konvexität:** C = Σ t(t+1) · PV(CFₜ) / [P(1+y)²]. Bessere Näherung: ΔP/P ≈ −D_mod · Δy + ½ · C · (Δy)².
- **Immunisierung (Duration Matching):** Duration der Anlagen = Duration der Verpflichtungen; dann gleichen sich Kurs- und Wiederanlageeffekt bei einer einmaligen parallelen Zinsänderung aus (Beispiel Pensionsverpflichtungen Vodafone).
- **Kritik:** nur für kleine, parallele Verschiebungen einer flachen Zinsstruktur; Rebalancing nötig.

## 8. Ausfallrisiko und CDS (BFIN Maurer, Exkurs CDS)

- **Ratings:** Investment Grade (AAA bis BBB−) vs. Non-Investment Grade; Länderratings; Ratings wandern über die Zeit (Migrationsmatrizen).
- **Yield Spread** = Rendite der Unternehmensanleihe − Rendite der Staatsanleihe gleicher Laufzeit. Bewertung durch Diskontieren mit risikofreiem Zins plus Spread. Spreads weiten sich in Krisen stark aus.
- **Credit Default Swap:** Sicherungsnehmer zahlt eine laufende Prämie (Spread) und erhält bei einem Kreditereignis (Insolvenz, Zahlungsausfall, Restrukturierung) den Verlust (Nennwert − Recovery). Zwecke: Absicherung, Spekulation, Arbitrage gegen Anleihen.
- Näherung: CDS-Spread ≈ Ausfallwahrscheinlichkeit p.a. · (1 − Recovery Rate). CDS-Spreads reagieren sofort auf neue Informationen (Beispiel 5-jährige CDS auf Staatsanleihen, Nov. 2025).

## 9. Agency-Probleme und Markteffizienz (OFIN Teil VI–VII)

- **Asymmetrische Information:** Adverse Selection vor Vertragsschluss (Akerlof, Market for Lemons), Moral Hazard nach Vertragsschluss.
- **Haftungsbeschränkung als Agency-Problem:** Mit Fremdkapital wählt der Unternehmer das riskantere Projekt mit negativem NPV (Asset Substitution, Überinvestition); umgekehrt Unterinvestition. Lösungen: Covenants, höherer Zins (begrenzt), Eigenbeteiligung.
- **Markteffizienz:** schwach, mittelstark, stark. Die meisten professionellen Anleger schlagen ihre Benchmark nicht. Effizienz bedeutet nicht geringe Volatilität. Überleitung zur Behavioral Finance (siehe 06).

## 10. Anleger in der Praxis (BFIN Hackethal Einführung)

- Privatanleger machen teure Fehler: zu geringe Diversifikation, hohe Kosten, Heimatbias, Trendjagd.
- System 1 (schnell, intuitiv) und System 2 (langsam, logisch) nach Kahneman; Beispiel Konjunktionsfehler („Maria ist Bibliothekarin und bei Greenpeace“).

## Bezug zum Trading-Bot

| Konzept | Einsatz im Bot |
| --- | --- |
| Markowitz, Tangentialportfolio, Sharpe Ratio | Gewichtung im Core, Zielgröße der Optimierung |
| Kovarianzmatrix, Korrelationen | Risk-Manager: Diversifikation und Klumpenrisiko messen |
| Tobin-Separation, Risikoaversion | 70/30-Aufteilung als Mischung aus sicherer und riskanter Komponente |
| CAPM-Regression (α, β, R²) | Jede Strategie auf Alpha nach Marktrisiko testen |
| Fama-French, Faktorprämien | Prüfen, ob Renditen nur Faktorprämien sind; Value- und Size-Signale |
| DDM, PVGO, g = ROE · b | Fundamental-Engine: Bewertung und Wachstumsplausibilität |
| Duration, Konvexität | Zinsrisiko der Anleihe-ETFs; Auswahl kurzer vs. langer Laufzeiten nach Regime |
| Spot und Forward Rates, Zinsstruktur | Makro-Signale für die News-Engine (Erwartungen, Inversion) |
| Credit Spreads, CDS | Stress-Indikator für die Regime-Erkennung |
| Robo-Advisor-Prozess | Vorlage für den Core: Klassen, Schätzung, Optimierung, ETFs, Rebalancing |
