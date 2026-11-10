@echo off
rem Neue Oberfläche des Tageslaufs (10.11.2026). Die alte (Tageslauf.bat) bleibt Reserve, bis Jakob umstellt.
rem Das IB Gateway muss für Abgleich und Senden laufen (Paper-Konto, Port 4002).
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" "tools\tageslauf.py" --neu
