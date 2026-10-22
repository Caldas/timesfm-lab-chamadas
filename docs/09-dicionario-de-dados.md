# 09 — Dicionário de dados

Colunas dos arquivos que o laboratório lê e gera. Todos têm `timestamp` (início do intervalo) e
`calls_offered`; as demais aparecem nos datasets com dados de atendimento.

## Colunas

| Coluna | Unidade | Como é calculada |
|---|---|---|
| `timestamp` | data/hora | Início do intervalo (30 min no `technion-bank` e no `synthetic-service`) |
| `calls_offered` | chamadas | Chamadas que chegaram no intervalo, atendidas ou não. **Zero** quando a central está fechada |
| `calls_answered` | chamadas | Chamadas atendidas por um agente (no `technion-bank`, `outcome` = AGENT) |
| `calls_abandoned` | chamadas | Chamadas em que o cliente desligou antes de ser atendido (no `technion-bank`, `outcome` = HANG) |
| `calls_other` | chamadas | Só no `technion-bank`: o que não é atendida nem abandono (`outcome` = PHANTOM) |
| `aht_seconds` | segundos | TMA: média do tempo de conversa das chamadas **atendidas** que chegaram no intervalo. Vazio se nenhuma foi atendida |
| `avg_wait_seconds` | segundos | Espera média na fila das chamadas **atendidas** que chegaram no intervalo. Vazio se nenhuma foi atendida |
| `service_level_pct` | % | Chamadas atendidas em até 20 s ÷ chamadas oferecidas, x 100. Vazio se não houve chamadas |
| `agents` | agentes | Só no `synthetic-service`: agentes na equipe do intervalo |
| `occupancy_pct` | % | Só no `synthetic-service`: tempo de agente ocupado ÷ tempo de agente disponível, x 100 |

## Regras que valem para todas

- **Atribuição ao intervalo:** a chamada conta no intervalo em que **chegou**, mesmo que seja atendida
  depois.
- **Nível de serviço:** o denominador são todas as chamadas oferecidas, inclusive as abandonadas. É a
  mesma definição do dimensionamento (Erlang) e do simulador.
- **Campos vazios** (NaN) significam "não definido", não zero: um intervalo sem chamadas atendidas não
  tem TMA.
- **Limiar do nível de serviço:** 20 segundos nos arquivos gerados. No dimensionamento ele é
  configurável (`service_level_seconds`).

## Cuidados com os dados do `technion-bank`

- A coluna de espera é o tempo na **fila**; o tempo na URA (resposta automática) não entra.
- O TMA é o tempo com o agente; não inclui trabalho pós-chamada.
- Os abandonos incluem clientes que desligaram na URA antes de entrar na fila.
- É uma central de banco de Israel de 1999: serve para estudar, não representa a sua operação.
