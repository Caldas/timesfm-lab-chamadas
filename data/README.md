# Dados

Todos os datasets viram o mesmo formato simples, que a interface e os notebooks leem:

| Coluna | Significado |
|---|---|
| `timestamp` | Início do intervalo (ex.: `1999-03-01 09:30:00`) |
| `calls_offered` | Chamadas recebidas (oferecidas) no intervalo; **zero** quando a central está fechada |

Os datasets com dados de atendimento (`technion-bank` e `synthetic-service`) trazem também colunas de
atendidas, abandonos, TMA, espera e nível de serviço: veja o
[dicionário de dados](../docs/09-dicionario-de-dados.md).

| Pasta | Conteúdo | Versionado? |
|---|---|---|
| `samples/` | `chamadas_sinteticas.csv`, gerado por `scripts/gerar_amostra.py` | Sim |
| `raw/<dataset>/` | Datasets públicos baixados por `scripts/baixar_datasets.py` | **Não** (está no `.gitignore`) |

A interface lista automaticamente todos os `.csv` dessas duas pastas.

## Baixar os datasets

```bash
python scripts/baixar_datasets.py                          # baixa TODOS
python scripts/baixar_datasets.py technion-bank nyc-311    # só os escolhidos
python scripts/baixar_datasets.py --lista                  # fontes e licenças no terminal
python scripts/baixar_datasets.py nyc-311 --nyc-ano-inicio 2018 --nyc-ano-fim 2019
python scripts/baixar_datasets.py --forcar                 # baixa de novo, ignorando o cache
python scripts/baixar_datasets.py --kaggle dono/dataset    # qualquer dataset do Kaggle (precisa de token)
```

No Windows, use `.\.venv\Scripts\python.exe scripts\baixar_datasets.py ...`.

Cada dataset vira `data/raw/<id>/<id>.csv` e uma nota `SOURCE.md` com a atribuição. Os arquivos
originais ficam em `data/raw/<id>/_raw/` (cache): rodar de novo não baixa nada outra vez.

Nenhum desses datasets é copiado para este repositório: eles são baixados sob demanda das fontes
originais, que têm condições de uso diferentes (abaixo).

## Datasets disponíveis

| Id | Chamadas de... | Granularidade | Período | Tamanho |
|---|---|---|---|---|
| `synthetic` | central fictícia (gerado), já incluído | 30 min | 12 semanas | ~80 KB |
| `synthetic-service` | a mesma central, com dados de atendimento (gerado pelo simulador), já incluído | 30 min | 12 semanas | ~350 KB |
| `technion-bank` | banco de Israel | 30 min (agregado de chamadas individuais) | 1999 (12 meses) | ~12 MB baixados |
| `hyndman-bank` | banco norte-americano | 5 min, dias úteis 7h–21h | mar–out/2003 | ~110 KB baixados |
| `nyc-311` | linha 311 de Nova York | 1 hora (agregado no servidor) | 2016–2019 (padrão) | ~1 MB de CSV |

### `synthetic`: chamadas sintéticas

- Gerado por este projeto (`callcenter_lab.synthetic.make_synthetic_calls`).
- Central aberta seg–sex 8h–20h e sáb 8h–14h, fechada aos domingos; pico no fim da manhã, pico menor
  à tarde, segundas mais cheias e sextas mais calmas.
