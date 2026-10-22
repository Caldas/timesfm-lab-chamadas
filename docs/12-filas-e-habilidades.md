# 12 — Várias filas e habilidades (opcional)

Até aqui o laboratório trata a central como **uma fila só**, atendida por agentes que respondem a tudo. Muitas
centrais têm **várias filas** (vendas, suporte, cobrança) e agentes que atendem só algumas delas. Este módulo é
**opcional**: fica desligado até você ativá-lo na aba **🧩 Filas e habilidades**.

## Dois jeitos de organizar a equipe

- **Equipes separadas:** cada fila tem os seus agentes, que só atendem aquela fila. É como dimensionar cada fila
  como se fosse uma central independente, e somar.
- **Equipe cruzada (habilidades cruzadas):** os mesmos agentes atendem **todas** as filas. Quando uma fila está
  calma, os agentes ajudam as outras.

Equipes cruzadas precisam de **menos agentes para a mesma meta**, porque as pausas e os picos de uma fila se
compensam com os das outras (o efeito de *pooling*, ou de "pôr as filas no mesmo balde"). O preço é treinar os agentes
em várias filas.

## Quando o Erlang C não serve

O Erlang C ([guia de dimensionamento](07-guia-de-dimensionamento.md)) responde bem a **uma pergunta**: quantos agentes
iguais uma fila precisa. Ele **não** responde a estas:

| Situação | Por que o Erlang C erra |
|---|---|
| Várias filas com agentes que atendem só algumas | Não existe uma fórmula só: depende de quem atende o quê |
| Equipes cruzadas | Dimensionar cada fila separadamente **superestima** a equipe |
| Prioridade entre filas | O Erlang C trata todas as chamadas como iguais |
| Agentes com habilidades diferentes | Os agentes não são "iguais" |

Nesses casos usamos o **simulador**, que reproduz a central chamada a chamada com as regras de atendimento.

### O tamanho do efeito de pooling

Quanto maior a carga, menos agentes por Erlang a fórmula pede (a "folga" proporcional diminui):

| Carga | Agentes (meta 80% em 20 s) | Agentes por Erlang |
|---|---|---|
| 4 Erlangs | 7 | 1,75 |
| 8 Erlangs | 12 | 1,50 |
| 16 Erlangs | 20 | 1,25 |
| 32 Erlangs | 38 | 1,19 |

Por isso uma fila grande é mais eficiente que duas pequenas. **Duas filas iguais de 8 Erlangs:** separadas, 12 + 12 =
**24 agentes**. Uma equipe cruzada que atende as duas (carga de 16) precisa de **20**, quatro a menos. Simulando:

| Equipe | Agentes | Nível de serviço simulado (20 s) |
|---|---|---|
| Separadas (12 + 12) | 24 | 89% em cada fila |
| Cruzada | 20 | 80,5% em cada fila |
| Cruzada, com os mesmos 24 agentes | 24 | 97,5% em cada fila |

Dimensionar cada fila separadamente **entrega um nível de serviço acima da meta** (89%), porque cada equipe é
arredondada para cima: sobra gente. A equipe cruzada cumpre a meta com 4 agentes a menos. Ou, com os mesmos 24,
atende 97,5%.

## Como a simulação decide quem atende quem

O simulador (`simulate_skills`) usa três ideias:

- **Grupos de agentes:** cada grupo diz **quais filas atende** e **quantos agentes tem em cada intervalo**. Um grupo
  de especialistas de vendas atende só `vendas`; um grupo "cruzado" atende todas.
- **Quando chega uma chamada** e há agentes livres que atendem aquela fila, escolhe-se um deles. Por padrão, o
  **especialista primeiro** (para manter os agentes cruzados livres para o que sobrar). Dá para escolher o cruzado
  primeiro.
- **Quando um agente fica livre**, ele pega uma chamada em espera entre as filas que sabe atender: por padrão, a que
  espera há **mais tempo**; ou, na regra de **prioridade**, a da fila mais importante primeiro.

