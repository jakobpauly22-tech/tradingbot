# Betrieb (Paper Trading) – Abweichungen und Festlegungen

Ablauf am Abend: `docs/BETRIEB_ABEND.md`.

## Abweichungen zum Backtest

| Seit | Abweichung | Grund | Wirkung |
| --- | --- | --- | --- |
| 03.11.2026 | **Routing über SMART** mit Xetra (IBIS2) als Primärbörse, Kontrakt per conId, statt Direktrouting an IBIS2 | Direktrouting blockieren die API-Vorsichtseinstellungen (Fehler 10311). Die Einstellungen im Gateway bleiben unverändert (Jakob). | Die Ausführung liegt nicht zwingend in der Xetra-Eröffnungsauktion, die der Backtest unterstellt (Eröffnungskurs). IBKR kann an einen anderen Platz routen, etwa gettex oder Tradegate. Der Ausführungsplatz steht je Ausführung im Journal (`ausfuehrungen.boerse`), damit sich die Abweichung messen lässt. |
| 04.11.2026 | **US-Käufe als Limit-On-Open** (tif OPG) | Ausführung zur Eröffnung, unabhängig von der Freigabezeit | Nimmt IBKR OPG für ein Papier nicht an, wird die Order abgelehnt gemeldet. Ein Ersatz-Ordertyp kommt nur mit Jakobs Zustimmung. Je Ausführung stehen Zeit, Handelsplatz und Eröffnungskurs des Heimatplatzes im Journal, die Abweichung im Protokoll. |
| 04.11.2026 | **Nachkauf abgelehnter oder verfallener Käufe** | Restfall eines Aufbaus (Jakob) | Fundamental: bis zum nächsten Quartalsstichtag, mit dem Gewicht vom letzten Stichtag. Technik: solange das Signal gilt (Crossover SMA50 > SMA200, Momentum 12−1 > 0). Der Backtest kennt keine Ablehnungen. |
| 03.11.2026 | **Stückzahl der Technik-Käufe zusätzlich durch die 1-%-Regel vom Limit begrenzt** | Risiko vom schlechtesten Einstieg (Jakob) | Der Backtest begrenzt über das Gewicht (Risiko vom Schluss, Ausführung zur Eröffnung); im Betrieb können es einzelne Stücke weniger sein. Zielgewichte, Reihenfolge nach Stärke und Restkasse kommen aus derselben Funktion `SatelliteStrategie.zielgewichte` wie im Backtest. |
| 03.11.2026 | **Kauflimit auf die gültige Kursstufe abgerundet** (reqMarketRule, gemeinsame Stufe der Regeln von SMART und Xetra) | Fehler 110: SXR1 221,34 € verletzt die Stufe 0,05 € ab 200 € | Das Limit liegt höchstens eine Kursstufe unter Vortagesschluss + 2 %, die 2-%-Grenze bleibt eingehalten. Verkaufslimits (falls künftig) werden aufgerundet. |

## Gebühren (04.11.2026)

- **Preismodell:** Das Kostenmodell (`config/backtest.yaml`, 1,25 € Minimum an EUR-Börsen) setzt das IBKR-Modell
  „Gestaffelt“ (Tiered) voraus. Das echte Konto ist seit 04.11.2026 darauf umgestellt; vorher galt Festpreis mit 3 €
  Minimum bei SMART.
- **Buchung (Entscheidung Jakob 04.11.2026, ersetzt die Festlegung vom Vormittag):** Das Paper-Konto rechnet Festpreis,
  3 € je Order, und lässt sich nicht umstellen. Journal und Kasse buchen deshalb die tatsächliche IBKR-Gebühr; die Kasse
  je Währung ist Teil des Abgleichs (Toleranz 0,05, Kassenbasis einmalig festgehalten). Die Modellgebühr (Tiered,
  1,25 € Minimum) steht je Ausführung daneben (`gebuehr_modell_eur`). Der Bericht weist den Buchwert zweimal aus: „wie
  gebucht (Paper, Festpreis)“ und „mit Modellgebühr (Tiered)“. Maßgeblich für den späteren Echtbetrieb ist der zweite.
  Der Risk-Manager prüft weiter mit der Modellgebühr. Die gemeldete IBKR-Gebühr steht täglich im Protokoll, damit ein
  späterer Wechsel des Paper-Kontos auf Tiered auffällt.

## Kontrakte (04.11.2026)

`config/kontrakte.yaml` (`tools/kontrakte_pruefen.py`, nur lesend) ordnet 514 Werte zu: Core, Satellite, Xetra-Gold,
EUR.USD (IDEALPRO) und die S&P-500-Aktien. Nicht auflösbar, also beim Senden Veto „Kontrakt unbekannt“:
- **SXRM.DE:** Die ISIN IE00B3VWN518 ist bei IBKR nicht an Xetra handelbar, nur an der SIX (CSBGU0, USD) und der LSE.
  Ob ein Ersatz oder ein anderer Platz kommt, entscheidet Jakob. Bis dahin kann der Satellite diesen Wert nicht kaufen.
- **KVUE:** Unter SMART/USD gibt es keinen Treffer (vermutlich nach der Übernahme nicht mehr gelistet).

## Zusammensetzung des S&P 500 (04.11.2026)

Quelle ist Wikipedia (aktuelle Liste und Änderungstabelle), Stand 01.11.2026; die letzte erfasste Änderung ist vom
06.10.2026 (TWLO rein, WBD und CTVA raus). Kenvue (KVUE) steht dort noch als Mitglied. Der letzte Yahoo-Kurs ist aber
vom 30.10.2026, und bei IBKR gibt es keinen Kontrakt; vermutlich ist die Notierung nach der Übernahme durch Kimberly-Clark
beendet. Seitdem entfernt der Tageslauf vor der Rangliste jeden Titel, dessen letzter Kurs älter als 5 Handelstage ist
oder der in `config/kontrakte.yaml` unter `nicht_aufloesbar` steht, und meldet ihn.

## Ersatz für SXRM (offen, Entscheidung Jakob)