- Licença: MIT, como o resto do projeto (https://github.com/Caldas/timesfm-lab-chamadas). Serve para testar sem internet.

### `synthetic-service`: atendimento sintético

- Gerado por `scripts/gerar_amostra.py` com o simulador (`callcenter_lab.wfm`): as mesmas 12 semanas do
  `synthetic`, com uma equipe dimensionada para a meta padrão (80% em 20 s) e clientes que desistem após
  ~2 minutos em média.
- Colunas: chamadas, atendidas, abandonos, TMA, espera média, nível de serviço, agentes e ocupação por
  intervalo (veja o [dicionário de dados](../docs/09-dicionario-de-dados.md)).
- Licença: MIT. Serve para estudar o dimensionamento sem internet e para validar as contas.

### `technion-bank`: banco anônimo de Israel

- **Fonte:** https://www.math-stat.unibe.ch/studium/skripten_und_lehrmaterial/datensaetze_imsv/callcenter/index_ger.html
  (espelho da Universidade de Berna dos dados do Technion SEE Center).
- **O que é:** uma linha por chamada (hora de entrada, fila, atendimento, agente), 12 meses de 1999,
  cerca de 444 mil chamadas. O script agrega por 30 minutos pela hora de entrada: chamadas, atendidas
  (`outcome` AGENT), abandonos (`outcome` HANG), outras (PHANTOM, classe que o próprio dataset separa),
  TMA (tempo com o agente), espera na fila e nível de serviço (atendidas em até 20 s / oferecidas).
- **Cuidado:** os abandonos incluem quem desligou ainda na URA, antes de chegar à fila, então a taxa de
  abandono do conjunto (cerca de 20%) mistura os dois casos. O TMA aqui é só o tempo com o agente.
- **Contexto:** central aberta dom–qui das 7h à meia-noite; sexta fecha às 14h e reabre no sábado à
  noite. É o dataset mais usado em pesquisa de call center.
- **Condições de uso:** não há licença formal. A página pede **citar a fonte** em qualquer publicação e
  **avisar o Prof. Avi Mandelbaum** (avim@ie.technion.ac.il). Por isso **não** é copiado para o repositório.
- **Atribuição:** dados da central telefônica do "Anonymous Bank" (Israel), fornecidos por Ilan Guedj e
  Avi Mandelbaum (Technion SEE Center).

### `hyndman-bank`: banco norte-americano

- **Fonte:** https://robjhyndman.com/data/callcenter.txt
- **O que é:** chegadas de chamadas a cada 5 minutos, de segunda a sexta das 7h às 21h, de um grande
  banco comercial, de 3/mar/2003 a 24/out/2003 (164 dias úteis). Fora do horário (noites, fins de
  semana), o script preenche zero.
- **Condições de uso:** o arquivo não traz licença. O pacote R `stR`, que o inclui, é GPL-3. Por isso
  **não** é copiado para o repositório.
- **Citação:** De Livera, Hyndman & Snyder (2011), *Forecasting time series with complex seasonal
  patterns using exponential smoothing*, Journal of the American Statistical Association 106(496),
  1513–1527.

### `nyc-311`: linha 311 de Nova York

- **Fonte:** https://data.cityofnewyork.us/City-Government/311-Call-Center-Inquiry/wewp-mm3p
- **O que é:** todas as chamadas atendidas por agente na linha 311 (data, hora, tema). O original tem
  cerca de 105 milhões de linhas; o script pede ao servidor a **contagem por hora** de 2016 a 2019 (padrão),
  que é rápido e pequeno.
- **Cuidado:** depois de março de 2020 o dado **não representa todas as chamadas atendidas**
  (mudanças de atendimento na pandemia). Por isso o período padrão termina em 2019.
- **Condições de uso:** a página do dataset não informa licença; são dados abertos da cidade de Nova
  York (veja os termos do NYC Open Data). Não é copiado para o repositório.
- **Atribuição:** NYC 311 Call Center Inquiry, NYC Open Data (id `wewp-mm3p`).

## Outros datasets de chamadas (não incluídos no script)

Opções públicas encontradas, com granularidade mensal ou de um mês só, menos adequadas para previsão
por intervalo. Confira a licença na página antes de usar:

- ServiceOntario, volumes mensais de chamadas (jan/2016–dez/2022), Open Government Licence – Ontario:
  https://data.ontario.ca/dataset/serviceontario-wait-times-and-call-volumes-contact-centres
- Local Pension Service (Reino Unido), chamadas mensais, Open Government Licence:
  https://ckan.publishing.service.gov.uk/dataset/lps-call-handling-stats/resource/26c71137-ae04-4010-b55f-8956859f4b9b
- Queensland / Sul da Austrália, contagem diária de chamadas, CC BY 3.0 AU:
  https://researchdata.edu.au/daily-registration-calls-ssq-month/658699

## Usando seus próprios dados

Qualquer CSV serve, desde que tenha uma coluna de **data/hora** e uma coluna **numérica** com o número
de chamadas. A interface adivinha as colunas e deixa você corrigir. Registros no mesmo horário são
tirados pela média; intervalos sem registro podem ser preenchidos com zero (central fechada) ou
interpolados.
