# 04 — Usando a interface

Abra a interface (veja [01-instalar.md](01-instalar.md) se ainda não instalou):

- **Mac e Ubuntu:** `./scripts/abrir_interface.sh`
- **Windows:** dois cliques em `scripts\abrir_interface.bat`

O navegador abre em `http://localhost:8501`.

## Barra lateral (esquerda)

### 1. Dados

- **Enviar um CSV**: arraste um arquivo seu. Se não enviar nada, você escolhe um arquivo da lista
  (`data/samples` e `data/raw`). O primeiro é sintético, para testar.
- **Coluna de data/hora** e **Coluna de volume**: a interface tenta adivinhar. Corrija se errar.
- **Filtrar por (opcional)**: se o arquivo mistura vários cruzamentos, escolha um.

### 2. Parâmetros

| Controle | Para que serve |
|---|---|
| **Agrupar por** | Intervalo da série: 15 minutos, hora ou dia. Os dados são agrupados nesse intervalo. |
| **Como agrupar** | *Somar* para contagens de veículos. *Média* para velocidade ou taxas. |
| **Quantos passos prever** | O horizonte. Com "Hora", 48 = próximas 48 horas. |
| **Quanto histórico usar** | Quantos passos recentes o modelo enxerga. |
| **Motor** | Deixe em `auto`: usa MLX no Mac Apple silicon e PyTorch nos demais (na GPU NVIDIA, se houver; senão na CPU). |

## Área principal

Mostra a **série preparada** (quantidade de pontos, início, fim e gráfico). Confira se parece com o
que você espera antes de prever.

### Aba "Previsão"

Clique em **Prever**. Na primeira vez o modelo é carregado (e baixado), o que demora. O gráfico mostra:

- linha azul: previsão mais provável;
- faixa azul clara: onde o valor deve ficar em ~80% dos casos.

Há um botão para baixar a previsão em CSV.

### Aba "Teste de realidade"

Clique em **Rodar teste de realidade**. O programa esconde os últimos passos (o tamanho é o
"Quantos passos prever"), prevê só com o que veio antes e compara com o real.

Como ler os números:

- **Erro médio (MAE)**: erro típico na unidade dos dados. Menor é melhor.
- **Erro percentual (MAPE)**: o mesmo, em %.
- **Dentro da faixa 10–90%**: o ideal é perto de 80%.
- **MAE de "repetir ciclo"**: a referência simples. A seta mostra se o TimesFM ficou melhor (verde,
  negativa) ou pior que ela.

## Experimentos para fazer

1. Compare previsões de 24, 72 e 168 horas. O erro cresce com o horizonte?
2. Use poucos dias de histórico, depois semanas. Quanto o histórico ajuda?
3. No arquivo sintético, o padrão é regular. Num dataset real, onde o modelo erra mais? Em feriados?
4. Troque "Hora" por "Dia" e veja o que muda.
