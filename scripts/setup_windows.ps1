# Instala o laboratorio no Windows 10/11.
# Detecta o que ja existe (Python, .venv, bibliotecas) e instala so o que falta.
#
# Uso (PowerShell, na raiz do repositorio):
#   powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
#   ... -Yes           responde "sim" as perguntas (instalar o Python com winget)
#   ... -Reinstalar    recria o .venv e reinstala tudo
# (so ASCII de proposito: o Windows PowerShell 5.1 nao mostra bem acentos e emojis)
param(
    [switch]$Yes,
    [switch]$Reinstalar
)

# Importante: nao usar $ErrorActionPreference = "Stop". No Windows PowerShell 5.1 ele transforma
# qualquer mensagem no stderr de um programa (pip, py) em erro fatal. Checamos os codigos de saida.
$ErrorActionPreference = "Continue"
Set-Location (Join-Path $PSScriptRoot "..")

function Stop-Setup($message) {
    Write-Host "[ERRO] $message" -ForegroundColor Red
    exit 1
}

function Invoke-Checked($exe, $arguments) {
    & $exe @arguments
    if ($LASTEXITCODE -ne 0) { Stop-Setup "Falhou: $exe $($arguments -join ' ')" }
}

# Roda um programa em silencio e diz se ele terminou com sucesso.
function Test-Runs($exe, $arguments) {
    & $exe @arguments *> $null
    return ($LASTEXITCODE -eq 0)
}

function Confirm-Action($question) {
    if ($Yes) { return $true }
    if (-not [Environment]::UserInteractive -or [Console]::IsInputRedirected) { return $false }
    $answer = Read-Host "$question [s/N]"
    return ($answer -match '^[sSyY]')
}

$versionCheck = "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"

# Acha um Python 3.10+ (o lancador 'py' primeiro: ignora o atalho da Microsoft Store).
# Devolve @(exe, args...) ou $null.
function Find-Python {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        # Prefere 3.12 (a mais testada); "-3" e o Python 3 mais novo instalado.
        foreach ($flag in @("-3.12", "-3.11", "-3.13", "-3.10", "-3")) {
            if (Test-Runs "py" @($flag, "-c", $versionCheck)) { return @("py", $flag) }
        }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        if (Test-Runs "python" @("-c", $versionCheck)) { return @("python") }
    }
    return $null
}

# --- 1. Python: usar o que ja existe; se faltar, oferecer instalar com winget ---
$pythonCmd = Find-Python
if (-not $pythonCmd) {
    Write-Host "[INFO] Nenhum Python 3.10+ encontrado."
    if ((Get-Command winget -ErrorAction SilentlyContinue) -and (Confirm-Action "Instalar o Python 3.12 com o winget agora?")) {
        & winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
        # Atualiza o PATH desta janela para enxergar o Python recem-instalado.
        $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
        $pythonCmd = Find-Python
        if (-not $pythonCmd) {
            $installed = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
            if (Test-Path $installed) { $pythonCmd = @($installed) }
        }
    }
}
if (-not $pythonCmd) {
    Stop-Setup "Python 3.10+ nao encontrado. Instale em https://www.python.org/downloads/windows/ (marque 'Add python.exe to PATH') ou rode: winget install Python.Python.3.12 - e rode este script de novo."
}

$pythonExe = $pythonCmd[0]
$pythonArgs = @()
if ($pythonCmd.Count -gt 1) { $pythonArgs = $pythonCmd[1..($pythonCmd.Count - 1)] }
$pythonVersion = (& $pythonExe @pythonArgs --version)
Write-Host "[OK] Python encontrado: $pythonVersion"

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

# --- 3. Ambiente virtual: reaproveitar se estiver bom ---
$venvPython = Join-Path $projectPath ".venv\Scripts\python.exe"
if ((-not $Reinstalar) -and (Test-Path $venvPython) -and (Test-Runs $venvPython @("-c", $versionCheck))) {
    Write-Host "[REUSO] Ambiente .venv ja existe e e compativel: reaproveitando."
} else {
    Write-Host "[INFO] Criando ambiente virtual em .venv ..."
    Invoke-Checked $pythonExe ($pythonArgs + @("-m", "venv", "--clear", ".venv"))
}

# --- 4. Dependencias: instalar so se algo estiver faltando ---
# 'pip --dry-run' lista "Would install ..." quando falta alguma coisa.
$dryRun = (& $venvPython -m pip install --dry-run -r requirements\windows.txt 2>&1 | Out-String)
$missing = ($LASTEXITCODE -ne 0) -or ($dryRun -match "(?m)^Would install")
if ((-not $Reinstalar) -and (-not $missing)) {
    Write-Host "[REUSO] Dependencias ja instaladas (requirements\windows.txt): nada a baixar."
} else {
    Write-Host "[INFO] Instalando as dependencias que faltam (pode levar alguns minutos) ..."
    Invoke-Checked $venvPython @("-m", "pip", "install", "--upgrade", "pip")
    Invoke-Checked $venvPython @("-m", "pip", "install", "-r", "requirements\windows.txt")
}
if (Test-Runs $venvPython @("-c", "import callcenter_lab")) {
    Write-Host "[REUSO] Pacote callcenter_lab ja instalado."
} else {
    Invoke-Checked $venvPython @("-m", "pip", "install", "-e", ".", "--no-deps")
}

# --- 5. Conferir ---
Write-Host "[INFO] Verificando o ambiente ..."
Invoke-Checked $venvPython @("scripts\verificar_ambiente.py")

Write-Host ""
Write-Host "[OK] Pronto! Para abrir a interface nas proximas vezes:" -ForegroundColor Green
Write-Host "   de dois cliques em scripts\abrir_interface.bat"
Write-Host "ou, no PowerShell:"
Write-Host "   .\.venv\Scripts\python.exe -m streamlit run app\app.py"