SXRM (IE00B3VWN518) ist bei IBKR nicht an Xetra handelbar. Kandidaten mit demselben Index (ICE US Treasury 7–10 Year)
gibt es nur bei iShares:
- **iShares $ Treasury Bond 7-10yr UCITS ETF USD (Dist), IE00B1FZS798, Xetra IUSM:** Yahoo-Historie ab 02.2009,
  ausschüttend wie IUSA. Replikation laut Quellen „optimiert/Sampling“, also physisch, aber nicht vollständig.
- **EUR-Hedged (Dist) IE00BGPP6697 und (Acc) IE000K1VI152:** Sie folgen der währungsgesicherten Variante des Index.
  Die Xetra-Historie (IBB1 ab 02.2019) reicht nicht bis 2012 zurück.
- Andere 7–10-Jahre-ETFs (Invesco, Xtrackers, Amundi, SPDR) folgen Bloomberg- oder iBoxx-Indizes, nicht dem ICE-Index.

**Entscheidung (Jakob 04.11.2026):** IUSM ersetzt SXRM (gleicher Fonds, ausschüttende Klasse, analog IUSA statt SXR8).
Ausschüttungen fließen wie bei IUSA in die Kasse; es gibt keine neue Variante. Eingetragen in `config/technik.yaml`. Den
Kontrakt trägt `tools/kontrakte_pruefen.py` nach dem Gateway-Start ein, nur wenn IBKR IUSM an Xetra in EUR führt. Bis
dahin bekommt IUSM wie zuvor SXRM ein Veto „Kontrakt unbekannt“.

## Kassenbasis und Zeitfenster (04.11.2026)

- Buchungen ohne Buchbezug (Zinsen, Kontogebühren) gehen in die Kassenbasis und werden protokolliert (Ereignis
  `kassenbasis`, Liste im Zustand `_konto`). Der Abgleich stoppt nur, wenn eine Abweichung je Währung 10 € übersteigt
  (`sicherheit.abgleich_buchung_ohne_buchbezug_max`). Ob eine Buchung bis 10 € tatsächlich Zins oder Gebühr ist, kann die
  API nicht belegen (dafür wären Flex-Abfragen nötig). Sie gilt deshalb als „vermutet“ und steht im Protokoll.
- **Zeitpunkt der Freigabe:** Für US-Käufe (Limit-On-Open) und den EUR→USD-Tausch zeigt der Tageslauf einen Hinweis, und
  bei der Freigabe erscheint eine Warnung in der Bestätigung: nicht vor 22:00 Uhr (US-Handel offen) und nicht zwischen
  22:55 und 23:15 Uhr (FX-Tagesschluss). Empfohlen sind 22:05–22:50 Uhr. Das ist ein Hinweis, keine Sperre.
- **S&P-500-Liste:** Sie wird wöchentlich erneuert (Wikipedia-Cache höchstens 7 Tage alt) und an jedem Quartalsstichtag
  zwingend neu abgerufen. Den Stand zeigt das Protokoll: Abruf der Liste und letzte erfasste Änderung.

## Verpasste Abende: Ausführungen außerhalb des API-Zeitfensters (09.11.2026)

- **Anlass:** Vom 04. bis 08.11.2026 lief kein Tageslauf. Die fünf Orders vom 03.11. wurden am 04.11. ausgeführt, aber
  `reqExecutions` liefert über das Gateway nur den laufenden Tag (am 09.11. geprüft: 0 Ausführungen, auch mit Zeitfilter
  ab 01.11.). Der alte Tageslauf hätte die Orders als „verfallen“ markiert (und als Nachkauf erneut vorgeschlagen) und dann
  am Bestands-Abgleich gestoppt.
- **Festgelegter Weg** (`betrieb/nachtrag.py`, im Tageslauf vor dem Abgleich): Eine Order unterwegs, deren Handelstag vorbei
  ist und die bei IBKR nicht mehr offen ist, gilt nur dann als verfallen, wenn die IBKR-Position nicht von den Büchern
  abweicht (Tausch: USD-Kasse). Weicht sie ab, wird mit Beleg nachgetragen und gemeldet: (a) Flex-Abfrage (Trades;
  `FLEX_TOKEN`, `FLEX_QUERY_ID` in `.env`), sonst (b) Position mit Einstand, nur bei Käufen, die die Position
  allein erklären. Der Preis ergibt sich als Einstand minus angenommener Gebühr je Stück (`config/betrieb.yaml`,
  `nachtrag.gebuehr`, je Markt und Währung, siehe unten), plausibilisiert gegen Limit und Tief/Hoch des Ausführungstags. Ohne Beleg stoppt der Lauf,
  nichts wird gebucht oder verfallen. Quelle je Ausführung in `ausfuehrungen.quelle`, Ereignis `nachtrag` im Journal.
  Werkzeug ohne Tageslauf: `tools/ausfuehrungen_nachtragen.py` (Trockenlauf auf Kopie, `--buchen` mit Sicherung).
- **Beleg des Einstands:** IBKR führt den Einstand inklusive Gebühr. Geprüft am 09.11.: Einstand × Stück − 3,00 € ergibt
  glatte Kurse (IUSA 67,39, SXR1 218,10, IJPA 70,86, IEMA 52,568), und die Kontokasse 990.709,16 € = 1.000.000,00 € −
  9.290,84 € (Summe Einstand × Stück) passt auf den Cent.
- **Kassenbasis erst nach stimmendem Bestand:** Der Kassen-Abgleich (und damit das erstmalige Festhalten der Kassenbasis)
  läuft nur noch, wenn der Bestands-Abgleich stimmt. Sonst hätte die Basis fehlende Käufe verschluckt.
- **Kontokasse:** Das Paper-Konto meldet die Kasse als `$LEDGER-CashBalance`, nicht als `CashBalance`. Bis 09.11. blieb
  der Kassen-Abgleich deshalb stillschweigend ungeprüft („IBKR meldet keine Kontokasse“). Aufgelaufene, noch nicht
  gebuchte Zinsen (`AccruedCash`, am 09.11. 225,74 €) zählen nicht. Werden sie gebucht, gehen sie als Buchung ohne
  Buchbezug in die Kassenbasis, wenn sie unter 10 € liegen. Bei mehr stoppt der Abgleich (siehe offene Punkte im
  Bericht vom 09.11.2026).
