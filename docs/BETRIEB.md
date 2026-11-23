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
- **(b) Erinnerung**, wenn an einem Xetra-Handelstag bis 22:25 kein Tageslauf lief (auch ein gestoppter Lauf zählt als
  gelaufen):
  - lokal: Aufgabe „TradingBot Waechter“ Mo–Fr 22:25 (der Abendlauf startet laut Ablauf erst nach
    22:15; 13.11.2026) (`tools/waechter.py`, einrichten mit
    `powershell -ExecutionPolicy Bypass -File tools\waechter_einrichten.ps1`); Ergebnis in `daten/betrieb/waechter.log`.
    An Xetra-Feiertagen unter der Woche sendet der Wächter nur ein Lebenszeichen an Healthchecks.
  - extern: Healthchecks.io bekommt nach jedem echten Lauf ein Lebenszeichen ohne Inhalt. Einstellung des Checks: Cron
    `0 18 * * 1-5`, Zeitzone Europe/Berlin, Karenz 5 h (Stand 13.11.2026); Benachrichtigung über die Telegram-Integration von
    Healthchecks. Damit kommt der Alarm um 23:00 auch bei ausgeschaltetem Laptop. Grenzen: Ein Lauf vor 18:00 deckt
    den Tag nicht ab; an Xetra-Feiertagen bei ausgeschaltetem Laptop gibt es einen Fehlalarm.
- **(c) Sofortmeldung:** Stopp im Tageslauf (als Kurzfassung mit Kopfzeile „GESTOPPT“), Ausnahme im Tageslauf (nur der
  Typ, dazu Lebenszeichen „fail“), Probleme beim Senden (abgelehnt, unbestätigt, Veto bei der zweiten Prüfung, Gateway
  nicht verbunden, Abgleich vor dem Senden weicht ab, Read-Only, Abbruch, bei IBKR offene Order, die im Journal nicht
  unterwegs ist). Grenze: Lehnt IBKR eine Order erst zur Eröffnung ab, erfährt der Bot das erst beim nächsten
  Abendlauf.
- **Warnungen beim Senden (Jakob 13.11.2026, Vorfall BF-B):** ib_async setzt bei Hinweis-Codes wie 399 („wird nicht vor
  09:30 US/Eastern platziert“) den Status auf `ValidationError`, obwohl die Order aktiv ist. Der Bot nimmt den Status
  deshalb aus orderStatus, nicht aus dem Fehlercode: PreSubmitted/Submitted/Filled = angenommen (Warnung im Meldungstext),
  Cancelled/Inactive = abgelehnt, ohne echten Status nach der Wartezeit = unbestätigt. Einzige Ausnahme ist 321
  (Read-Only), die Order kommt dann nie bei IBKR an und gilt als abgelehnt.
- **Abgleich der offenen Orders nach dem Senden (Jakob 13.11.2026):** Alle bei IBKR offenen Orders (alle Client-IDs,
  `reqAllOpenOrders`) werden mit dem Journal verglichen. Fehlt eine offene Order im Journal (auch ohne orderRef, etwa von
  Hand angelegt) oder ist ihr Vorschlag nicht unterwegs (unterwegs = gesendet, unbestätigt, ausgeführt), kommt die
  Sofortmeldung „Order bei IBKR offen, im Journal nicht unterwegs: <Titel>“ (nur Kürzel) und je Order ein Ereignis
  `order_offen_nicht_unterwegs`. Nichts wird automatisch storniert.
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
  - **Split ohne Yahoo-Ereignis (SPYI-Fall, Jakob 12.11.2026):** Beim SPYI-Split vom Februar 2026 führte Yahoo kein Split-Ereignis. Ist die Reihe bereinigt, fehlt das Ereignis aber noch 5 Xetra-Handelstage nach dem Flex-Beleg, schlägt der Bot vor, das Verhältnis aus dem Flex-Beleg für die Aktienzahl zu übernehmen (Kennzeichnung „Quelle: Flex“, Ereignis `flex_split_vorschlag`).
    - Es gilt erst nach Jakobs Quittung in der Oberfläche (Knopf „Split … aus Flex übernehmen“ am gestoppten Buch, Ereignis `flex_split_quittiert` mit Zeitstempel). Hing der Stopp nur daran, hebt er sich sofort auf.
    - Danach trägt die Bewertung den Split am ersten Handelstag ab dem Stichtag in die Split-Spalte ein, nur in einer Kopie (`aktuell.split_ereignisse_ergaenzen`); ein Yahoo-Ereignis bleibt vorrangig. Cache und Backtest bleiben unberührt.
    - Ist die Yahoo-Reihe selbst noch unbereinigt, gibt es keinen Vorschlag; das Buch bleibt gestoppt.
  - **Piotroski „keine neuen Aktien“ (vorgemerkt 12.11., umgesetzt 13.11.2026):** Datenkorrektur, keine neue Variante. t−1 kommt aus derselben Einreichung wie t (Rückfall: Split-Faktoren); wirksam ab dem Rebalancing-Stichtag 04.01.2027 für Auswahl A/B und Risk-Manager-Veto, beim ersten Lauf danach einmal Ereignis `datenkorrektur_angewendet`. Bis dahin rechnet die Bewertung beide Werte mit (`eq_offer_alt`, `eq_offer_neu`, `piotroski_filter_korrigiert`). Ergebnis und Neulauf: docs/FUNDAMENTAL.md, Abschnitt Datenkorrektur.
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

