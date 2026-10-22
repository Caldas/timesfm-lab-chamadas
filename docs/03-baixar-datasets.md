# 03 — Baixar datasets de chamadas

Um único script, `scripts/baixar_datasets.py`, baixa os datasets públicos de central telefônica e os
converte para o formato do laboratório (`timestamp`, `calls_offered`). As fontes, licenças e
detalhes de cada um estão em [data/README.md](../data/README.md).

> Cada dataset tem as suas condições de uso (alguns pedem citar a fonte, um pede avisar o autor).
> Leia o [data/README.md](../data/README.md) antes de reutilizar os dados em qualquer trabalho.

## Baixar todos

```bash
# Mac e Ubuntu
source .venv/bin/activate
python scripts/baixar_datasets.py
```

```powershell
# Windows (PowerShell), sem precisar ativar o ambiente
.\.venv\Scripts\python.exe scripts\baixar_datasets.py
```

Sem argumentos, ele baixa **todos**: `technion-bank`, `hyndman-bank` e `nyc-311` (cerca de 2 minutos,
com internet). Os arquivos ficam em `data/raw/<dataset>/`.

## Baixar só alguns

Passe os nomes que quiser:

```bash
python scripts/baixar_datasets.py technion-bank
python scripts/baixar_datasets.py technion-bank nyc-311
```

## Ver o que existe

```bash
python scripts/baixar_datasets.py --lista
```

Mostra cada dataset com descrição, granularidade, período, fonte e licença.

## Opções

| Opção | Para que serve |
|---|---|
| `--lista` | Mostra os datasets, fontes e licenças, sem baixar nada |
| `--forcar` | Baixa de novo, ignorando o que já está em `data/raw/` |
| `--saida PASTA` | Salva em outra pasta (padrão: `data/raw`) |
| `--nyc-ano-inicio 2018 --nyc-ano-fim 2019` | Anos do `nyc-311` (padrão 2016–2019) |
| `--kaggle dono/dataset` | Baixa qualquer dataset do Kaggle (veja abaixo) |

Rodar de novo não baixa nada outra vez: os arquivos originais ficam guardados em
`data/raw/<dataset>/_raw/` e o script avisa `[REUSO]`.

## Depois de baixar

Abra a interface ([04](04-usando-a-interface.md)). Os arquivos aparecem na lista da barra lateral
como `technion-bank/technion-bank.csv`, `hyndman-bank/hyndman-bank.csv` etc.

Dica de intervalo na interface: o `technion-bank` está em 30 minutos, o `hyndman-bank` em 5 minutos
e o `nyc-311` em 1 hora; escolha o "Intervalo" igual ou maior que o do arquivo.

## Usar um dataset do Kaggle (opcional)

O Kaggle tem muitos datasets de call center, mas as licenças variam e muitos são sintéticos. Confira
a página antes de usar. Para baixar um, você precisa de uma conta e de um token:

1. Instale o cliente no ambiente do projeto: `pip install kaggle`.
2. No Kaggle, clique na sua foto → **Settings** → seção **API** e crie um token (siga a página: ela
   mostra o formato atual).
3. Se for um arquivo `kaggle.json`, coloque-o na pasta `.kaggle` da sua conta.

**Mac e Ubuntu** (`~/.kaggle/`):

```bash
mkdir -p ~/.kaggle
mv ~/Downloads/kaggle.json ~/.kaggle/
chmod 600 ~/.kaggle/kaggle.json
```

**Windows** (`C:\Users\SEU_USUARIO\.kaggle\`), no PowerShell:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.kaggle"
Move-Item "$env:USERPROFILE\Downloads\kaggle.json" "$env:USERPROFILE\.kaggle\"
```

> O token é uma senha. Nunca coloque no Git. O projeto já ignora arquivos `kaggle.json`.

4. Aceite os termos na página do dataset e baixe:

```bash
python scripts/baixar_datasets.py --kaggle dono/nome-do-dataset
```

O "dono/nome" aparece no endereço da página: `kaggle.com/datasets/dono/nome-do-dataset`. O arquivo
precisa ter uma coluna de data/hora e uma de número de chamadas; a interface deixa você escolher as
colunas.

## Usar seus próprios dados

Qualquer CSV com uma coluna de data/hora e uma de chamadas serve. Exporte do seu sistema o número de
chamadas oferecidas por intervalo e arraste o arquivo na interface. **Atenção à privacidade:** use
só dados agregados (contagens por intervalo), sem números de telefone ou dados de clientes.
