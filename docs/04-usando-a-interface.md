# 04 — Usando a interface

Abra a interface (veja [01-instalar.md](01-instalar.md) se ainda não instalou):

- **Mac e Ubuntu:** `./scripts/abrir_interface.sh`
- **Windows:** dois cliques em `scripts\abrir_interface.bat`

O navegador abre em `http://localhost:8501`.

## Barra lateral (esquerda)

### 1. Dados

- **Enviar um CSV**: arraste um arquivo seu. Se não enviar nada, você escolhe um arquivo da lista
  (`data/samples` e `data/raw`). Os de `data/samples` são sintéticos, para testar (volume, atendimento, eventos e
  filas); os datasets públicos aparecem depois de rodar `scripts/baixar_datasets.py` ([03](03-baixar-datasets.md)).
- **Coluna de data/hora** e **Coluna de chamadas**: a interface tenta adivinhar. Corrija se errar.
- **Filtrar por (opcional)**: se o arquivo mistura várias filas, equipes ou unidades, escolha uma.

### 2. Parâmetros

| Controle | Para que serve |
|---|---|
| **Intervalo** | Tamanho do intervalo da série: 5, 10, 15, 20 ou 30 minutos, hora ou dia (o padrão é **30 minutos**). Os dados são agrupados nele. Use um intervalo igual ou maior que o do arquivo. |
| **Como agrupar** | *Somar* para chamadas recebidas. *Média* para métricas como TMA. |
| **Intervalos sem registro** | *Preencher com zero* quando a central fecha (o normal para chamadas). *Interpolar* só para falhas de medição. |
| **Quantos intervalos prever** | O horizonte. Com 30 minutos, 48 = um dia; 336 = uma semana. |
| **Quanto histórico usar** | Quantos intervalos recentes o modelo enxerga. Com 30 minutos, 1344 = 4 semanas. |
| **Motor** | Deixe em `auto`: usa MLX no Mac Apple silicon e PyTorch nos demais (na GPU NVIDIA, se houver; senão na CPU). |

A interface tem sete abas: **Previsão**, **Teste de realidade**, **Dimensionamento**, **Escala**, **Cenários**,
**Acompanhamento do dia** e **Filas e habilidades**. As duas últimas são opcionais, e o calendário de eventos
(*4. Eventos*, na barra lateral) também.

## Área principal

Mostra a **série preparada** (número de intervalos, início, fim, total de chamadas e gráfico). Confira
se parece com o que você espera antes de prever: picos nos horários certos, zeros quando fechado.

### Aba "Previsão"

Clique em **Prever**. Na primeira vez o modelo é carregado (e baixado), o que demora. O gráfico mostra:

- linha azul: previsão mais provável;
- faixa azul clara: onde o volume deve ficar em ~80% dos casos.

Há um botão para baixar a previsão em CSV.

### Aba "Teste de realidade"

Clique em **Rodar teste de realidade**. O programa esconde os últimos intervalos (o tamanho é o
"Quantos intervalos prever"), prevê só com o que veio antes e compara com o real.

Como ler os números:

- **Erro médio (MAE)**: erro típico em chamadas por intervalo. Menor é melhor.
- **Erro % ponderado (WAPE)**: erro total dividido pelo total de chamadas. A medida principal.
- **Viés**: positivo = previu chamadas a mais (risco de sobra de agentes); negativo = a menos (risco de
  falta). O ideal é perto de zero.
- **Dentro da faixa 10–90%**: o ideal é perto de 80%.
- **WAPE de "mesma semana anterior"**: a referência simples (repetir a mesma hora da semana passada).
  A seta mostra se o TimesFM ficou melhor (verde, negativa) ou pior que ela.

Se o trecho escondido não tiver chamadas (por exemplo, só domingo, com a central fechada), os
percentuais aparecem como "n/d": escolha outro horizonte.

## Eventos (opcional)

Na barra lateral, **4. Eventos: feriados e campanhas** carrega um calendário de eventos (CSV). Com ele, a aba
Previsão pergunta **como usar os eventos** (ajuste pelo efeito informado, covariáveis do modelo ou não usar), e o
teste de realidade mostra **Com e sem eventos**. Veja o [guia de feriados e campanhas](10-feriados-e-campanhas.md).

## Aba "Dimensionamento"

Transforma o volume de chamadas em **quantos agentes cada intervalo precisa**. A explicação da conta está no
[guia de dimensionamento](07-guia-de-dimensionamento.md); aqui, o passo a passo da tela.

Na barra lateral, **3. Dimensionamento (configuração)** reúne os parâmetros:

| Parâmetro | Para que serve |
|---|---|
| Exemplo para começar | Preenche a meta com um exemplo (80% em 20 s ou 90% em 30 s). São exemplos editáveis |
| Meta de nível de serviço | X% das chamadas atendidas em até Y segundos |
| Ocupação máxima | Teto de ocupação dos agentes |
| Limitar a espera média (ASA) | Opcional |
| Clientes desistem da fila | Liga o Erlang A e pede a paciência média |
| TMA padrão | Tempo médio de atendimento usado quando não há outro |
| Shrinkage | Pausas, treinamento, absenteísmo, férias e outros (em %) |
| Calcular custo | Custo por hora de uma pessoa escalada (opcional) |
| Horas pagas por dia | Para converter horas em pessoas (FTE) |

