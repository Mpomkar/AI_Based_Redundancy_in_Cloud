@echo off
REM Double-click or run from repo root: scripts\setup.bat
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
pause