## Übernahme und Delisting buchen (A3, Jakob 12.11.2026)

A3 bucht Übernahmen (TC, Merger) und Delisting wertlos (DW), aber erst nach Jakobs Bestätigung in der Oberfläche und nur mit Flex-Beleg (`kapitalmassnahmen._buchen_uebernahme`).

- **Ablauf:**
  1. Erkennen (A1): Das Buch, das den Titel hält, wird gestoppt. Eine erkannte Maßnahme stoppt das Buch jetzt auch ohne Abweichung zu IBKR.
  2. Am gestoppten Buch zeigt die Oberfläche die Konditionen laut Flex-Beleg (Verhältnis, Barbetrag je Aktie, Flex-Posten) mit den Knöpfen „Bestätigen“ und „Ablehnen“. Beides steht mit Zeitstempel im Journal (`massnahme_bestaetigt`, `massnahme_abgelehnt`).
  3. Gebucht wird im nächsten Tageslauf nach der Bestätigung (Entscheidung 2), nur bei exakt passender Probe. Sonst bleibt der Stopp, und eine Meldung nennt den Grund.
- **Probe:**
  - Abgang laut Flex = Bücher vor dem Stichtag.
  - Neue ganze Stück = floor(Stück × Verhältnis) laut Flex, verteilt nach größtem Rest (wie A2).
  - Barbetrag laut Flex = Stück × Barbetrag je Aktie (Barzuzahlung) + Spitzenausgleich. Gibt es keine Spitze, muss der Barbetrag auf ± 0,05 passen.
  - Danach Bücher = IBKR-Position.
  - Der neue Conid muss in `config/kontrakte.yaml` stehen.
- **Konditionen:** Sie werden aus der IBKR-Beschreibung gelesen („… WITH &lt;ISIN&gt; 14625 FOR 100000 AND USD 3.50“, „… FOR USD 50.00 PER SHARE“). Das Format ist am ersten echten Beleg zu prüfen. Werte von Hand gibt es nicht; ist die Beschreibung nicht lesbar, gelten die Flex-Stückzahlen und -Beträge.
- **Einstand und Barkomponente** (Entscheidung 1):
  - Der Einstand geht voll auf die neuen Aktien über (Anschaffungsdatum übernommen); nur eine verkaufte Spitze nimmt ihren Anteil mit.
  - Jeder Posten trägt eine Art (`kapitalmassnahmen_posten.art`), steuerlich getrennt von Dividenden und Veräußerungen:
    - `barzuzahlung`: „Barzuzahlung (§ 20 Abs. 4a, zu prüfen)“. Lässt sich umrechnen, falls die Vorschrift nicht greift.
    - `barabfindung`: reine Barübernahme, Veräußerung § 20 Abs. 2, zu prüfen.
    - `spitzenausgleich`: Bruchteil, Veräußerung, zu prüfen (gilt auch für die Spitzen aus A2).
    - `bestand`: Stückposten mit übertragenem Einstand.
- **Delisting:**
  - Nur DW gilt als „Delisting wertlos“: Der Titel wird ausgebucht, der Einstand wird zum Verlust.
  - Ein DW mit Gegenleistung im Beleg wird nicht gebucht.
  - Ein Delisting, bei dem der Handel weitergeht (z. B. außerbörslich), ist kein DW. Ein unbekanntes Kürzel stoppt wie in A1 und wird nie automatisch gebucht. Die Oberfläche bietet dafür nur „Ablehnen (nicht buchen)“, danach kommt die Quittung.
- **Ablehnen** (Entscheidung 4): Status „abgelehnt“, das Buch bleibt gestoppt bis zur Quittung. Abweichungen der Titel einer abgelehnten Maßnahme werden weiter dem Buch zugeordnet (kein Stopp für alles). Quittieren geht erst, wenn der Abgleich des Buchs sauber ist.
- **Strategiezustand:** Der untergegangene Titel fällt aus der Technik-Position und aus Fundamental-Ziel und -Rang, damit es keinen Nachkauf eines delisteten Titels gibt. Gesendete Orders werden nicht umgedeutet: Das Buch bleibt gestoppt, bis sie abgeschlossen sind. Nicht gesendete Vorschläge werden „ersetzt“.
- **Fremdtitel** (Entscheidung 3):
  - Fundamental-Bücher halten erhaltene Aktien bis zum nächsten Quartalsstichtag; dann entscheidet die Auswahlregel. Ein Titel außerhalb des gefilterten Universums wird verkauft.
  - Technik-Bücher bekommen im nächsten Lauf einen Ausstiegsvorschlag für jeden Titel außerhalb des Universums (Ausstiege sind immer erlaubt).
- **Kenvue** (Primärquellen geprüft 12.11.2026): Gemeinsame Pressemitteilung vom 03.11.2025: 3,50 USD bar und 0,14625 Kimberly-Clark-Aktien je Kenvue-Aktie. 8-K vom 02.11.2026: Vollzug am 02.11.2026, Bruchteile bar zum VWAP-Durchschnitt der 5 Handelstage vor dem Vollzug. Kein Buch hielt KVUE; der Fall dient als Test (`test_kapitalmassnahmen_a3.py`).


## Abspaltung buchen (A4, Jakob 13.11.2026)

A4 bucht Abspaltungen (SO, Spin-off) nach Jakobs Bestätigung in der Oberfläche, nur mit Flex-Beleg (`kapitalmassnahmen._buchen_abspaltung`).

