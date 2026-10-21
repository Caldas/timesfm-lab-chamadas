# 06 — Problemas comuns

Rode primeiro o diagnóstico (com o ambiente ativado: `source .venv/bin/activate`):

```bash
python scripts/verificar_ambiente.py
```

Ele diz o que está faltando.

## `command not found: python3` ou `brew`

Faltam as ferramentas do [Passo 2](01-instalar-mac.md). Instale o Homebrew e rode
`brew install git python@3.12`. Feche e abra o Terminal depois.

## `permission denied: ./scripts/setup_mac.sh`

```bash
chmod +x scripts/setup_mac.sh
./scripts/setup_mac.sh
```

## `Precisa de Python 3.10 ou mais novo`

```bash
brew install python@3.12
PYTHON=python3.12 ./scripts/setup_mac.sh
```

## `No module named 'timesfm3'` (ou `streamlit`, `pandas`…)

O ambiente virtual não está ativo ou a instalação não terminou.

```bash
source .venv/bin/activate     # o Terminal deve mostrar (.venv)
./scripts/setup_mac.sh        # reinstala
```

## O motor aparece como `torch` em vez de `mlx`

O MLX só funciona em Mac com Apple silicon e com Python nativo (arm64). Confira:

```bash
python -c "import platform; print(platform.machine())"
```

Deve mostrar `arm64`. Se mostrar `x86_64`, seu Python roda em modo de compatibilidade: instale o do
Homebrew (`brew install python@3.12`) e rode o setup de novo. Em Mac Intel o `torch` é o esperado.

## O download do modelo falha ou fica parado

- Confira a internet. Em rede de empresa, o certificado de segurança pode bloquear o download.
- Tente de novo: o download recomeça de onde parou.
- O modelo é baixado do Hugging Face para `~/.cache/huggingface/`.

## `Falha no download` do Kaggle

- O token está em `~/.kaggle/kaggle.json`? Veja [03](03-baixar-dados-kaggle.md).
- Você abriu a página do dataset e aceitou os termos?
- O nome "dono/dataset" está certo?

## A interface mostra "Não consegui ler o arquivo" ou "Problema nos dados"

- Abra o CSV no Excel e confira se há uma coluna de data/hora e uma de números.
- Escolha as colunas certas na barra lateral.
- Datas em formato diferente (ex.: `31/12/2024`) às vezes são lidas errado. Teste no Excel
  convertendo para `2024-12-31`.

## O gráfico tem poucos pontos / "Reduza o horizonte"

O teste de realidade precisa de histórico suficiente. Reduza o horizonte, aumente
"Quanto histórico usar" ou escolha um agrupamento menor (por exemplo, Hora em vez de Dia).

## A interface não abre no navegador

Abra manualmente <http://localhost:8501>. Se a porta estiver ocupada:
`streamlit run app/app.py --server.port 8502`.

## Está lento

- Reduza "Quanto histórico usar" e o horizonte.
- Feche outros programas pesados.
- Na primeira previsão o modelo é carregado, o que leva mais tempo. As seguintes são mais rápidas.

## Nada resolveu

Envie ao mantenedor: o comando que você rodou, a **mensagem de erro inteira** e a saída de
`python scripts/verificar_ambiente.py`.
