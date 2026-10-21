#!/usr/bin/env bash
# Instala o laboratório no Ubuntu (ou outro Linux baseado em Debian).
# Rode na raiz do repositório:
#   ./scripts/setup_linux.sh          # PyTorch só-CPU (leve, recomendado)
#   ./scripts/setup_linux.sh --gpu    # PyTorch com CUDA, para placa NVIDIA (download de ~3 GB)
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "[ERRO] Este script é para Linux. Veja docs/01-instalar.md"
  exit 1
fi

USE_GPU=0
for arg in "$@"; do
  case "$arg" in
    --gpu) USE_GPU=1 ;;
    -h|--help) sed -n '2,6p' "$0"; exit 0 ;;
    *) echo "[ERRO] Opção desconhecida: $arg"; exit 1 ;;
  esac
done

PY="${PYTHON:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "[ERRO] python3 não encontrado. Instale com: sudo apt install python3 python3-venv python3-pip"
  exit 1
fi
if ! "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
  echo "[ERRO] Precisa de Python 3.10 ou mais novo. Versão atual: $("$PY" --version)"
  echo "       Use Ubuntu 22.04 ou mais novo, ou instale outro Python e rode: PYTHON=python3.12 $0"
  exit 1
fi
# No Ubuntu o módulo venv vem num pacote separado.
if ! "$PY" -c 'import ensurepip, venv' >/dev/null 2>&1; then
  echo "[ERRO] Faltam os módulos venv/pip do Python. Instale com:"
  echo "       sudo apt install python3-venv python3-pip"
  exit 1
fi

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
echo "[INFO] Usando $("$PY" --version) ($PY) em $(uname -m)"

echo "[1/4] Criando ambiente virtual em .venv ..."
"$PY" -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip

echo "[2/4] Instalando o PyTorch ..."
if [[ "$USE_GPU" == "0" ]]; then
  # A versão padrão do Linux traz CUDA (~3 GB); a versão CPU tem uns 200 MB.
  if ! python -m pip install torch --index-url https://download.pytorch.org/whl/cpu; then
    echo "[AVISO] Não consegui a versão só-CPU; instalando a versão padrão (maior)."
    python -m pip install torch
  fi
else
  python -m pip install torch
fi

echo "[3/4] Instalando as demais dependências (pode levar alguns minutos) ..."
python -m pip install -r requirements/linux.txt
python -m pip install -e . --no-deps

echo "[4/4] Verificando o ambiente ..."
python scripts/verificar_ambiente.py

cat <<MSG

[OK] Pronto! Para usar nas próximas vezes:
   ./scripts/abrir_interface.sh
ou, manualmente:
   source .venv/bin/activate
   streamlit run app/app.py
MSG