- **Probelauf auf einer Kopie des echten Journals:** `tools/tageslauf.py --kopie` (Gateway nur lesend, sendet nie, keine
  Sicherung).

## Entscheidungen Jakob 09.11.2026 (nach dem Nachtrag)

- **Verpasste Tage im Technikbuch:** Der Tageslauf prüft die Schlusskurse seit dem letzten Lauf der Reihe nach (Signaltag
  des Vorlaufs im Strategiezustand, `vor_signaltag`). Ausstiege aus verpassten Tagen (Stop, Signalende, Zeit-Stop) werden
  wie im Backtest zur nächsten Gelegenheit nachgeholt; der Vorschlag nennt den Tag („Stop 69.04 gerissen am 06.11.,
  nachgeholt“). Einstiege verpasster Tage werden verworfen, gekauft wird nur, wenn das Signal am aktuellen Tag gilt (auch
  die Monatsprüfung von Momentum läuft am aktuellen Tag). Fundamental- und Realbuch haben keine Tagesausstiege.
- **Zinsen (Jakob 09.11., Zinsbilanz 10.11.2026):** Eine Kassenerhöhung ist eine belegte Zinsbuchung, wenn die
  aufgelaufenen Zinsen (`AccruedCash`) gesunken sind und die **Zinsbilanz** (Gutschrift + aktueller Zinsstand − letzter
  Zinsstand, also die seit dem letzten Lauf neu entstandenen Zinsen) zwischen −0,05 € und geschätztem Tageszins ×
  Kalendertage seit dem letzten Lauf + 1 € liegt. Das deckt zwei Fälle:
  - Die Gutschrift enthält Tage nach dem letzten Lauf.
  - Gutgeschrieben wird nur der Vormonat, während der letzte Lauf schon Tage des neuen Monats enthielt (Rest im neuen
    Zinsstand).

  Weitere Regeln:
  - Der Tageszins wird aus der Veränderung der aufgelaufenen Zinsen zwischen zwei Läufen ohne Gutschrift geschätzt.
    Ohne Schätzung gilt nur der Zuschlag von 1 €.
  - Belegte Zinsbuchungen gehen in die Kassenbasis, mit Ereignis und Protokoll, ohne Stopp. Die Bücher erhalten keine
    Zinsen (wie im Backtest).
  - Andere Abweichungen über 10 € stoppen weiter.
  - Zinsstand, Datum (`zinsstand_tag`) und Tageszins hält jeder stimmende Abgleich im Zustand `_konto` fest.
- **Flex:** Token und Abfrage-ID nur in der `.env` als `FLEX_TOKEN` und `FLEX_QUERY_ID` (richtet Jakob ein).
- **Gebühr beim Nachtrag über die Position**, je Markt und Währung (`nachtrag.gebuehr`): Xetra EUR 3,00 € je Order
  (Paper-Festpreis); US-Aktien nach IBKR Pro Fixed, 0,005 USD je Aktie, mindestens 1,00 USD, höchstens 1 % des
  Orderwerts (Quelle: interactivebrokers.com/en/pricing/commissions-stocks.php, geprüft 09.11.2026; FINRA-CAT-Gebühr
  0,000003 USD je Stück vernachlässigt). Die Gebühr ist als „angenommen“ markiert (`ausfuehrungen.gebuehr_angenommen`;
  die fünf Nachträge vom 09.11. ebenso). Beim nächsten Flex-Abruf werden sie abgeglichen: Die abgeleitete Zeile wird
  durch die Flex-Ausführungen ersetzt, alt und neu stehen im Ereignis `nachtrag_abgleich`. Weicht die Stückzahl ab, stoppt
  der Lauf. Fehlt eine Order in der Flex-Abfrage, bleibt sie „angenommen“ (Zeitraum der Abfrage weit genug wählen).

## Read-Only-Vorfall 09.11.2026 und Prüfung vor dem Senden (10.11.2026)

- **Ablauf laut Journal, Freigabeprotokoll und Windows-Ereignisanzeige:**
  - 22:06:48: Freigabe mit Read-Only im Gateway. Die ersten beiden Orders (Crossover: Verkauf EUNN.DE, Kauf EUNK.DE)
    bekamen 22:07:05–21 Fehler 321 („Die API befindet sich im schreibgeschützten Modus“, Status ValidationError) und
    gelangten nie zu IBKR.
  - Ab 22:07:22: Die nächsten Orders (Tausch EUR→USD fundamental_a und _b, 20 + 17 US-Käufe) nahm IBKR sofort an
    (PreSubmitted, permId 192793080–117).
  - 22:07:36: Windows schloss das Fenster („Application Hang“). Das Senden lief im Fenster-Thread, und allein die
    Wartezeiten auf die beiden Ablehnungen (je 8 s) froren es ein. WMT und WST wurden deshalb erst im zweiten Lauf um
    22:08 gesendet, zusammen mit den 4 Momentum-Orders.
- **Festgehalten (Jakob 10.11.2026): Das Gateway parkt unter Read-Only blockierte Orders und sendet sie beim Abschalten
  nach.** Darauf, dass Read-Only das Senden blockiert, ist also kein Verlass; deshalb prüft der Bot vor dem Senden selbst.
  Anmerkung aus dem Abgleich: Die beiden Crossover-Orders mit Fehler 321 wurden nicht nachgesendet. Die Orders, die bei
  IBKR angekommen sind, hat der Bot nach seinem Protokoll erst ab 22:07:22 übergeben und IBKR sofort bestätigt. Ein
  Parken lässt sich aus den Protokollen nicht belegen, aber auch nicht ausschließen. Die Folgerung gilt unabhängig davon.
