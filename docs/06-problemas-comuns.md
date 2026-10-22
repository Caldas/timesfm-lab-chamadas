# 06 — Problemas comuns

Rode primeiro o diagnóstico. Ele diz o que está faltando:

```bash
# Mac e Ubuntu
.venv/bin/python scripts/verificar_ambiente.py
```

```powershell
# Windows (PowerShell)
.\.venv\Scripts\python.exe scripts\verificar_ambiente.py
```

Seções: [Mac](#mac) · [Ubuntu](#ubuntu) · [Windows](#windows) · [em todos os sistemas](#em-todos-os-sistemas).

# Mac

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

(No Ubuntu use `./scripts/setup_linux.sh`; no Windows, `scripts\setup_windows.ps1`.)

## O motor aparece como `torch` em vez de `mlx`

- **Mac Intel:** `torch` é o esperado (o MLX só existe para Apple silicon). Funciona, mas é mais lento.
- **Mac Apple silicon:** o MLX só funciona com Python nativo (arm64). Confira:

```bash
python -c "import platform; print(platform.machine())"
```

Deve mostrar `arm64`. Se mostrar `x86_64`, seu Terminal ou seu Python roda em modo de
compatibilidade (Rosetta). Instale o Python do Homebrew (`brew install python@3.12`), abra um
Terminal novo e rode o setup de novo; se precisar, force o modo nativo:

```bash
arch -arm64 ./scripts/setup_mac.sh
```

## Mac Intel: `Could not find a version that satisfies the requirement torch==2.2.2`

Seu Python é novo demais (3.13 ou mais). No Mac Intel o PyTorch só existe para Python 3.10 a 3.12:

```bash
brew install python@3.12
rm -rf .venv
PYTHON=python3.12 ./scripts/setup_mac.sh
```

## Mac Intel: `A module that was compiled using NumPy 1.x cannot be run in NumPy 2`

O NumPy ficou novo demais para o PyTorch 2.2. Com o ambiente ativo:

```bash
python -m pip install "numpy<2"
```

## Mac Intel: está muito lento

É esperado: a CPU Intel é bem mais lenta que o chip Apple. Use históricos de 300 a 600 passos,
horizontes menores, e evite rodar o teste de realidade com horizontes longos.

# Ubuntu

## `python3 -m venv` falha / `ensurepip is not available`

Falta o pacote do venv:

```bash
sudo apt install python3-venv python3-pip
```

## `Precisa de Python 3.10 ou mais novo`

Seu Ubuntu é antigo (20.04 traz o Python 3.8). Use o Ubuntu 22.04 ou mais novo, ou instale um Python
mais novo (por exemplo, `sudo apt install python3.12 python3.12-venv`) e rode:

```bash
PYTHON=python3.12 ./scripts/setup_linux.sh
```

## `externally-managed-environment`

O Ubuntu 24.04 bloqueia `pip install` fora de um ambiente virtual. Use sempre o `.venv` criado pelo
script (`source .venv/bin/activate`). Não rode `pip install` com `sudo`.

## `--gpu pedido, mas o driver NVIDIA não respondeu`

O comando `nvidia-smi` precisa funcionar. Instale o driver (`sudo ubuntu-drivers install`, reinicie)
ou rode sem `--gpu` (modo CPU).

## O programa usa a CPU mesmo tendo placa NVIDIA

Você instalou sem `--gpu`. Apague a pasta `.venv` e rode `./scripts/setup_linux.sh --gpu`. Para
conferir: `python scripts/verificar_ambiente.py` mostra "torch ... na GPU".

## O download do PyTorch é enorme

Sem `--gpu`, o script baixa a versão leve só-CPU (~200 MB). Se baixou uns 3 GB, o endereço da versão
leve estava indisponível e ele usou a padrão (com CUDA): é normal, só demora.

## `./scripts/setup_linux.sh: Permission denied`

```bash
chmod +x scripts/*.sh
```

# Windows

## `python` abre a Microsoft Store

É o atalho da loja, não o Python. Instale o Python de verdade (`winget install Python.Python.3.12` ou
em python.org) e use o comando `py`. Feche e abra o PowerShell depois.

## "A execução de scripts foi desabilitada neste sistema"

Rode o script assim (vale só para esse comando):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
```

Para ativar o ambiente com `.\.venv\Scripts\Activate.ps1`, rode uma vez:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. Ou nem ative: use
`.\.venv\Scripts\python.exe ...`.

## `WinError 206` / "O nome do arquivo ou a extensão é muito grande"

O caminho do projeto é longo demais para o Windows. Mova o projeto para uma pasta curta, como
`C:\timesfm-lab`, apague a pasta `.venv` e rode a instalação de novo. (Alternativa, com
administrador: ativar "caminhos longos" no Windows e reiniciar.)

## O PowerShell mostra símbolos estranhos no lugar de acentos ou emojis

É só a fonte/código de página do console. Não afeta o funcionamento. No Windows Terminal (Windows 11)
aparece certo.

## O Firewall do Windows pergunta sobre o Python

Pode clicar em **Cancelar**: a interface abre normalmente neste computador.

## `torch` não instala em Windows ARM64

O PyTorch pode não ter pacote para esse processador. Use um computador x64, ou o Ubuntu/Mac.

## `scripts\abrir_interface.bat` diz "Ambiente nao encontrado"

Rode antes o `scripts\setup_windows.ps1` (veja [01-instalar-windows.md](01-instalar-windows.md)).

# Em todos os sistemas

## O download do modelo falha ou fica parado

- Confira a internet. Em rede de empresa, o certificado de segurança pode bloquear o download.
- Tente de novo: o download recomeça de onde parou.
- O modelo é baixado do Hugging Face para `~/.cache/huggingface/`.

## `baixar_datasets.py` falha ou dá `Falha ao baixar`

- Confira a internet. Em rede de empresa, o certificado de segurança pode bloquear o download.
- Baixe um dataset de cada vez para ver o erro de cada um: `python scripts/baixar_datasets.py technion-bank`.
- As fontes são sites de terceiros (Universidade de Berna, robjhyndman.com, NYC Open Data) e podem ficar
  fora do ar por algumas horas: tente de novo mais tarde. O que já foi baixado fica guardado em `data/raw/`.
- `python scripts/baixar_datasets.py --forcar` baixa tudo de novo se algum arquivo ficou corrompido.

## `Falha no download` do Kaggle (`--kaggle`)

- Instalou o cliente com `pip install kaggle`?
- O token está em `~/.kaggle/kaggle.json` (no Windows, `C:\Users\SEU_USUARIO\.kaggle\kaggle.json`)?
  Veja [03](03-baixar-datasets.md).
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

Abra manualmente <http://localhost:8501>. Se a porta estiver ocupada, passe outra porta ao script
de abrir (Mac/Ubuntu: `./scripts/abrir_interface.sh --server.port 8502`; Windows:
`scripts\abrir_interface.bat --server.port 8502`).

## Está lento

- Reduza "Quanto histórico usar" e o horizonte.
- Feche outros programas pesados.
- Na primeira previsão o modelo é carregado, o que leva mais tempo. As seguintes são mais rápidas.

## Nada resolveu

Envie ao mantenedor: o comando que você rodou, a **mensagem de erro inteira** e a saída de
`python scripts/verificar_ambiente.py`.
