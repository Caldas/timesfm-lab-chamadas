# 01 — Instalar no Mac

Tempo estimado: 15 a 30 minutos (a maior parte é download).

## O que você precisa

- Um Mac. O ideal é **Apple silicon** (M1, M2, M3, M4): o TimesFM roda com o motor MLX, que é
  otimizado para esses chips. Mac com processador Intel também funciona, só que mais lento.
- macOS 14 ou mais novo (recomendado).
- 8 GB de memória ou mais.
- Uns 5 GB livres em disco.
- Internet (a primeira execução baixa o modelo).

Para saber qual chip você tem: menu  → **Sobre Este Mac**.

## Passo 1 — Abrir o Terminal

Aperte `Cmd + Espaço`, digite **Terminal** e Enter. É uma janela onde você digita comandos. Se algo
aqui parecer estranho, veja o [glossário](05-glossario-ti.md).

## Passo 2 — Instalar as ferramentas básicas

Você precisa de **Homebrew** (instalador de programas), **Git** (baixa o projeto) e **Python**.

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

O script cria um ambiente isolado (`.venv`), instala as bibliotecas e confere se tudo está certo.
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
source .venv/bin/activate
streamlit run app/app.py
```

O navegador abre sozinho em `http://localhost:8501`. Para fechar, volte ao Terminal e aperte
`Ctrl + C`. Veja como usar em [04-usando-a-interface.md](04-usando-a-interface.md).

## Nas próximas vezes

Só dois comandos, dentro da pasta do projeto:

```bash
source .venv/bin/activate
streamlit run app/app.py
```

## Atualizar o projeto

```bash
git pull
source .venv/bin/activate
python -m pip install -r requirements/mac.txt
```

## Notebooks (opcional)

```bash
source .venv/bin/activate
jupyter lab
```

Abra a pasta `notebooks/` e execute as células com `Shift + Enter`.

Algo deu errado? Veja [06-problemas-comuns.md](06-problemas-comuns.md).