- **Prüfung vor jedem Senden** (`IbkrBroker.schreibzugriff`): eine reine Abfrage ohne Order (`reqCompletedOrders`). Unter
  Read-Only antwortet das Gateway sofort mit Fehler 321 (geprüft 10.11.2026). Fehler 321 oder keine Antwort in 3 s
  bedeutet: kein `placeOrder`, auch kein Tausch, und die Meldung „Read-Only im Gateway ist aktiv – bitte ausschalten und
  Tageslauf neu starten“. Kommt trotzdem während des Sendens eine 321-Ablehnung, bricht der Bot sofort ab und übergibt
  keine weitere Order. `ValidationError` zählt als „abgelehnt“, nicht mehr als „unbestätigt“.
- **Fenster:** Zwischen den Orders und während des Wartens auf IBKR verarbeitet das Fenster seine Ereignisse
  (kein „Keine Rückmeldung“ mehr). Ein zweites Senden ist gesperrt, solange eines läuft. Jede Ausnahme beim Senden wird
  zur Meldung (Ereignis `senden_abbruch`) und beendet das Fenster nie.
- **Korrektur des Journals** (`tools/journal_korrektur_20261110.py`, nichts storniert):
  - Die beiden Crossover-Orders sind von „unbestaetigt“ auf „abgelehnt“ gesetzt.
  - Der Crossover-Strategiezustand ist auf den Stand nach dem Lauf vom 03.11. zurückgesetzt. Der Tageslauf am 10.11.
    prüft damit die Tage ab 04.11. und schlägt den nachgeholten EUNN-Stop und EUNK neu vor.
  - Alle 41 bei IBKR angekommenen Orders standen schon korrekt als „gesendet“ mit Order-ID im Journal.

## Neue Oberfläche des Tageslaufs (Jakob 10.11.2026)

- **Variante A: Tkinter mit ttk**, Theme sv-ttk 2.6.1 (reines Python/Tcl, unter Python 3.15/Tk 9.0 geprüft; Extra
  `oberflaeche` in `pyproject.toml`, ohne das Paket ein eingebautes Theme). **Eine spätere Weboberfläche wäre nur zur
  Anzeige; Senden bleibt ausschließlich in Tkinter.**
- **Start:**
  - `Tageslauf_neu.bat` (`tools/tageslauf.py --neu`): echtes Journal.
  - `Tageslauf_Probe_neu.bat` (`--neu --kopie`): Probe auf einer Kopie des echten Journals, Gateway nur lesend, sendet
    nie.
  - Die alte Oberfläche (`Tageslauf.bat`, `betrieb/oberflaeche.py`) bleibt Reserve. Umgestellt wird erst nach einem
    sauberen Probelauf und einem echten Abend mit der neuen Oberfläche.
- **Nur Darstellung:** Die Daten kommen aus `betrieb/ansicht.py` (nur lesend). Freigabe und Senden laufen unverändert
  über `freigeben_und_senden`. Wählbar ist wie bisher: ohne Veto, in freigeschalteten Büchern (Probe: alle), Realbuch
  einzeln, Skalierungsbücher als Sammelfreigabe. Neu im Laufergebnis, nur zur Anzeige: Signaltage (Xetra/NYSE), letzte
  Schlusskurse in EUR, SPYI-Reihe.
- **Kopfzeile mit Ampel:**
  - Gateway, Schreibzugriff (Read-Only) und Freigabefenster.
  - Uhrzeit US/FX, alle 30 s neu.
  - Letzter Tageslauf: gelb bei verpassten Handelstagen.
  - Datenstand der Schlusskurse und Senden je Buch.
  - Im Probe-Modus ein oranges Band.
  - Gateway und Schreibzugriff werden **nur beim Start und per „Status prüfen“** geprüft (reine Abfrage ohne Order).
    Bei Read-Only ist „Freigeben und senden“ gesperrt, bis „Status prüfen“ grün zeigt. Vor dem Senden prüft der Bot
    zusätzlich selbst.
- **Übersicht je Buch:**
  - Buchwert wie gebucht und mit Modellgebühr; Kasse je Währung mit reserviertem Anteil.
  - Positionen einklappbar, mit Ø Kaufkurs, Kurs und Wert; offene Orders.
  - **Entwicklung seit Messbeginn:** Buch als TWR (`kennzahlen.performance.zeitgewichtete_rendite`) gegen SPYI Kauf und
    Halten ab dem Schlusskurs am Messbeginn, ohne Kosten, Bruchstücke, mit denselben Einzahlungen wie das Buch (zurzeit
    nur das Startkapital; weitere Einzahlungen führt das Journal noch nicht).
- **Vorschläge:** Tabelle mit Filter je Buch und Detailbereich.
- **Protokoll:** eigener Reiter, Meldungen farbig (ok, Hinweis, Fehler), Filter „nur Hinweise und Fehler“.

### Nach dem ersten Probelauf (10.11.2026)

- **Orders unterwegs (Logikfehler im Probelauf 10:04, galt für beide Oberflächen):** Der Probelauf hat die 39 US-Käufe
  von fundamental_a und fundamental_b als verfallen markiert und neu vorgeschlagen, dazu einen Tausch. Die Ursachen:
  - Die Probe-Verbindung (Client-ID 94) sah die offenen Orders von Client 1 nicht.
  - „Handelstag vorbei“ wurde am Signaltag gemessen (NYSE 06.11.), nicht an der Sitzung, für die die Order gilt (10.11.).

  Behoben:
  - Eine Order gilt für die erste Eröffnung ihres Heimatplatzes nach dem Senden (`nachtrag.gueltig_fuer`).
  - Offene Orders werden über `reqAllOpenOrders` für alle Client-IDs gelesen.
  - **Fundamental-Bücher mit Orders unterwegs gelten als aufgebaut** (Jakob): kein Aufbau, kein Nachkauf, kein Tausch;
    nur der Quartalsstichtag rechnet trotzdem.
  - Folge: Läuft der Tageslauf vor dem NYSE-Schluss, gelten nicht ausgeführte US-Käufe bis zum nächsten Abend als
    unterwegs.

  Test: `tests/betrieb/test_unterwegs.py`.
