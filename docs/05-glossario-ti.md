# 05 — Glossário

Duas partes: termos de **TI** (para quem está começando) e termos de **central de atendimento** como
aparecem neste laboratório.

## Termos de TI

| Termo | Em português simples |
|---|---|
| **Terminal** | Janela onde você digita comandos em vez de clicar. No Mac: `Cmd + Espaço` → "Terminal". No Ubuntu: `Ctrl + Alt + T`. No Windows, o equivalente é o **PowerShell** (menu Iniciar → "PowerShell"). |
| **Comando** | Uma instrução digitada no Terminal, seguida de Enter. |
| **Pasta / diretório** | Igual a uma pasta do Finder. `cd nome` entra numa pasta; `cd ..` volta; `ls` lista o conteúdo. |
| **Python** | A linguagem de programação usada aqui. |
| **Biblioteca / pacote** | Código pronto que outras pessoas escreveram e que o projeto reutiliza (pandas, numpy, TimesFM…). |
| **pip** | O instalador de bibliotecas do Python. |
| **Ambiente virtual (venv)** | Uma "caixa" separada, na pasta `.venv`, com as bibliotecas só deste projeto, para não bagunçar o resto do computador. Precisa ser **ativado**: `source .venv/bin/activate` no Mac/Ubuntu, `.\.venv\Scripts\Activate.ps1` no Windows (o terminal passa a mostrar `(.venv)`). |
| **Git** | Programa que guarda o histórico de um projeto e baixa/atualiza cópias dele. |
| **GitHub** | Site onde o projeto fica hospedado. |
| **Repositório (repo)** | A pasta do projeto, com todo o histórico. |
| **Clone (`git clone`)** | Baixar uma cópia do repositório para o seu computador. |
| **`git pull`** | Atualizar sua cópia com as novidades do GitHub. |
| **Homebrew (`brew`)** | Instalador de programas para Mac, via Terminal. |
| **`apt`** | Instalador de programas do Ubuntu (`sudo apt install nome`). `sudo` = "executar como administrador". |
| **`winget`** | Instalador de programas do Windows, via PowerShell. |
| **PowerShell** | O terminal do Windows. |
| **CSV** | Arquivo de planilha em texto puro: linhas, com valores separados por vírgula (ou ponto e vírgula). Abre no Excel. |
| **Streamlit** | A ferramenta que cria a interface web deste projeto. |
| **Notebook (Jupyter)** | Documento com texto e código em "células" que você roda uma a uma e vê o resultado logo abaixo. Ótimo para estudar. |
| **Modelo / pesos** | O "cérebro" já treinado do TimesFM: um arquivo grande baixado na primeira execução. |
| **Hugging Face** | Site onde o modelo está armazenado para download. |
| **MLX** | Tecnologia da Apple para rodar modelos de IA com eficiência nos chips M1/M2/M3/M4. |
| **CPU / GPU** | O processador comum / o processador gráfico, bom para cálculos de IA. |
| **CUDA** | Tecnologia das placas de vídeo **NVIDIA** que acelera cálculos de IA. Só vale se você tiver uma placa NVIDIA. |
| **Localhost** | O seu próprio computador. `http://localhost:8501` é um endereço que só existe no seu computador. |
| **Erro / traceback** | Mensagem de problema. Leia a **última linha**, que costuma dizer o que houve. |

## Termos de central de atendimento e previsão

| Termo | Como aparece aqui |
|---|---|
| **Chamadas oferecidas (`calls_offered`)** | Chamadas que chegaram à central num intervalo, atendidas ou não. É a coluna que o laboratório prevê. |
| **Intervalo** | O "balde" de tempo em que as chamadas são contadas: 5, 15 ou 30 minutos, hora ou dia. |
| **Horizonte** | Quantos intervalos à frente a previsão cobre. |
| **Sazonalidade** | Padrão que se repete: o mesmo pico de manhã todo dia, a segunda cheia toda semana. |
| **TMA (tempo médio de atendimento)** | Duração média de cada chamada. Não é previsto aqui, mas junto com o volume dimensiona a equipe. |
| **Nível de serviço** | Meta como "80% das chamadas atendidas em 20 segundos". Não é calculado aqui. |
| **Erlang C** | Fórmula clássica que transforma volume previsto, TMA e nível de serviço em número de agentes. Fora do escopo deste laboratório. |
| **Quantil (10%–90%)** | Limites da faixa de incerteza da previsão: o volume deve ficar entre eles em ~80% dos casos. |
| **WAPE** | Erro total / total de chamadas, em %. A medida de acerto principal. |
| **Viés** | Se a previsão tende a errar para mais (+) ou para menos (−) no total. |
| **Backtest (teste de realidade)** | Esconder o final do histórico, prever, e comparar com o que aconteceu. |
| **Zero-shot** | O modelo prevê uma série que nunca viu, sem treinamento. |

## Atalhos úteis no Terminal

- `Ctrl + C`: interrompe o que está rodando (por exemplo, fecha a interface). Vale nos três sistemas.
- Seta para cima: repete o comando anterior.
- `Tab`: completa nomes de pastas e arquivos.
- Limpar a tela: `Cmd + K` (Mac), `Ctrl + L` (Ubuntu), `cls` (Windows).

## Quando travar

Copie a **mensagem de erro inteira**, veja [06-problemas-comuns.md](06-problemas-comuns.md) e, se não
resolver, mande a mensagem para quem mantém o projeto.
