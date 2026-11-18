# Unabhängige Prüfung: Regime-Engine, Datenkorrekturen c2, Regime-Schattenbuch

Geprüft am 15.11.2026 (Code-Stand 6a3e7b2), niedergeschrieben am 16.11.2026. Auftrag von Jakob: unabhängig und kritisch
auf Look-ahead-Fehler, Datenlecks über die Tresorgrenze und Rechenfehler prüfen, nichts ändern. Die Prüfung war rein
lesend; an Code, Konfiguration und Daten wurde nichts geändert.

Umfang:

1. Regime-Engine mit Backtest-Werkzeug (`docs/REGIME.md`, `src/tradingbot/engines/regime/`, `tools/backtest_regime.py`).
2. Datenkorrekturen aus Teil c2 (Rohkurs-Marktwert, Streubesitz-Prüfung, SIVB, Kappungen DD/DISCK/BMS,
   CSC-Ausschüttung, EQ_OFFER-Korrektur).
3. Regime-Schattenbuch im Tageslauf (`src/tradingbot/betrieb/regimebuch.py`).

## Gesamtbild

- **Regime-Urteil:** Kein Befund ändert das Urteil „V1 nicht bestanden“. Im gewerteten Lauf (Festlegung b628678) wurde
  kein Look-ahead- und kein Rechenfehler gefunden.
- **c2:** Kein Rechenfehler in den Formeln und kein Look-ahead in den Stichtagsrechnungen gefunden. Gefunden wurden
  zwei Tresor-Befunde und mehrere Lücken in der Absicherung von c3.
- **Betrieb:** Ein Befund mit möglicher Wirkung auf Orders (Befund 2), sonst Fehlalarme und Reproduzierbarkeit.

Bezug: **Betrieb** = Paper Trading; **c3** = gewerteter Neulauf ab 01.12.2026; **Regime-Urteil** = gewerteter Lauf vom
15.11.2026; **Tresor** = Wissen über den Zeitraum ab 01.01.2025.

## Übersicht

| Nr. | Befund | Schwere | Bezug | Stelle |
| --- | --- | --- | --- | --- |
| 1 | Zustände von V1 aus dem Tresorzeitraum stehen in der Doku | mittel | Tresor (künftige Regime-Varianten) | `docs/REGIME.md:299-300` |
| 2 | Gegenläufige Orders von Realbuch und „regime“ in SPYI.DE | mittel | Betrieb | `betrieb/tageslauf.py:592-598`, `:833`, ab `:1057` |
| 8 | Einordnungswerkzeug liest Tresordaten über die Betriebsfreigabe | mittel | Tresor und Prozess, c3 indirekt | `tools/split_ereignisse_einordnen.py:63-66` |
| 9 | Splits nach der Tresorgrenze stehen namentlich in der Doku | niedrig bis mittel | Tresor (künftige Fundamental-Varianten) | `docs/FUNDAMENTAL.md:673-675`, `:692-695` |
| 10 | Abnahme prüft die Tiingo-Splitspalte der Yahoo-Reihen nicht | niedrig bis mittel | c3 | `daten/rohkurse_marktwert.py:71-88` |
| 11 | Rückfall auf Teil b bei Reihen mit möglichem verdecktem Faktor | niedrig bis mittel | c3 | `daten/sp500_nachbau.py:210-219` |
| 3 | Steuern mindern die Wertreihe, aber nicht die Kasse | niedrig bis mittel | Regime-Urteil (nur Höhe), alle Backtests, c3 | `backtest/simulation.py:538-540` |
| 4 | Pünktliche Bewertung sieht weniger als die Neuberechnung | niedrig | Betrieb | `engines/regime/signale.py:177-178`, `betrieb/regimebuch.py:228-236` |
| 5 | Gemeinsamer Kurs-Cache für Betrieb und Backtest | niedrig | Betrieb, Reproduzierbarkeit | `betrieb/regimebuch.py:343`, `daten/kurse.py:149-153` |
| 6 | Festlegungsprüfung deckt nicht alles ab | niedrig | Regime-Urteil (im Lauf ohne Wirkung) | `tools/backtest_regime.py:27` |
| 12 | Streubesitz-Prüfung rechnet Abspaltungsfaktoren in die Aktienzahl | niedrig | c3 (Gewichte im Index-Nachbau) | `daten/sp500_nachbau.py:243`, `daten/index_nachbau.py:62-69` |
| 13 | EQ_OFFER, Weg B behandelt Abspaltungen als Split | niedrig | c3 | `tools/auswertung_scores.py:144`, `engines/fundamental/aktienzahl.py:147-149` |
| 14 | Fehlerschwelle der Abnahme sperrt c3 nicht | niedrig | c3 (Ablauf) | `tools/pruefe_rohkurse.py:72`, `:95-99` |
| 7 | Statische Mischung wiederholt gescheiterte Orders nicht | Hinweis | Regime-Urteil (im Lauf ohne Fall) | `engines/regime/buch.py:60-63` |
| 15 | CSC-Ausschüttung wird still übersprungen, wenn der Tag fehlt | Hinweis | kein gewertetes Ergebnis | `daten/sp500_nachbau.py:97-98` |

