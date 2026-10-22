# 08 — Guia de escala e cenários

O [dimensionamento](07-guia-de-dimensionamento.md) diz **quantas pessoas** cada intervalo precisa. A **escala** diz
**quem trabalha em qual turno**, e os **cenários** respondem a perguntas "e se...". Este guia explica as duas coisas
e como usá-las nas abas **📅 Escala** e **🧮 Cenários**.

## A cadeia completa, agora até a escala

```
chamadas previstas → agentes por intervalo → pessoas escaladas → escala de turnos → custo e cobertura
```

## Escala de turnos

### O problema

Você tem a necessidade de pessoas escaladas por intervalo (a coluna *Pessoas escaladas* do dimensionamento, que já
inclui o shrinkage). Turnos têm hora de início e duração fixas, então não dá para cobrir cada intervalo na medida:
um turno de 8 horas cobre manhã, tarde e os picos juntos. A escala escolhe **quantas pessoas colocar em cada turno,
em cada dia**, para cobrir a necessidade **pelo menor custo**.

### Os turnos

Cada linha da tabela de turnos descreve um tipo de turno:

| Coluna | Para que serve |
|---|---|
| `nome`, `início`, `horas` | Identificação, hora de começo (`HH:MM`) e duração no local, pausa de refeição incluída |
| `dias` | Em quais dias da semana o turno existe: `seg-sex`, `sab`, `dom`, `seg, qua`... |
| `refeição_min` | Duração da pausa de refeição (0 = sem pausa) |
| `janela_início_h` e `janela_fim_h` | A pausa tem que **começar** entre essas horas depois do início do turno (ex.: de 3 a 5 horas) |
| `mín_pessoas` e `máx_pessoas` | Se o turno for usado num dia, no mínimo e no máximo essas pessoas |
| `máx_em_pausa_%` | No máximo essa parte do turno em pausa ao mesmo tempo (escalona os almoços) |
| `custo_hora` | Custo da hora desse turno (em branco = o custo padrão) |
| `refeição_paga` | Marque se a pausa de refeição é paga. Se não, só as horas trabalhadas contam no custo |

Os turnos de exemplo (manhã 08–16h, intermediário 10–18h, tarde 12–20h e sábado 08–14h) são **só exemplos**: troque
pelos da sua operação. Início, duração e pausa precisam ser **múltiplos do intervalo** do dimensionamento (30 minutos,
por exemplo). Turnos que atravessam a meia-noite funcionam.

### As regras

- **Dias de trabalho por semana:** cada pessoa trabalha no máximo N dias por semana (padrão: 5). A escala devolve
  quantas **pessoas** (headcount) a equipe precisa ter para respeitar isso. Exemplo: 2 pessoas por dia, 7 dias por
  semana, são 14 turnos; com 5 dias por pessoa, são 14 ÷ 5 = 2,8, ou seja, **3 pessoas**.
- **Pessoas disponíveis (opcional):** se você tem um limite de gente, a escala cobre o que for possível e **mostra a
  falta**. Ela nunca esconde que não deu para cobrir.
- **Pausas de refeição escalonadas:** a escala escolhe a hora da pausa de cada pessoa dentro da janela, de modo que a
  cobertura não despenque na hora do almoço.

### Como a cobertura é contada

> cobertura de um intervalo = pessoas no turno − pessoas na pausa de refeição

Ela é comparada com a necessidade (pessoas escaladas). **Cuidado para não contar duas vezes:** a pausa de refeição é
tirada da cobertura, então o shrinkage *Pausas* deve ter só as pausas curtas (cafezinho). Se o seu "Pausas" já inclui
o almoço, reduza-o ou use turnos sem pausa de refeição.

### Exemplo com os dados de exemplo

Uma sexta-feira da central de exemplo: 1.269 chamadas, pico de **20 agentes** atendendo e **27 pessoas escaladas**
(meta 80% em 20 s, shrinkage 25%). Com os turnos de exemplo e o custo de 20 por hora, a escala ótima é:

| Turno | Pessoas | Horas pagas | Custo |
|---|---|---|---|
| Manhã 08–16h | 19 | 133 | 2.660 |
| Intermediário 10–18h | 10 | 70 | 1.400 |
| Tarde 12–20h | 12 | 84 | 1.680 |
| **Total** | **41** | **287** | **5.740** |

As pausas de refeição ficam escalonadas (por exemplo, as 12 pessoas da tarde se dividem entre 15h00 e 16h30), e
nenhum intervalo fica descoberto. Sobram **87 horas** de pessoas acima da necessidade: turnos fixos de 8 horas não
acompanham os picos, e é por isso que a escala mostra a **sobra** ao lado da falta. Se a sobra incomoda, a saída é
oferecer turnos mais curtos ou mais variados. Acrescentando dois turnos de 4 horas nos horários de pico (09–13h e
14–18h), o custo do mesmo dia cai de 5.740 para 5.200 e a sobra de 87 para 60 horas (o notebook 05 mostra como).

