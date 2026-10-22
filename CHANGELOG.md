# Changelog

## v1.0.0 — 2026-10-21

Primeira versão estável.

### O que tem
- **Previsão de chamadas** com o TimesFM 3.0 (zero-shot): previsão pontual e faixa de incerteza de 10% a 90%.
- **Interface web** (Streamlit) em português: carrega um CSV, escolhe colunas e intervalo (5 min a dia),
  prevê, e faz o **teste de realidade** (WAPE, viés, MAE, cobertura) contra a "mesma semana anterior".
- **Quatro sistemas suportados:** Mac Apple silicon (MLX), Mac Intel (PyTorch CPU), Ubuntu (CPU ou GPU
  NVIDIA com `--gpu`) e Windows 10/11 (CPU).
- **Instalação por sistema**, idempotente: detecta Python, `.venv` e bibliotecas e instala só o que
  falta; oferece instalar o Python (Homebrew, apt, winget). Atalhos de duplo clique para Windows
  (`.bat`) e Mac (`.command`).
- **Datasets públicos de chamadas** com um único script (`scripts/baixar_datasets.py`, todos ou
  escolhidos): `technion-bank`, `hyndman-bank` e `nyc-311`, mais um exemplo sintético incluído.
  Fontes e licenças em `data/README.md`.
- **Documentação em português** (conceitos de previsão para call center, instalação por sistema,
  glossário, problemas comuns) e dois notebooks didáticos.
- **CI** em Ubuntu, Windows e macOS (Apple silicon e Intel): testes, instalação real de cada sistema,
  segunda execução idempotente, instalação a partir de um Ubuntu sem Python e, sob demanda, uma
  previsão real com o modelo.

### Pacote do release
- O `.zip`/`.tar.gz` do release é **enxuto**: só traz o necessário para rodar (instaladores, atalhos,
  requisitos, docs, notebooks, dado de exemplo e o laboratório compilado em `wheels/`). Não inclui
  `src/`, `tests/` nem a configuração de desenvolvimento. É montado por `scripts/montar_release.py`.
- A interface abre com `python -m callcenter_lab` (ou pelos atalhos).

### Limitações conhecidas
- Uso de GPU NVIDIA (`--gpu`), Windows ARM64 e Linux ARM não foram testados.
- O download dos datasets depende de sites de terceiros; os testes automáticos usam respostas
  simuladas.
- Os pesos do TimesFM 3.0 têm licença **não comercial**. Os datasets não fazem parte do repositório e
  têm condições de uso próprias.
- Só prevê **volume de chamadas**; não calcula escalas nem número de agentes (Erlang).
- Não usa covariáveis (feriados, campanhas) nesta versão.
