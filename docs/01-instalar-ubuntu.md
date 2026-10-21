# 01 — Instalar no Ubuntu

Pensado para Ubuntu 22.04 e 24.04 (o teste automático do projeto roda no 24.04). Outros Linux
baseados em Debian devem servir.
Tempo estimado: 10 a 25 minutos.

## O que você precisa

- Ubuntu 22.04 ou mais novo (o Python do Ubuntu 20.04 é antigo demais).
- 8 GB de memória ou mais e uns 5 GB livres em disco.
- Internet.
- Opcional: placa de vídeo **NVIDIA** com driver instalado, para previsões mais rápidas.

## Passo 1 — Abrir o Terminal

Aperte `Ctrl + Alt + T`.

## Passo 2 — Instalar as ferramentas básicas

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip
```

O pacote `python3-venv` é importante: no Ubuntu ele vem separado do Python. Sem ele, a instalação
falha ao criar o ambiente. Confira a versão (precisa ser 3.10 ou mais nova):

```bash
python3 --version
```

## Passo 3 — Baixar o projeto

```bash
cd ~
git clone https://github.com/Caldas/timesfm-lab-trafego.git
cd timesfm-lab-trafego
```

## Passo 4 — Instalar tudo

Sem placa NVIDIA (ou se não tiver certeza), use o modo padrão. Ele instala o PyTorch só para CPU,
que é leve (cerca de 200 MB):

```bash
./scripts/setup_linux.sh
```

Se tiver placa **NVIDIA** com driver funcionando (`nvidia-smi` mostra a placa), use:

```bash
./scripts/setup_linux.sh --gpu
```

Esse modo baixa o PyTorch com CUDA, que é bem maior (cerca de 3 GB).

Se aparecer "permission denied": `chmod +x scripts/*.sh` e tente de novo.

No final você deve ver `✅ Tudo certo.`

## Passo 5 — Testar o modelo (primeira vez)

```bash
source .venv/bin/activate
python scripts/verificar_ambiente.py --com-modelo
```

Na primeira vez ele baixa o modelo do Hugging Face. Se aparecer `✅ Previsão de 24 passos gerada`,
está funcionando.

## Passo 6 — Abrir a interface

```bash
./scripts/abrir_interface.sh
```

O navegador abre em `http://localhost:8501`. Para fechar, volte ao Terminal e aperte `Ctrl + C`.
Se o navegador não abrir sozinho (por exemplo, acessando por SSH), abra o endereço manualmente.
Veja como usar em [04-usando-a-interface.md](04-usando-a-interface.md).

## GPU NVIDIA

- Com `--gpu`, o programa usa a GPU automaticamente (`verificar_ambiente.py` mostra o nome da placa).
- Para forçar a CPU mesmo com GPU: `TRAFEGO_DEVICE=cpu ./scripts/abrir_interface.sh`.
- O uso de GPU depende do driver NVIDIA instalado e compatível com o CUDA do PyTorch.
- Este modo ainda não foi testado numa placa real durante a criação do projeto; se der erro, volte
  ao modo CPU (rode `./scripts/setup_linux.sh` sem `--gpu` numa pasta nova ou apague `.venv` antes).

## Atualizar o projeto

```bash
git pull
./scripts/setup_linux.sh        # (ou com --gpu)
```

## Notebooks (opcional)

```bash
source .venv/bin/activate
jupyter lab
```

## Observações

- O Ubuntu 24.04 não deixa instalar pacotes Python "soltos" (erro `externally-managed-environment`).
  Aqui isso não é problema, porque tudo é instalado dentro do `.venv`.
- Em Linux ARM (por exemplo, Ubuntu num Raspberry Pi ou numa máquina Ampere), o script tenta usar o
  PyTorch CPU para ARM, mas isso não foi testado.

Algo deu errado? Veja [06-problemas-comuns.md](06-problemas-comuns.md).
