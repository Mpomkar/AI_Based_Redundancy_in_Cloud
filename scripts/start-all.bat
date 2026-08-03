@echo off
REM Opens backend + frontend in new windows
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-all.ps1"
