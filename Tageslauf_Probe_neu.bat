@echo off
rem Neue Oberfläche als Probe auf einer Kopie des echten Journals: Gateway nur lesend, sendet nie, kein Messbeginn.
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" "tools\tageslauf.py" --neu --kopie
