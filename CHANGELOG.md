# Changelog

## v2.0.0 — Dimensionamento por intervalo

Além de prever o volume de chamadas, o laboratório agora **dimensiona a equipe**: do volume previsto e
do TMA aos agentes e pessoas escaladas por intervalo, validado por um simulador de central.

### Novidades
- **Aba Dimensionamento** na interface: volume (previsão do TimesFM ou histórico) + TMA + meta de nível de
  serviço → agentes por intervalo, pessoas escaladas, custo, gráficos contra a meta e a ocupação máxima,
  faixa de volume (cenários 10% e 90%), resumo por dia (horas, FTE) e download em CSV.
- **Configuração do dimensionamento** (painel na barra lateral e `StaffingConfig`): intervalo (5 a 60 min),
  meta "X% em Y segundos", ocupação máxima, espera média máxima, paciência dos clientes, TMA, shrinkage e
  custo; exemplos editáveis; salvar e carregar em JSON. Os valores iniciais são exemplos, não referência.
- **Motor Erlang**: Erlang C (probabilidade de espera, ASA, nível de serviço, agentes para a meta com teto de
  ocupação) e Erlang A (com abandono), estáveis para cargas altas e vetorizados por intervalo.
- **TMA e carga de trabalho**: TMA constante, por dia/hora ou por arquivo, gerador de TMA de exemplo e carga
  em Erlangs; previsão de TMA com o TimesFM (opcional).
- **Shrinkage**: componentes configuráveis (pausas, treinamento, absenteísmo, férias, outros), pessoas
  escaladas e FTE por dia.
- **Simulador da central**: simulação por eventos (chegadas, atendimento, paciência, equipe por intervalo),
  métricas por intervalo, replicações com intervalo de confiança e gerador de dados sintéticos. Validado contra
  as fórmulas: Erlang C e Erlang A batem com a simulação dentro da margem de erro.
- **Dados com atendimento**: `technion-bank` agora traz atendidas, abandonos, TMA, espera e nível de serviço
  por intervalo; novo `synthetic-service` (gerado pelo simulador); dicionário de dados.
- **Documentação e notebooks**: guia de dimensionamento, glossário de call center, notebooks 03 (Erlang e
  dimensionamento) e 04 (simulação e validação).
- Intervalos de 10 e 20 minutos na interface.

### Limitações
- Uma fila só, agentes iguais: filas e habilidades ficam para a v2.2 (opcional).
- Ainda não há escala de turnos nem cenários "e se" (v2.1).
- O dimensionamento supõe chegadas ao acaso e atendimento sem pressa; confira no simulador.
- Os valores de exemplo (meta, shrinkage, TMA) não são de nenhuma operação real.


## v1.0.0 — 2026-10-21

Primeira versão estável.

### O que tem
- **Previsão de chamadas** com o TimesFM 3.0 (zero-shot): previsão pontual e faixa de incerteza de 10% a 90%.
- **Interface web** (Streamlit) em português: carrega um CSV, escolhe colunas e intervalo (5 min a dia),
  prevê, e faz o **teste de realidade** (WAPE, viés, MAE, cobertura) contra a "mesma semana anterior".
- **Quatro sistemas suportados:** Mac Apple silicon (MLX), Mac Intel (PyTorch CPU), Ubuntu (CPU ou GPU
  NVIDIA com `--gpu`) e Windows 10/11 (CPU).
- **Instalação por sistema**, idempotente: detecta Python, `.venv` e bibliotecas e instala só o que
  falta; oferece instalar o Python (Homebrew, apt, winget). Atalhos de duplo clique para Windows
  (`.bat`) e Mac (`.command`).
- **Datasets públicos de chamadas** com um único script (`scripts/baixar_datasets.py`, todos ou
  escolhidos): `technion-bank`, `hyndman-bank` e `nyc-311`, mais um exemplo sintético incluído.
  Fontes e licenças em `data/README.md`.
- **Documentação em português** (conceitos de previsão para call center, instalação por sistema,
  glossário, problemas comuns) e dois notebooks didáticos.
- **CI** em Ubuntu, Windows e macOS (Apple silicon e Intel): testes, instalação real de cada sistema,
  segunda execução idempotente, instalação a partir de um Ubuntu sem Python e, sob demanda, uma
  previsão real com o modelo.

### Pacote do release
- O `.zip`/`.tar.gz` do release é **enxuto**: só traz o necessário para rodar (instaladores, atalhos,
  requisitos, docs, notebooks, dado de exemplo e o laboratório empacotado em `wheels/`). Não inclui
  `src/`, `tests/` nem a configuração de desenvolvimento. É montado por `scripts/montar_release.py`.
- A interface abre com `python -m callcenter_lab` (ou pelos atalhos).

### Limitações conhecidas
- Uso de GPU NVIDIA (`--gpu`), Windows ARM64 e Linux ARM não foram testados.
- O download dos datasets depende de sites de terceiros; os testes automáticos usam respostas
  simuladas.
- Os pesos do TimesFM 3.0 têm licença **não comercial**. Os datasets não fazem parte do repositório e
  têm condições de uso próprias.
- Só prevê **volume de chamadas**; não calcula escalas nem número de agentes (Erlang).
- Não usa covariáveis (feriados, campanhas) nesta versão.
