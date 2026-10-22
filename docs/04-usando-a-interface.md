# 04 — Usando a interface

Abra a interface (veja [01-instalar.md](01-instalar.md) se ainda não instalou):

- **Mac e Ubuntu:** `./scripts/abrir_interface.sh`
- **Windows:** dois cliques em `scripts\abrir_interface.bat`

O navegador abre em `http://localhost:8501`.

## Barra lateral (esquerda)

### 1. Dados

- **Enviar um CSV**: arraste um arquivo seu. Se não enviar nada, você escolhe um arquivo da lista
  (`data/samples` e `data/raw`). O primeiro é sintético, para testar; os datasets públicos aparecem
  depois de rodar `scripts/baixar_datasets.py` ([03](03-baixar-datasets.md)).
- **Coluna de data/hora** e **Coluna de chamadas**: a interface tenta adivinhar. Corrija se errar.
- **Filtrar por (opcional)**: se o arquivo mistura várias filas, equipes ou unidades, escolha uma.

### 2. Parâmetros

| Controle | Para que serve |
|---|---|
| **Intervalo** | Tamanho do intervalo da série: 5, 15 ou 30 minutos, hora ou dia. Os dados são agrupados nele. Use um intervalo igual ou maior que o do arquivo. |
| **Como agrupar** | *Somar* para chamadas recebidas. *Média* para métricas como TMA. |
| **Intervalos sem registro** | *Preencher com zero* quando a central fecha (o normal para chamadas). *Interpolar* só para falhas de medição. |
| **Quantos intervalos prever** | O horizonte. Com 30 minutos, 48 = um dia; 336 = uma semana. |
| **Quanto histórico usar** | Quantos intervalos recentes o modelo enxerga. Com 30 minutos, 1344 = 4 semanas. |
| **Motor** | Deixe em `auto`: usa MLX no Mac Apple silicon e PyTorch nos demais (na GPU NVIDIA, se houver; senão na CPU). |

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

## Experimentos para fazer

1. Compare previsões de 48, 96 e 336 intervalos (30 minutos). O erro cresce com o horizonte?
2. Use poucos dias de histórico, depois semanas. Quanto o histórico ajuda?
3. No arquivo sintético o padrão é regular. Num dataset real (`technion-bank`), onde o modelo erra mais?
   Nos picos? Nas segundas? Em dias atípicos?
4. Troque "30 minutos" por "Hora" e veja o que muda no WAPE.
5. No `nyc-311`, que opera 24 horas, compare o erro de fins de semana com o de dias úteis.
6. No Dimensionamento, suba a meta de 80% para 95%: quantos agentes a mais por intervalo? E se o TMA subir 10%?
7. Ligue "Clientes desistem da fila" com paciência de 120 s: a equipe diminui? Confira no simulador.
