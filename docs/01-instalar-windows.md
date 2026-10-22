# 01 — Instalar no Windows

Windows 10 ou 11. Tempo estimado: 15 a 30 minutos.

## O que você precisa

- 8 GB de memória ou mais e uns 5 GB livres em disco.
- Internet.
- O modelo roda na **CPU** (o PyTorch para Windows é instalado em versão leve, sem GPU).

## Passo 1 — Instalar o Python e o Git

Você precisa do **Git** para baixar o projeto. O Python pode ser instalado agora ou depois: o script
do Passo 3 procura um Python 3.10+ e, se não achar, **oferece instalá-lo com o `winget`**.

Há duas formas de instalar agora. Escolha uma.

**Forma A — pelo terminal (mais rápida).** Abra o menu Iniciar, digite **PowerShell** e Enter:

```powershell
winget install Python.Python.3.12
winget install Git.Git
```

**Forma B — pelos instaladores.**

- Python: <https://www.python.org/downloads/windows/>. Na primeira tela do instalador, **marque**
  "Add python.exe to PATH" e deixe o "py launcher" marcado.
- Git: <https://git-scm.com/download/win> (pode aceitar as opções padrão).

**Feche e abra o PowerShell de novo** depois de instalar. Confira:

```powershell
py --version
git --version
```

> Se digitar `python` e abrir a Microsoft Store, é o atalho da loja, não o Python de verdade. Use
> `py`, como acima, ou instale o Python pelo passo anterior.

## Passo 2 — Baixar o projeto numa pasta curta

Use uma pasta com caminho **curto**, como `C:\timesfm-lab`. O Windows tem um limite de tamanho de
caminho que pode quebrar a instalação em pastas fundas (erro `WinError 206`).

```powershell
cd C:\
git clone https://github.com/Caldas/timesfm-lab-chamadas.git timesfm-lab
cd timesfm-lab
```

## Passo 3 — Instalar tudo

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
```

O `-ExecutionPolicy Bypass` vale só para esse comando e evita o bloqueio de scripts do Windows.
O script verifica o que já existe (Python, `.venv`, bibliotecas) e instala só o que falta; se o
Python não existir, ele pergunta antes de instalar (adicione `-Yes` ao final para responder "sim"
automaticamente, ou `-Reinstalar` para refazer tudo do zero). No final você deve ver `Tudo certo` e
`[OK] Pronto!`.

## Passo 4 — Testar o modelo (primeira vez)

```powershell
.\.venv\Scripts\python.exe scripts\verificar_ambiente.py --com-modelo
```

Na primeira vez baixa o modelo (alguns minutos). Se aparecer "Previsão de 24 passos gerada", está
funcionando.

## Passo 5 — Abrir a interface

**Dois cliques** em `scripts\abrir_interface.bat` (na pasta do projeto, no Explorador de Arquivos).
Ou pelo PowerShell:

```powershell
.\.venv\Scripts\python.exe -m callcenter_lab
```

O navegador abre em `http://localhost:8501`. Para fechar, feche a janela preta ou aperte `Ctrl + C`.

Na primeira vez, o **Firewall do Windows** pode perguntar sobre o Python. Pode clicar em
**Cancelar** ou permitir só em redes privadas: a interface funciona neste computador de qualquer jeito.

Veja como usar em [04-usando-a-interface.md](04-usando-a-interface.md).

## Ativar o ambiente (quando precisar)

Para rodar comandos como `jupyter lab` ou `python scripts\baixar_datasets.py`:

```powershell
.\.venv\Scripts\Activate.ps1
```

Se aparecer erro de "execução de scripts desabilitada", rode uma vez:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Ou, sem ativar, chame o Python do ambiente direto: `.\.venv\Scripts\python.exe scripts\...`.

## Atualizar o projeto

```powershell
git pull
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
```

## Notebooks (opcional)

```powershell
.\.venv\Scripts\Activate.ps1
jupyter lab
```

## Observações

- Windows em ARM64 (por exemplo, alguns notebooks Copilot+): o PyTorch pode não ter pacote para esse
  processador. Isso não foi testado.
- Em Windows 10/11, ative "caminhos longos" só se precisar mesmo de uma pasta funda (exige
  administrador): veja [06-problemas-comuns.md](06-problemas-comuns.md).

Algo deu errado? Veja [06-problemas-comuns.md](06-problemas-comuns.md).
