# 07 — Guia de dimensionamento

A previsão diz **quantas chamadas** vão chegar. O dimensionamento diz **quantas pessoas** você precisa para
atendê-las com a qualidade que você quer. Este guia explica a conta, passo a passo, e como fazê-la na aba
**Dimensionamento** da interface.

## A cadeia completa

```
chamadas previstas → TMA → carga (Erlangs) → agentes por intervalo → pessoas escaladas (shrinkage)
```

## Passo 1 — Carga de trabalho (Erlangs)

A **carga** mede quanto trabalho chega por intervalo, em "agentes ocupados o tempo todo":

> carga (Erlangs) = chamadas × TMA ÷ duração do intervalo

Exemplo: 60 chamadas em 30 minutos, com TMA de 300 segundos (5 minutos):
60 × 300 s ÷ 1.800 s = **10 Erlangs**. Ou seja, se as chamadas chegassem perfeitamente espaçadas, 10 agentes
estariam sempre ocupados. Na prática elas chegam ao acaso, então 10 agentes não bastam.

## Passo 2 — Agentes necessários (Erlang C)

Como as chamadas chegam em rajadas, **precisa de folga** acima da carga para que a fila não cresça. O Erlang C
calcula, para uma carga e um número de agentes, a probabilidade de a chamada esperar, a espera média (ASA) e o
**nível de serviço** (chamadas atendidas em até Y segundos).

Com a carga de 10 Erlangs e TMA de 300 s (meta: 80% em 20 segundos):

| Agentes | Chamadas que esperam | Nível de serviço (20 s) | Espera média (ASA) | Ocupação |
|---|---|---|---|---|
| 10 | 100% | 0% | infinita | 100% |
| 11 | 68% | 36% | 205 s | 91% |
| 12 | 45% | 61% | 67 s | 83% |
| 13 | 29% | 77% | 29 s | 77% |
| **14** | 17% | **87%** | 13 s | 71% |
| 15 | 10% | 93% | 6 s | 67% |

O dimensionamento escolhe **o menor número de agentes que cumpre a meta**: aqui, 14. Repare que a meta de 80%
exige 14 agentes para uma carga de 10: o ganho de cada agente adicional vai diminuindo.

### Ocupação máxima

Equipes no limite cansam e erram. O parâmetro **ocupação máxima** (exemplo: 85%) impõe um teto: o cálculo nunca
devolve uma equipe que passe dele, mesmo que a meta de nível de serviço já tenha sido atingida. Vale também a
**espera média máxima (ASA)**, opcional.

### Sensibilidade à meta e ao TMA

Com o mesmo volume (60 chamadas em 30 min):

| Mudança | Agentes |
|---|---|
| Meta 80% em 20 s, TMA 300 s (base) | 14 |
| Meta 90% em 30 s | 15 |
| Meta 95% em 20 s | 16 |
| TMA 270 s (−10%) | 13 |
| TMA 330 s (+10%) | 15 |

Um TMA 10% maior custa **um agente a mais** nesse intervalo. Por isso importa informar o TMA certo por horário.

## Passo 3 — Quando os clientes desistem (Erlang A)

O Erlang C supõe que **ninguém desliga**. Se os clientes desistem depois de algum tempo, o Erlang C **superestima**
a equipe necessária. Marque **"Clientes desistem da fila"** e informe a paciência média: o cálculo passa a usar o
**Erlang A**, que também estima a taxa de abandono.

Exemplo (mesma carga, paciência média de 120 s): a meta de 80% em 20 s pede **12 agentes** (não 14), com cerca de
82% de nível de serviço e 7% de abandono esperado. Menos agentes porque a fila encurta sozinha quando as pessoas
desligam, mas ao custo de perder esses clientes.

## Passo 4 — Shrinkage e pessoas escaladas

Os agentes calculados são os que precisam estar **atendendo**. Mas as pessoas também fazem pausas, treinamentos,
faltam e saem de férias. O **shrinkage** é a parte do tempo pago em que o agente **não** está disponível:

> pessoas escaladas = agentes ÷ (1 − shrinkage)

Com 14 agentes e 25% de shrinkage: 14 ÷ 0,75 = 18,7, que arredonda para **19 pessoas escaladas**.

Os componentes são configuráveis (pausas, treinamento, absenteísmo, férias, outros). Os valores iniciais da
interface (25% no total) são **apenas um exemplo**; use os da sua operação.

A interface também mostra o resumo **por dia**: horas de agente, horas escaladas, pico de pessoas e **FTE**
(pessoas equivalentes de tempo integral = horas escaladas ÷ horas pagas por dia).

## Como fazer na interface

1. Carregue os dados e prepare a série (intervalo de **5 a 60 minutos**; o dimensionamento usa o mesmo intervalo).
2. Na barra lateral, abra **3. Dimensionamento (configuração)**: meta de nível de serviço, ocupação máxima,
   paciência (se quiser Erlang A), TMA padrão, shrinkage e custo. Dá para começar por um exemplo e
   **salvar/carregar a configuração** em um arquivo JSON.
3. Na aba **👥 Dimensionamento**, escolha o **volume** (previsão do TimesFM ou os últimos intervalos do histórico)
   e o **TMA** (constante, exemplo sintético ou arquivo CSV) e clique em **Dimensionar**.
4. Veja os agentes e pessoas escaladas por intervalo, os gráficos contra a meta e a **faixa de volume**:
   quantos agentes o cenário baixo (10%) e o alto (90%) da previsão pedem.
5. Clique em **Validar no simulador** para conferir o nível de serviço de verdade (veja abaixo).
6. Baixe o resultado em CSV.

### Arquivo de TMA

Dois formatos de CSV:

- por intervalo: colunas `timestamp,aht_seconds`;
- perfil semanal: colunas `weekday,hour,aht_seconds` (`weekday` 0 = segunda-feira, 6 = domingo).

Intervalos sem TMA no arquivo usam o TMA padrão.

## Validar no simulador

As fórmulas de Erlang são aproximações com hipóteses. O **simulador** reproduz uma central de verdade, chamada a
chamada: chegadas ao acaso, tempos de atendimento variáveis, clientes que desistem, a equipe de cada intervalo. Ele
roda várias vezes e mostra a **média e a margem de erro (95%)** do nível de serviço, do abandono, da espera e da
ocupação. Se o simulador ficar bem abaixo da meta, o cálculo está otimista para o seu caso.

Nos testes do projeto, o simulador confirma as fórmulas: numa central com carga 10, 12 agentes e TMA de 300 s, o
Erlang C prevê 60,7% de nível de serviço e a simulação (20 execuções) deu 61,8% ± 2,7. Com abandono (Erlang A,
9 agentes, paciência de 60 s), 63,6% previsto contra 63,9% ± 1,0 simulado, e 22,7% de abandono previsto contra
22,5% ± 0,6.

## Limites

- **Uma fila só**, com agentes iguais. Várias filas e habilidades ficam para uma versão futura (opcional).
- O Erlang supõe chegadas ao acaso (Poisson) e atendimento sem pressa. Dias com picos muito bruscos ou
  campanhas podem fugir disso: confira no simulador.
- Os valores de exemplo (meta, ocupação, shrinkage, TMA) **não são referência** de nenhuma operação.
- O dimensionamento só vale tanto quanto a previsão de volume: veja o **teste de realidade** (WAPE e viés).
- Este laboratório é para estudo. Valide antes de usar para escalar equipes de verdade.