Pfade ohne führendes Verzeichnis liegen unter `src/tradingbot/`. Die Nummern folgen der Reihenfolge der Prüfung
(1–7 Teile 1 und 3, 8–15 Teil 2); die Tabelle ist nach Schwere sortiert.

## Befunde im Einzelnen

### 1. Zustände von V1 aus dem Tresorzeitraum stehen in der Doku (mittel; Tresor)

- **Stelle:** `docs/REGIME.md:299-300`.
- **Befund:** Der Abschnitt zum zweiten Probelauf nennt die Wechsel von V1 im Jahr 2025 (März auf „Risiko aus“, Juli
  zurück auf „Risiko an“).
- **Begründung:** Zusammen mit dem bekannten Marktverlauf 2025 lässt sich V1 damit informell im Tresorzeitraum
  beurteilen. Die Regel „keine Wertentwicklung auswerten“ (`docs/REGIME.md:231-232`) deckt das Protokoll im Journal ab,
  nicht diese Zeilen in Git.
- **Wirkung:** Auf das Urteil keine (V1 steht, keine Anpassung). Für jede spätere Regime-Variante ist der Tresor an
  dieser Stelle angebrochen.

### 2. Gegenläufige Orders von Realbuch und „regime“ in SPYI.DE (mittel; Betrieb)

- **Stelle:** `betrieb/tageslauf.py:592-598` (Vorschläge beider Bücher), `:592` und `:833` (Sperre „Order unterwegs“ nur
  je Buch), Sendeschleife ab `:1057`.
- **Befund:** Die Vorschläge beider Bücher entstehen unabhängig. In der Sendeschleife wurde keine Prüfung über Bücher
  hinweg gefunden.
- **Begründung:** Fällt ein Kauf des Realbuchs (Limit Vortagesschluss + 2 %) auf denselben Abend wie ein Verkauf von
  „regime“ (Limit Vortagesschluss − 2 %), liegen beide in derselben Eröffnungsauktion im selben Konto.
- **Nicht geprüft:** Wie IBKR darauf reagiert (Ablehnung oder Ausführung gegeneinander).

### 3. Steuern mindern die Wertreihe, aber nicht die Kasse (niedrig bis mittel; Regime-Urteil nur in der Höhe, alle Backtests)

- **Stelle:** `backtest/simulation.py:538-540`.
- **Befund:** Die Jahressteuer wird nur von `wert_nach_steuern` abgezogen; die Kasse im Lauf bleibt unberührt.
- **Begründung an den Zahlen des Laufs** (`daten/backtests/20261115T142803_regime_V1/`): V1 kauft am 01.12.2015 mit dem
  vollen Verkaufserlös (Zielwert 14.589 €), obwohl für 2015 816 € Steuer anfallen. Bis 2023 summieren sich bei V1 rund
  2.395 € Steuern; Anfang 2024 ist V1 damit zu etwa 111 % seines Nachsteuerwerts investiert. Bei Kaufen und Halten
  sind es nur rund 230 €.
- **Wirkung:** Schwankung und Drawdown von V1 sind in der gewerteten Reihe verstärkt. Das Urteil kippt nicht:
  Kriterium a verfehlt klar (Sharpe 0,45 gegen 0,65 in Hälfte 1), Kriterium c besteht in Hälfte 2 klar (−18,2 % gegen
  Grenze −26,0 %).
- **Einordnung:** Die Regel „Abfluss ohne Zwangsverkauf“ ist die Entscheidung vom 01.11.2026. Die Wirkung trifft jedes
  Buch, das Gewinne realisiert und voll reinvestiert, also auch Backtest A in c3.

### 4. Pünktliche Bewertung sieht weniger als die Neuberechnung (niedrig; Betrieb)

- **Stelle:** `engines/regime/signale.py:177-178` mit `daten/makro.py:121`; Neuberechnung in
  `betrieb/regimebuch.py:228-236`.
- **Befund:** Die Signale zählen den Wert des Vortags mit. FRED hat ihn am Bewertungsabend noch nicht (als Abweichung
  dokumentiert, `docs/REGIME.md:247-248`). Die Neuberechnung im Folgemonat enthält ihn.
