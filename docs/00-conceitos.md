# 00 — Conceitos

Você já conhece central de atendimento. Aqui traduzimos os termos de ciência de dados para o seu mundo.

## Série temporal

Uma sequência de medições em intervalos regulares. Exemplo: o número de chamadas que a central recebe
a cada 30 minutos. É exatamente o que o relatório de chamadas oferecidas por intervalo do seu sistema
produz.

Uma série de chamadas costuma ter:

- **Sazonalidade diária**: picos no fim da manhã e no meio da tarde, vale na hora do almoço.
- **Sazonalidade semanal**: segunda-feira cheia, sexta e fim de semana mais calmos.
- **Eventos**: feriados, campanhas, envio de boletos, falhas de serviço, dia seguinte a um feriado.
- **Ruído**: variação aleatória de um intervalo para o outro, mesmo num dia "normal".
- **Horário fechado**: intervalos com zero chamadas, porque a central não está aberta.

## Previsão (forecast)

Dado o histórico até agora, estimar o volume dos próximos intervalos. O **horizonte** é quantos
intervalos à frente você quer prever. Com intervalos de 30 minutos, horizonte 48 = o próximo dia;
336 = a próxima semana.

## Modelo de fundação

A maioria dos modelos de previsão é treinada com os dados de **uma** série (a sua fila) e só serve para
ela. O **TimesFM** é diferente: foi treinado antes, pelo Google, com uma enorme quantidade de séries de
vários assuntos. Por isso consegue prever uma série que **nunca viu**, sem treinar nada (*zero-shot*).
Você entrega o histórico e recebe a previsão.

É como um analista experiente que já viu milhares de gráficos de assuntos variados (visitas a sites, energia,
vendas...) e reconhece o padrão na sua série, sem conhecer a sua central. Para entender como ele aprendeu e como
funciona por dentro, sem jargão, veja o [guia 13](13-como-o-timesfm-funciona.md).

## Previsão pontual e quantis

O modelo devolve duas coisas:

- **Previsão pontual**: o valor mais provável em cada intervalo (a mediana).
- **Quantis**: uma faixa de incerteza. Aqui mostramos a faixa entre o quantil 10% e o 90%: o modelo
  espera que o volume real caia dentro dela em cerca de 80% das vezes.

Faixa estreita significa confiança; faixa larga, incerteza. Para o planejamento, a borda superior da
faixa é um cenário de pico a considerar.

## Como saber se a previsão é boa: o teste de realidade (backtest)

Prever o futuro não dá para conferir na hora. Então fazemos assim: **escondemos o final do histórico**,
prevemos usando só o que sobrou e comparamos com o que realmente aconteceu.

Métricas usadas:

| Métrica | O que significa |
|---|---|
| **WAPE** | Erro total dividido pelo total de chamadas, em %. É a medida de acerto mais usada em call center: não se distorce com horários calmos ou fechados. "Errei 12% do volume." |
| **Viés** | Se a previsão, no total, pediu **mais** chamadas do que chegaram (positivo: risco de sobra de agentes) ou **menos** (negativo: risco de falta). Perto de zero é o ideal. |
| **MAE** | Erro médio absoluto, em chamadas por intervalo. "Em média, erramos 6 chamadas por intervalo." |
| **Cobertura 10–90%** | Quanto do real ficou dentro da faixa. O ideal é perto de 80%. Muito menos: o modelo está otimista demais. |
| **Mesma semana anterior** | Uma referência simples: repetir o que aconteceu na mesma hora da semana passada. Se o TimesFM não ganha dessa regra simples, ele não está ajudando naquele caso. |

## Onde isso entra no seu trabalho

A previsão de volume é o primeiro passo do dimensionamento: com o volume previsto por intervalo, o
tempo médio de atendimento (TMA) e o nível de serviço alvo, calcula-se quantos agentes são
necessários (tipicamente com a fórmula de Erlang C). **Este laboratório só cobre a previsão de
volume**; ele não calcula escalas nem agentes.

## Limites importantes

- O modelo **não sabe** de eventos que não estão nos dados (campanha, falha, feriado local). Nesta
  versão ele usa só o histórico da própria série.
- Quanto mais regular o padrão, melhor a previsão. Dias atípicos continuam difíceis.
- Aqui só prevemos **chamadas recebidas**; abandono, TMA e nível de serviço ficam fora.
- É um laboratório de estudo, não uma ferramenta de decisão. Valide antes de usar na operação.
- Os pesos do TimesFM 3.0 têm licença **não comercial**.