- **Erkennen:** Die Mutter steht nur in der Beschreibung („CMCSA(US20030N1019) SPINOFF 1 FOR 25 (VSNT, …)“), die Flex-Zeile nennt die Tochter. A1 ergänzt die Mutter, damit das Buch, das sie hält, gestoppt wird. Format am ersten echten Beleg prüfen.
- **Bestätigung** (Entscheidung 1): wie A3. Die Oberfläche zeigt Mutter, Verhältnis und Flex-Posten; gebucht wird im nächsten Tageslauf, nur bei exakt passender Probe.
- **Probe:** Mutter-Stückzahl unverändert; Tochter = floor(Stück × Verhältnis) laut Flex, Spitzen nach größtem Rest, Bruchteile nur mit Barausgleich; danach Bücher = IBKR-Position für Mutter und Tochter.
- **Einstand** (Jakobs Regel): Aufteilung nach den Schlusskursen am ersten gemeinsamen Handelstag ab dem Stichtag, Anteil Tochter = r · C_Tochter / (r · C_Tochter + C_Mutter). Die Summe bleibt gleich; eine verkaufte Spitze nimmt ihren Anteil mit. Fehlt ein Kurs, wartet die Buchung, das Buch bleibt gestoppt. Posten-Art der Mutter: `einstand_aufteilung` (Stück unverändert).
- **Anschaffungsdatum** (Entscheidung 2): Datum der Mutterposten, „zu prüfen“. Das Journal führt den Einstand als gleitenden Durchschnitt mit dem Tag des ersten Kaufs; der Buchungstext nennt zusätzlich alle Kaufposten der Mutter mit Datum und Stück.
- **Form 8937:** In der Oberfläche kann der Anteil der Mutter laut Form 8937 mit Quelle eingetragen werden, auch nach der Buchung. Das Journal (Ereignis `form8937`) zeigt beide Aufteilungen und die Differenz; gebucht bleibt nach Schlusskursen.
- **Steuer:** „zu prüfen“: Abspaltung nach § 20 Abs. 4a Satz 7 EStG oder Sachausschüttung; der Buchungstext nennt den Wert der Tochter am Kurstag.
- **Tochter ohne Conid** (Entscheidung 3): nur Meldung, das Buch läuft weiter. Steht am Quartalsstichtag ihr Verkauf an, ist nur dieser Titel gesperrt (Zustand `verkauf_gesperrt`), mit täglicher Sofortmeldung, bis die Conid in `config/kontrakte.yaml` steht; dann schlägt der nächste Lauf den Verkauf vor.
- **Halten:** Fundamental-Bücher halten die Tochter bis zum nächsten Quartalsstichtag; dann entscheidet die Auswahlregel (wie Fremdtitel in A3).
- **Vorschläge der Mutter** vor dem Stichtag bleiben stehen, mit dem Hinweis „Limit prüfen“ (der Kurs fällt um den Wert der Tochter).
- **Test:** nachgestellt mit Versant (1 VSNT je 25 CMCSA), `tests/betrieb/test_kapitalmassnahmen_a4.py`.
- **Pflicht vor Echtgeld: FIFO-Steuerauswertung** (Jakob 13.11.2026). Das Journal führt den Einstand als gleitenden Durchschnitt; vor Echtgeld kommt eine Auswertung nach FIFO aus den Einzelausführungen (§ 20 Abs. 4 Satz 7 EStG), einschließlich der Anschaffungsdaten aus Kapitalmaßnahmen. Kein Umbau des Journals.

## Eigener Kurs-Cache des Betriebs (Befund 5, Jakob 16./17.11.2026)

- **Anlass:** Tageslauf, Senden, Fundamental-Bewertung und Regimebuch luden Kurse über `daten/cache/kurse`, den auch die
  Backtests lesen. Bei einem neuen Split lädt der Kurslader die ganze Historie neu; ein Betriebslauf konnte so die
  Entwicklungsdaten bis 2024 ersetzen.
- **Regel:** Im Betriebsmodus nutzt `lade_kurse` ohne ausdrücklichen Cache nur `daten/betrieb/cache/kurse`
  (`daten.kurse.kurscache`, `betrieb/kurscache.py`). Außerhalb des Betriebsmodus ändert sich nichts.
- **Einmalige Übernahme:** Beim ersten Lauf im Betriebsmodus, auch bei einem Probelauf (`--kopie`, `--probe`), werden alle
  Kursdateien aus `daten/cache/kurse` kopiert, ohne Downloads. Die Marke `daten/betrieb/cache/kurse/UEBERNAHME.json` hält
  Zeitpunkt und Zahl der Dateien fest; danach wird nie wieder kopiert. Das Protokoll jedes Laufs nennt den Kurs-Cache, beim
  ersten Mal mit der Zahl der übernommenen Dateien (Jakob 17.11.2026).
- **Nicht umfasst:** SEC-Fakten der Fundamental-Bewertung liegen weiter im Standard-Cache (kein Kurs-Cache; Backtests
  begrenzen sie über `filed`).

## Gegenläufige Orders im selben Titel (Befund 2, Jakob 16.11.2026)

- **Anlass:** Realbuch und „regime“ handeln beide SPYI.DE. Ein Kauf des einen und ein Verkauf des anderen lägen in derselben
  Eröffnungsauktion im selben Konto. Wie IBKR das behandelt, ist nicht verlässlich belegt; der Bot schließt es selbst aus.
