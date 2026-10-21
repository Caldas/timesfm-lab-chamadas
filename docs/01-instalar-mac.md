# 01 — Instalar no Mac

> Usa Ubuntu ou Windows? Veja o [índice de instalação](01-instalar.md).

Tempo estimado: 15 a 30 minutos (a maior parte é download).

## O que você precisa

- Um Mac. Os dois tipos funcionam:
  - **Apple silicon** (M1, M2, M3, M4): o TimesFM roda com o motor MLX, otimizado para esses chips.
  - **Intel**: roda com PyTorch na CPU, que é **bem mais lento** (veja a seção
    [Mac Intel](#mac-intel) abaixo).
- macOS 14 ou mais novo (recomendado para Apple silicon).
- 8 GB de memória ou mais.
- Uns 5 GB livres em disco.
- Internet (a primeira execução baixa o modelo).

Para saber qual chip você tem: menu  → **Sobre Este Mac**.

## Passo 1 — Abrir o Terminal

Aperte `Cmd + Espaço`, digite **Terminal** e Enter. É uma janela onde você digita comandos. Se algo
aqui parecer estranho, veja o [glossário](05-glossario-ti.md).

## Passo 2 — Instalar as ferramentas básicas

Você precisa de **Homebrew** (instalador de programas), **Git** (baixa o projeto) e **Python**.
O script de instalação (Passo 4) confere se o Python já existe e, se não existir e o Homebrew
estiver instalado, **oferece instalá-lo**. Então, se preferir, pode pular a instalação do Python
abaixo.

1. Instale o Homebrew seguindo as instruções de <https://brew.sh> (um comando para colar no Terminal).
2. Depois:

```bash
brew install git python@3.12
```

3. Confira:

```bash
python3 --version
git --version
```

O Python precisa ser 3.10 ou mais novo.

> Em Mac com Apple silicon, use o Python do Homebrew (que é nativo). Um Python antigo rodando em modo
> de compatibilidade (Rosetta) não consegue usar o MLX.

## Passo 3 — Baixar o projeto

```bash
cd ~/Documents
git clone https://github.com/Caldas/timesfm-lab-trafego.git
cd timesfm-lab-trafego
```

Se o repositório estiver privado, peça ao dono para te convidar como colaboradora e entre na sua conta
do GitHub quando o Git pedir.

## Passo 4 — Instalar tudo

```bash
./scripts/setup_mac.sh
```

O script verifica o que já existe (Python, `.venv`, bibliotecas) e instala só o que falta, cria um
ambiente isolado (`.venv`) e confere se tudo está certo. Opções: `--yes` (responde "sim" às
perguntas) e `--reinstalar` (refaz tudo do zero).
Se aparecer "permission denied", rode `chmod +x scripts/setup_mac.sh` e tente de novo.

No final você deve ver `✅ Tudo certo.`

## Passo 5 — Testar o modelo (primeira vez)

```bash
source .venv/bin/activate
python scripts/verificar_ambiente.py --com-modelo
```

Na primeira vez ele **baixa o modelo** do Hugging Face (alguns minutos). Depois fica guardado no seu
Mac. Se aparecer `✅ Previsão de 24 passos gerada`, está tudo funcionando.

## Passo 6 — Abrir a interface

```bash
./scripts/abrir_interface.sh
```

O navegador abre sozinho em `http://localhost:8501`. Para fechar, volte ao Terminal e aperte
`Ctrl + C`. Veja como usar em [04-usando-a-interface.md](04-usando-a-interface.md).

## Nas próximas vezes

Um comando, dentro da pasta do projeto:

```bash
./scripts/abrir_interface.sh
```

## Atualizar o projeto

```bash
git pull
source .venv/bin/activate
python -m pip install -r requirements/mac.txt
```

## Mac Intel

O processo é o mesmo, com três diferenças:

1. **Python 3.10, 3.11 ou 3.12** (não use o 3.13 ou mais novo). O PyTorch parou de publicar versões
   para Mac Intel depois da 2.2.2, e essa versão não existe para Python mais novo. O `setup_mac.sh`
   procura o Python certo sozinho; se não achar, instale e rode de novo:

   ```bash
   brew install python@3.12
   PYTHON=python3.12 ./scripts/setup_mac.sh
   ```

2. **Mais lento.** O modelo roda na CPU. A primeira previsão leva mais tempo (carrega o modelo), e as seguintes
   levam de alguns segundos a poucos minutos, dependendo do seu Mac. Na interface, reduza "Quanto histórico usar"
   (por exemplo, 500) e "Quantos passos prever" para testar rápido.

3. **Atualização de projeto:** use `requirements/mac-intel.txt` em vez de `mac.txt`:

   ```bash
   python -m pip install -r requirements/mac-intel.txt
   ```

Para conferir: `python scripts/verificar_ambiente.py` deve mostrar `Motor escolhido: torch`.

## Notebooks (opcional)

```bash
source .venv/bin/activate
jupyter lab
```

Abra a pasta `notebooks/` e execute as células com `Shift + Enter`.

Algo deu errado? Veja [06-problemas-comuns.md](06-problemas-comuns.md).