Para uma **semana** inteira da mesma central (13 a 19 de maio), com no máximo 5 dias por pessoa, a escala pede
**56 pessoas** e custa 35.520. Simulando a central com os agentes que essa escala realmente entrega, o nível de
serviço fica em torno de **94% ± 1**, bem acima da meta de 80%, por causa da sobra.

### Validar a escala no simulador

O botão **Validar a escala no simulador** roda o simulador com os agentes que a escala entrega (cobertura menos
shrinkage). Ele responde: "com essa escala, a central cumpre a meta?". Se ficar abaixo, falta cobertura em algum
horário; se ficar muito acima, há sobra (custo desnecessário).

### O que o solver faz (e o que não faz)

- A escala é calculada de forma **exata** (programação inteira, solver HiGHS do `scipy`), não por palpite. Se o
  tempo máximo de cálculo acabar antes da prova de que é a melhor possível, a tela diz "melhor encontrada no limite de
  tempo".
- Ela cobre a **quantidade**, não **quem**: não atribui nomes a turnos nem trata preferências, férias individuais
  ou competências. O headcount é uma estimativa agregada do limite de dias por semana.
- Não trata regras trabalhistas específicas (intervalo mínimo entre turnos, folga aos domingos, banco de horas). Use
  `dias`, `máx_pessoas` e o limite de dias por semana para aproximar as suas regras.

## Cenários "e se"

### Cenários lado a lado

Cada cenário refaz o dimensionamento mudando o que você pedir. A **primeira linha é a referência**; as demais mostram
a diferença para ela. As colunas da tabela de cenários:

| Coluna | O que muda |
|---|---|
| `volume` | Qual previsão usar: `baixo` (10%), `esperado` ou `alto` (90%). Baixo e alto só existem com a previsão do TimesFM |
| `fator_volume` | Multiplica as chamadas (1,1 = 10% a mais) |
| `fator_TMA` | Multiplica o TMA (1,1 = 10% maior) |
| `shrinkage_pp` | Soma pontos percentuais ao shrinkage total (+5 = 5 pontos a mais), mantendo a proporção entre os componentes |
| `nível_serviço_%` e `segundos` | Outra meta (em branco = a da configuração) |
| `ocupação_máx_%` e `paciência_s` | Outro teto de ocupação ou outra paciência dos clientes |

Resultado do exemplo (a mesma sexta-feira, custo de 20 por hora):

| Cenário | Pico de agentes | Horas de agente | Horas escaladas | Custo | Variação de horas de agente |
|---|---|---|---|---|---|
| Base | 20 | 148 | 200 | 4.000 | 0% |
| Volume alto (90%) | 25 | 185 | 250 | 5.000 | +25% |
| Volume baixo (10%) | 16 | 123 | 168 | 3.360 | −17% |
| Volume +10% | 22 | 160 | 219 | 4.380 | +8% |
| TMA +10% | 22 | 160 | 219 | 4.380 | +8% |
| Absenteísmo +5 pontos | 20 | 148 | 217 | 4.330 | 0% |
| Meta 90% em 20 s | 21 | 162 | 221 | 4.410 | +9% |

Repare em duas coisas: **o volume alto pede 25% mais horas**, e o **absenteísmo não muda os agentes que precisam
atender**, só quantas pessoas é preciso escalar (e o custo).

Se já existe uma escala gerada, a tabela também mostra **como essa escala fixa cobriria cada cenário**: intervalos
com falta, horas de falta e horas de sobra. É a pergunta "e se o volume vier no cenário alto, a escala que montei
aguenta?". No exemplo, a escala da sexta-feira cobre o dia base sem falta, mas com 30% a mais de volume deixa 11
intervalos descobertos (18,5 horas de falta).

### Sensibilidade

Varia **um parâmetro de cada vez** em torno da configuração atual: shrinkage, TMA, volume, meta de nível de serviço
ou ocupação máxima. A tabela e o gráfico mostram o efeito em agentes, horas, FTE e custo. Serve para descobrir o que
mais pesa no seu dimensionamento. No exemplo, 10% a mais de TMA e 5 pontos a mais de shrinkage pesam parecido nas
horas escaladas (219 e 216,5 contra 200), mas só o TMA muda as horas de agente, porque o shrinkage só altera quantas
pessoas é preciso escalar.

## Exportar

Cada aba tem botões para baixar a tabela em **CSV**, e o botão **Baixar tudo em Excel (.xlsx)** reúne tudo o que foi
calculado até aquele momento em uma planilha: resumo, configuração, dimensionamento por intervalo e por dia, faixa
de volume, a escala (turnos, pausas e cobertura), os cenários e a sensibilidade. O resumo traz um aviso de que são
dados de um laboratório de estudo.

## Limites

- Uma fila só, com agentes iguais (filas e habilidades ficam para a v2.2, opcional).
- A escala é por **quantidade de pessoas**, não por pessoa.
- Os turnos, o custo e o shrinkage de exemplo **não são referência** de nenhuma operação.
- É um laboratório de estudo. Valide a escala antes de usá-la de verdade.
