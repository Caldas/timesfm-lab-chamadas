# 13 — Como o TimesFM funciona (sem jargão)

Este guia é para quem **não é da área de TI** e quer entender o que está acontecendo quando clica em **Prever**:
de onde vem o modelo, como ele aprendeu e o que ele faz com os dados da sua central. Não precisa de matemática.

> **Em uma frase:** o TimesFM é um modelo que **já estudou uma quantidade enorme de séries de números ao longo do
> tempo** e, olhando o histórico que você mostra, **continua o desenho da série** (com uma faixa de incerteza) usando
> os padrões que ele aprendeu a reconhecer.

## 1. Uma analogia: o planejador experiente

Imagine uma pessoa que passou a vida olhando gráficos de todo tipo: visitas a sites, consumo de energia, vendas,
tráfego de carros. Ela não conhece a **sua** central, mas reconhece padrões que se repetem em tudo: "de segunda a
sexta é parecido, o sábado é diferente", "tem um pico no fim da manhã", "depois do feriado volta ao normal".

Se você mostra a ela as últimas semanas da sua fila e pergunta "e amanhã?", ela não precisa de treino específico: ela
**reconhece o formato** e continua o desenho. O TimesFM faz isso, só que com muito mais gráficos na bagagem.

Por isso ele é chamado de **modelo de fundação**: um modelo geral, treinado antes por quem o criou (o Google
Research), que serve para muitas situações sem ser treinado de novo. Em previsão, isso se chama **zero-shot**
("zero exemplos seus"): você entrega a série e ele prevê, sem etapa de treinamento do seu lado.

## 2. De onde vêm os dados do treino

O TimesFM aprendeu com séries de **muitas áreas diferentes**, sem ser especialista em nenhuma. Segundo a ficha pública
do modelo 3.0, o treino usou:

| Fonte | O que é |
|---|---|
| **Wikipedia (visitas às páginas)** | Quantas pessoas abriram cada página, dia após dia (dados até novembro de 2023) |
| **Google Trends** | O interesse de busca por milhares de termos ao longo do tempo (dados até o fim de 2022) |
| **Conjuntos públicos de pesquisa** (GiftEval) | Séries de energia, clima, tráfego, vendas e outros usados por pesquisadores para comparar modelos |
| **Dados sintéticos** | Séries **inventadas** por computador, com tendências, ciclos diários e semanais e ruído, para ensinar padrões básicos |

Para ter uma ordem de grandeza: na primeira versão do TimesFM (2023), o Google Research informou cerca de **100
bilhões de pontos de dados** (cada "ponto" é uma medição, como "quantas visitas nesta hora"). A ficha do modelo 3.0
**não informa o total**, então não afirmamos um número para ela.

Dois pontos importantes para o seu uso:

- **Nenhuma central de atendimento foi usada de propósito** como fonte principal, até onde a documentação pública
  informa. O modelo conhece **ritmos** (diário, semanal, sazonal), não a **sua** operação.
- Os dados de treino são **públicos ou sintéticos**. Os dados que você carrega no laboratório **não são enviados ao
  Google nem usados para treinar nada**: o modelo roda no seu computador (veja a seção 7).

## 3. Como ele aprendeu

O treino é uma espécie de **jogo de esconder o final**, repetido bilhões de vezes:

1. Pega-se um pedaço de uma série (por exemplo, 3 semanas de visitas a uma página).
2. **Esconde-se o que veio depois** (os próximos dias), que o modelo não vê.
3. O modelo **chuta** o que veio depois.
4. Compara-se o chute com o que de fato aconteceu e **mede-se o erro**.
5. O modelo **ajusta** seus parâmetros internos para errar um pouco menos da próxima vez.

Depois de repetir isso com um número gigantesco de séries e de trechos, o modelo "internaliza" como as séries
costumam se comportar: ciclos que se repetem, picos que voltam, quedas em dias especiais.

É a mesma ideia dos assistentes de texto: aprendem a **prever a próxima palavra** lendo muito texto, e o TimesFM
aprende a **prever os próximos números** lendo muitas séries. Por isso a tecnologia por baixo é parecida.

**O teste de realidade** do laboratório faz exatamente esse jogo, mas com a **sua** série: esconde o final, pede a
previsão e compara com o real. Veja o [guia 04](04-usando-a-interface.md).

### O que são "parâmetros" e "pesos"

Os **parâmetros** (também chamados de **pesos**) são os milhões de números dentro do modelo que guardam o que ele
aprendeu. São como as "regulagens" que o treino foi ajustando. O TimesFM 3.0 tem cerca de **300 milhões** deles
(0,3 bilhão, segundo a ficha do modelo). O arquivo que o laboratório baixa na primeira execução **é esse conjunto de
regulagens**, já prontas. Ele **não aprende nada novo** enquanto você usa.

## 4. Por baixo dos panos, passo a passo

Quando você clica em **Prever**, acontece isto:

```
 histórico da sua fila                                   previsão + faixa
 (números por intervalo)                                 (próximos intervalos)
        │                                                        ▲
        ▼                                                        │
 1. Normalizar ──▶ 2. Cortar em blocos ──▶ 3. Transformar em ──▶ 4. Camadas de   ──▶ 5. Desfazer a
    (mesma escala)    ("patches" de 32)       "fichas"             atenção              normalização
                                                                   (reconhecer          e entregar os
                                                                    padrões)            números
```

**1. Normalizar.** Uma fila de 50 chamadas por intervalo e uma de 5.000 têm o mesmo "formato", só que em escalas
diferentes. O modelo primeiro coloca a série numa escala comum (para olhar o **formato**, não o tamanho) e, no final,
desfaz isso para devolver números na sua escala.

**2. Cortar em blocos.** A série é dividida em blocos de **32 pontos seguidos**, chamados *patches* ("remendos").
Com intervalos de 30 minutos, um bloco é **16 horas** de atendimento. É como ler um texto por frases em vez de letra
por letra: dá ao modelo uma visão mais completa e é bem mais rápido.

**3. Transformar em "fichas".** Cada bloco vira uma lista de números que o computador consegue comparar (o equivalente
a uma "palavra" no texto). O modelo também anota **a posição** de cada bloco: ele sabe o que veio antes e o que veio
depois.

**4. Camadas de atenção.** É o coração do modelo, uma rede do tipo *transformer* (a mesma família dos assistentes de
texto). Em cada camada, cada bloco **"olha" para os blocos anteriores e decide quais importam mais** para entender o
momento atual. Por exemplo: ao ver uma segunda-feira, dar mais peso às segundas anteriores do que à quarta-feira de
ontem. O TimesFM 3.0 tem **20 camadas** empilhadas, e cada uma refina o entendimento da anterior. Esse mecanismo de
"dar atenção ao que importa" é o que permite reconhecer padrões que se repetem de forma espaçada, como o ciclo semanal.

**5. Prever blocos à frente.** O modelo gera a previsão também **em blocos** (no 3.0, de **64 pontos**: com intervalos
de 30 minutos, mais de um dia inteiro de uma vez). Se você pede um horizonte maior, ele repete o processo: usa o que
acabou de prever como se fosse histórico e prevê o próximo bloco. Quanto mais blocos encadeados, maior a chance de o
erro acumular, e é por isso que **prever 1 dia é mais confiável que prever 4 semanas**.

### A faixa de incerteza

Em vez de um único número, o modelo devolve **9 estimativas** para cada intervalo, do cenário baixo ao alto
(10%, 20%, ... 90%). Isso é o que o laboratório mostra:

- a **linha** é a estimativa do meio (a mediana: metade dos cenários acima, metade abaixo);
- a **faixa clara** vai da estimativa de 10% à de 90%: o volume deve cair dentro dela em cerca de 80% dos casos.

A faixa é a parte mais útil para o planejamento: ela diz **quanta confiança** a previsão merece em cada horário.

### O que mudou na versão 3.0

As versões anteriores olhavam **uma série de cada vez**. A 3.0 foi feita também para **olhar várias séries juntas**
(por exemplo, vendas de vários produtos) e aceitar **informações extras conhecidas de antemão**, como um calendário de
feriados e campanhas. Esse recurso se chama **covariáveis** e é o que o laboratório usa no
[guia 10](10-feriados-e-campanhas.md). Segundo a ficha do modelo, a 3.0 combina camadas de atenção entre o tempo e
entre as séries e uma normalização reversível de cada série. Detalhes técnicos estão na ficha do modelo e no artigo
científico (veja as fontes ao final).

## 5. Quanta história ele enxerga

O modelo só vê a parte **mais recente** da série, até um limite. No TimesFM 3.0, o limite do código é de **15.360
pontos**. Com intervalos de 30 minutos, isso é cerca de **320 dias**. Se você carrega mais que isso, o excedente mais
antigo é descartado.

No laboratório, a opção **Quanto histórico usar** controla esse tamanho (o padrão, 1.344 intervalos de 30 minutos,
equivale a 4 semanas). Mais histórico ajuda a **ver sazonalidades longas** (como um pico todo fim de ano), mas
também deixa a previsão mais lenta e pode "diluir" mudanças recentes. Vale experimentar: é o experimento 2 do
[guia 04](04-usando-a-interface.md).

## 6. O que ele sabe e o que não sabe

**Sabe bem:**

- ciclos **diário** e **semanal** (pico no fim da manhã, sexta mais calma, domingo fechado);
- **tendência** (volume crescendo ou caindo aos poucos);
- **fechado = zero**: se a central fecha aos domingos, os zeros do histórico mostram isso;
- dar uma **faixa** de incerteza coerente com o ruído da série.

**Não sabe (e precisa da sua ajuda):**