- **Wirkung:** Liegt ein Signal nahe der Schwelle, meldet das Buch eine „Abweichung vom Protokoll“ und vermutet
  fälschlich geänderte Kurse. Eine nachgeholte Bewertung sieht aus demselben Grund einen Tag mehr als eine pünktliche.

### 5. Gemeinsamer Kurs-Cache für Betrieb und Backtest (niedrig; Betrieb, Reproduzierbarkeit)

- **Stelle:** `betrieb/regimebuch.py:343`, `daten/kurse.py:149-153`, Filter in `daten/kurse.py:178`.
- **Befund:** Das Regimebuch lädt SPYI.DE über den Standard-Cache, den auch der Backtest liest. Passt die Überlappung
  nicht, lädt der Kurslader die ganze Historie neu und ersetzt damit auch die Entwicklungsdaten bis 2024.
- **Wirkung:** Die Tresorgrenze hält an dieser Stelle nur der Filter beim Lesen. Ein Leck wurde nicht gefunden; ein
  Betriebslauf kann aber die Datenbasis eines späteren Backtests verändern.

### 6. Festlegungsprüfung deckt nicht alles ab (niedrig; Regime-Urteil, im Lauf ohne Wirkung)

- **Stelle:** `tools/backtest_regime.py:27`.
- **Befund:** Eingefroren sind nur `docs/REGIME.md` und `src/tradingbot/engines/regime`, nicht das Werkzeug selbst,
  Simulation, Kennzahlen oder `config/`.
- **Geprüft:** Zwischen b628678 und dem Lauf gab es an diesen Dateien keine Änderung; der Lauf lief mit sauberem Stand
  b628678 (`meta.json` des Laufs).

### 7. Statische Mischung wiederholt gescheiterte Orders nicht (Hinweis; Regime-Urteil, im Lauf ohne Fall)

- **Stelle:** `engines/regime/buch.py:60-63`; Festlegung in `docs/REGIME.md:159`.
- **Befund:** Die Mischung merkt sich Gewicht und Quartal schon beim Signal. Scheitert die Order am Folgetag, kommt
  sie nicht wieder.
- **Geprüft:** Im Lauf gab es nur eine verworfene Order (02.10.2015, 1-%-Regel), keinen Tag ohne Handel.

### 8. Einordnungswerkzeug liest Tresordaten über die Betriebsfreigabe (mittel; Tresor und Prozess, c3 indirekt)

- **Stelle:** `tools/split_ereignisse_einordnen.py:63-66`; Regel in `backtest/tresor.py:114-117`; Liste
  `config/kapitalmassnahmen_historie.yaml`; `daten/kapitalmassnahmen_historie.py:123-140` und `:179`.
- **Befund:** Das Werkzeug läuft im Betriebsmodus mit `bis=heute` und lädt Kurse des ganzen Universums und SEC-Fakten
  ohne Datumsgrenze. Die Betriebsfreigabe ist nur für den Tageslauf gedacht; einen Eintrag im Tresor-Protokoll gibt es
  nicht.
- **Folge in Git:** Die Liste enthält 28 Zeilen mit Daten aus 2025/2026. Ereignisse aus 2024 können mit Einreichungen
  aus 2025 eingeordnet worden sein. Inhaltlich ist das harmlos (Split oder Abspaltung war am Ereignistag öffentlich),
  formal ist es Wissen von jenseits der Grenze.
- **Wirkung in der Rechnung:** keine, weil `korrektur` nur Ereignisse der begrenzten Kursreihe durchläuft. Der Kopf der
  Liste behauptet aber einen Datumsfilter, den `lade_ereignisse` nicht hat.

### 9. Splits nach der Tresorgrenze stehen namentlich in der Doku (niedrig bis mittel; Tresor)

- **Stelle:** `docs/FUNDAMENTAL.md:673-675` und `:692-695`, `docs/berichte/2026-11-15_rohkurse_abnahme.md`,
  `daten/cache/tiingo/roh_bis_tresor/abnahme.csv`.
- **Befund:** 22 Reihen mit verdecktem Faktor sind mit Faktor genannt (zum Beispiel ORLY 15, BKNG 25, NFLX 10,
  NKTR 1/15).
- **Begründung:** Ein Split nach 2024 ist ein Hinweis auf die Kursentwicklung im Tresorzeitraum. In Regeln oder
  Parameter fließt das nicht ein; nur die Stichprobenauswahl hängt daran.

### 10. Abnahme prüft die Tiingo-Splitspalte der Yahoo-Reihen nicht (niedrig bis mittel; c3)

- **Stelle:** `daten/rohkurse_marktwert.py:71-88`; Verwendung in `engines/fundamental/multiples.py:125-129` und
  `daten/sp500_nachbau.py:158`.