- **Regel vor dem Senden** (`betrieb/gegenlaeufig.py`, eingebunden in die Sendeschleife):
  - Liegt im selben Titel schon eine Order eines anderen Buchs in Gegenrichtung (unterwegs oder bei IBKR offen, auch ohne
    Bot-Kennung), wird die neue nicht gesendet.
  - Kommen am selben Abend beide Richtungen neu, geht der Verkauf raus (Risiko senken), der Kauf wartet.
  - „Wartet“: Meldung „WARTET – gegenläufige Order im selben Titel“, Ereignis `wartet_gegenlaeufig`, eigene Kategorie in
    der Sofortmeldung nach dem Senden. Die Freigabe bleibt bis zu ihrem Ablauf stehen; der Vorschlag kommt am nächsten
    Abend von selbst wieder. Gleiche Richtung in mehreren Büchern bleibt erlaubt, Tausch ist nicht betroffen.

## Zwei Orders im selben Titel nach einem verpassten Abend (Befund 17, Jakob 16.11.2026)

- Die Abweichung zur IBKR-Position wird je Titel gemessen; nach einem verpassten Abend gelten deshalb alle Orders eines
  Titels als Verdacht. Bisher stoppte der Lauf, wenn nur eine davon ausgeführt war („alles oder nichts“).
- **Neu** (`betrieb/nachtrag.py`): Eine Verdachts-Order ohne Flex-Treffer gilt als verfallen, wenn der Flex-Bericht ihren
  Handelstag abdeckt (`fromDate` ≤ Handelstag ≤ `toDate`) **und** die belegten Ausführungen die Abweichung des Titels genau
  erklären. Die belegte Order wird gebucht; Ereignis „verfallen“ mit Verweis auf Befund 17. Sonst Stopp wie bisher.

## Wächter gegen ein verschobenes Universum (Jakob 17.11.2026)

- **Anlass:** `daten/universum/kursstatus.csv` hängt an der Zeilennummer des Universums. Der Wikipedia-Abruf der Probe am
  16.11.2026 um 22:18 brachte eine Zeile mehr (896 → 897): DAY steht neu alphabetisch an Stelle 120, ab dort rücken alle
  Zeilen um eins. 653 von 813 Zuordnungen zeigten danach auf ein anderes Symbol (648 verschoben, 5 inhaltlich geändert).
  *Korrektur 18.11.2026: Hier stand „89 Zeilen mehr (fast alle vor 2012 beendet)“; das war falsch (Prüfbericht, Befund 19).* Der echte Lauf um 22:39 lief schon damit; der Vorschlag P (fundamental_b) war nachweislich nicht
  betroffen (gleiche Zeile 893, Kurs 103,68 USD = Yahoo-Schluss von P).
- **Sperre:** `pruefe_zuordnung` (in `lade_firmendaten` und vor dem Kursabruf der Fundamental-Bewertung) verlangt je
  genutzter Zeile denselben Ticker wie in `kursstatus.csv`, sonst `UniversumVerschoben`. Im Tageslauf setzen dann nur die
  Fundamental-Bücher aus (Sofortmeldung, Ereignis `fundamental_gesperrt`, Buchwert trotzdem gespeichert); alle anderen
  Bücher laufen normal. Backtest- und c3-Werkzeuge brechen laut ab.
- **Stand 18.11.2026:** Backtest und c3 nutzen einen eingefrorenen Wikipedia-Stand (Schritt 1,
  `docs/berichte/2026-11-18_universum_eingefroren.md`). `kursstatus.csv` wird in Betrieb und Backtest über den
  Schlüssel (Ticker, von, bis) zugeordnet (Schritt 2, `daten/kursstatus.py`). Am Betriebsstand finden 5 Statuszeilen
  ihre Mitgliedschaft nicht mehr (XEC, IR, CDAY, DAY, KVUE), daher bleibt die Sperre der Fundamental-Bücher.
- **Schritt 3 (18.11.2026, `betrieb/universum_betrieb.py`):** Der Betrieb hat einen eigenen Wikipedia-Cache, ein
  eigenes Universum und einen eigenen Kursstatus in `daten/betrieb/cache/universum/`. Beim ersten Zugriff werden die
  Seiten einmalig aus `daten/cache/universum` übernommen (Zeitstempel bleiben, Marke `UEBERNAHME.json`).
  - Kursstatus: Statuszeilen aus `kursstatus.csv` werden über den Schlüssel zugeordnet, sonst über Ticker und CIK mit
    überlappendem Zeitraum (genau ein Treffer, sonst laut; Jakob 18.11.2026). Heute betrifft das KVUE, IR, DAY und XEC
    (eine Protokollzeile).
  - Neue Mitglieder (heute OKTA) werden wie in `tools/kurse_universum.py` geprüft, einschließlich Namensabgleich
    (`daten.kursquellen.pruefe_mitgliedschaft`), und in `kursstatus_neu.csv` festgehalten. Ohne gültige Reihe bleiben
    sie außen vor (Meldung und Sofortmeldung).
  - Betriebskorrektur (`betrieb_korrekturen` in `config/universum_korrekturen.yaml`): CDAY endet am 01.02.2024.
    Greift sie nicht mehr, gibt es eine Sofortmeldung statt eines Fehlers.
  - Wächter: Eine CIK, die am Stichtag mehrfach Mitglied ist, führt zu `UniversumVerschoben` (Fundamental-Bücher setzen
    aus). Ausgenommen sind bekannte Aktiengattungen aus dem eingefrorenen Stand (GOOG/GOOGL, FOX/FOXA, NWSA/NWS). Ein
    heutiges Mitglied ohne gültige Kursreihe führt zu einer Meldung.
  - `lade_firmendaten` liest Kurse über `kurscache()`. Bis 18.11.2026 las die Fundamental-Bewertung des Betriebs hier
    still `daten/cache/kurse`, das der Betrieb seit Befund 5 nicht mehr aktualisiert. Das hat sich nicht ausgewirkt,
    weil die Sperre seit demselben Tag galt.
  - `tools/kontrakte_pruefen.py` nutzt den Betriebsstand.
  - Probe im Ersatzbereich (Scratchpad, 18.11.2026): 503 heutige Mitglieder, `bewertung_am(17.11.2026)` mit 397 Firmen,
    OKTA enthalten, KVUE und CDAY nicht, keine Sperre.
