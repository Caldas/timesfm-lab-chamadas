@echo off
rem Abre a interface no navegador (Windows). De dois cliques neste arquivo.
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
  echo [ERRO] Ambiente nao encontrado. Rode antes: scripts\setup_windows.ps1
  echo Veja docs\01-instalar-windows.md
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m callcenter_lab %*
pause