- **Befund:** Die Abnahme vergleicht nur den Rohkurs mit der Yahoo-Reihe und deren Faktoren. Die Rechnung nutzt danach
  die Tiingo-Splitfaktoren, für den Marktwert und für die Streubesitz-Prüfung.
- **Wirkung:** Fehlt bei Tiingo ein Split, ist der Marktwert um den Faktor falsch. Liegt ein Tiingo-Faktor an einem
  anderen Tag als in der Liste, bleibt er als „ungeklärt“ in der Aktienzahl.
- **Bisherige Sicherung:** nur die Vergleichsspalten in Schritt 4 der Checkliste c3 („prüfen“), ohne Kriterium und
  ohne Abbruch. Der zweite Probelauf war für die abgedeckten Reihen sauber; 158 Reihen sind noch offen.

### 11. Rückfall auf Teil b bei Reihen mit möglichem verdecktem Faktor (niedrig bis mittel; c3)

- **Stelle:** `daten/sp500_nachbau.py:210-219` (Rückfall), `daten/cache/tiingo/roh_bis_tresor/abnahme.csv`.
- **Befund:** Sieben Reihen bestehen die Abnahme nicht und rechnen nach Teil b: HWM, BX, MTCH, DD (Yahoo), GEV, AMTM,
  BXLT. Bei DD (H 0,80) und MTCH (H 0,29) weicht der Faktor von 1 ab, ist aber bei rund 50 % passenden Tagen nicht
  verlässlich bestimmt.
- **Wirkung:** Für diese Firmen sind Marktwert und Streubesitz-Prüfung nicht nur ungeprüft, sondern möglicherweise um
  den Faktor falsch. Die Regel „markiert und gezählt“ macht das im Bericht nicht sichtbar.

### 12. Streubesitz-Prüfung rechnet Abspaltungsfaktoren in die Aktienzahl (niedrig; c3)

- **Stelle:** `daten/sp500_nachbau.py:243`, `daten/index_nachbau.py:62-69`.
- **Befund:** Die Aktienzahl wird mit allen Faktoren der Prüfbasis auf Kursbasis gebracht; der Faktor K aus Teil b
  wirkt nur in der Fortschreibung.
- **Wirkung:** Liegt eine Abspaltung zwischen dem Messtag der Aktienzahl und dem des Streubesitzes, ist der Börsenwert
  um den Faktor falsch. Mit Rohreihen betrifft das nur die wenigen Abspaltungen, die Tiingo als Split führt
  (MRK 1,048), also innerhalb der Spanne 30–130 %. Im Rückfall bleiben die größeren Yahoo-Faktoren. Betroffen sind die
  Gewichte im Index-Nachbau und die Plausibilitätsprüfung des Marktwerts.

### 13. EQ_OFFER, Weg B behandelt Abspaltungen als Split (niedrig; c3)

- **Stelle:** `tools/auswertung_scores.py:144`, `engines/fundamental/aktienzahl.py:147-149`.
- **Befund:** Übergeben wird die Split-Spalte der bereinigten Reihe, die auch Abspaltungen enthält; Weg B multipliziert
  damit den Vorjahreswert.
- **Wirkung:** Eine Abspaltung zwischen den beiden Einreichungen kann fälschlich „keine neuen Aktien“ ergeben.
  Höchstens 12 von 12.595 Firmen-Stichtagen (Zahl der Fälle mit Weg B); Weg A ist nicht betroffen.

### 14. Fehlerschwelle der Abnahme sperrt c3 nicht (niedrig; c3-Ablauf)

- **Stelle:** `tools/pruefe_rohkurse.py:72` und `:95-99`, Sperre in `daten/rohkurse_marktwert.py:106-120`.
- **Befund:** `abnahme.csv` wird geschrieben, bevor die 5-%-Schwelle geprüft wird. Die Sperre prüft nur, ob ein Eintrag
  existiert.
- **Wirkung:** Nach einer überschrittenen Schwelle starten die c3-Werkzeuge technisch trotzdem; der Halt steht nur in
  der Checkliste.

### 15. CSC-Ausschüttung wird still übersprungen, wenn der Tag fehlt (Hinweis; kein gewertetes Ergebnis)

- **Stelle:** `daten/sp500_nachbau.py:97-98`.
- **Befund:** Fehlt der Ex-Tag in der Reihe, übergeht `buche_abspaltungen` den Eintrag ohne Meldung, anders als die
  SIVB-Korrektur, die laut abbricht.

## Ohne Befund geprüft

**Regime-Engine und Backtest**

- Wissensstand: Trend bis zum Bewertungstag, Marktreihen bis zum Vortag, UNRATE mit dem ALFRED-Stand des Vortags,
  Order zur nächsten Eröffnung.