- **Schritt 4 (Befund 20, 18.11.2026, `daten/schicht.py`):** Eine Probe (`--probe`, `--kopie`, Probefenster) verändert
  keine Betriebs- oder Entwicklungsdaten mehr.
  - Der ganze Probe-Prozess läuft in einer Schicht unter `daten/betrieb/probe/cache/`. Gelesen wird zuerst dort, dann
    das Original; geschrieben wird nur dort. Zu Beginn jeder Probe wird die Schicht geleert.
  - Erfasst sind alle Cache-Stellen: Parquet (Kurse, Universum, SIC, SEC-Tabellen, Makro), SEC-JSON und
    Einreichungsköpfe, Tiingo (Kurse, Metadaten, Stundenzähler, Liste), Wikipedia, SEC-Namen, Yahoo-Namen, die
    Übernahmen des Betriebs und `kursstatus_neu.csv`. Journale, Berichte und `betriebsfreigaben.log` der Probe
    bleiben wie bisher in ihren Probe-Pfaden.
  - Grenze: Tiingo-Abfragen einer Probe zählen nur im Stundenzähler der Schicht. Der echte Lauf sieht sie nicht,
    das Limit gilt aber je API-Schlüssel.
  - Nachweis: Test byteweise über jede Schreibstelle (`tests/daten/test_schicht.py`). Gegenprobe am 18.11.2026 an
    echten Daten: Universum des Betriebs und `bewertung_am` mit Kursabruf in der Schicht; 0 von 16.834 Dateien in
    `daten/cache` und `daten/betrieb/cache` geändert, 477 Dateien in der Schicht.

## Zeitmessung im Tageslauf (Jakob 17.11.2026, nur Anzeige)

- Am Ende jedes Tageslaufs steht im Protokoll „Dauer je Abschnitt: …; gesamt … s“ (Vorbereitung, Gateway und Abgleich,
  Realbuch, Regime, Technik-Bücher, Fundamental-Bücher, S&P-500-Liste, Fundamental-Bewertung, Risk-Manager und Speichern,
  Sicherung), beim Senden „Dauer je Abschnitt (Senden): …“. Gespeichert in `Laufergebnis.dauer`; am Ablauf ändert sich
  nichts (`betrieb/zeitmessung.py`).

## SEC-Aktualisierung im Betrieb (Festlegung Schritt 0, Jakob 23.11.2026)

Festgelegt vor dem Code. Schwellen und Abnahmekriterien werden nach einem Lauf nicht geändert; eine Verfehlung bleibt
im Bericht stehen, die Ursache wird gesucht und mit Jakob besprochen.

### Anlass

- Die Fundamental-Bewertung des Betriebs liest SEC-Daten nur aus dem Standard-Cache und lädt nie nach:
  `sec_erstmeldungen` über `standard_cache()` (`engines/fundamental/aktuell.py`), dazu `lade_firmendaten`,
  `lade_aktienfakten` und `lade_sic_historien`. Alle 806 companyfacts stammen vom 02.11.2026. Firmen mit zu altem
  Abschluss fallen über `veraltet` still heraus.
- Ohne Aktualisierung fehlen der Bewertung zum Quartalswechsel am 04.01.2027 alle Einreichungen ab dem 02.11.2026.
- **Befund beim Lesen (23.11.2026):** Betrieb und Probe haben in den Entwicklungs-Cache geschrieben. Geprüft und
  festgehalten im Abschnitt „Datenstand des Entwicklungs-Caches“ unten. Schritt 1 schließt diesen Weg; nichts wird
  zurückgedreht (Jakob 23.11.2026).

### Regeln

- **Eigener SEC-Cache des Betriebs.** Er liegt unter `daten/betrieb/cache/` und hat dieselben Bereiche wie der
  Entwicklungs-Cache:
  - `sec/companyfacts`, `sec/submissions`, `sec/koepfe`,
  - `sec_erstmeldungen`, `sec_aktienfakten`, `sec_aktienfakten_quartale`,
  - `universum/sic_historie`.
- **Lesen und schreiben:** Im Betriebsmodus lesen und schreiben alle SEC-Wege nur dort, auch `SecClient`, die
  abgeleiteten Tabellen und die SIC-Historie. Außerhalb des Betriebsmodus ändert sich nichts. `betriebspfad` sperrt den
  Bereich für Backtest- und Auswertungswerkzeuge (Tresor-Trennung).
