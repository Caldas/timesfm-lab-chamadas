# TimesFM Lab — Central de Chamadas

Laboratório em português para **estudar e testar o [TimesFM 3.0](https://github.com/google-research/timesfm)**
(modelo de fundação do Google Research para previsão de séries temporais) na **previsão do volume de
chamadas de uma central de atendimento telefônico** e no **dimensionamento da equipe** (quantos agentes
por intervalo, com Erlang C/A, shrinkage e simulação), na **escala de turnos**, em cenários "e se" e, se você quiser,
em **feriados e campanhas**, no **acompanhamento do dia** e em **várias filas com habilidades cruzadas**.

Foi pensado para quem **conhece muito de gestão de central telefônica e está começando em TI**: tudo é
explicado passo a passo, e há uma interface web para mexer nos dados sem escrever código.

> Este projeto é de estudo. Não é um produto do Google nem uma ferramenta para decidir o dimensionamento
> de equipes sem validação.

## O que você vai conseguir fazer

1. Instalar tudo no seu computador (Mac, Ubuntu ou Windows) seguindo um guia.
2. Baixar datasets públicos de chamadas com **um comando** (todos, ou só os que escolher).
3. Abrir uma interface no navegador, carregar o volume de chamadas por intervalo e ver a previsão.
4. Fazer um **teste de realidade**: esconder o final da série, prever e comparar com o que de fato
   aconteceu (WAPE, viés, cobertura), contra a regra simples "mesma semana anterior".
5. **Dimensionar a equipe**: do volume previsto, do TMA e da meta de nível de serviço (configuráveis)
   aos agentes por intervalo e às pessoas escaladas, conferindo o resultado em um **simulador** de central.
   Depois, gerar a **escala de turnos** ao menor custo, comparar **cenários "e se"** e baixar tudo em **Excel**.
6. Opcionalmente: informar **feriados e campanhas** num calendário, **acompanhar o dia** (previsto x realizado, alertas
   e re-previsão) e dimensionar **várias filas**, comparando equipes separadas com uma equipe cruzada.
7. Abrir notebooks que explicam, em pequenos passos, o que o código faz.

## Comece aqui

| Passo | Guia |
|---|---|
| Entender os conceitos | [docs/00-conceitos.md](docs/00-conceitos.md) |
| Como o TimesFM funciona e foi treinado (sem jargão) | [docs/13-como-o-timesfm-funciona.md](docs/13-como-o-timesfm-funciona.md) |
| Instalar (escolha seu sistema) | [docs/01-instalar.md](docs/01-instalar.md): [Mac](docs/01-instalar-mac.md) · [Ubuntu](docs/01-instalar-ubuntu.md) · [Windows](docs/01-instalar-windows.md) |
| Baixar datasets de chamadas | [docs/03-baixar-datasets.md](docs/03-baixar-datasets.md) e [data/README.md](data/README.md) |
| Usar a interface | [docs/04-usando-a-interface.md](docs/04-usando-a-interface.md) |
| Dimensionar a equipe (Erlang, shrinkage, simulador) | [docs/07-guia-de-dimensionamento.md](docs/07-guia-de-dimensionamento.md) |
| Escala de turnos e cenários "e se" | [docs/08-guia-de-escala-e-cenarios.md](docs/08-guia-de-escala-e-cenarios.md) |
| Várias filas e habilidades (opcional) | [docs/12-filas-e-habilidades.md](docs/12-filas-e-habilidades.md) |
| Acompanhamento do dia (alertas e re-previsão) | [docs/11-acompanhamento-do-dia.md](docs/11-acompanhamento-do-dia.md) |
| Feriados e campanhas (calendário de eventos) | [docs/10-feriados-e-campanhas.md](docs/10-feriados-e-campanhas.md) |
| Colunas dos dados | [docs/09-dicionario-de-dados.md](docs/09-dicionario-de-dados.md) |
| Dúvidas de TI e de call center | [docs/05-glossario-ti.md](docs/05-glossario-ti.md) e [docs/06-problemas-comuns.md](docs/06-problemas-comuns.md) |

Resumo rápido (depois de ler o guia do seu sistema):

| Sistema | Instalar (uma vez) | Abrir a interface |
|---|---|---|
| Mac (Apple silicon ou Intel) | `./scripts/setup_mac.sh` | `./scripts/abrir_interface.sh` |
| Ubuntu | `./scripts/setup_linux.sh` (ou `--gpu` com placa NVIDIA) | `./scripts/abrir_interface.sh` |
| Windows | `powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1` | dois cliques em `scripts\abrir_interface.bat` |

Prefere não usar o terminal? Baixe o `.zip` na página de
[Releases](https://github.com/Caldas/timesfm-lab-chamadas/releases): é um pacote **enxuto, só com o que
se precisa para rodar** (sem a pasta de código-fonte: o laboratório vem empacotado em `wheels/`). Use os atalhos de duplo clique da pasta
`scripts` (`instalar_windows.bat`, `instalar_mac.command`): veja [docs/01-instalar.md](docs/01-instalar.md).

Datasets públicos de chamadas:

```bash
python scripts/baixar_datasets.py                          # baixa todos
python scripts/baixar_datasets.py technion-bank nyc-311    # só os escolhidos
python scripts/baixar_datasets.py --lista                  # fontes e licenças
```

| Dataset | O que é | Granularidade |
|---|---|---|
| `technion-bank` | Central de um banco de Israel, 1999 (444 mil chamadas) | 30 min |
| `hyndman-bank` | Central de um banco norte-americano, 2003 | 5 min |
| `nyc-311` | Linha 311 de Nova York, 2016–2019 | 1 hora |

O projeto também traz, **já prontos e sem precisar de internet**, quatro arquivos sintéticos em `data/samples/`:
`chamadas_sinteticas.csv` (volume), `chamadas_sinteticas_atendimento.csv` (com atendimento),
`chamadas_sinteticas_eventos.csv` com o calendário `eventos/eventos_exemplo.csv` (feriados e campanhas) e
`chamadas_sinteticas_filas.csv` (três filas). Fontes, licenças e condições de uso dos datasets públicos:
[data/README.md](data/README.md).

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

## O que é testado automaticamente

A cada alteração, o CI (GitHub Actions) roda os testes (Ubuntu, Windows e macOS), o **script de instalação real** e o
**pacote enxuto** do release (descompactado, instalado, aberto e usado para dimensionar, simular, gerar escala e Excel,
e para filas, eventos e acompanhamento do dia) em Ubuntu, Windows, Mac Apple silicon e Mac Intel. O job manual
"Real forecast" também baixa o modelo e gera uma previsão nos quatro sistemas. O que **não** é testado automaticamente: uso de GPU NVIDIA (`--gpu`),
Windows ARM64, Linux ARM e o download dos datasets a partir das fontes originais (os testes usam
respostas simuladas, para não depender de sites de terceiros).

## Estrutura

```
src/callcenter_lab/   código: interface (app.py e as abas *_ui.py), loading, metrics, model, backtest, datasets,
                      synthetic, events (feriados e campanhas) e intraday (acompanhamento do dia)
src/callcenter_lab/wfm/  dimensionamento: config, workload (TMA), erlang, shrinkage, simulator, plan,
                         scheduling (escala), scenarios (cenários), queues e skills (filas e habilidades),
                         tables e export (Excel)
notebooks/            notebooks didáticos (previsão, avaliação, Erlang, simulação e escala)
data/samples/         dados de exemplo (sintéticos): volume, atendimento, eventos e filas
data/README.md        datasets públicos: fontes, licenças e condições de uso
docs/                 guias em português
scripts/              instalação por sistema (setup_mac.sh, setup_linux.sh, setup_windows.ps1),
                      abrir a interface, verificar o ambiente e baixar datasets
tests/                testes automatizados (unidade e interface)
release/              texto do LEIA-ME do pacote; scripts/montar_release.py monta o release
```

## Licenças — leia

- O **código deste repositório** é MIT (veja [LICENSE](LICENSE)).
- O **TimesFM 3.0**: o código é Apache-2.0, mas os **pesos do modelo 3.0 têm licença não comercial**
  (uso comercial só por serviços autorizados do Google Cloud, como o BigQuery ML). Este laboratório é
  para estudo; não use os pesos 3.0 em produto ou trabalho remunerado.
- **Os datasets não fazem parte deste repositório**: são baixados das fontes originais, cada um com a sua
  licença ou condição de uso (alguns pedem citar a fonte; um pede avisar o autor). Veja
  [data/README.md](data/README.md).
- Ao usar dados da sua própria central, use apenas dados **agregados** (contagem por intervalo), sem
  telefones nem dados de clientes.

O código e os nomes técnicos estão em inglês; a documentação e a interface, em português.