- Tresor im Backtest: `stand_mit_tresor` begrenzt Beobachtungen und Wissensstand.
- Haltepflicht: Der Verlauf von V1 in der Laufablage hält sie an allen 13 Wechseln ein, und die Trades passen dazu.
- Steuerrechnung: Vorabpauschale, Teilfreistellung und Verlustvortrag 2016–2018 an den Zahlen der Ablage nachgerechnet.
- Lückenregel: Der Diff von `signale.py` gegen b628678 enthält nur die Ergänzung; ohne Lücke ergibt sie rechnerisch
  denselben Wert wie `sahm_wert`.

**Schattenbuch**

- Nachholen rechnet mit dem Wissensstand des Monatsendes, das Protokoll bleibt maßgeblich, die Haltepflicht läuft über
  die protokollierten Rohzustände.

**c2**

- Rohkurs-Marktwert: Die Formel stimmt für Split und Abspaltung; Aktienzahl und Streubesitz gelten erst ab dem Tag
  nach `filed`; die Ersatz-Aktienzahl hat den richtigen Messtag.
- Streubesitz-Prüfung mit Rohkursen: Kurs und Aktienzahl stehen auf derselben Split-Basis, auch bei einem Split
  zwischen den Messtagen.
- SIVB: Die Schutzprüfung greift. Der Kurs vom 28.03.2023 gilt rückwirkend ab 10.03. (so entschieden); ohne Wirkung
  auf Buch A, weil Finanzwert.
- Kappungen DD, DISCK, BMS: Sie wirken auf bereinigte und rohe Reihen und über `lade_firmendaten` auch im Backtest A.
- EQ_OFFER, Weg A: Der Vergleichswert stammt aus derselben Einreichung und ist ab deren `filed` bekannt.
- Stichprobe: Die Auswahl ist eingefroren und nutzt die ungeprüften Streubesitzwerte.

## Nicht geprüft (Stand 16.11.2026)

- **Teil 2:** Nachlader (`daten/tiingo_rohkurse.py`), `tools/gegenprobe_index.py`,
  `tools/obergrenze_abspaltungen_tiingo.py`. Ob BMS nach der Kappung den Delisting-Grund „Übernahme“ bekommt, ist nicht
  verifiziert (in `config/universum_korrekturen.yaml` steht nur DD).
- **Teil 3:** am 16.11.2026 nachgeholt, siehe Abschnitt „Nachtrag Teil 3“ unten.
- **Befund 2:** Verhalten von IBKR bei gegenläufigen Orders desselben Kontos.

## Reihenfolge der Behebung (Jakob 16.11.2026)

Jeweils erst Plan, dann Code, volle Testsuite vor jedem Commit.

- **Heute vor dem Tageslauf:** Teil 3 der Prüfung zu Ende führen (nur lesen); Ergebnis bis 20:00 an Jakob. Findet sich
  etwas, das am Abend schiefgehen kann, wird das Senden für „regime“ für heute gesperrt.
- **Vor dem 30.11. (Betrieb):** Befunde 2, 4, 5.
- **Vor c3 (01.12.):** Befund 3 (Steuer aus der Kasse, als Korrektur der Simulation, Zusage „unabhängig vom Ergebnis
  übernommen“ vorher festhalten, Wirkung auf das Regime-Urteil nachrechnen); Befunde 10, 11, 14 (harte Absicherung von
  c3); Befunde 12, 13, 15 und Delisting-Grund BMS.
- **Tresor (1, 8, 9):** Protokoll über das, was über den Zeitraum ab 2025 bekannt geworden ist; Einordnungswerkzeug auf
  die Tresorgrenze begrenzen; Kopf der Liste korrigieren.
  - **Hinweis zur Ablage (Jakob 16.11.2026):** eigene Datei `docs/TRESOR_BEKANNT.md`; in `docs/TRESOR_PROTOKOLL.md`
    nur ein Verweis. Grund: `docs/TRESOR_PROTOKOLL.md` ist die Datei, die `backtest/tresor.py` für die Tresor-Öffnungen
    selbst anlegt und liest; jede Tabellenzeile mit vier Spalten gilt dort als geöffnete Phase
    (`backtest/tresor.py:67-75`). Der Verweis darf deshalb keine solche Zeile sein.
- **Niedrig:** Befunde 6 und 7.
- **Danach:** die offenen Teile der Prüfung.
- **Zu den Befunden 16–18 (Jakob 16.11.2026):** Befund 17 gehört zu Befund 2 und wird mit ihm behoben (vor dem
  30.11.). Zu Befund 16: Die Flex-Abfrage ist seit dem 12.11.2026 eingerichtet.
