# 09 Ökonometrie

Grundlagenwissen für Backtests, Faktorregressionen und Ereignisstudien. Quellen: *Ökonometrie Finance & Accounting (BOEF)* SoSe 2026, Teil I (Statistik, Matrixalgebra, Portfolio-Anwendung), Teil II (Regressionsanalyse), Teil III (Performancemessung, CAPM-Test, Ereignisstudien) sowie Vorlesung Teil 2 von Schüwer (multiple Regression, Validität, Daten, funktionale Form, Interaktionen, Paneldaten; Folien 1–145, aktualisierte Fassungen und Vorab-Version für 125–145).

## 1. Statistische Grundlagen (Teil I)

- **Momente:** Erwartungswert, Varianz, Schiefe, Kurtosis. **Anscombe-Quartett:** gleiche Kennzahlen, völlig verschiedene Daten → immer plotten.
- **Schätzer:** Mittelwert x̄ = (1/n)Σxᵢ; Varianz s² = (1/(n−1)) Σ(xᵢ − x̄)² (Freiheitsgrad-Korrektur); Kovarianz s_xy = (1/(n−1)) Σ(xᵢ − x̄)(yᵢ − ȳ); Korrelation r = s_xy/(s_x s_y).
- **Matrixalgebra:** Transposition, Multiplikation, Inverse, quadratische Form x′Ax, Ableitungsregeln (∂(a′x)/∂x = a; ∂(x′Ax)/∂x = 2Ax bei symmetrischem A). Matrixmultiplikation als Transformation von Daten (Beispiel Bildmerkmale); Umsetzung in Excel (MMULT, MINVERSE, MTRANS).
- **Portfolio-Anwendung:** Varianz w′Σw; **Minimum-Varianz-Portfolio für N Anlagen:** w_MVP = Σ⁻¹1 / (1′Σ⁻¹1); Kontrolle mit dem Zwei-Anlagen-Fall aus OFIN.

## 2. Lineare Regression (Teil II, Schüwer)

- **Modell:** y = Xβ + u. **OLS-Schätzer:** β̂ = (X′X)⁻¹X′y; Residuen û = y − Xβ̂.
- **Annahmen:**
  - A1 Linearität in den Parametern.
  - A2 Voller Rang von X (keine perfekte Multikollinearität), Zufallsstichprobe.
  - A3 **Exogenität:** E(u|X) = 0.
  - A4 **Homoskedastizität und keine Autokorrelation:** Var(u|X) = σ²I.
  - (A5 Normalverteilung der Fehler für exakte Tests in kleinen Stichproben.)
- **Gauss-Markov:** Unter A1–A4 ist OLS der beste lineare unverzerrte Schätzer (BLUE). Var(β̂|X) = σ²(X′X)⁻¹; σ̂² = û′û/(n − k − 1).
- **Tests:** t-Test für einzelne Koeffizienten t = β̂ⱼ / se(β̂ⱼ); F-Test für gemeinsame Hypothesen; Konfidenzintervalle β̂ ± t_krit · se.
- **Modellgüte:** R² = 1 − SSR/SST; adjustiertes R̄² = 1 − (1 − R²)(n − 1)/(n − k − 1); Standardfehler der Regression.
- **Annahmenverletzungen:** Heteroskedastizität und Autokorrelation → robuste (White, Newey-West) Standardfehler; Endogenität → verzerrte Schätzer. **Fallbeispiel Preiselastizität:** Preisänderungen sind endogen (mit u korreliert); Lösung über Instrumentvariablen.
- **Interpretation:** ceteris paribus; Korrelation ist keine Kausalität.

## 3. Validität (Schüwer)

- **Interne Validität** (kausaler Effekt in der Stichprobe korrekt geschätzt). Gefährdungen, die Schätzer inkonsistent machen:
  1. **Ausgelassene Variablen** (Omitted Variable Bias: Verzerrung = β_ausgelassen · Korrelation mit dem Regressor).
  2. Fehlspezifikation der funktionalen Form.
  3. Messfehler in den unabhängigen Variablen (Abschwächung Richtung null).
  4. Stichprobenauswahl (Selection Bias, z. B. nur überlebende Firmen).
  5. Simultanität (umgekehrte Kausalität).
- **Externe Validität:** Übertragbarkeit auf andere Populationen, Zeiträume, Märkte. Auch Prognosen müssen intern und extern valide sein.

## 4. Daten und funktionale Form (Schüwer)

- **Datenarten:** Querschnitt, Zeitreihe, gepoolte Querschnitte, **Paneldaten** (dieselben Einheiten über die Zeit).
- **Nichtlinearitäten:** quadratische Terme (Wendepunkt −β₁/(2β₂)); Logarithmen:

| Modell | Interpretation von β₁ |
| --- | --- |
| linear-linear | Δy = β₁ · Δx |
| log-linear (ln y auf x) | +1 Einheit x → ca. 100·β₁ % Änderung von y |
| linear-log (y auf ln x) | +1 % x → ca. β₁/100 Einheiten y |
| log-log | Elastizität: +1 % x → β₁ % y |