A configuração pode ser salva em um arquivo JSON e carregada depois. O **intervalo** vem da escolha em
*2. Parâmetros* (de 5 a 60 minutos para dimensionar).

Na aba, escolha o **volume** (previsão do TimesFM ou últimos intervalos do histórico) e o **TMA** (constante,
exemplo sintético ou arquivo CSV) e clique em **Dimensionar**. Você vê:

- o pico de agentes e de pessoas escaladas, o nível de serviço esperado e o custo;
- o gráfico de agentes por intervalo, com a **faixa de volume** (cenários 10% e 90% da previsão);
- os gráficos de nível de serviço e de ocupação contra a meta e o teto;
- a tabela por intervalo e o resumo por dia (horas, FTE), com download em CSV;
- **Validar no simulador**: simula a central com essa equipe e mostra o nível de serviço de verdade, com margem
  de erro.

## Aba "Escala"

Transforma o dimensionamento em **turnos**: quantas pessoas em cada turno, em cada dia, ao menor custo. A conta
está no [guia de escala e cenários](08-guia-de-escala-e-cenarios.md). Faça antes o dimensionamento.

1. Edite a **tabela de turnos** (início, duração, dias, pausa de refeição, mínimo e máximo de pessoas, custo). Dá
   para acrescentar e apagar linhas. Os turnos que vêm preenchidos são só exemplos.
2. Defina o **máximo de dias por semana** de cada pessoa, o custo padrão por hora e, se quiser, o número de pessoas
   disponíveis. Clique em **Gerar escala**.
3. Veja as **pessoas necessárias** (headcount), o custo, os intervalos com **falta** e as horas de **sobra**, o
   gráfico de cobertura contra a necessidade, os turnos por dia, as pausas e a cobertura por intervalo, com download
   em CSV.
4. **Validar a escala no simulador** mostra o nível de serviço que ela realmente entrega.

Se o período do dimensionamento não tem necessidade de pessoas (por exemplo, só um domingo com a central fechada),
a aba explica e não gera escala.

## Aba "Cenários"

Responde a perguntas "e se...". Edite a tabela de cenários (volume baixo/esperado/alto, fator de volume, fator de
TMA, pontos de shrinkage, outra meta ou ocupação) e clique em **Comparar cenários**: a primeira linha é a
referência e as outras mostram a diferença. Se já existe uma escala, a tabela mostra também como ela cobriria cada
cenário. Em **Sensibilidade**, escolha um parâmetro e veja o efeito de variá-lo, um de cada vez.

## Aba "Acompanhamento do dia" (opcional)

Compara o **plano da manhã** com as chamadas que estão chegando, avisa quando o dia sai da faixa prevista (desvio
acumulado e intervalos seguidos fora da faixa) e **re-prevê o resto do dia**, projetando o total. Com um dia passado,
você escolhe o horário de corte e vê se re-prever teria ajudado. Veja o
[guia do acompanhamento do dia](11-acompanhamento-do-dia.md).

## Aba "Filas e habilidades" (opcional)

Desligada até você marcar **Ativar filas e habilidades**. Para arquivos com **várias filas** (uma coluna de fila):
dimensiona cada fila com a sua equipe e **compara** equipes separadas com uma equipe cruzada (os mesmos agentes
atendem todas as filas), medindo a diferença pelo simulador. Veja o [guia de filas e habilidades](12-filas-e-habilidades.md).

## Baixar os resultados

Cada tabela tem um botão de **CSV**. O botão **Baixar tudo em Excel (.xlsx)** (nas abas Dimensionamento, Escala e
Cenários) reúne em uma planilha tudo que foi calculado até ali.

## Experimentos para fazer

1. Compare previsões de 48, 96 e 336 intervalos (30 minutos). O erro cresce com o horizonte?
2. Use poucos dias de histórico, depois semanas. Quanto o histórico ajuda?
3. No arquivo sintético o padrão é regular. Num dataset real (`technion-bank`), onde o modelo erra mais?
   Nos picos? Nas segundas? Em dias atípicos?
4. Troque "30 minutos" por "Hora" e veja o que muda no WAPE.
5. No `nyc-311`, que opera 24 horas, compare o erro de fins de semana com o de dias úteis.
6. No Dimensionamento, suba a meta de 80% para 95%: quantos agentes a mais por intervalo? E se o TMA subir 10%?
7. Ligue "Clientes desistem da fila" com paciência de 120 s: a equipe diminui? Confira no simulador.
8. Na aba Escala, troque os turnos de 8 horas por turnos de 4 e 6 horas. A sobra diminui? E o custo?
9. Na aba Cenários, compare o volume alto com a escala que você gerou: quantas horas de falta aparecem?