- Die Behebung übernimmt eine neue Sitzung; dieser Bericht ist ihre Grundlage.

## Nachtrag Teil 3 (16.11.2026, nur gelesen): zwei Bücher in SPYI.DE, Verkaufslimit, Abgleich

Anlass: Am Abend des 16.11.2026 kauft „regime“ erstmals SPYI.DE, während das Realbuch SPYI.DE hält. Gelesen wurden
`betrieb/nachtrag.py`, `risiko/manager.py`, `broker/basis.py`, `broker/ibkr.py` (`sende`), `betrieb/buchstopp.py` und
die zugehörigen Stellen in `betrieb/tageslauf.py`.

**Ergebnis für den Abend: nichts gefunden, das den Kauf falsch buchen oder falsch senden würde.** Das Senden für
„regime“ wurde nicht gesperrt.

- **Kaufweg:** Derselbe Weg wie in den anderen Büchern (Limit, gültig für den nächsten Handelstag,
  `broker/ibkr.py:387-392`). Der Risk-Manager prüft Kasse, Budget, 1-%-Gebührenregel und Limitabstand gegen das Buch
  „regime“ (`risiko/manager.py:147-169`); als Core-Buch mit ETF gibt es keine Positionsgrenze (`:192-195`).
- **Zuordnung der Ausführung:** über die Kennung der Order „<Buch>:<Vorschlag>“ (`betrieb/tageslauf.py:112-116`), also
  eindeutig auch bei zwei Büchern im selben Titel.
- **Abgleich:** summiert je Titel über alle Bücher (`betrieb/buchstopp.py:44-47`); eine Abweichung in SPYI.DE stoppt
  Realbuch und „regime“, nicht den ganzen Lauf (`:55-62`). Die Kassenbasis ändert sich durch das neue Buch nicht
  (`betrieb/tageslauf.py:245-249`).
- **Gegenläufige Orders (Befund 2) heute:** nicht möglich. Das Realbuch kauft nur, und SPYI.DE steht nicht im
  Technik-Universum (`config/technik.yaml`).

### 16. Nachtrag über die Position entfällt für SPYI.DE (niedrig; Betrieb)

- **Stelle:** `betrieb/nachtrag.py:220-221`, Stopp in `betrieb/tageslauf.py:403-405`.
- **Befund:** Der Weg „Position mit Einstand“ gilt nur, wenn kein Buch den Titel hält. Weil das Realbuch SPYI.DE hält,
  bleibt für eine Ausführung von „regime“ außerhalb des API-Zeitfensters (verpasster Abend) nur die Flex-Abfrage.
- **Wirkung:** Enthält der Flex-Bericht die Ausführung nicht (nicht eingerichtet, Zeitraum zu kurz, noch nicht
  erzeugt), stoppt der ganze Tageslauf, bis der Beleg da ist. Es wird nichts falsch gebucht.

### 17. Zwei Orders im selben Titel aus zwei Büchern nach einem verpassten Abend (niedrig; Betrieb)

- **Stelle:** `betrieb/nachtrag.py:115-116`, `:218-219`, `:295-296`.
- **Befund:** Haben Realbuch und „regime“ am selben Abend je eine Order in SPYI.DE unterwegs, wird der Folgeabend
  verpasst und nur eine ausgeführt, dann gelten beide als Verdacht (die Abweichung wird je Titel gemessen). Die nicht
  ausgeführte Order hat keinen Flex-Beleg, der Weg über die Position scheidet aus („mehrere Orders unterwegs“), und
  wegen „alles oder nichts“ wird auch die belegte nicht gebucht.
- **Wirkung:** Stopp des Tageslaufs, den kein späterer Lauf von selbst auflöst. Tritt nur auf, wenn beide Bücher am
  selben Abend eine SPYI-Order senden.

### 18. Verkauf mit Limit ist im Betrieb noch nie gelaufen (Hinweis; Betrieb)

- **Stelle:** `broker/ibkr.py:393-396`, `risiko/manager.py:171-180`, `broker/basis.py:133-138`,
  `betrieb/tageslauf.py:1081-1083`.
- **Befund:** Risk-Manager, Senderiegel und Adapter sind untereinander stimmig (Limit nur im Buch „regime“ erlaubt und
  dort verlangt, höchstens 2 % unter dem letzten Kurs). Der Weg ist aber erst beim ersten Wechsel auf „Risiko aus“
  im echten Betrieb zu sehen; bis dahin ist er nur durch Tests belegt.

## Stand der Behebung (16.11.2026, nachgetragen)

