# 03 — Baixar dados do Kaggle

O [Kaggle](https://www.kaggle.com) é um site com milhares de conjuntos de dados públicos. Há dois
caminhos: baixar pelo site (mais simples) ou pelo script (automático).

> Cada dataset tem a própria licença. Leia na página do dataset antes de usar.

## Caminho A — Baixar pelo site (sem token)

1. Crie uma conta gratuita no Kaggle e entre.
2. Abra a página do dataset (sugestões em [data/README.md](../data/README.md)).
3. Clique em **Download** e descompacte o arquivo `.zip`.
4. Na interface, use **Enviar um CSV** na barra lateral e escolha o arquivo.

Ou copie o `.csv` para a pasta `data/raw/` do projeto: ele aparece sozinho na lista da interface.

## Caminho B — Pelo script

### 1. Criar o token do Kaggle (uma vez só)

1. No Kaggle, clique na sua foto → **Settings**.
2. Na seção **API**, crie um token. Siga as instruções da própria página: ela mostra o formato atual
   (um arquivo `kaggle.json` ou uma chave de acesso).
3. Se for o arquivo `kaggle.json`, coloque-o na pasta `.kaggle` da sua conta:

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

### 2. Aceitar os termos do dataset

Alguns datasets exigem que você abra a página e aceite os termos antes de baixar.

### 3. Baixar

Mac e Ubuntu:

```bash
source .venv/bin/activate
python scripts/baixar_kaggle.py --lista            # nomes curtos sugeridos
python scripts/baixar_kaggle.py metro-interstate   # baixa para data/raw/
```

Windows (PowerShell), sem precisar ativar o ambiente:

```powershell
.\.venv\Scripts\python.exe scripts\baixar_kaggle.py --lista
.\.venv\Scripts\python.exe scripts\baixar_kaggle.py metro-interstate
```

Qualquer dataset: `python scripts/baixar_kaggle.py dono/nome-do-dataset` (o "dono/nome" aparece no
endereço da página: `kaggle.com/datasets/dono/nome-do-dataset`).

Depois abra a interface; os arquivos baixados estão na lista.

## Dica: o que procurar

Para este laboratório serve qualquer CSV com uma coluna de **data/hora** e uma coluna de **contagem
de veículos** (ou volume). Procure no Kaggle por "traffic volume", "traffic counts", "vehicle count".
Quanto mais longo o histórico (semanas ou meses, em intervalo regular), melhor.