- **Probe sperrt wie der echte Lauf:** Bei Read-Only (oder ohne Gateway) ist „Freigeben“ auch im Probe-Modus gesperrt,
  bis „Status prüfen“ grün zeigt. Die Probe sendet trotzdem nie.
- **Titel:** „Name (Kürzel)“. Die Namen kommen aus lokalen Quellen, ohne Netz:
  - ETFs und ETCs: `config/technik.yaml` (ohne „(Acc)/(Dist)“); Core: `config/betrieb.yaml` (`core.name`).
  - US-Aktien: zuerst der Yahoo-Namenscache (`daten/cache/namen/yahoo.json`, richtige Schreibweise, z. B. „Domino's
    Pizza“), dann SEC `company_tickers` und der IBKR-Name aus `config/kontrakte.yaml`. SEC und IBKR schreiben in
    Großbuchstaben ohne Apostroph („DOMINOS PIZZA INC“) und dienen nur als Ersatz.
  - Die Rechtsform (Inc., Corporation, Ltd. …) wird weggelassen.
- **Detailbereich:** rechts, verschiebbar, anfangs etwa 40 % der Breite, scrollbar. Gegliedert in:
  - Kopf (Name, Buch, Aktion, Stück, Limit, Wert).
  - Warum.
  - Kennzahlen als Tabelle (Kennzahl, Wert, Branchenmedian, ✓/✗ farbig). Accruals und KGV sind besser, wenn sie unter
    dem Branchenmedian liegen; EBIT/EV, wenn darüber.
  - Filter als Ampel: Piotroski ≥ 7 grün, 4–6 gelb, ≤ 3 rot; Altman nach Zone; Beneish über −1,78 rot.
  - Was dagegen spricht (orange), mit den Hinweisen des Risk-Managers.
  - Widerlegt, wenn.
  - Technisches (conId, Routing, These) eingeklappt.

  Bei Technik-Vorschlägen: Kurs, SMA50, SMA200, Abstand, Momentum, Stop und maximaler Verlust in €. Die Werte kommen aus
  dem neuen Anzeigefeld `BuchVorschlag.daten`; die Rechnung bleibt unverändert.
- **Farben:**
  - Aktion als Schriftfarbe: Kauf grün, Verkauf rot, Tausch blau.
  - Status als Hintergrund der Zeile, weil `ttk.Treeview` keine einzelnen Zellen färben kann: Veto hellrot, freigegeben
    hellgelb, gesendet hellblau, ausgeführt hellgrün, abgelehnt/verfallen grau.
  - Abweichung zu SPYI grün oder rot. Alles andere neutral.

## Benachrichtigungen (Jakob 12.11.2026)

Modul `betrieb/benachrichtigung.py`, Schalter in `config/betrieb.yaml` (`benachrichtigung`), Zugangsdaten nur in `.env`.

- **(a) Kurzfassung** nach jedem echten Tageslauf per Telegram: Signaltage, Abgleich ok, gestoppt oder nicht geprüft,
  Vorschläge je Buch (frei/Veto), Bücher mit Datenbefund, abgelehnte und verfallene Orders seit dem letzten Lauf,
  Buchwert je Buch (wie gebucht und mit Modellgebühr, gegenüber Startkapital und Vortag).
- **(b) Erinnerung**, wenn an einem Xetra-Handelstag bis 22:00 kein Tageslauf lief (auch ein gestoppter Lauf zählt als
  gelaufen):
  - lokal: Aufgabe „TradingBot Waechter“ Mo–Fr 22:00 (`tools/waechter.py`, einrichten mit
    `powershell -ExecutionPolicy Bypass -File tools\waechter_einrichten.ps1`); Ergebnis in `daten/betrieb/waechter.log`.
    An Xetra-Feiertagen unter der Woche sendet der Wächter nur ein Lebenszeichen an Healthchecks.
  - extern: Healthchecks.io bekommt nach jedem echten Lauf ein Lebenszeichen ohne Inhalt. Einstellung des Checks: Cron
    `0 18 * * 1-5`, Zeitzone Europe/Berlin, Karenz 4 h 30 min; Benachrichtigung über die Telegram-Integration von
    Healthchecks. Damit kommt die Erinnerung um 22:30 auch bei ausgeschaltetem Laptop. Grenzen: Ein Lauf vor 18:00 deckt
    den Tag nicht ab; an Xetra-Feiertagen bei ausgeschaltetem Laptop gibt es einen Fehlalarm.
- **(c) Sofortmeldung:** Stopp im Tageslauf (als Kurzfassung mit Kopfzeile „GESTOPPT“), Ausnahme im Tageslauf (nur der
  Typ, dazu Lebenszeichen „fail“), Probleme beim Senden (abgelehnt, unbestätigt, Veto bei der zweiten Prüfung, Gateway
  nicht verbunden, Abgleich vor dem Senden weicht ab, Read-Only, Abbruch). Grenze: Lehnt IBKR eine Order erst zur
  Eröffnung ab, erfährt der Bot das erst beim nächsten Abendlauf.
- **Sicherheit:** Der Bot sendet nur (Telegram `sendMessage`), ruft nie Nachrichten ab und öffnet keinen Port; über
  Nachrichten lässt sich nichts auslösen. Inhalte kommen aus einer Positivliste; Freitexte des Tageslaufs (etwa
  Kassenstände des Kontos im Stopptext) gehen nie hinaus, aus einem Stopp nur Kategorie und betroffene Titel. Konto-IDs
  und Werte geheimer `.env`-Variablen werden vor dem Versand zusätzlich entfernt. Ein Fehler beim Melden bricht den
  Tageslauf nie ab und steht im Protokoll (Ereignis `benachrichtigung`). Probe und Kopie melden nie.
- **Echtbetrieb:** `eurobetraege: false` zeigt nur Prozente und Status.
- **Einrichtung (Jakob):** Bot bei @BotFather anlegen, Token als `TELEGRAM_BOT_TOKEN` in `.env`; dem Bot eine Nachricht
  schreiben und die Chat-ID einmalig über `https://api.telegram.org/bot<Token>/getUpdates` im Browser ablesen, als
  `TELEGRAM_CHAT_ID` eintragen (der Bot selbst ruft getUpdates nie auf). Check bei Healthchecks.io anlegen, Ping-URL als
  `HEALTHCHECKS_PING_URL`.
