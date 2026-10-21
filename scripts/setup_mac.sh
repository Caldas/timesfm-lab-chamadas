#!/usr/bin/env bash
# Instala o laboratório no Mac. Rode na raiz do repositório: ./scripts/setup_mac.sh
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "❌ Este script é para macOS. Veja docs/01-instalar-mac.md"
  exit 1
fi

PY="${PYTHON:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "❌ python3 não encontrado. Instale com: brew install python@3.12 (veja docs/01-instalar-mac.md)"
  exit 1
fi
if ! "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
  echo "❌ Precisa de Python 3.10 ou mais novo. Versão atual: $("$PY" --version)"
  exit 1
fi

if [[ "$(uname -m)" == "arm64" ]]; then
  REQ="requirements/mac.txt"
  echo "ℹ️  Apple silicon detectado: usando o motor MLX."
else
  REQ="requirements/mac-intel.txt"
  echo "ℹ️  Mac Intel detectado: usando PyTorch em CPU (mais lento)."
fi

echo "➡️  Criando ambiente virtual em .venv ..."
"$PY" -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

echo "➡️  Instalando dependências (pode levar alguns minutos) ..."
python -m pip install --upgrade pip
python -m pip install -r "$REQ"
python -m pip install -e . --no-deps

echo "➡️  Verificando o ambiente ..."
python scripts/verificar_ambiente.py

cat <<MSG

✅ Pronto! Para usar nas próximas vezes:
   source .venv/bin/activate
   streamlit run app/app.py
MSG
