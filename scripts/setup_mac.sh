#!/usr/bin/env bash
# Instala o laboratório no Mac (Apple silicon ou Intel).
# Detecta o que já existe (Python, .venv, bibliotecas) e instala só o que falta.
#
# Uso (na raiz do repositório):
#   ./scripts/setup_mac.sh                # normal
#   ./scripts/setup_mac.sh --yes          # responde "sim" às perguntas (instalar Python via Homebrew)
#   ./scripts/setup_mac.sh --reinstalar   # recria o .venv e reinstala tudo
set -euo pipefail

cd "$(dirname "$0")/.."

ASSUME_YES=0
FORCE=0
for arg in "$@"; do
  case "$arg" in
    -y|--yes) ASSUME_YES=1 ;;
    --reinstalar) FORCE=1 ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "[ERRO] Opção desconhecida: $arg"; exit 1 ;;
  esac
done

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "[ERRO] Este script é para macOS. Veja docs/01-instalar.md"
  exit 1
fi

ARCH="$(uname -m)"

# Terminal aberto em modo Rosetta num Mac Apple silicon aparece como x86_64 e instalaria a versão lenta.
if [[ "$ARCH" == "x86_64" && "$(sysctl -in sysctl.proc_translated 2>/dev/null || echo 0)" == "1" ]]; then
  echo "[ERRO] Este Terminal está rodando em modo Rosetta (emulando Intel) num Mac Apple silicon."
  echo "       Rode: arch -arm64 ./scripts/setup_mac.sh   (veja docs/06-problemas-comuns.md)"
  exit 1
fi

# Python aceito: 3.10+; no Intel o PyTorch só existe até a 2.2.2 (Python 3.10 a 3.12);
# no Apple silicon o Python precisa ser nativo (arm64) para usar o MLX.
if [[ "$ARCH" == "arm64" ]]; then
  PYCHECK='import sys, platform; sys.exit(0 if sys.version_info >= (3, 10) and platform.machine() == "arm64" else 1)'
  REQ="requirements/mac.txt"
  CANDIDATES=(python3 python3.12 python3.13 python3.11 python3.10)
else
  PYCHECK='import sys; sys.exit(0 if (3, 10) <= sys.version_info[:2] <= (3, 12) else 1)'
  REQ="requirements/mac-intel.txt"
  CANDIDATES=(python3.12 python3.11 python3.10 python3)
fi

confirm() {
  [[ "$ASSUME_YES" == "1" ]] && return 0
  [[ -t 0 ]] || return 1
  local answer
  read -r -p "$1 [s/N] " answer
  [[ "$answer" =~ ^[sSyY] ]]
}

python_ok() {
  command -v "$1" >/dev/null 2>&1 && "$1" -c "$PYCHECK" >/dev/null 2>&1
}

find_python() {
  if [[ -n "${PYTHON:-}" ]]; then
    python_ok "$PYTHON" && echo "$PYTHON"
    return 0
  fi
  local candidate brew_py
  for candidate in "${CANDIDATES[@]}"; do
    if python_ok "$candidate"; then echo "$candidate"; return 0; fi
  done
  if command -v brew >/dev/null 2>&1; then
    brew_py="$(brew --prefix 2>/dev/null)/bin/python3.12"
    if python_ok "$brew_py"; then echo "$brew_py"; return 0; fi
  fi
  return 0
}

deps_missing() {
  # pip --dry-run lists "Would install ..." when anything is missing. Capture first: piping into
  # `grep -q` can make pip die from SIGPIPE and fool `pipefail`.
  local out
  out="$("$VENV_PY" -m pip install --dry-run -r "$1" 2>&1)" || return 0
  grep -q "^Would install" <<<"$out"
}

# --- 1. Python: usar o que já existe; se faltar, oferecer instalar ---
PY="$(find_python)"
if [[ -z "$PY" ]]; then
  echo "[INFO] Nenhum Python compatível encontrado."
  if command -v brew >/dev/null 2>&1 && confirm "Instalar o Python 3.12 com o Homebrew agora?"; then
    brew install python@3.12
    PY="$(find_python)"
  fi
fi
if [[ -z "$PY" ]]; then
  if [[ "$ARCH" == "arm64" ]]; then
    echo "[ERRO] Precisa de Python 3.10 ou mais novo (nativo arm64)."
  else
    echo "[ERRO] No Mac Intel é preciso Python 3.10, 3.11 ou 3.12 (o PyTorch não existe para versões mais novas)."
  fi
  echo "       Instale com: brew install python@3.12   (Homebrew: https://brew.sh)"
  echo "       Depois rode de novo: ./scripts/setup_mac.sh"
  exit 1
fi
if [[ "$ARCH" == "arm64" ]]; then
  echo "[OK] Python encontrado: $("$PY" --version) ($PY). Motor: MLX (Apple silicon)."
else
  echo "[OK] Python encontrado: $("$PY" --version) ($PY). Motor: PyTorch em CPU (Mac Intel, mais lento)."
fi

# --- 2. Ambiente virtual: reaproveitar se estiver bom ---
if [[ "$FORCE" == "0" && -x .venv/bin/python ]] && .venv/bin/python -c "$PYCHECK" >/dev/null 2>&1; then
  echo "[REUSO] Ambiente .venv já existe e é compatível: reaproveitando."
else
  echo "[INFO] Criando ambiente virtual em .venv ..."
  "$PY" -m venv --clear .venv
fi
VENV_PY=".venv/bin/python"

# --- 3. Dependências: instalar só se algo estiver faltando ---
if [[ "$FORCE" == "0" ]] && ! deps_missing "$REQ"; then
  echo "[REUSO] Dependências já instaladas ($REQ): nada a baixar."
else
  echo "[INFO] Instalando as dependências que faltam (pode levar alguns minutos) ..."
  "$VENV_PY" -m pip install --upgrade pip
  "$VENV_PY" -m pip install -r "$REQ"
fi
# O próprio laboratório: no pacote do release vem como wheel (pasta wheels/); no repositório, em modo editável.
WHEEL="$(ls wheels/callcenter_lab-*.whl 2>/dev/null | head -n 1 || true)"
INSTALLED="$("$VENV_PY" -c 'import callcenter_lab; print(callcenter_lab.__version__)' 2>/dev/null || true)"
if [[ -n "$WHEEL" ]]; then
  WHEEL_VERSION="$(basename "$WHEEL" | cut -d- -f2)"
  if [[ "$FORCE" == "0" && "$INSTALLED" == "$WHEEL_VERSION" ]]; then
    echo "[REUSO] Pacote callcenter_lab $INSTALLED já instalado."
  else
    echo "[INFO] Instalando o pacote callcenter_lab $WHEEL_VERSION ..."
    "$VENV_PY" -m pip install --no-deps --force-reinstall "$WHEEL"
  fi
elif [[ -n "$INSTALLED" ]]; then
  echo "[REUSO] Pacote callcenter_lab $INSTALLED já instalado."
else
  "$VENV_PY" -m pip install -e . --no-deps
fi

# --- 4. Conferir ---
echo "[INFO] Verificando o ambiente ..."
"$VENV_PY" scripts/verificar_ambiente.py

cat <<MSG

✅ Pronto! Para usar nas próximas vezes:
   ./scripts/abrir_interface.sh
ou, manualmente:
   source .venv/bin/activate
   python -m callcenter_lab
MSG
