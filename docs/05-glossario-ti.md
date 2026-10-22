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
| **Erlang** | Unidade de carga: 1 Erlang = um agente ocupado o tempo todo. Carga = chamadas × TMA ÷ duração do intervalo. |
| **Erlang C / Erlang A** | Fórmulas que dizem quantos agentes uma carga exige para uma meta de nível de serviço. O Erlang C supõe que ninguém desiste; o Erlang A considera clientes que desligam. |
| **Ocupação** | Parte do tempo em que o agente está atendendo (carga ÷ agentes). Alta demais cansa a equipe. |
| **ASA (espera média)** | Tempo médio que uma chamada espera até ser atendida. |
| **Shrinkage** | Parte do tempo pago em que o agente não atende (pausas, treinamento, faltas, férias). |
| **Pessoas escaladas** | Agentes necessários ÷ (1 − shrinkage), arredondado para cima. |
| **FTE** | Pessoa equivalente de tempo integral: horas escaladas ÷ horas pagas por dia de uma pessoa. |
| **Escala** | Distribuição das pessoas em turnos, em cada dia, para cobrir o dimensionamento ao menor custo. |
| **Turno** | Período de trabalho com início e duração fixos (ex.: 08:00 às 16:00), com pausa de refeição opcional. |
| **Headcount** | Quantas pessoas a equipe precisa ter, considerando o limite de dias trabalhados por semana. |
| **Cobertura** | Pessoas no turno menos as que estão na pausa de refeição, em cada intervalo. |
| **Falta e sobra** | Pessoas a menos ou a mais que a necessidade em um intervalo. A escala mostra as duas. |
| **Cenário "e se"** | Uma versão do dimensionamento com algo diferente (volume, TMA, shrinkage ou meta) para comparar com a base. |
| **Sensibilidade** | O efeito de mudar um parâmetro de cada vez (ex.: TMA +5%, +10%) no dimensionamento. |
| **Evento (feriado, campanha)** | Dia que muda o volume de chamadas e que você informa em um calendário. Tem um tipo e, opcionalmente, um efeito (multiplicador do volume normal). |
| **Efeito de um evento** | Quanto o volume muda: 1,5 = 50% a mais; 0,3 = 70% a menos. Você informa; o ajuste usa esse número. |
| **Covariável** | Série extra, conhecida também no futuro (como os dias de evento), que se dá ao modelo junto com o histórico. |
| **Horário de corte** | No acompanhamento do dia, o primeiro intervalo que ainda não se conhece: o que vem antes é realizado, o que vem depois é previsão. |
| **Desvio acumulado** | Quanto o realizado do dia está acima ou abaixo do planejado até agora, em %. |
| **Re-previsão** | Nova previsão do resto do dia, usando o que já aconteceu hoje. |
| **Fila (queue)** | Um fluxo de chamadas com a sua própria espera: vendas, suporte, cobrança. |
| **Habilidade (skill)** | Qual fila um agente sabe atender. Um agente pode ter mais de uma. |
| **Equipe cruzada** | Agentes que atendem várias filas. Precisa de menos agentes que equipes separadas para a mesma meta. |
| **Pooling** | O efeito de juntar filas na mesma equipe: as sobras de uma cobrem as faltas das outras. |
| **Roteamento** | A regra que decide qual chamada um agente livre atende (a que espera há mais tempo, ou a da fila prioritária). |
| **Simulador** | Programa que reproduz a central chamada a chamada para conferir as fórmulas. |

## Atalhos úteis no Terminal

- `Ctrl + C`: interrompe o que está rodando (por exemplo, fecha a interface). Vale nos três sistemas.
- Seta para cima: repete o comando anterior.
- `Tab`: completa nomes de pastas e arquivos.
- Limpar a tela: `Cmd + K` (Mac), `Ctrl + L` (Ubuntu), `cls` (Windows).

## Quando travar

Copie a **mensagem de erro inteira**, veja [06-problemas-comuns.md](06-problemas-comuns.md) e, se não
resolver, mande a mensagem para quem mantém o projeto.
