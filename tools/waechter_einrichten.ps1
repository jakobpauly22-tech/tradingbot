# Richtet die Windows-Aufgabe „TradingBot Wächter“ ein: montags bis freitags 22:25, tools\waechter.py (Jakob 12.11.2026,
# Uhrzeit 22:25 seit 13.11.2026: der Abendlauf startet laut Ablauf erst nach 22:15).
# Einmal von Hand ausführen (normaler Benutzer, keine Administratorrechte nötig):
#   powershell -ExecutionPolicy Bypass -File tools\waechter_einrichten.ps1
# Entfernen: Unregister-ScheduledTask -TaskName "TradingBot Waechter" -Confirm:$false
# StartWhenAvailable: verpasster Start (Laptop schlief) wird nachgeholt; nach Mitternacht meldet der Wächter nichts mehr.
# Der Laptop wird nicht aufgeweckt; dafür gibt es Healthchecks.io.

$projekt = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projekt ".venv\Scripts\pythonw.exe"
$skript = Join-Path $projekt "tools\waechter.py"
if (-not (Test-Path $python)) { throw "Python der .venv nicht gefunden: $python" }

$aktion = New-ScheduledTaskAction -Execute $python -Argument "`"$skript`"" -WorkingDirectory $projekt
$ausloeser = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday -At 22:25
$einstellungen = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
Register-ScheduledTask -TaskName "TradingBot Waechter" -Action $aktion -Trigger $ausloeser -Settings $einstellungen `
    -Description "Erinnerung, wenn an einem Xetra-Handelstag bis 22:25 kein Tageslauf lief (tools\waechter.py)" -Force
Write-Output "Aufgabe 'TradingBot Waechter' eingerichtet: Mo-Fr 22:25, $skript"