- **Interaktionsmodelle:** y = β₀ + β₁x + β₂z + β₃(x·z) + u; der Effekt von x hängt von z ab: ∂y/∂x = β₁ + β₃z. Alle Einzelterme einschließen; Einzelkoeffizienten nicht isoliert interpretieren; marginale Effekte mit Konfidenzintervallen über den Wertebereich darstellen. Interaktion mit Dummy = unterschiedliche Steigungen je Gruppe.
- **Modellspezifikation:** Basisregression, dann schrittweise Kontrollen; Ergebnisse in Tabellen mit mehreren Spezifikationen berichten (Robustheit).

## 5. Paneldaten (Schüwer, Folien 125–145)

- Modell yᵢₜ = β₀ + δ₀d₂ₜ + β₁xᵢₜ + aᵢ + uᵢₜ mit unbeobachteter, zeitkonstanter Heterogenität aᵢ (Beispiel Verkehrstote und Biersteuer).
- **Gepoolte OLS** ist nur konsistent, wenn aᵢ nicht mit x korreliert.
- **Erste Differenzen:** Δyᵢ = δ₀ + β₁Δxᵢ + Δuᵢ eliminiert aᵢ; Nachteil: Beobachtungen gehen verloren.
- **Fixed Effects (Within-Schätzer):** Mittelwerte je Einheit abziehen und OLS schätzen; äquivalent zu einer Dummy-Variablen je Einheit (LSDV). Effekte zeitkonstanter Variablen nicht schätzbar. Für T = 2 identisch mit ersten Differenzen. Vorsicht bei großem T und seriell korrelierten Fehlern; unbalancierte Panels möglich.
- Vorteil: Kontrolle zeitinvarianter unbeobachteter Faktoren verringert Omitted Variable Bias.

## 6. Performancemessung und CAPM-Test (Teil III)

- **Sharpe Ratio** SR = (μ_p − r_f)/σ_p; **Treynor Ratio** TR = (μ_p − r_f)/β_p; **Jensens Alpha** = Achsenabschnitt der Regression r_p − r_f = α + β(r_M − r_f) + ε. Alle Größen sind Schätzungen mit Unsicherheit.
- **CAPM-Test (zweistufig):** 1. Zeitreihenregressionen liefern β̂ᵢ; 2. Querschnittsregression der mittleren Überrenditen auf β̂ᵢ: r̄ᵢ − r_f = γ₀ + γ₁β̂ᵢ + ηᵢ. Zu testen ist die **verbundene Hypothese** H₀: γ₀ = 0 und γ₁ = r̄_M − r_f (F-Test), nicht nur einzelne Koeffizienten. Umsetzung in Excel (Datei daten_capm_test.xlsx).

## 7. Ereignisstudien (Teil III)

- **Drei Perioden:** Schätzfenster (Kontrollperiode, üblich 252 Handelstage), Ereignisfenster [T₁, T₂] (beginnt einige Tage vor dem Ereignis wegen Informationslecks), Post-Ereignisperiode (langfristige Effekte, z. B. nach Börsengängen).
- **Normale Rendite:** einfacher Mittelwert r̄ᵢ oder **Marktmodell** r̃ᵢₜ = α̂ᵢ + β̂ᵢ r_Mₜ.
- **Abnormale Rendite:** ARᵢₜ = rᵢₜ − r̃ᵢₜ; **kumulierte abnormale Rendite:** CARᵢ,ₜ* = Σ ARᵢ,T₁+ⱼ; Signifikanz t = CAR / (√t* · σ_AR). Über viele Ereignisse mitteln (CAAR).

## Bezug zum Trading-Bot

| Konzept | Einsatz im Bot |
| --- | --- |
| OLS, Matrixform, robuste Standardfehler | Faktorregressionen der Strategierenditen (Newey-West wegen Autokorrelation) |
| Jensens Alpha, Sharpe, Treynor mit Tests | Backtest-Bericht: ist das Alpha statistisch signifikant? |
| Omitted Variable Bias, Selection Bias | Keine Scheinzusammenhänge: Kontrollfaktoren, Daten mit delisteten Titeln |
| Simultanität, Endogenität | Vorsicht bei News- und Sentiment-Signalen (Kurs treibt Nachricht und umgekehrt) |
| Externe Validität | Out-of-Sample- und Walk-Forward-Tests, andere Märkte und Perioden |
| Log-Renditen, Elastizitäten | Renditen als Logs für Zeitaggregation, Interpretation von Sensitivitäten |
| Interaktionsmodelle | Regime-abhängige Signale: Wirkung eines Signals je nach Trendstärke (ADX) oder Volatilität |
| Panelregression mit Fixed Effects | Querschnittstests von Fundamentalsignalen über viele Aktien und Jahre |
| Ereignisstudien (AR, CAR) | News-Engine: Messung von Earnings- und Nachrichteneffekten, PEAD |
| MVP-Formel Σ⁻¹1/(1′Σ⁻¹1) | Risikominimierende Gewichtung als robuste Alternative |
