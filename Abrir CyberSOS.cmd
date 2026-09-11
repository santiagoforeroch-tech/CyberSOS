@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\abrir_cybersos.ps1"
if errorlevel 1 pause
endlocal
