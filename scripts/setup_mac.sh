#!/usr/bin/env bash
# Instala o laboratório no Mac (Apple silicon ou Intel).
# Rode na raiz do repositório: ./scripts/setup_mac.sh
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "❌ Este script é para macOS. Veja docs/01-instalar-mac.md"
  exit 1
fi

ARCH="$(uname -m)"

# Terminal aberto em modo Rosetta num Mac Apple silicon aparece como x86_64 e instalaria a versão lenta.
if [[ "$ARCH" == "x86_64" && "$(sysctl -in sysctl.proc_translated 2>/dev/null || echo 0)" == "1" ]]; then
  echo "❌ Este Terminal está rodando em modo Rosetta (emulando Intel) num Mac Apple silicon."
  echo "   Rode: arch -arm64 ./scripts/setup_mac.sh   (veja docs/06-problemas-comuns.md)"
  exit 1
fi

# No Intel, o PyTorch só existe até a versão 2.2.2, que só suporta Python 3.10 a 3.12.
pick_python() {
  if [[ -n "${PYTHON:-}" ]]; then
    echo "$PYTHON"
  elif [[ "$ARCH" == "arm64" ]]; then
    echo "python3"
  else
    for candidate in python3.12 python3.11 python3.10; do
      if command -v "$candidate" >/dev/null 2>&1; then
        echo "$candidate"
        return
      fi
    done
    echo "python3"
  fi
}

PY="$(pick_python)"
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "❌ Python não encontrado. Instale com: brew install python@3.12 (veja docs/01-instalar-mac.md)"
  exit 1
fi
if ! "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
  echo "❌ Precisa de Python 3.10 ou mais novo. Versão atual: $("$PY" --version)"
  exit 1
fi

if [[ "$ARCH" == "arm64" ]]; then
  REQ="requirements/mac.txt"
  echo "ℹ️  Apple silicon detectado: usando o motor MLX."
else
  REQ="requirements/mac-intel.txt"
  echo "ℹ️  Mac Intel detectado: usando PyTorch em CPU (mais lento)."
  if ! "$PY" -c 'import sys; sys.exit(0 if sys.version_info < (3, 13) else 1)'; then
    echo "❌ No Mac Intel é preciso Python 3.10, 3.11 ou 3.12 (o seu é $("$PY" --version))."
    echo "   Rode: brew install python@3.12 && PYTHON=python3.12 ./scripts/setup_mac.sh"
    exit 1
  fi
fi
echo "ℹ️  Usando $("$PY" --version) ($PY)"

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
