# TimesFM Lab — Tráfego

Laboratório em português para **estudar e testar o [TimesFM 3.0](https://github.com/google-research/timesfm)**
(modelo de fundação do Google Research para previsão de séries temporais) usando dados de tráfego.

Foi pensado para quem **conhece muito de planejamento de tráfego e está começando em TI**: tudo é
explicado passo a passo, e há uma interface web para mexer nos dados sem escrever código.

> Este projeto é de estudo. Não é um produto do Google nem uma ferramenta para decisões de engenharia.

## O que você vai conseguir fazer

1. Instalar tudo no seu computador (Mac, Ubuntu ou Windows) seguindo um guia.
2. Abrir uma interface no navegador, carregar um CSV de contagem de tráfego e ver a previsão.
3. Fazer um **teste de realidade**: esconder o final da série, prever e comparar com o que de fato aconteceu.
4. Abrir notebooks que explicam, em pequenos passos, o que o código faz.

## Comece aqui

| Passo | Guia |
|---|---|
| Entender os conceitos | [docs/00-conceitos.md](docs/00-conceitos.md) |
| Instalar (escolha seu sistema) | [docs/01-instalar.md](docs/01-instalar.md): [Mac](docs/01-instalar-mac.md) · [Ubuntu](docs/01-instalar-ubuntu.md) · [Windows](docs/01-instalar-windows.md) |
| Baixar dados do Kaggle | [docs/03-baixar-dados-kaggle.md](docs/03-baixar-dados-kaggle.md) |
| Usar a interface | [docs/04-usando-a-interface.md](docs/04-usando-a-interface.md) |
| Dúvidas de TI | [docs/05-glossario-ti.md](docs/05-glossario-ti.md) e [docs/06-problemas-comuns.md](docs/06-problemas-comuns.md) |

Resumo rápido (depois de ler o guia do seu sistema):

| Sistema | Instalar (uma vez) | Abrir a interface |
|---|---|---|
| Mac (Apple silicon ou Intel) | `./scripts/setup_mac.sh` | `./scripts/abrir_interface.sh` |
| Ubuntu | `./scripts/setup_linux.sh` (ou `--gpu` com placa NVIDIA) | `./scripts/abrir_interface.sh` |
| Windows | `powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1` | dois cliques em `scripts\abrir_interface.bat` |

> **Plataformas suportadas:**
>
> | Sistema | Motor |
> |---|---|
> | Mac **Apple silicon** | MLX (rápido) |
> | Mac **Intel** | PyTorch em CPU (mais lento; exige Python 3.10–3.12) |
> | **Ubuntu** 22.04+ | PyTorch em CPU, ou em GPU NVIDIA (`--gpu`) |
> | **Windows** 10/11 | PyTorch em CPU |
>
> O suporte ao Jetson Orin Nano fica para uma fase futura.

## Estrutura

```
app/          interface Streamlit
src/trafego_lab/   código (dados, métricas, modelo, backtest)
notebooks/    notebooks didáticos
data/samples/ dados de exemplo (sintéticos)
docs/         guias em português
scripts/      instalação por sistema (setup_mac.sh, setup_linux.sh, setup_windows.ps1),
              abrir a interface, verificar o ambiente e baixar do Kaggle
tests/        testes unitários básicos
```

## Licenças — leia

- O **código deste repositório** é MIT (veja [LICENSE](LICENSE)).
- O **TimesFM 3.0**: o código é Apache-2.0, mas os **pesos do modelo 3.0 têm licença não comercial**
  (uso comercial só por serviços autorizados do Google Cloud, como o BigQuery ML). Este laboratório é
  para estudo; não use os pesos 3.0 em produto ou trabalho remunerado.
- Cada dataset do Kaggle tem a sua própria licença: confira antes de reutilizar.

O código e os nomes técnicos estão em inglês; a documentação e a interface, em português.
