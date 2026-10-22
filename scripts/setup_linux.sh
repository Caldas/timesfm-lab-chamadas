#!/usr/bin/env bash
# Instala o laboratório no Ubuntu (ou outro Linux baseado em Debian).
# Detecta o que já existe (Python, venv, .venv, PyTorch, bibliotecas) e instala só o que falta.
#
# Uso (na raiz do repositório):
#   ./scripts/setup_linux.sh                # PyTorch só-CPU (leve, recomendado)
#   ./scripts/setup_linux.sh --gpu          # PyTorch com CUDA, para placa NVIDIA (~3 GB)
#   ./scripts/setup_linux.sh --yes          # responde "sim" às perguntas (instalar pacotes com apt)
#   ./scripts/setup_linux.sh --reinstalar   # recria o .venv e reinstala tudo
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "[ERRO] Este script é para Linux. Veja docs/01-instalar.md"
  exit 1
fi

USE_GPU=0
ASSUME_YES=0
FORCE=0
for arg in "$@"; do
  case "$arg" in
    --gpu) USE_GPU=1 ;;
    -y|--yes) ASSUME_YES=1 ;;
    --reinstalar) FORCE=1 ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "[ERRO] Opção desconhecida: $arg"; exit 1 ;;
  esac
done

PYCHECK='import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'
REQ="requirements/linux.txt"
PY="${PYTHON:-python3}"

confirm() {
  [[ "$ASSUME_YES" == "1" ]] && return 0
  [[ -t 0 ]] || return 1
  local answer
  read -r -p "$1 [s/N] " answer
  [[ "$answer" =~ ^[sSyY] ]]
}

apt_install() {
  local sudo_cmd=""
  if [[ "$(id -u)" -ne 0 ]]; then
    command -v sudo >/dev/null 2>&1 || { echo "[ERRO] Preciso de root ou sudo para instalar pacotes."; return 1; }
    sudo_cmd="sudo"
  fi
  $sudo_cmd apt-get update
  $sudo_cmd env DEBIAN_FRONTEND=noninteractive apt-get install -y "$@"
}

deps_missing() {
  # pip --dry-run lists "Would install ..." when anything is missing. Capture first: piping into
  # `grep -q` can make pip die from SIGPIPE and fool `pipefail`.
  local out
  out="$("$VENV_PY" -m pip install --dry-run -r "$1" 2>&1)" || return 0
  grep -q "^Would install" <<<"$out"
}

python_present() { command -v "$PY" >/dev/null 2>&1; }
python_version_ok() { python_present && "$PY" -c "$PYCHECK" >/dev/null 2>&1; }
venv_ok() { python_present && "$PY" -c 'import ensurepip, venv' >/dev/null 2>&1; }

# --- 1. Python e módulo venv: usar o que já existe; se faltar, oferecer instalar com apt ---
if ! python_present || ! venv_ok; then
  missing="python3 python3-venv python3-pip"
  if python_present && ! venv_ok; then
    echo "[INFO] Python encontrado, mas faltam os módulos venv/pip."
  else
    echo "[INFO] Python não encontrado."
  fi
  if command -v apt-get >/dev/null 2>&1 && confirm "Instalar com apt ($missing) agora?"; then
    # shellcheck disable=SC2086
    apt_install $missing
  else
    echo "[ERRO] Instale com: sudo apt install $missing"
    echo "       Depois rode de novo: $0"
    exit 1
  fi
fi
if ! python_version_ok; then
  echo "[ERRO] Precisa de Python 3.10 ou mais novo. Versão atual: $("$PY" --version)"
  echo "       Use Ubuntu 22.04 ou mais novo, ou instale outro Python e rode: PYTHON=python3.12 $0"
  exit 1
fi
echo "[OK] Python encontrado: $("$PY" --version) ($PY) em $(uname -m)"

if [[ "$USE_GPU" == "1" ]]; then
  if ! command -v nvidia-smi >/dev/null 2>&1 || ! nvidia-smi >/dev/null 2>&1; then
    echo "[ERRO] --gpu pedido, mas o driver NVIDIA não respondeu (nvidia-smi). Instale o driver ou rode sem --gpu."
    exit 1
  fi
  echo "[INFO] Modo GPU: PyTorch com CUDA."
else
  echo "[INFO] Modo CPU: PyTorch só-CPU."
  if command -v nvidia-smi >/dev/null 2>&1; then
    echo "[INFO] Placa NVIDIA detectada. Para usá-la, rode: $0 --gpu"
  fi
fi

# --- 2. Ambiente virtual: reaproveitar se estiver bom ---
if [[ "$FORCE" == "0" && -x .venv/bin/python ]] && .venv/bin/python -c "$PYCHECK" >/dev/null 2>&1; then
  echo "[REUSO] Ambiente .venv já existe e é compatível: reaproveitando."
else
  echo "[INFO] Criando ambiente virtual em .venv ..."
  "$PY" -m venv --clear .venv
fi
VENV_PY=".venv/bin/python"

# --- 3. PyTorch: só instalar se faltar (ou se o tipo, CPU/GPU, não for o pedido) ---
torch_kind() {
  "$VENV_PY" -c 'import torch; print("gpu" if torch.version.cuda else "cpu")' 2>/dev/null || echo "none"
}
KIND="$(torch_kind)"
WANT="cpu"; [[ "$USE_GPU" == "1" ]] && WANT="gpu"
if [[ "$FORCE" == "0" && "$KIND" == "$WANT" ]]; then
  echo "[REUSO] PyTorch ($WANT) já instalado."
elif [[ "$FORCE" == "0" && "$KIND" == "gpu" && "$WANT" == "cpu" ]]; then
  echo "[REUSO] PyTorch com CUDA já instalado: mantendo (rode com --reinstalar para trocar por só-CPU)."
else
  [[ "$KIND" != "none" ]] && "$VENV_PY" -m pip uninstall -y torch
  echo "[INFO] Instalando o PyTorch ($WANT) ..."
  "$VENV_PY" -m pip install --upgrade pip
  if [[ "$USE_GPU" == "0" ]]; then
    # A versão padrão do Linux traz CUDA (~3 GB); a versão CPU tem uns 200 MB.
    if ! "$VENV_PY" -m pip install torch --index-url https://download.pytorch.org/whl/cpu; then
      echo "[AVISO] Não consegui a versão só-CPU; instalando a versão padrão (maior)."
      "$VENV_PY" -m pip install torch
    fi
  else
    "$VENV_PY" -m pip install torch
  fi
fi

# --- 4. Demais dependências: instalar só se algo estiver faltando ---
if [[ "$FORCE" == "0" ]] && ! deps_missing "$REQ"; then
  echo "[REUSO] Dependências já instaladas ($REQ): nada a baixar."
else
  echo "[INFO] Instalando as dependências que faltam (pode levar alguns minutos) ..."
  "$VENV_PY" -m pip install -r "$REQ"
fi
if "$VENV_PY" -c "import callcenter_lab" >/dev/null 2>&1; then
  echo "[REUSO] Pacote callcenter_lab já instalado."
else
  "$VENV_PY" -m pip install -e . --no-deps
fi

# --- 5. Conferir ---
echo "[INFO] Verificando o ambiente ..."
"$VENV_PY" scripts/verificar_ambiente.py

cat <<MSG

[OK] Pronto! Para usar nas próximas vezes:
   ./scripts/abrir_interface.sh
ou, manualmente:
   source .venv/bin/activate
   streamlit run app/app.py
MSG
