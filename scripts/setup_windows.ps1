# Instala o laboratorio no Windows 10/11.
# Rode no PowerShell, na raiz do repositorio:
#   powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
# (so ASCII de proposito: o Windows PowerShell 5.1 nao mostra bem acentos e emojis)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

function Stop-Setup($message) {
    Write-Host "[ERRO] $message" -ForegroundColor Red
    exit 1
}

function Invoke-Checked($exe, $arguments) {
    & $exe @arguments
    if ($LASTEXITCODE -ne 0) { Stop-Setup "Falhou: $exe $($arguments -join ' ')" }
}

# --- 1. Achar um Python 3.10+ (o lancador 'py' primeiro: ignora o atalho da Microsoft Store) ---
$pythonCmd = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    foreach ($version in @("3.12", "3.11", "3.13", "3.10")) {
        & py "-$version" -c "import sys" 2>$null
        if ($LASTEXITCODE -eq 0) { $pythonCmd = @("py", "-$version"); break }
    }
}
if (-not $pythonCmd -and (Get-Command python -ErrorAction SilentlyContinue)) {
    & python -c "import sys" 2>$null
    if ($LASTEXITCODE -eq 0) { $pythonCmd = @("python") }
}
if (-not $pythonCmd) {
    Stop-Setup "Python nao encontrado. Instale em https://www.python.org/downloads/windows/ (marque 'Add python.exe to PATH') e rode de novo."
}

$pythonExe = $pythonCmd[0]
$pythonArgs = @()
if ($pythonCmd.Count -gt 1) { $pythonArgs = $pythonCmd[1..($pythonCmd.Count - 1)] }

& $pythonExe @pythonArgs -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if ($LASTEXITCODE -ne 0) {
    Stop-Setup "Precisa de Python 3.10 ou mais novo. Instale um mais novo em python.org."
}
$pythonVersion = (& $pythonExe @pythonArgs --version)
Write-Host "[INFO] Usando $pythonVersion"

# --- 2. Avisos de ambiente ---
if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") {
    Write-Host "[AVISO] Windows em ARM64: o PyTorch pode nao ter pacote para este processador. Se a instalacao falhar, veja docs\06-problemas-comuns.md" -ForegroundColor Yellow
}
$projectPath = (Get-Location).Path
$longPaths = (Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name LongPathsEnabled -ErrorAction SilentlyContinue).LongPathsEnabled
if ($projectPath.Length -gt 80 -and $longPaths -ne 1) {
    Write-Host "[AVISO] O caminho do projeto e longo ($($projectPath.Length) caracteres) e os 'caminhos longos' do Windows estao desligados." -ForegroundColor Yellow
    Write-Host "        A instalacao pode falhar com 'WinError 206'. Mova o projeto para uma pasta curta (ex.: C:\timesfm-lab)." -ForegroundColor Yellow
}

# --- 3. Ambiente virtual e dependencias ---
Write-Host "[1/3] Criando ambiente virtual em .venv ..."
Invoke-Checked $pythonExe ($pythonArgs + @("-m", "venv", ".venv"))
$venvPython = Join-Path $projectPath ".venv\Scripts\python.exe"

Write-Host "[2/3] Instalando dependencias (pode levar alguns minutos) ..."
Invoke-Checked $venvPython @("-m", "pip", "install", "--upgrade", "pip")
Invoke-Checked $venvPython @("-m", "pip", "install", "-r", "requirements\windows.txt")
Invoke-Checked $venvPython @("-m", "pip", "install", "-e", ".", "--no-deps")

Write-Host "[3/3] Verificando o ambiente ..."
Invoke-Checked $venvPython @("scripts\verificar_ambiente.py")

Write-Host ""
Write-Host "[OK] Pronto! Para abrir a interface nas proximas vezes:" -ForegroundColor Green
Write-Host "   de dois cliques em scripts\abrir_interface.bat"
Write-Host "ou, no PowerShell:"
Write-Host "   .\.venv\Scripts\python.exe -m streamlit run app\app.py"
