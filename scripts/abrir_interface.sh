#!/usr/bin/env bash
# Abre a interface no navegador (Mac e Linux). Rode: ./scripts/abrir_interface.sh
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -x .venv/bin/python ]]; then
  echo "[ERRO] Ambiente não encontrado. Rode antes o script de instalação do seu sistema:"
  echo "       Mac: ./scripts/setup_mac.sh    Ubuntu: ./scripts/setup_linux.sh"
  exit 1
fi

exec .venv/bin/python -m callcenter_lab "$@"