- **Verbindungstest:** `.venv\Scripts\python tools\verbindungstest.py` schickt nur „Verbindung ok“ per Telegram und
  pingt Healthchecks über `…/log` (Eintrag im Protokoll ohne Statuswechsel, überdeckt also keinen ausgefallenen
  Abendlauf). Liest weder Journal noch Gateway; Exit-Code 1, wenn etwas nicht eingerichtet ist oder fehlschlägt.

## Bardividenden und Quellensteuer (A0, Jakob 12.11.2026)

Modul `betrieb/dividenden.py`, Einstellungen in `config/betrieb.yaml` (`dividenden`), Tabelle `kassenbuchungen` im Journal.

- **Beleg:** nur Flex-Bargeldtransaktionen (*Dividends*, *Payment In Lieu Of Dividends*, *Withholding Tax*). Kein Buchen
  ohne Flex-Beleg. Gebucht wird automatisch mit Meldung, je `transactionID` und Buch genau einmal; Storno- und
  Korrekturzeilen sind eigene Belege mit Vorzeichen.
- **Aufteilung:** Bestand je Buch zum Handelsschluss vor dem Ex-Tag (Kauf am Ex-Tag: kein Anspruch). Probe:
  Buchstücke × Satz je Stück (aus der Flex-Beschreibung) = Brutto auf 0,05; sonst keine Buchung und Stopp
  („Dividendenbeleg nicht verbuchbar“). Anteilig nach Stück, auf Cent gerundet, Rest an das letzte Buch. Quellensteuer
  folgt der Aufteilung der zugehörigen Dividende (actionID, sonst Conid und Zahltag).
- **Währung:** in der Originalwährung (USD-Dividende in die USD-Kasse des Buchs), Eurowert zum Kurs des Laufs.
- **Steuer:** jede Buchung trägt einen Hinweis „zu prüfen“ (Kapitalertrag § 20 Abs. 1 Nr. 1 EStG; Quellensteuer
  anrechenbar nach § 32d Abs. 5 EStG; Ersatzzahlung).
- **Zahltag:** Flex reicht nur bis zum Vortag. Der Kassenabgleich hält jede Abnahme von `AccruedDividend` mit dem
  Kassenzugang fest. Ist `dividenden.vormerkung` an und `accrued_dividend_ausweis` (netto/brutto) eingetragen, wird ein
  passender Zugang als „Flex-Beleg folgt“ vorgemerkt statt übernommen oder gestoppt; Dividende und Zinsgutschrift am
  selben Tag: der Rest muss die Zinsregel erfüllen. Bestätigt Flex die Vormerkung nicht innerhalb von 3 Xetra-
  Handelstagen oder weicht Flex-Netto über 0,05 ab: Stopp und Sofortmeldung. Offene Vormerkung: gelbe Lampe
  „Dividenden“ und Zeile in der Kurzfassung.
- **Prüfung brutto/netto:** Beim ersten echten Fall vergleicht der Lauf die Abnahme von `AccruedDividend` mit Brutto und
  Netto laut Flex und meldet das Ergebnis (Ereignis `dividende`). Erst danach trägt Jakob den Ausweis ein und schaltet
  `vormerkung` an. Bis dahin: Zahltag bis 10 € als „vermutet“ in die Kassenbasis, darüber Stopp für einen Tag.
- **„vermutet“-Übernahmen:** stehen in der Kurzfassung (Währung und Betrag; ohne Eurobeträge nur „Kassendifferenz
  übernommen“). Belegt Flex später eine Dividende im selben Zeitfenster mit gleichem Betrag, wird die Übernahme aus der
  Kassenbasis zurückgenommen (keine Doppelzählung).

## Kapitalmaßnahmen: Erkennen und Stopp je Buch (A1, Jakob 12.11.2026)

A1 erkennt Kapitalmaßnahmen und stoppt das betroffene Buch. A1 selbst bucht nichts: Split, Reverse-Split und Tickerwechsel bucht A2 (Abschnitt unten), Übernahme und Delisting kommen in A3, Abspaltung in A4.

- **Quelle:** Flex-Abschnitt „Corporate Actions“ (`CorporateAction`, `betrieb/kapitalmassnahmen.py`). Die Typ-Kürzel stammen aus der IBKR-Referenz (geprüft 12.11.2026):

  | Kürzel | Bedeutung | Art im Journal |
  | --- | --- | --- |
  | FS, FI | Split | split |
  | RS | Reverse-Split | reverse_split |
  | IC | Issue Change | tickerwechsel |
  | TC | Merger | uebernahme |
  | SO | Spin Off | abspaltung |
  | DW | Delist Worthless | delisting |
  | alle übrigen | | sonstige |

  Achtung: **TC ist ein Merger, kein Tickerwechsel.**
- **Annahmen, am ersten echten Beleg zu prüfen:**
  - Die Zeilen einer Maßnahme werden über `actionID` gebündelt; ohne `actionID` über Typ, Stichtag und Beschreibung.
  - Die Barkomponente steht in `proceeds`, die Stückänderung in `quantity`.
- **Journal:**
  - `kapitalmassnahmen` enthält eine Zeile je Beleg und Buch; `_konto` steht für die Flex-Posten des ganzen Kontos. Status: erkannt → bestätigt → gebucht oder abgelehnt.
  - `kapitalmassnahmen_posten` enthält die Posten: Stück, Barbetrag in Originalwährung, übertragener Einstand und Anschaffungstag.
  - Nur gebuchte Posten zählen. Sie gehen ein in:
    - Bestand
    - Kasse und Kasse je Währung
    - Ø Kaufkurs und „gekauft am“
    - Bestand vor dem Ex-Tag bei Dividenden
  - Steuerhinweis immer „zu prüfen“.