- **Einmalige Übernahme** wie beim Kurs-Cache (Befund 5):
  - Beim ersten Zugriff im Betriebsmodus werden alle Dateien der genannten Bereiche byteweise kopiert, ohne Downloads.
  - Die Marke `UEBERNAHME.json` hält Zeitpunkt, Quelle und Dateizahl je Bereich fest. Danach wird nie wieder kopiert.
  - Bricht die Übernahme ab, wiederholt der nächste Lauf sie vollständig.
- **Der Tageslauf lädt keine SEC-Daten.** Er liest nur den Betriebs-Cache und `STAND.json`. Ausnahme: Neue Mitglieder
  des Betriebsuniversums werden geprüft wie bisher (`betrieb/universum_betrieb.py`), ab jetzt mit dem Betriebs-Cache.
- **Aktualisierung nur über das Werkzeug `tools/sec_aktualisieren.py`**, getrennt vom Abendlauf:
  - **CIKs:** heutige Mitglieder des Betriebsuniversums plus Vorgänger-CIKs, etwa 550.
  - **Je CIK:** companyfacts neu laden (erzwungen, unabhängig vom Alter). Danach `sec_erstmeldungen`,
    `sec_aktienfakten` und `sec_aktienfakten_quartale` neu bauen.
  - **SIC-Historie wird mit aktualisiert:** Je CIK werden die submissions geladen. Für jedes neue 10-K, dessen Kopf
    noch nicht im Cache liegt, kommt der Einreichungskopf dazu; die SIC-Historie wird ergänzt.
  - **Drosselung nach SEC-Regeln:**
    - höchstens 8 Anfragen je Sekunde über die vorhandene `Drossel` (`config/fundamental.yaml`, SEC-Grenze 10/s),
    - User-Agent aus `SEC_USER_AGENT` in `.env`, gzip,
    - bei 429/503 Wiederholung mit Pause (`mit_wiederholung`),
    - bei 403 lauter Abbruch ohne weitere Anfragen.
  - **Prüfregel vor der Übernahme je CIK:**
    - Alle bisherigen Erstmeldungen bleiben unverändert (taxonomie, konzept, einheit, start, ende, wert, filed, accn,
      form); neu hinzukommen dürfen nur Zeilen.
    - Für die SIC-Historie gilt dasselbe: bestehende Einträge bleiben, neue werden nur angehängt.
    - Ist die Regel verletzt, behält diese CIK ihren alten Stand vollständig, und es gibt eine Meldung im Protokoll des
      Werkzeugs und als Sofortmeldung. Spätere Korrekturen der SEC ersetzen so nie einen zuerst gemeldeten Wert.
  - **Übernahme in den Betriebsstand:** jede Datei atomar. Am Ende schreibt das Werkzeug `STAND.json`:
    - Zeitpunkt des Laufs und `erfolgreich` (ja/nein),
    - je CIK Stand „übernommen“, „alter Stand“ (Prüfregel verletzt) oder „Fehler“, mit Abrufzeit und Text,
    - `letzter_erfolg`: Zeitpunkt des letzten erfolgreichen Laufs. Nur ein erfolgreicher Lauf setzt ihn neu; sonst
      wird er unverändert übernommen.
  - **Schutz:**
    - Es nimmt die Laufsperre (`betrieb/sperre.py`), läuft also nie neben einem Tageslauf.
    - Es gilt die `Fehlerschwelle` wie in `tools/sec_fakten_universum.py`. Bei Überschreitung wird `STAND.json`
      trotzdem geschrieben, mit `erfolgreich: false` und unverändertem `letzter_erfolg` (Jakob 23.11.2026). Bereits
      geprüfte CIKs bleiben übernommen.
  - **`--probe`:** läuft vollständig in der Probe-Schicht (`daten/schicht.py`), die zu Beginn geleert wird.
    Betriebs- und Entwicklungsdaten bleiben byteweise unverändert.
- **Zeitplan:**
  - Windows-Aufgabenplanung, Samstag 10:00, verpasste Ausführung nachholen, auch im Akkubetrieb.
  - Eigener Healthchecks-Check mit `HEALTHCHECKS_SEC_PING_URL` in `.env`: Erfolg pingt die URL, ein Fehlschlag
    (Abbruch, Fehlerschwelle, 403) pingt `…/fail`.
  - Erster echter Lauf am Samstag, 05.12.2026. Der Lauf am Samstag, 02.01.2027 liefert den Stand für den
    Quartalswechsel am 04.01.2027.
- **Meldungen im Tageslauf (nur Meldung, nie Stopp):**
  - Das Protokoll nennt immer „SEC-Stand vom …“ (`letzter_erfolg` aus `STAND.json`) und, wenn der letzte Lauf nicht
    erfolgreich war, auch diesen Lauf mit der Zahl der Fehler.
  - Liegt `letzter_erfolg` mehr als **9 Tage** zurück, gibt es eine Sofortmeldung. Dasselbe gilt, wenn
    `STAND.json` fehlt oder unlesbar ist; die Bewertung läuft dann mit dem vorhandenen Betriebs-Cache weiter.
  - **Liste je Firma**, wenn die neueste Erstmeldung (`filed`) mehr als **120 Tage** vor dem Bewertungstag liegt:
    Symbol und Alter in Tagen.
  - **Immer:** die Zahl der Firmen, die wegen `veraltet` aus der Bewertung fallen (bisher still).

### Entwicklungs-Cache: Aktualisierung nur ausdrücklich (Zusage, Jakob 23.11.2026)

