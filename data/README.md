# Dados

| Pasta | Conteúdo | Versionado? |
|---|---|---|
| `samples/` | Dados sintéticos gerados por `scripts/gerar_amostra.py` (contagem horária de veículos, 8 semanas) | Sim |
| `raw/` | Datasets baixados do Kaggle por `scripts/baixar_kaggle.py` | **Não** (está no `.gitignore`) |

A interface lista automaticamente todos os `.csv` dessas duas pastas.

## Datasets sugeridos do Kaggle

Confira **licença, colunas e período na página de cada dataset** antes de usar: este repositório não
redistribui nenhum deles.

| Nome curto | Slug | Página | Observação |
|---|---|---|---|
| `metro-interstate` | `anshtanwar/metro-interstate-traffic-volume` | [link](https://www.kaggle.com/datasets/anshtanwar/metro-interstate-traffic-volume) | Volume de tráfego de uma rodovia interestadual dos EUA; costuma trazer clima e feriados (útil para estudar covariáveis no futuro). |
| `junctions` | `fedesoriano/traffic-prediction-dataset` | [link](https://www.kaggle.com/datasets/fedesoriano/traffic-prediction-dataset) | Contagem de veículos por cruzamento; use o filtro "Filtrar por" da interface para escolher um cruzamento. |

```bash
python scripts/baixar_kaggle.py --lista
python scripts/baixar_kaggle.py metro-interstate
```

Qualquer outro dataset serve, desde que tenha uma coluna de data/hora e uma de contagem:
`python scripts/baixar_kaggle.py dono/nome-do-dataset`.

> As colunas exatas desses datasets não foram conferidas na criação deste repositório. Se a interface
> escolher a coluna errada, corrija nos seletores da barra lateral.

## Formato esperado

Um CSV com pelo menos:

- uma coluna de **data/hora** (ex.: `2024-03-04 08:00:00`);
- uma coluna **numérica** com o volume.

A interface adivinha as colunas e deixa você corrigir. Dados com vários registros no mesmo horário
são tirados pela média; lacunas pequenas são preenchidas por interpolação.
