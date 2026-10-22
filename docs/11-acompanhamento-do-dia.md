# 11 — Acompanhamento do dia

O plano é feito de manhã, com o histórico que existe **antes** do dia. Durante o dia, as chamadas chegam, e às vezes
o dia foge do plano: uma campanha que ninguém avisou, uma falha que gera ligações. A aba **📈 Acompanhamento do dia**
compara o plano com o que está acontecendo, avisa quando o dia sai da faixa prevista e **re-prevê o resto do dia**.
Este recurso é **opcional**.

## O que a aba faz

Dado um dia e um **horário de corte** (o primeiro intervalo que ainda não é conhecido):

1. **Plano da manhã:** prevê o dia inteiro usando só o histórico anterior ao dia, com a faixa de 10% a 90%.
2. **Previsto × realizado:** para os intervalos antes do corte, compara o plano com o que chegou e diz se cada
   intervalo ficou **acima**, **abaixo** ou **dentro** da faixa.
3. **Alertas:** um intervalo fora da faixa é normal (acontece 20% das vezes por definição). O que importa é o desvio
   que **se sustenta**: por padrão, **3 intervalos seguidos** fora da faixa, do mesmo lado. Além disso, o **desvio
   acumulado** do dia vira um nível: **ok**, **atenção** (a partir de 10%) ou **crítico** (a partir de 20%). Os
   limites são configuráveis na tela.
4. **Re-previsão:** prevê os intervalos que faltam usando também o que já aconteceu hoje.
5. **Projeção do dia:** o realizado até agora mais a re-previsão do resto, comparado com o total planejado.

## Um exemplo real (com o TimesFM 3.0)

Nos dados de exemplo com campanhas (`chamadas_sinteticas_eventos.csv`), a sexta-feira 24/05 teve uma **campanha** que
o plano da manhã não conhecia. O plano previu **1.236** chamadas; no fim do dia foram **1.917**. Acompanhando o dia em
diferentes horários de corte:

| Corte | Desvio acumulado | Nível | Projeção do dia | WAPE do resto do dia: plano | WAPE: re-previsão |
|---|---|---|---|---|---|
| 10h | +43,0% | crítico | 1.565 | 36,7% | 22,5% |
| 11h | +39,8% | crítico | 1.664 | 38,5% | 18,6% |
| 13h | +47,4% | crítico | 1.788 | 39,2% | 14,2% |
| 15h | +49,5% | crítico | 1.862 | 40,6% | 10,7% |

A leitura:

- **O alerta aparece cedo.** Às 10h, com só duas horas de funcionamento, o desvio acumulado já era de +43% (crítico).
  No corte das 13h houve um **desvio sustentado**: 10 intervalos seguidos (de 08h00 a 12h30, cinco horas) **acima da
  faixa**, 47,7% acima do plano.
- **A projeção melhora com o dia.** Quanto mais do dia é conhecido, mais perto da realidade: 1.565 às 10h, 1.862 às
  15h, contra 1.917 de fato.
- **Re-prever ajuda muito num dia fora do padrão.** O WAPE do resto do dia caiu de 39% (plano da manhã) para 14%
  (re-previsão às 13h).
- **Num dia comum, o ganho é pequeno** e não há alerta: na sexta-feira 17/05, às 12h, o desvio foi de +0,8% (ok) e o
  WAPE do resto do dia foi 12,3% (plano) contra 11,1% (re-previsão).

Isso é uma central sintética e um dia de campanha construído para o teste; em dados reais os números serão outros, mas
o comportamento (avisar cedo, projetar melhor ao longo do dia) é o que a tela mostra para o seu caso.

## Na interface

1. Escolha o **dia a acompanhar**. Se os dados terminam no meio do dia, ele é tratado como **em andamento** e o corte é
   o fim dos dados. Se o dia já está completo, você escolhe o **horário de corte** e vê o que teria acontecido: como o
   resto do dia é conhecido, a tela compara o plano e a re-previsão com o real e diz se **re-prever ajudou**.
2. Ajuste, se quiser, os limites de **atenção** e **crítico** e quantos **intervalos seguidos** disparam o alerta.
3. Clique em **Acompanhar o dia**. Aparecem o aviso do dia, o desvio acumulado, a projeção, o gráfico (plano com a
   faixa, realizado, re-previsão) e a tabela dos **desvios que se sustentam**. Há download em CSV.

Se você carregou um calendário de eventos, o plano e a re-previsão usam o mesmo modo de eventos escolhido na aba
Previsão ([guia de feriados e campanhas](10-feriados-e-campanhas.md)).

## Como usar no dia a dia

O laboratório **não se conecta ao sistema da central**: você exporta as chamadas do dia até agora (a mesma planilha
de chamadas por intervalo), carrega o arquivo e acompanha. Para olhar de novo mais tarde, exporte de novo e recarregue.

## Limites

- A re-previsão só enxerga o que já aconteceu: ela **não sabia** da campanha de manhã, aprende com o desvio
  conforme ele aparece.
- Poucas horas de dados (corte muito cedo) significam pouca informação: o alerta é útil, mas a projeção ainda é
  incerta.
- Aqui só se acompanham **chamadas recebidas**; o nível de serviço real do dia, abandono e TMA não entram.
- O acompanhamento **não refaz o dimensionamento sozinho**. Use a projeção para decidir se vale redimensionar.
- É um laboratório de estudo: valide antes de usar na operação.
