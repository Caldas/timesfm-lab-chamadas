# 00 — Conceitos

Você já conhece tráfego. Aqui traduzimos os termos de ciência de dados para o seu mundo.

## Série temporal

Uma sequência de medições em intervalos regulares. Exemplo: o número de veículos que passam em um
cruzamento a cada hora. É exatamente o que um contador de tráfego produz.

Uma série de tráfego costuma ter:

- **Sazonalidade diária**: picos de manhã e no fim da tarde.
- **Sazonalidade semanal**: dias úteis diferentes de sábado e domingo.
- **Eventos**: feriados, obras, chuva, jogos de futebol.
- **Ruído**: variação aleatória de uma hora para outra.

## Previsão (forecast)

Dado o histórico até hoje, estimar os próximos valores. O **horizonte** é quantos passos à frente
você quer prever. Se os dados são horários e o horizonte é 48, o modelo prevê as próximas 48 horas.

## Modelo de fundação

A maioria dos modelos de previsão é treinada com os dados de **uma** série (o seu cruzamento) e só
serve para ela. O **TimesFM** é diferente: foi treinado antes, pelo Google, com uma enorme quantidade
de séries de vários assuntos. Por isso consegue prever uma série que **nunca viu**, sem treinar nada
(*zero-shot*). Você entrega o histórico e recebe a previsão.

É como um engenheiro experiente que já viu milhares de cruzamentos e reconhece o padrão no seu.

## Previsão pontual e quantis

O modelo devolve duas coisas:

- **Previsão pontual**: o valor mais provável em cada passo (a mediana).
- **Quantis**: uma faixa de incerteza. Aqui mostramos a faixa entre o quantil 10% e o 90%: o modelo
  espera que o valor real caia dentro dela em cerca de 80% das vezes.

Uma faixa estreita significa confiança; uma faixa larga, incerteza.

## Como saber se a previsão é boa: o teste de realidade (backtest)

Prever o futuro não dá para conferir na hora. Então fazemos assim: **escondemos o final do histórico**,
prevemos usando só o que sobrou e comparamos com o que realmente aconteceu.

Métricas usadas:

| Métrica | O que significa |
|---|---|
| **MAE** | Erro médio absoluto, na mesma unidade dos dados (veículos/hora). "Em média, erramos 120 veículos por hora." |
| **MAPE** | Erro médio em porcentagem. Ignora horas com contagem zero. |
| **Cobertura 10–90%** | Quanto do real ficou dentro da faixa. O ideal é perto de 80%. Muito menos: o modelo está otimista demais. |
| **Repetir ciclo anterior** | Uma referência simples: repetir as últimas 24 horas (ou 7 dias). Se o TimesFM não ganha dessa regra simples, ele não está ajudando naquele caso. |

## Limites importantes

- O modelo **não sabe** de eventos que não estão nos dados (acidente, obra, show). Nesta versão do
  laboratório ele usa só o histórico da própria série.
- Quanto mais regular o padrão, melhor a previsão.
- É um laboratório de estudo, não uma ferramenta de decisão de engenharia.
- Os pesos do TimesFM 3.0 têm licença **não comercial**.