- Der `SecClient` lädt außerhalb des Betriebs nicht mehr von selbst neu; bisher geschah das nach 7 Tagen
  (`cache_max_alter_tage`). Was im Cache liegt, gilt.
- Nachgeladen wird nur, was fehlt, oder auf ausdrücklichen Schalter bzw. mit einem eigenen Werkzeug. Jede solche
  Aktualisierung wird mit Datum und Anlass dokumentiert.
- **Zusage:** Vor jedem Backtest-Neulauf wird festgehalten, ob der Entwicklungs-Cache seit dem letzten Lauf
  aktualisiert wurde und mit welchem Stand der Lauf rechnet. Eine Aktualisierung zwischen zwei Läufen, die verglichen
  werden, braucht Jakobs Zustimmung.
- Umsetzung in Schritt 1, zusammen mit dem eigenen Cache des Betriebs.

### Datenstand des Entwicklungs-Caches (geprüft 23.11.2026)

**Zusage:** Der Entwicklungs-Cache wurde seit dem 16./19.11.2026 vom Betrieb verändert, schon ab dem 09.11.2026 durch
einen Lauf außerhalb der Entwicklung. Verändert wurden die submissions von 3 CIKs, zwei Einreichungsköpfe und der
Eintrag für OKTA in der SIC-Historie; companyfacts und Erstmeldungen sind unverändert. **Auswirkung auf Backtests:
keine.** Keine der betroffenen CIKs hat vor 2025 eine SIC-Zeile, die ein Backtest liest; die SIC-Zeilen aller
Mitglieder des eingefrorenen Universums stammen aus den Köpfen vom 02.11.2026. Der Stand wird nicht zurückgedreht.

Prüfung an den Dateien, ohne Netz (Zuordnung über den eingefrorenen Stand `lade_universum()` und den Betriebsstand):

- **`sic_historie.parquet`** (zuletzt geschrieben 19.11.2026, 22:37, Tageslauf)
  - Meta 807 CIKs, 860 Zeilen mit 804 CIKs. Die 3 übrigen CIKs haben eine leere Historie, also keine Zeile.
  - Drei CIKs mit Zeilen gehören nicht zum eingefrorenen Universum, auch nicht als Vorgänger:
    - **1660134 Okta** (SIC 7372 ab 12.03.2018). Im eingefrorenen Universum nie Mitglied, also auch nicht vor 2025;
      im Betriebsuniversum Mitglied ab 30.10.2026. Beide Köpfe (0001660134-18-000007, 0001660134-26-000020) wurden am
      09.11.2026 um 09:43 geladen, vor Befund 20, während der Betriebsarbeit an 04f2ac4/915f827. Welcher Lauf das
      war, lässt sich nicht mehr feststellen.
    - **75488 Pacific Gas & Electric** und **1069996 FedNat**. In keinem der beiden Universen, Köpfe vom 02.11.2026,
      also Altbestand aus dem ersten Aufbau und nicht vom Betrieb.
  - Warum die Datei bei jedem Lauf neu geschrieben wird: `lade_sic_historien` merkt sich nur CIKs mit Zeilen. CIKs ohne
    10-K gelten deshalb bei jedem Aufruf als neu, werden erneut abgefragt (submissions) und lösen das Schreiben aus. Das
    gilt im Betrieb wie im Backtest. Der Zeitstempel vom 19.11. sagt deshalb nichts über eine inhaltliche Änderung.
  - Inhaltlich ändern kann sich eine Zeile nur über einen neu geladenen Kopf. Außer den beiden OKTA-Köpfen sind alle
    1.814 Köpfe vom 02.11.2026. Die Zeilen aller anderen CIKs entsprechen deshalb dem Stand vom 02.11.2026. Eine
    ältere Kopie der Datei gibt es nicht; alle fünf Kopien unter `daten/` sind gleich (SHA a08f62b3…).
- **submissions vom 16.11.2026, 22:22** (Probe vor Befund 20, dort als „drei SEC-Einreichungen“ gezählt):
  - **2089271 Honeywell Aerospace (HONA):** im eingefrorenen Universum ab 29.06.2026, ohne 10-K.
  - **2115436 ExxonMobil (XOM, neue CIK):** im eingefrorenen Universum durchgehend, mit Vorgänger 34088, ohne 10-K.
  - **2128626 Vylor (VYLR):** im eingefrorenen Universum ab 01.10.2026, ohne 10-K.
  - Die SIC-Historie aller drei ist leer, vorher wie nachher, weil es kein 10-K gibt. XOM bekommt seine SIC über die
    Vorgänger-CIK 34088 (2911 ab 26.02.2010, Kopf vom 02.11.2026), unverändert. HONA und VYLR sind erst ab 2026
    Mitglied und liegen außerhalb jedes Backtests.
- **Übrige submissions:** 2.027 Dateien vom 17.11.2026 um 10 Uhr (Werkzeuge zu Befund 19 in der Entwicklung, Nachladen
  nach 7 Tagen) sowie einzelne vom 13., 15. und 16.11. (Entwicklung). submissions gehen nur über die 10-K-Liste in die
  SIC-Historie ein, und die bleibt für bekannte CIKs unverändert (siehe oben).

### Abnahme A (Schritt 1, vor dem Merge, ohne Download)

