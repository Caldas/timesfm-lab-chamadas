#!/bin/bash
# Instala o laboratório no Mac. Dê dois cliques neste arquivo no Finder.
# (na primeira vez, o macOS pode pedir: clique com o botão direito > Abrir > Abrir)
cd "$(dirname "$0")/.." || exit 1
./scripts/setup_mac.sh "$@"
status=$?
echo
read -n 1 -s -r -p "Tecle qualquer tecla para fechar esta janela..." || true
echo
exit $status
