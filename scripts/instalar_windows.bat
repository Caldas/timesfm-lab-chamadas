@echo off
rem Instala o laboratorio no Windows. De dois cliques neste arquivo.
rem (equivale a: powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1)
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_windows.ps1" %*
set SETUP_EXIT=%ERRORLEVEL%
echo.
pause
exit /b %SETUP_EXIT%
