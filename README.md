# TimesFM Lab — Tráfego

Laboratório em português para **estudar e testar o [TimesFM 3.0](https://github.com/google-research/timesfm)**
(modelo de fundação do Google Research para previsão de séries temporais) usando dados de tráfego.

Foi pensado para quem **conhece muito de planejamento de tráfego e está começando em TI**: tudo é
explicado passo a passo, e há uma interface web para mexer nos dados sem escrever código.

> Este projeto é de estudo. Não é um produto do Google nem uma ferramenta para decisões de engenharia.

## O que você vai conseguir fazer

1. Instalar tudo no Mac (Apple silicon) seguindo um guia.
2. Abrir uma interface no navegador, carregar um CSV de contagem de tráfego e ver a previsão.
3. Fazer um **teste de realidade**: esconder o final da série, prever e comparar com o que de fato aconteceu.
4. Abrir notebooks que explicam, em pequenos passos, o que o código faz.

## Comece aqui

| Passo | Guia |
|---|---|
| Entender os conceitos | [docs/00-conceitos.md](docs/00-conceitos.md) |
| Instalar no Mac | [docs/01-instalar-mac.md](docs/01-instalar-mac.md) |
| Baixar dados do Kaggle | [docs/03-baixar-dados-kaggle.md](docs/03-baixar-dados-kaggle.md) |
| Usar a interface | [docs/04-usando-a-interface.md](docs/04-usando-a-interface.md) |
| Dúvidas de TI | [docs/05-glossario-ti.md](docs/05-glossario-ti.md) e [docs/06-problemas-comuns.md](docs/06-problemas-comuns.md) |

Resumo rápido (depois de ler o guia de instalação):

```bash
./scripts/setup_mac.sh          # instala tudo
source .venv/bin/activate
python scripts/verificar_ambiente.py
streamlit run app/app.py        # abre a interface
```

> **Plataformas:** esta primeira fase cobre o **Mac** (Apple silicon com MLX; Intel com PyTorch em CPU).
> O suporte ao Jetson Orin Nano fica para uma fase futura, depois de testado no aparelho.

## Estrutura

```
app/          interface Streamlit
src/trafego_lab/   código (dados, métricas, modelo, backtest)
notebooks/    notebooks didáticos
data/samples/ dados de exemplo (sintéticos)
docs/         guias em português
scripts/      instalação, verificação e download do Kaggle
tests/        testes unitários básicos
```

## Licenças — leia

- O **código deste repositório** é MIT (veja [LICENSE](LICENSE)).
- O **TimesFM 3.0**: o código é Apache-2.0, mas os **pesos do modelo 3.0 têm licença não comercial**
  (uso comercial só por serviços autorizados do Google Cloud, como o BigQuery ML). Este laboratório é
  para estudo; não use os pesos 3.0 em produto ou trabalho remunerado.
- Cada dataset do Kaggle tem a sua própria licença: confira antes de reutilizar.

O código e os nomes técnicos estão em inglês; a documentação e a interface, em português.
