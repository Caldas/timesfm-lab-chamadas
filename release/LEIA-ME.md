# TimesFM Lab — Central de Chamadas

Este pacote traz **só o necessário para rodar** o laboratório de previsão de chamadas com o TimesFM 3.0.
(O código-fonte do projeto, os testes e a configuração de desenvolvimento ficam no repositório:
https://github.com/Caldas/timesfm-lab-chamadas. Aqui o código vem empacotado (wheel), na pasta `wheels/`.)

## Para começar (uma vez)

| Sistema | Instalar | Abrir a interface |
|---|---|---|
| Windows 10/11 | duplo clique em `scripts\instalar_windows.bat` | duplo clique em `scripts\abrir_interface.bat` |
| Mac (Apple silicon ou Intel) | duplo clique em `scripts/instalar_mac.command` | duplo clique em `scripts/abrir_interface.command` |
| Ubuntu 22.04+ | `./scripts/setup_linux.sh` (ou `--gpu` com placa NVIDIA) | `./scripts/abrir_interface.sh` |

O instalador confere o que você já tem (Python, ambiente, bibliotecas) e instala só o que falta. Se
faltar o Python, ele pergunta antes de instalar.

- **Windows:** se aparecer "O Windows protegeu o computador", clique em *Mais informações* e depois em
  *Executar assim mesmo*.
- **Mac:** na primeira vez, clique com o botão direito no arquivo, *Abrir*, e confirme em *Abrir*.

Depois de abrir a interface, escolha `chamadas_sinteticas.csv` na barra lateral e clique em **Prever**.
Para dimensionar a equipe, use a aba **Dimensionamento** (guia: `docs/07-guia-de-dimensionamento.md`); depois a
**Escala** de turnos e os **Cenários** "e se" (guia: `docs/08-guia-de-escala-e-cenarios.md`). São opcionais: o **calendário de eventos** 
(feriados e campanhas, `docs/10`), o **acompanhamento do dia** (`docs/11`) e as **filas e habilidades** (`docs/12`).

## O que tem aqui

```
scripts/        instaladores, atalhos de duplo clique, baixar datasets, verificar o ambiente
wheels/         o laboratório empacotado (instalado pelo script de instalação)
requirements/   bibliotecas de cada sistema (usadas pelo script de instalação)
docs/           guias em português (comece por docs/01-instalar.md e docs/00-conceitos.md)
notebooks/      notebooks didáticos (jupyter lab)
data/           quatro arquivos de exemplo (volume, atendimento, eventos e filas) e README com as fontes
                e licenças dos datasets públicos
```

## Datasets públicos de chamadas

```
python scripts/baixar_datasets.py                          # todos
python scripts/baixar_datasets.py technion-bank nyc-311    # só os escolhidos
python scripts/baixar_datasets.py --lista                  # fontes e licenças
```

No Windows, use `.venv\Scripts\python.exe scripts\baixar_datasets.py`. Fontes, licenças e condições de
uso: `data/README.md`.

## Licenças

- O código do laboratório é MIT (`LICENSE`).
- Os **pesos do TimesFM 3.0 têm licença não comercial**: este laboratório é para estudo.
- Os datasets não vêm no pacote; cada um tem as suas condições de uso (`data/README.md`).

Algo deu errado? `docs/06-problemas-comuns.md`.