| Situação | Por que é difícil | O que fazer no laboratório |
|---|---|---|
| **Feriados e campanhas** | O modelo não tem calendário; só vê números. Uma campanha nova parece um pico "sem motivo" | Informe o **calendário de eventos** ([guia 10](10-feriados-e-campanhas.md)) |
| **O que está acontecendo hoje** | A previsão da manhã não sabe de uma falha às 10h | Use o **acompanhamento do dia** ([guia 11](11-acompanhamento-do-dia.md)) |
| **Por que** o volume mudou | Ele prevê o formato, não explica as causas | Cruze com o que você sabe da operação |
| **Mudanças bruscas permanentes** (novo produto, troca de sistema) | O passado deixa de valer e o modelo continua o desenho antigo | Use menos histórico, só o período novo |
| **Pouco histórico** | Sem semanas suficientes, o ciclo semanal não aparece | Carregue pelo menos algumas semanas |

No teste do projeto, com os dados de exemplo e campanhas, o **ajuste pelo efeito informado** (o planejador diz "a
campanha aumenta 50%") derrubou o erro nos dias de campanha de **35% para 9%**, enquanto as covariáveis do modelo
quase não mudaram a previsão. Ou seja: **conhecimento do negócio ainda vale muito**, e o modelo é um assistente, não
um oráculo.

## 7. Onde ele roda e o que acontece com os seus dados

- **No seu computador.** A primeira execução baixa o conjunto de pesos (do site Hugging Face, uma vez). Depois, a
  previsão é calculada localmente.
- **Os seus dados ficam com você.** O laboratório não envia o seu CSV a nenhum serviço e o modelo não aprende com ele.
- Mesmo assim, use dados **agregados** (contagens por intervalo), sem telefones nem dados de clientes. Veja o
  [README](../README.md).
- **Licença:** os pesos do TimesFM 3.0 têm licença **não comercial**. Este laboratório é para estudo, não para
  produto ou trabalho remunerado.

## 8. Perguntas frequentes

**O TimesFM "pensa" ou "entende" a minha central?** Não. Ele reconhece **padrões estatísticos** parecidos com outros
que já viu. Pode acertar o formato sem saber o que é uma central de atendimento.

**Por que a previsão muda se eu mudar uma configuração?** Porque o modelo enxerga outra coisa: o histórico, o
horizonte, o intervalo e o motor (MLX ou PyTorch, que fazem as contas de formas ligeiramente diferentes) mudam o que
entra e como é calculado. Pequenas diferenças entre computadores e motores são normais.

**Por que não usar só "o mesmo dia da semana passada"?** É uma boa regra simples, e é justamente a **referência** do
teste de realidade. O modelo vale a pena quando **bate** essa regra na **sua** série; quando não bate, a regra simples
é melhor e mais barata.

**Ele é um ChatGPT?** É da mesma família de tecnologia (a rede *transformer*), mas faz outra coisa: não conversa nem
escreve texto. Recebe **números** e devolve **números**.

**Posso confiar cegamente na previsão?** Não. Use o **teste de realidade** para medir o erro (WAPE e viés) na sua
série, olhe a **faixa** e valide o dimensionamento no **simulador**. Este laboratório é de estudo.

## 9. Mini-glossário deste guia

| Termo | Significado simples |
|---|---|
| **Modelo de fundação** | Modelo geral, treinado antes em muitos dados, usado sem treinar de novo |
| **Zero-shot** | Prever sem nenhum treino com os dados do usuário |
| **Parâmetros / pesos** | Os números internos que guardam o que o modelo aprendeu |
| **Patch** | Bloco de pontos seguidos da série (32 no TimesFM 3.0), tratado como uma "palavra" |
| **Transformer / atenção** | Tipo de rede em que cada parte "olha" para as anteriores e escolhe o que importa |
| **Normalização** | Colocar séries de tamanhos diferentes na mesma escala para comparar o formato |
| **Quantil** | Um ponto da faixa de incerteza (o de 10% é o cenário baixo; o de 90%, o alto) |
| **Covariável** | Informação extra conhecida de antemão (feriado, campanha) que ajuda a explicar a série |
| **Horizonte** | Quantos intervalos à frente a previsão cobre |

## Fontes

- Das, Kong, Sen, Zhou. *A decoder-only foundation model for time-series forecasting*. ICML 2024
  (<https://arxiv.org/abs/2310.10688>): o artigo original do TimesFM.
- Blog do Google Research, *A decoder-only foundation model for time-series forecasting*
  (<https://research.google/blog/a-decoder-only-foundation-model-for-time-series-forecasting/>): explicação
  para o público geral (patches, dados de treino de cerca de 100 bilhões de pontos na versão 1.0).
- Ficha do modelo TimesFM 3.0 no Hugging Face (<https://huggingface.co/google/timesfm-3.0-pytorch>): camadas, patches,
  parâmetros, fontes de dados e licença.
- Repositório do TimesFM (<https://github.com/google-research/timesfm>): histórico das versões e limite de contexto.

> Os números deste guia (parâmetros, camadas, patches, contexto) são os publicados nessas fontes na data desta
> versão. Se o Google atualizar o modelo, confira as fontes.