- **A1 Übernahme:** Dateizahl je Bereich und SHA-256 jeder übernommenen Datei sind gleich der Quelle.
- **A2 Bewertung:** `tools/bewertung_vergleich.py` meldet versiegelt „identisch“ gegen die Referenz vom 18.11.2026
  (Git 6e4ff8a, eingefrorene Eingaben).
  - Das Werkzeug bildet dafür die neuen Pfade (`betrieb/cache/<Bereich>`) auf die eingefrorenen Dateien
    (`cache/<Bereich>`) ab, nur für die SEC-Bereiche und mit SHA-Prüfung.
  - Diese Erweiterung bekommt einen eigenen Test. Die Referenz wird nicht ersetzt.
- **A3 Trennung:** Test byteweise, dass Betriebs- und Probewege den Entwicklungs-Cache nicht verändern. Gegenprobe
  an echten Daten mit einer Probe: 0 Dateien außerhalb der Schicht geändert.
- **A4 Entwicklung:** Test, dass `SecClient` außerhalb des Betriebs ohne Schalter nicht nachlädt, auch wenn der Cache
  älter als 7 Tage ist.
- **A5:** volle Testsuite grün, einschließlich `tests/musterloesungen/test_uebungen.py`.

### Stand Schritt 1 (23.11.2026, Branch `sec-betriebscache`)

- `betrieb/seccache.py`: Übernahme und Wege. `daten/sec.py`: `sec_rohwurzel()` und `sec_cache()`, die im
  Betriebsmodus auf den Betriebs-Cache zeigen. Umgestellt sind `SecClient`, `lade_erstmeldungen`,
  `lade_aktienfakten`, `lade_sic_historien`, `lade_firmendaten` (nur Erstmeldungen) und `bewertung_am`.
  `tools/tageslauf.py` schreibt die Protokollzeile zur Übernahme.
- **Zusätzlich übernommen:** `sec/suche` und `sec/company_tickers.json.gz`. Beide liest der `SecClient` ebenfalls aus
  seiner Wurzel; ohne Übernahme würde der Betrieb sie neu abfragen. `sec/volltext_*` (8-K-Texte der
  Entwicklungswerkzeuge) wird nicht übernommen.
- `SecClient` ohne `max_alter` lädt nie von selbst nach. `cache_max_alter_tage` in `config/fundamental.yaml` ist nur
  noch ein Richtwert für ausdrückliches Nachladen.
- **Abnahme A** (23.11.2026):
  - **A1:** 6.907 Dateien übernommen (in der Probe-Schicht), 0 Abweichungen bei SHA-256.
  - **A2:** versiegelt „identisch“ (397 Firmen, 3.376 SEC-Dateien abgebildet). Gegenprobe mit gelöschten Dateien am
    alten Ort: ebenfalls identisch, also liest die Bewertung nur noch den Betriebspfad.
  - **A3:** Bewertung am 18.11.2026 in der Probe: 0 von 16.841 Dateien in `daten/cache` und `daten/betrieb/cache`
    geändert. Tests byteweise in `tests/betrieb/test_seccache.py`.
  - **A4:** Test, dass der `SecClient` auch nach 30 Tagen ohne ausdrückliches `max_alter` nicht nachlädt.
  - **A5:** volle Suite (siehe Commit).
- Die echte Übernahme nach `daten/betrieb/cache` geschieht beim ersten Betriebslauf nach dem Merge, ohne Downloads,
  mit Protokollzeile.

### Abnahme B (Schritt 5, erster echter Lauf am 05.12.2026, Bericht in `docs/berichte/`)

- **B1 Bestand:** Je CIK sind alle Erstmeldungen des Entwicklungs-Caches (Stand 02.11.2026) im Betriebs-Cache
  identisch (alle Spalten aus der Prüfregel). Kriterium: keine Abweichung. Abweichende CIKs bleiben nach der
  Prüfregel auf dem alten Stand und stehen einzeln im Bericht.
- **B2 Neue Zeilen:** Neue Erstmeldungen haben `filed` am oder nach dem 30.10.2026 (letzter Handelstag vor dem Abruf
  am 02.11.2026 und ein Tag Puffer für die Verzögerung der SEC-API). Kriterium: keine neue Zeile mit früherem `filed`.
  Jede gefundene Zeile steht einzeln im Bericht.
- **B3 Bewertung, begrenzt:** Mit dem Betriebs-Cache, SEC-Zeilen begrenzt auf `filed` ≤ 01.11.2026, liefert
  `bewertung_am(18.11.2026)` im versiegelten Vergleich „identisch“ gegen die Referenz. Dafür bekommt das Werkzeug die
  Begrenzung als Schalter, mit Test.
- **B4 Bewertung, voll:** Ohne Begrenzung weichen nur Firmen ab, die eine neue Erstmeldung mit `filed` ab dem
  02.11.2026 haben. Jede Abweichung steht mit Firma, Einreichung und geänderten Kennzahlen im Bericht.
- **B5 Trennung:** Der Entwicklungs-Cache ist vor und nach dem Lauf byteweise gleich (SHA-Liste).
- **B6 Lauf:**
  - Das Protokoll nennt Zahl der Anfragen, Dauer, gemessene höchste Rate (≤ 8/s), Fehler unter der Fehlerschwelle,
    `STAND.json` und den Erfolgs-Ping.
  - Die Probe davor (`--probe`) hat 0 Dateien außerhalb der Schicht geändert.
- **B7 Tageslauf:** Der Tageslauf nach dem 05.12.2026 zeigt den SEC-Stand, die Liste über 120 Tage und die Zahl der
  wegen `veraltet` herausfallenden Firmen.