- **Neue Conids:** Sie stehen nur als Vorschlag in `conid_vorschlaege`, mit IBKR-Symbol, ISIN und vorgeschlagenem Yahoo-Ticker. `config/kontrakte.yaml` passt Jakob selbst an.
- **Stopp je Buch** (`betrieb/buchstopp.py`, Zustand `_buchstopps` im Journal):
  - Weicht ein Titel ab, stoppen die Bücher, die ihn halten oder eine Order dafür unterwegs haben. Hält ihn keines, stoppen die Bücher einer erkannten Maßnahme mit diesem Titel.
  - Hält kein Buch die Position und passt keine Maßnahme: Stopp für alles.
  - Bei der Kontokasse gilt ebenfalls Stopp für alles. Ausnahme: Die Differenz passt in Währung und Betrag (± 0,05) zur Barkomponente einer erkannten Maßnahme laut Flex. Dann stoppen nur deren Bücher, und die Kassenbasis bleibt bis zur Buchung unverändert.
  - Ein gestopptes Buch:
    - bekommt keine Vorschläge, keinen Buchwert und keinen neuen Strategiezustand;
    - ist nicht freigebbar und wird beim Senden übersprungen;
    - zeigt eine rote Lampe „Stopp &lt;Buch&gt;“ und „Senden &lt;Buch&gt;: gestoppt“;
    - erscheint in der Kurzfassung mit Kategorie und Titeln, ohne Stück und Beträge;
    - löst beim Eintritt eine Sofortmeldung aus.
  - Die übrigen Bücher laufen weiter.
- **Stop-Loss im gestoppten Technik-Buch:**
  - Es gibt keinen Vorschlag, nur die Sofortmeldung „Stop gerissen in gestopptem Buch: &lt;Titel&gt;“.
  - Ist der Titel von der Maßnahme betroffen, kommt der Zusatz „Werte vor Buchung der Maßnahme, ggf. Fehlalarm“.
  - Titel außerhalb des Universums werden nicht geprüft; das steht im Protokoll.
- **Aufhebung:**
  - Automatisch mit Meldung „Stopp aufgehoben“, aber nur, wenn alle Belege des Stopps für das Buch gebucht sind und der Abgleich des Buchs sauber ist.
  - Verschwindet die Abweichung ohne gebuchten Beleg, bleibt das Buch gestoppt, bis Jakob auf der Buchkarte „Stopp quittieren“ drückt. Die Quittung steht als Ereignis `stopp_quittiert` mit Zeitstempel im Journal.
  - Solange die Abweichung besteht, ist keine Quittung möglich.
- **Backlog (vor Echtgeld):** Ausstiege für nicht betroffene Titel im gestoppten Buch.

## Split, Reverse-Split und Tickerwechsel buchen (A2, Jakob 12.11.2026)

A2 bucht Split (FS, FI), Reverse-Split (RS) und Tickerwechsel (IC) mit Flex-Beleg automatisch und meldet die Buchung (`kapitalmassnahmen.buchen`, im Tageslauf direkt nach dem Erkennen und vor dem Abgleich).

- **Nur bei exakt passender Probe** (Entscheidung 1). Sonst wird nichts gebucht, das Buch bleibt gestoppt und eine Meldung nennt den Grund.
  - Verhältnis r = neue Stück je alte Stück. Beim Split kommt es aus der Beschreibung („SPLIT 2 FOR 1“ → 2, „SPLIT 1 FOR 10“ → 0,1), beim Tickerwechsel aus den Stückzahlen.
  - Flex darf eine Zeile mit der Änderung liefern oder zwei Zeilen (alte Stücke ab, neue zu).
  - Bücher vor dem Stichtag × r: Die ganzen Stück müssen exakt der Flex-Angabe entsprechen. Eine Spitze ist nur mit Barausgleich im Beleg erlaubt; ohne Spitze darf kein Barbetrag über 0,05 im Beleg stehen.
  - Nach der Buchung müssen die Bücher je Titel ganzzahlig exakt der IBKR-Position entsprechen.
- **Buchung je Buch:**
  - Grundlage ist der Bestand des Buchs vor dem Stichtag (`journal.bestand_vor`). Ausführungen am Stichtag laufen schon in neuen Einheiten.
  - Gebucht wird: alte Stücke ab, neue zu. Der Einstand bleibt in Summe gleich (gleitender Durchschnitt), das Anschaffungsdatum wird übernommen. Steuer immer „zu prüfen“.
  - Alles läuft in einer Transaktion (`journal.massnahme_buchen`). Bricht etwas ab, bleibt alles beim Alten; ein zweiter Lauf bucht nicht doppelt.
- **Spitzen beim Reverse-Split** (Entscheidung 2): Jedes Buch bekommt zuerst seine ganzen Stücke. Die übrigen ganzen Stücke gehen einzeln an die Bücher mit dem größten rechnerischen Rest; bei Gleichstand entscheidet der Buchname.
  - Die verbleibende Spitze wird zum Barausgleichskurs laut Beleg (Barbetrag ÷ Spitze des Kontos) abgerechnet: Abgang mit anteiligem Einstand, oder Zukauf, wenn ein Buch aufgerundet wurde. Die Beträge sind auf Cent gerundet, ihre Summe entspricht exakt dem Beleg.
  - Ohne Barausgleichskurs, aber mit Aufrundung, wird nicht gebucht.
  - Jede Buchung steht als Ereignis `kapitalmassnahme_gebucht` im Journal (alt → neu, Einstand, Spitze, Steuer).
