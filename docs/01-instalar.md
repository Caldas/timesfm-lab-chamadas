# 01 — Instalar: escolha o seu sistema

O laboratório funciona em quatro tipos de computador. Cada um tem o seu guia e o seu script de
instalação, otimizado para ele.

| Seu computador | Guia | Script de instalação | Motor | Velocidade |
|---|---|---|---|---|
| Mac com **Apple silicon** (M1, M2, M3, M4) | [01-instalar-mac.md](01-instalar-mac.md) | `./scripts/setup_mac.sh` | MLX | rápida |
| Mac com processador **Intel** | [01-instalar-mac.md](01-instalar-mac.md#mac-intel) | `./scripts/setup_mac.sh` | PyTorch (CPU) | mais lenta |
| **Ubuntu** (22.04 ou mais novo) | [01-instalar-ubuntu.md](01-instalar-ubuntu.md) | `./scripts/setup_linux.sh` | PyTorch (CPU, ou GPU NVIDIA com `--gpu`) | média (rápida com GPU) |
| **Windows** 10 ou 11 | [01-instalar-windows.md](01-instalar-windows.md) | `scripts\setup_windows.ps1` | PyTorch (CPU) | média |

Para saber qual Mac você tem: menu  → **Sobre Este Mac**.

## Sem usar o terminal: atalhos de duplo clique

Se você baixou o pacote `.zip` do [release](https://github.com/Caldas/timesfm-lab-chamadas/releases),
descompacte e use os atalhos dentro da pasta `scripts`:

| Sistema | Instalar (uma vez) | Abrir a interface |
|---|---|---|
| Windows | `scripts\instalar_windows.bat` | `scripts\abrir_interface.bat` |
| Mac | `scripts/instalar_mac.command` | `scripts/abrir_interface.command` |
| Ubuntu | `./scripts/setup_linux.sh` (terminal) | `./scripts/abrir_interface.sh` (terminal) |

- **Windows:** se o Windows mostrar "O Windows protegeu o computador", clique em **Mais informações** e
  depois em **Executar assim mesmo**.
- **Mac:** na primeira vez, o macOS pode bloquear o arquivo (veio da internet). Clique com o botão
  direito, **Abrir**, e confirme em **Abrir**. Se aparecer "permissão negada", abra o Terminal na pasta
  do projeto e rode `chmod +x scripts/*.command scripts/*.sh`.

## O que os scripts fazem (todos)

Os scripts **primeiro verificam o que já existe** e só instalam o que falta. Podem ser rodados quantas
vezes quiser (por exemplo, depois de um `git pull`): numa segunda execução, com tudo já instalado,
terminam em segundos sem baixar nada.

1. **Python:** procuram um Python compatível. Se já existe, usam. Se não existe, **perguntam se podem
   instalá-lo** (Homebrew no Mac, `apt` no Ubuntu, `winget` no Windows). Se você responder não, mostram
   o comando para você instalar.
2. **Ambiente isolado (`.venv`):** se a pasta já existe e é compatível, reaproveitam; senão, criam.
   Não mexem no resto do computador.
3. **Bibliotecas:** conferem o que já está instalado e baixam só o que falta (no Ubuntu isso inclui o
   PyTorch, só-CPU ou com GPU).
4. **Verificação:** rodam `scripts/verificar_ambiente.py` para conferir se está tudo certo.

Opções dos scripts:

| Opção | Mac e Ubuntu | Windows | Para que serve |
|---|---|---|---|
| Responder "sim" às perguntas | `--yes` | `-Yes` | Instalar o Python sem perguntar (ou em modo automático) |
| Refazer tudo do zero | `--reinstalar` | `-Reinstalar` | Recriar o `.venv` e reinstalar tudo, se o ambiente estiver estragado |
| GPU NVIDIA | `--gpu` (só Ubuntu) | | PyTorch com CUDA |

Sem perguntas possíveis (por exemplo, rodando num servidor sem teclado) e sem `--yes`/`-Yes`, os
scripts não instalam nada do sistema: só mostram o que fazer.

Depois da instalação, o uso é igual nos quatro sistemas: **abrir a interface**, escolher um CSV e
prever. Veja [04-usando-a-interface.md](04-usando-a-interface.md).

## Comandos equivalentes por sistema

| Ação | Mac e Ubuntu (Terminal) | Windows (PowerShell) |
|---|---|---|
| Abrir a interface | `./scripts/abrir_interface.sh` | dois cliques em `scripts\abrir_interface.bat` |
| Ativar o ambiente | `source .venv/bin/activate` | `.\.venv\Scripts\Activate.ps1` |
| Rodar sem ativar | `.venv/bin/python scripts/...` | `.\.venv\Scripts\python.exe scripts\...` |
| Verificar o ambiente | `python scripts/verificar_ambiente.py` | `python scripts\verificar_ambiente.py` |
| Notebooks | `jupyter lab` | `jupyter lab` |
| Atualizar o projeto | `git pull` e o setup de novo | `git pull` e o setup de novo |

Dica: "ativar o ambiente" só é preciso para rodar comandos como `python scripts/...` ou
`jupyter lab`. Para abrir a interface, o script de abrir já cuida disso.

## Requisitos mínimos em todos os sistemas

- 8 GB de memória (recomendado) e uns 5 GB livres em disco.
- Internet na instalação e na primeira previsão (o modelo é baixado uma vez).
- Python 3.10 ou mais novo (no Mac Intel, entre 3.10 e 3.12).

Algo deu errado? Veja [06-problemas-comuns.md](06-problemas-comuns.md).
