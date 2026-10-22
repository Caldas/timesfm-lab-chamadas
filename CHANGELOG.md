# Changelog

## v2.2.0 — Opcionais: eventos, acompanhamento do dia e filas

Três recursos **opcionais** (nada muda para quem não os usa) e uma correção importante.

### Correção
- **O intervalo padrão da interface era 15 minutos** nas versões v2.0.0 e v2.1.0 (ao acrescentar as opções de 10 e 20
  minutos, a posição da opção de 30 minutos mudou e o padrão passou a ser a de 15). Com os dados de exemplo, de 30
  minutos, a série saía com zeros alternados e o dimensionamento ficava errado até o usuário trocar o intervalo. Agora o
  padrão é 30 minutos, escolhido pelo nome, e há um teste que garante isso.

### Novidades
- **Feriados e campanhas:** calendário de eventos em CSV (`data`, `fim`, `tipo`, `efeito`, `nome`), usado de duas
  maneiras: **ajuste pelo efeito informado** (limpa o histórico do efeito e o reaplica nos dias futuros; o padrão) e
  **covariáveis do TimesFM**. O teste de realidade compara a previsão sem eventos, com covariáveis e com ajuste. Nos
  dados de exemplo e com o TimesFM 3.0 de verdade, as covariáveis quase não mudaram a previsão, enquanto o ajuste
  derrubou o WAPE de 35% para 9% nos dias de campanha (com o efeito informado igual ao real).
- **Acompanhamento do dia:** compara o plano da manhã com o realizado, avisa quando o dia sai da faixa 10–90%
  (desvio acumulado e intervalos seguidos fora da faixa), re-prevê o resto do dia e projeta o total.
- **Várias filas e habilidades:** carregamento com coluna de fila, dimensionamento de cada fila, simulador com
  agentes de várias habilidades e roteamento (mais antiga na espera ou prioridade), e comparação de **equipes
  separadas × equipe cruzada**. No exemplo de três filas, a equipe cruzada precisou de 15% menos horas de agente.
- **Documentação:** guias `docs/10` (feriados e campanhas), `docs/11` (acompanhamento do dia) e `docs/12` (filas e
  habilidades), novos termos no glossário e novos dados de exemplo (`synthetic-events`, `synthetic-queues`).

### Limitações
- O calendário de eventos é por dia; o ajuste supõe um multiplicador igual ao longo do dia.
- A equipe cruzada trata os agentes como igualmente bons em todas as filas.
- O acompanhamento do dia não se conecta ao sistema da central: você carrega o arquivo com o que já aconteceu.

## v2.1.0 — Escala de turnos, cenários e Excel

Do dimensionamento à escala: o laboratório agora distribui as pessoas em turnos ao menor custo, compara
cenários "e se" e leva tudo para o Excel.

### Novidades
- **Aba Escala:** modelos de turno editáveis (início, duração, dias, pausa de refeição, mínimo e máximo de
  pessoas, custo), escala ótima por programação inteira (solver HiGHS do `scipy`) com pausas de refeição
  escalonadas, limite de dias por semana por pessoa, limite de pessoas disponíveis, cobertura contra necessidade
  (falta e sobra por intervalo), headcount, custo e **validação no simulador**.
- **Aba Cenários:** compara cenários lado a lado (volume baixo/esperado/alto, fatores de volume e de TMA,
  pontos de shrinkage, outra meta ou ocupação), com custo e a diferença para a referência; se há uma escala, mostra
  como ela cobriria cada cenário. **Sensibilidade** de um parâmetro de cada vez.
- **Exportação:** botões de CSV em cada tabela e **planilha Excel** única (resumo, configuração,
  dimensionamento por intervalo e por dia, faixa de volume, escala, cenários e sensibilidade).
- **Documentação e notebook:** guia de escala e cenários (`docs/08`), novos termos no glossário e o notebook 05
  (escala de turnos).
- Novas dependências: `scipy` (solver da escala) e `openpyxl` (Excel). O instalador cuida delas.

### Limitações
- A escala é por **quantidade de pessoas**, não por pessoa: não atribui nomes nem trata preferências, férias
  individuais, competências ou regras trabalhistas específicas.
- Uma fila só, com agentes iguais: filas e habilidades ficam para a v2.2 (opcional).
- Os turnos, o custo e o shrinkage de exemplo não são de nenhuma operação real.

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
