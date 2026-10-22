#!/bin/bash
# Abre a interface no Mac. Dê dois cliques neste arquivo no Finder.
cd "$(dirname "$0")/.." || exit 1
./scripts/abrir_interface.sh "$@"
status=$?
echo
read -n 1 -s -r -p "Tecle qualquer tecla para fechar esta janela..." || true
echo
exit $status
