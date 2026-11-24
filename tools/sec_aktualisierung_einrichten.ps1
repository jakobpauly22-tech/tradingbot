# Richtet die Windows-Aufgabe „TradingBot SEC-Aktualisierung“ ein: samstags 10:00, tools\sec_aktualisieren.py --protokoll
# (SEC-Aktualisierung Schritt 4, Festlegung Jakob 23.11.2026, docs/BETRIEB.md).
# Einmal von Hand ausführen (normaler Benutzer, keine Administratorrechte nötig):
#   powershell -ExecutionPolicy Bypass -File tools\sec_aktualisierung_einrichten.ps1
# Entfernen: Unregister-ScheduledTask -TaskName "TradingBot SEC-Aktualisierung" -Confirm:$false
# StartWhenAvailable: verpasster Start (Laptop aus oder im Ruhezustand) wird nachgeholt; auch im Akkubetrieb.
# Der Lauf nimmt die Laufsperre des Tageslaufs, läuft also nie neben ihm. Ausgabe: daten\betrieb\sec_aktualisierung.log.
# Healthchecks: HEALTHCHECKS_SEC_PING_URL in .env (Erfolg = Ping, Fehlschlag = /fail). Der Laptop wird nicht aufgeweckt.

$projekt = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projekt ".venv\Scripts\pythonw.exe"
$skript = Join-Path $projekt "tools\sec_aktualisieren.py"
if (-not (Test-Path $python)) { throw "Python der .venv nicht gefunden: $python" }

$aktion = New-ScheduledTaskAction -Execute $python -Argument "`"$skript`" --protokoll" -WorkingDirectory $projekt
$ausloeser = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Saturday -At 10:00
$einstellungen = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)
Register-ScheduledTask -TaskName "TradingBot SEC-Aktualisierung" -Action $aktion -Trigger $ausloeser -Settings $einstellungen `
    -Description "SEC-Daten des Betriebs aktualisieren (tools\sec_aktualisieren.py, Pruefregel je CIK, STAND.json, Healthchecks)" -Force
Write-Output "Aufgabe 'TradingBot SEC-Aktualisierung' eingerichtet: samstags 10:00, $skript --protokoll"