- **Werte in Kurseinheiten** (Entscheidung 3). Die vollständige Liste steht in `kapitalmassnahmen.EINHEITEN`; `test_kurseinheiten_vollstaendig` prüft, dass jede Journalspalte und jedes gespeicherte Zustandsfeld eingeordnet ist.

  | Feld | Einheit | Bei Split |
  | --- | --- | --- |
  | Technik-Zustand `stop`, `atr_signal` (in „vor“ und „nach“) | Kurs | ÷ r, Ereignis `kurseinheiten` |
  | offene Vorschläge vor dem Stichtag: `limit_preis`, `letzter_kurs_eur`, `stop` | Kurs | ÷ r |
  | offene Vorschläge vor dem Stichtag: `stueck` | Stück | × r (Stück × Limit und damit die Reservierung bleiben gleich) |
  | Ausführungen (Preis, Stück, Eröffnung), Dividenden (Stück, Satz), Posten | historisch | bleiben (Belegprinzip); die Anzeige rechnet Ø = Einstand ÷ Stück |
  | Zielgewichte, Ränge, Beträge gesamt, Daten, Texte | neutral | bleiben; beim Tickerwechsel wird nur der Schlüssel umbenannt |

  Indikatoren (SMA50/200, ATR, 55-Tage-Hoch, 20-Tage-Tief, RSI, ADX, 12−1) sind nicht gespeichert; jeder Lauf rechnet sie aus der Kursreihe neu. Trailing-Stops mit gespeichertem Hochpunkt gibt es nicht (der Stop ist fest: Einstieg − 2 × ATR). Das Risiko bis zum Stop bleibt gleich: 10 × (100 − 90) = 20 × (50 − 45).
- **Kursreihe** (Entscheidung 4): Solange Yahoo die Historie noch nicht bereinigt hat (Sprung am Stichtag von etwa 1/r, Band ± 15 %), bereinigt der Lauf die Reihe selbst: vor dem Sprung Kurse und Ausschüttung ÷ r, Volumen × r.
  - Das geschieht **nur im Speicher des Laufs**. Der Kurs-Cache, der Tresor und die Backtest-Daten bleiben unberührt.
  - Meldung „Kursreihe X selbst bereinigt … Kurs-Cache unverändert“.
  - Jeder Lauf entscheidet neu; ist kein Sprung mehr da, bleibt die Reihe unverändert. Doppelt bereinigt wird also nie.
  - Danach besteht die Reihe die Datenprüfung (Sprung > 15 %) ohne Ausnahme.
- **Fundamental: Kurs und Kennzahlen je Aktie** (Entscheidung 4, Ergänzung):
  - Die Engine rechnet den Marktwert aus Schluss × Aktienzahl (SEC). Die Aktienzahl wird über die Yahoo-Spalte `split` auf die Kursbasis gebracht (`aktien_splitbereinigt`). E/P und EBIT/EV hängen am Marktwert, die Dividende je Aktie an der Reihe. EPS, Buchwert je Aktie und Dividende je Aktie aus SEC nutzt die Engine nicht direkt.
  - Kurs und Kennzahlen passen erst zusammen, wenn die Reihe im Cache bereinigt ist (kein Sprung) **und** Yahoo den Split als Ereignis mit Faktor r führt. Eine nur im Speicher bereinigte Reihe genügt nicht, weil die Bewertung den Cache liest.
  - Bis dahin bleibt ein Fundamental-Buch, das den Titel hält oder eine Order dafür unterwegs hat, gestoppt. Passt es einmal, wird der Beleg nicht erneut geprüft (`kennzahlen_passend` im Kontozustand).
  - Beim SPYI-Split vom Februar 2026 führte Yahoo kein Split-Ereignis. In so einem Fall bleibt das Buch gestoppt, bis Jakob entscheidet.
  - **Offener Punkt:** Piotroski (Signal „keine neuen Aktien“) vergleicht die erstgemeldeten gewichteten Aktienzahlen zweier Jahre. Liegt ein Split dazwischen, sieht das wie eine Kapitalerhöhung aus, bis ein volles Jahr nach dem Split gemeldet ist. Das betrifft auch den Backtest und ist in A2 nicht geändert.
- **Order über den Stichtag:**
  - Offene Vorschläge vor dem Stichtag werden umgerechnet: Ereignis `order_an_split_angepasst` bei gesendeten Orders, sonst `kurseinheiten`.
  - Das Buch bleibt gestoppt, bis die Order abgeschlossen ist (ausgeführt, storniert oder verfallen).
  - Hat IBKR die Order angepasst (ausgeführte Stück = Stück × r), wird das gemeldet und der Stopp nach sauberem Abgleich aufgehoben.
  - Weicht die Ausführung davon ab (unverändert oder teilweise ausgeführt), bleibt das Buch gestoppt, bis Jakob quittiert (`quittung_noetig`).
  - Beim Tickerwechsel wird eine gesendete Order nicht umgedeutet; noch nicht gesendete Vorschläge für den alten Titel werden „ersetzt“.
  - Ein negativer Bestand in einem Buch stoppt das Buch, auch wenn er mit IBKR übereinstimmt (nur long).
- **Tickerwechsel** (Entscheidung 5): Gebucht wird erst, wenn der neue Conid in `config/kontrakte.yaml` steht. Steht der alte Titel im Technik-Universum, muss auch der neue in `config/technik.yaml` stehen. Bis dahin bleibt das Buch gestoppt und die Meldung nennt den fehlenden Eintrag.
- **Aufhebung:** wie in A1, zusätzlich:
  - Jeder Titel des Stopps muss in einem gebuchten Beleg vorkommen.
  - Für die Titel des Stopps darf keine Order mehr unterwegs sein.
  - Steht `quittung_noetig` im Stopp, hebt nur Jakobs Quittung ihn auf.
- **Anzeige:** Ø Kaufkurs und Einstand werden jetzt als gleitender Durchschnitt über Käufe, Verkäufe und Maßnahmen gerechnet (`journal.einstaende`). Vorher galten nur die Käufe; nach einem Teilverkauf und Split ergab das einen falschen Ø.
- **Restrisiko (Paper akzeptiert, Entscheidung 6):** Eine Order, die abends vor einem Ex-Tag gesendet wird, kann über den Split laufen. A2 erkennt das erst danach.
- **Pflicht vor Echtgeld: A5 (Vorwarnung).** Kapitalmaßnahmen müssen vor dem Senden aus einer Vorwarnung (SEC/Yahoo) bekannt sein, damit keine Order über einen Stichtag läuft; das gilt mindestens für Verkäufe über einen Reverse-Split. Ohne A5 kein Echtgeld.