Exemplo da prioridade, com duas filas de 4 Erlangs e só 8 agentes cruzados (sem folga nenhuma): sem prioridade, as
duas ficam em ~4% de nível de serviço. Com a fila A prioritária, a **A sobe para 26%** e a B fica em ~4%: a prioridade
não cria agentes, só decide quem espera.

## Na interface

1. Em *1. Dados*, escolha um arquivo com uma **coluna de fila** (texto com 2 a 20 valores diferentes), como
   `chamadas_sinteticas_filas.csv` (vendas, suporte e cobrança). Sem filtro, a interface avisa que os valores do mesmo
   horário seriam tirados pela média: use *Filtrar por* para ver uma fila, ou a aba de filas para todas.
2. Na aba **🧩 Filas e habilidades (opcional)**, marque **Ativar filas e habilidades**.
3. Confira a coluna da fila e ajuste o **TMA de cada fila** (as filas de exemplo têm TMA diferentes: vendas 240 s,
   suporte 420 s, cobrança 300 s).
4. Escolha o volume (últimos intervalos do histórico ou previsão do TimesFM para cada fila).
5. **Dimensionar cada fila:** tabela por fila (pico de agentes, horas de agente, pessoas escaladas) e gráfico de
   agentes empilhados por fila, com download em CSV.
6. **Comparar equipes separadas × cruzada:** dimensiona as duas equipes para a mesma meta, simula as duas várias vezes e
   mostra horas de agente, o nível de serviço de cada fila e a economia.

### O exemplo das três filas

Uma terça-feira inteira de `chamadas_sinteticas_filas.csv` (2.586 chamadas, meta 80% em 20 s, dos horários de
funcionamento 8h às 20h, 20 simulações):

| Equipe | Pico de agentes | Horas de agente | Pior nível de serviço (simulado) |
|---|---|---|---|
| Separadas (uma por fila) | 40 | 355,5 | 84% |
| Cruzada | 35 | 302 | 82% |

A equipe cruzada precisa de **15% menos horas de agente** (302 contra 355,5) e de **16% menos horas escaladas**
(407,5 contra 485,5), com nível de serviço parecido e acima da meta nas três filas.

## Para usar no código

```python
from callcenter_lab.wfm import (
    AgentGroup, QueueSpec, build_queue_plans, compare_pooling, simulate_skills_replications,
)

# cada fila sozinha, com o TMA de cada uma
plans = build_queue_plans(calls_by_queue, config, {"vendas": 240, "suporte": 420})

# equipes separadas × cruzada, simuladas
resultado = compare_pooling(calls_by_queue, config, {"vendas": 240, "suporte": 420}, n_replications=20)
resultado.summary

# uma equipe híbrida à sua maneira: especialistas e cruzados
grupos = [
    AgentGroup("especialistas de vendas", ("vendas",), 5),
    AgentGroup("cruzados", ("vendas", "suporte"), 8),
]
filas = [QueueSpec("vendas", aht_seconds=240), QueueSpec("suporte", aht_seconds=420, priority=1)]
simulate_skills_replications({"vendas": volume_vendas, "suporte": volume_suporte}, grupos, filas, 30, routing="priority")
```

O notebook e a interface cobrem as duas equipes padrão; o código acima serve para desenhar equipes híbridas.

## Limites

- A equipe cruzada é dimensionada somando as cargas das filas e usando o TMA médio ponderado (um Erlang sobre a
  carga total). É uma boa aproximação para o ponto de partida; **confira no simulador**, como a interface faz.
- Os agentes cruzados são tratados como **igualmente bons** em todas as filas: o TMA depende da fila, não do agente.
  Agentes menos experientes em uma fila (e mais lentos nela) não são modelados.
- A escala de turnos (aba Escala) trabalha com **um** requisito de pessoas por intervalo: use a soma das filas ou o
  total da equipe cruzada.
- Treinar agentes em várias filas **tem custo e tempo**, que o laboratório não calcula.
- É um laboratório de estudo: valide antes de usar na operação.
