# 05 — Glossário de TI para quem está começando

| Termo | Em português simples |
|---|---|
| **Terminal** | Janela onde você digita comandos em vez de clicar. No Mac: `Cmd + Espaço` → "Terminal". |
| **Comando** | Uma instrução digitada no Terminal, seguida de Enter. |
| **Pasta / diretório** | Igual a uma pasta do Finder. `cd nome` entra numa pasta; `cd ..` volta; `ls` lista o conteúdo. |
| **Python** | A linguagem de programação usada aqui. |
| **Biblioteca / pacote** | Código pronto que outras pessoas escreveram e que o projeto reutiliza (pandas, numpy, TimesFM…). |
| **pip** | O instalador de bibliotecas do Python. |
| **Ambiente virtual (venv)** | Uma "caixa" separada, na pasta `.venv`, com as bibliotecas só deste projeto, para não bagunçar o resto do Mac. Precisa ser **ativado** com `source .venv/bin/activate` (o Terminal passa a mostrar `(.venv)`). |
| **Git** | Programa que guarda o histórico de um projeto e baixa/atualiza cópias dele. |
| **GitHub** | Site onde o projeto fica hospedado. |
| **Repositório (repo)** | A pasta do projeto, com todo o histórico. |
| **Clone (`git clone`)** | Baixar uma cópia do repositório para o seu Mac. |
| **`git pull`** | Atualizar sua cópia com as novidades do GitHub. |
| **Homebrew (`brew`)** | Instalador de programas para Mac, via Terminal. |
| **CSV** | Arquivo de planilha em texto puro: linhas, com valores separados por vírgula (ou ponto e vírgula). Abre no Excel. |
| **Streamlit** | A ferramenta que cria a interface web deste projeto. |
| **Notebook (Jupyter)** | Documento com texto e código em "células" que você roda uma a uma e vê o resultado logo abaixo. Ótimo para estudar. |
| **Modelo / pesos** | O "cérebro" já treinado do TimesFM: um arquivo grande baixado na primeira execução. |
| **Hugging Face** | Site onde o modelo está armazenado para download. |
| **MLX** | Tecnologia da Apple para rodar modelos de IA com eficiência nos chips M1/M2/M3/M4. |
| **CPU / GPU** | O processador comum / o processador gráfico, bom para cálculos de IA. |
| **Localhost** | O seu próprio computador. `http://localhost:8501` é um endereço que só existe no seu Mac. |
| **Erro / traceback** | Mensagem de problema. Leia a **última linha**, que costuma dizer o que houve. |

## Atalhos úteis no Terminal

- `Ctrl + C`: interrompe o que está rodando (por exemplo, fecha a interface).
- Seta para cima: repete o comando anterior.
- `Tab`: completa nomes de pastas e arquivos.
- `Cmd + K`: limpa a tela.

## Quando travar

Copie a **mensagem de erro inteira**, veja [06-problemas-comuns.md](06-problemas-comuns.md) e, se não
resolver, mande a mensagem para quem mantém o projeto.