| Befund | Stand | Commits | Nachweis |
| --- | --- | --- | --- |
| 3 | behoben | d1996a9, ca95bc0, f96ee50, d066bf6, 3c44de0, 5e7e851 | `docs/berichte/2026-11-16_steuer_aus_kasse.md` (Regime: Kriterium b Hälfte 2 kippt, Urteil bleibt; Technik und Phase 2 ohne Kipp) |
| 10, 11, 14 | behoben | 6b61d4c, 0a68654, a3d6439 | Kriterium „Splitspalte“ nach dem ersten Lauf geändert (Jakob); zweiter Abnahmelauf 18 von 563, `docs/berichte/2026-11-16_1247_rohkurse_abnahme.md` |
| 12 | behoben (nur c3) | a3d6439 | Tests mit Abspaltung zwischen den Messtagen |
| 13, 15, BMS | behoben | 46acbf7 | EQ_OFFER Weg B auch im Betriebsweg (bis 04.01.2027 nur Anzeige); BMS: Übernahme, 8-K Item 2.01 vom 11.06.2019 |
| 1, 8, 9 | behoben bzw. protokolliert | eeded02 | `docs/TRESOR_BEKANNT.md`; Einordnungswerkzeug nur bis zur Tresorgrenze; Kopf der Liste korrigiert |
| 6, 7 | behoben | 6f4712c (Festlegung 7g in `docs/REGIME.md`) | Mit 6f4712c trifft `tools/backtest_regime.py --vergleich-ablage` alle sechs Ablagen vom 16.11.2026 (`20261116T1004*_regime_*`, Werte, Trades, Kriterien) genau; Prüflauf 16.11.2026 ohne Abweichung. |
| 2, 17, 4, 5 | Plan freigegeben (Jakob 16.11.2026) | – | Umsetzung am 17.11.2026 nach dem Tageslauf |
| 16, 18 | Hinweise | – | Befund 16: Flex seit 12.11.2026 eingerichtet; Befund 18: erster echter Fall beim nächsten Wechsel auf „Risiko aus“ |

## Nachtrag 17.11.2026: Universum verschoben, Probe schreibt Betriebsdaten

Gefunden beim Testlauf vor dem ersten Commit (17.11.2026, etwa 10:45), nach Jakobs Freigabe vom selben Tag aufgenommen.

### 19. Universum gegen `kursstatus.csv` verschoben (hoch; Betrieb und c3)

- **Stelle:** `daten/universum.py` (`lade_wikipedia`, `lade_universum`, `universum_aktualisieren`), Zuordnung über die
  Zeilennummer in `daten/sp500_nachbau.lade_firmendaten` und `engines/fundamental/aktuell.bewertung_am`.
- **Befund:** Der Betrieb erneuert den Wikipedia-Cache wöchentlich, und diesen Cache lesen auch Backtest und c3. Der
  Abruf vom 16.11.2026 um 22:18 (Probe) brachte eine Zeile mehr (896 → 897): DAY steht neu alphabetisch an Stelle 120,
  ab dort rücken alle Zeilen um eins. Inhaltlich geändert haben sich ab 2012 nur XEC und IR (Datum um einen Tag), CDAY
  und DAY (andere Darstellung, CDAY jetzt fälschlich ohne Ende) sowie KVUE durch den echten Indexwechsel vom 30.10.2026
  (KVUE raus, OKTA neu). Weil `kursstatus.csv` an der Zeilennummer hängt, zeigen 653 von 813 Zuordnungen auf ein
  anderes Symbol. Über den Schlüssel (Ticker, von, bis) nachgemessen: 649 Statuszeilen um eins verschoben (davon eine
  zufällig mit gleichem Ticker an der neuen Stelle), 159 unverschoben, 5 ohne Treffer (XEC, IR, CDAY, DAY, KVUE).
- **Korrektur (18.11.2026):** In der ersten Fassung dieses Befunds, in `docs/BETRIEB.md` und in der Commit-Nachricht
  von bc97ac7 stand „89 Zeilen mehr, fast alle vor 2012 beendet“. Das war falsch: Diese Zeilen gab es schon vorher, sie
  stehen nur nicht in `kursstatus.csv`. Die Commit-Nachricht bleibt unverändert (gepusht); maßgeblich ist dieser Befund.
- **Wirkung:**
  - Der echte Lauf vom 16.11.2026 um 22:39 lief schon damit, weil die Probe das neue Universum für den Tag gespeichert
    hatte. Der einzige Einzelaktien-Vorschlag (P, fundamental_b) war nachweislich nicht betroffen: gleiche Zeile 893,
    Kurs gleich dem Yahoo-Schluss, eigene SEC-Daten.
  - Der Test `test_now_2020_bis_2022_mit_echten_daten` schlägt fehl. Alle c3-Werkzeuge und das Einordnungswerkzeug
    hätten falsch zugeordnet.
- **Sofortmaßnahme (17.11.2026, bc97ac7):** Wächter `pruefe_zuordnung` in `lade_firmendaten` und vor dem Kursabruf der
  Fundamental-Bewertung, mit lautem Abbruch. Im Tageslauf setzen nur die Fundamental-Bücher aus.
- **Behebung (Jakob 17.11.2026, Plan ab 18.11.2026, vor c3):**
  - Den Wikipedia-Stand für Backtest und c3 auf den Stand von `kursstatus.csv` (02.11.2026) einfrieren. Abnahme
    (freigegeben 17.11.2026): (a) 896 Zeilen, (b) alle 813 Statuszeilen passen über Zeilennummer und Schlüssel,
    (c) jede CIK aus `scores_eq_offer` (13.11.2026, 33 Stichtage) ist am Stichtag Mitglied; die betroffenen Fälle ab
    2012 einzeln im Bericht. *Korrektur 18.11.2026: Hier stand „813 Zeilen“; 813 ist die Zahl der Statuszeilen.*
  - Der Betrieb bekommt einen eigenen Wikipedia-Cache. Der Indexwechsel vom Oktober 2026 gehört nur in den
    Betriebsstand.
  - Zuordnung über den Schlüssel (Ticker, von, bis) in Betrieb **und** Backtest, zusätzlich zum eingefrorenen Stand.

### 20. Probelauf schreibt Betriebs- und Entwicklungsdaten (mittel; Betrieb)

- **Stelle:** `tools/tageslauf.py` (`--kopie`, `--probe`) über `betrieb/tageslauf.tageslauf` mit
  `universum_aktualisieren`, `aktuell.kurse_aktualisieren` und den SEC-Abrufen.
- **Befund:** Die Probe vom 16.11.2026 (22:17 bis 22:30) hat geschrieben:
  - 515 Kursdateien,
  - beide Wikipedia-Seiten,
  - das Universum,
  - drei SEC-Einreichungen.

  Der echte Lauf um 22:39 hat das Universum daraus übernommen.
- **Regel (Jakob 17.11.2026):** Eine Probe darf keinerlei Betriebsdaten verändern: keine Kurse, kein Wikipedia, kein
  Universum, keine SEC-Daten. Dass die Probe seit Befund 5 in den Kurs-Cache des Betriebs schreibt, ist bis dahin in
  Ordnung. Plan zusammen mit Befund 19.

## Stand der Behebung (17.11.2026, nachgetragen)

| Befund | Stand | Commits | Nachweis |
| --- | --- | --- | --- |
| 5 | behoben | 9c37723 | Eigener Kurs-Cache des Betriebs `daten/betrieb/cache/kurse`; einmalige Übernahme ohne Downloads, auch im Probelauf, Protokollzeile mit Zahl der Dateien; Test: Split-Neuladen im Betrieb lässt den Standard-Cache byteweise unverändert |
| 19 (Sofortmaßnahme) | Sperre | bc97ac7 | `pruefe_zuordnung`; Tageslauf: nur die Fundamental-Bücher setzen aus |
| 17 | behoben | 7c68e2c | Flex-Zeitraum deckt den Handelstag ab und die Belege erklären die Abweichung, dann gilt die Order ohne Treffer als verfallen; Test mit dem Szenario aus dem Befund und zwei Gegenfällen |
| 4 | behoben | 380e952 | Datenstand im Protokoll, nachgeholte Bewertung ohne Vortageswert, Meldung „Datenstand“ bei alten Einträgen; `docs/REGIME.md` 9c (bricht den Freeze 7g, gewollt) |
| 2 | behoben | 4622221 | Gegenläufige Orders über Bücher: Verkauf vor Kauf, bestehende Order hat Vorrang; Meldung, Ereignis, Sofortmeldung |
| 9 (Rest) | behoben | dieser Commit | `tools/pruefe_rohkurse.py` nennt H ≠ 1 nur als Anzahl |
| 8 (Rest) | offen | – | Lauf des begrenzten Einordnungswerkzeugs zurückgestellt, bis Befund 19 behoben ist (Checkliste c3, Schritt 1b) |
| 19 (Zahl) | korrigiert | dieser Commit (18.11.2026) | „89 Zeilen mehr“ war falsch; richtig 896 → 897, nachgemessen am Cache vom 16.11.2026 22:18 |
| 19, 20 | offen | – | Plan freigegeben (Jakob 17.11.2026), Umsetzung ab 18.11.2026 |

Alle Commits vom 17.11.2026 mit der vollen Suite: alles grün außer dem bekannten roten Test aus Befund 19. Das Committen
mit diesem Vermerk hat Jakob freigegeben.
