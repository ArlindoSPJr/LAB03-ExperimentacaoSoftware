# Lab03 — Mineração de Métricas DORA

Pipeline que minera métricas DORA (frequência de deploy, lead time, change failure rate e tempo de recuperação) de repositórios open-source do GitHub que usam GitHub Actions.

Janela de observação fixa: **2025-10-01 a 2026-09-30** (UTC), definida em `config.yaml`. Não altere.

## Como replicar (30 repositórios)

**1. Requisitos:** Python 3.12, git, pip e uma conta no GitHub.

**2. Token.** Crie um token em GitHub > *Settings* > *Developer settings* > *Personal access tokens*: *fine-grained* com acesso só a "Public repositories (read-only)", ou *classic* **sem nenhum escopo**. O pipeline só lê dados públicos. Defina a variável de ambiente (o token nunca é gravado em disco):

```
# Linux / macOS / Git Bash
export GITHUB_TOKEN="<seu-token>"

# Windows PowerShell
$env:GITHUB_TOKEN = "<seu-token>"
```

**3. Clone e instale** (em clone novo, sem a pasta `cache/`):

```
git clone https://github.com/ArlindoSPJr/LAB03-ExperimentacaoSoftware.git
cd LAB03-ExperimentacaoSoftware
python3.12 -m venv .venv                # Windows: py -3.12 -m venv .venv
source .venv/bin/activate               # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

No Windows, clone num caminho curto (por exemplo, `C:\lab03`). Em caminhos longos, o `pip install` pode falhar com `OSError: [Errno 2] No such file or directory` por causa do limite de 260 caracteres do Windows. Outra saída é ativar o suporte a caminhos longos: <https://pip.pypa.io/warnings/enable-long-paths>.

**4. Guarde o dataset original.** O pipeline **sobrescreve** `data/metricas.csv`, `data/funil.csv` e `data/elegiveis_sorteio.csv`. Copie o original para fora do repositório, pois é com ele que você vai comparar:

```
# Linux / macOS / Git Bash
cp data/metricas.csv ../metricas_original.csv

# Windows PowerShell
Copy-Item data\metricas.csv ..\metricas_original.csv
```

**5. Execute o comando único:**

```
python -m pipeline --config config.subamostra30.yaml
```

**6. Espere.** O cache começa vazio, então todas as respostas vêm da API. Quando a cota (5.000 requisições por hora) acaba, o pipeline **pausa sozinho** até a renovação e o terminal parece parado: é normal. Erros 5xx são repetidos com espera de 1, 2, 4, 8 e 16 s. Se interromper (`Ctrl+C`, queda de rede), rode **o mesmo comando** de novo: ele continua de onde parou, sem repetir chamadas.

Referência: em clone limpo, com Python 3.12 no Windows e cache vazio, a execução levou cerca de **1h15** (21/10/2026). Os 30 repositórios passaram nos critérios de inclusão, e as métricas e a classificação DORA ficaram idênticas às do dataset original.

**7. Compare com o original**, repositório a repositório (coluna `repo`), usando o novo `data/metricas.csv` e o arquivo guardado no passo 4:

- diferença relativa de `deploy_freq_week`, `lead_time_a_days`, `lead_time_b_days`, `cfr_ci`, `cfr_entrega` e `recovery_median_h`;
- % de repositórios com a mesma classificação DORA (`dora_overall`).

Pequenas diferenças são esperadas: os repositórios continuam recebendo commits e as datas de coleta diferem. A amostra final pode ter menos de 30 linhas, porque os repositórios passam de novo pelos critérios de inclusão; os descartes aparecem em `data/funil.csv`.

**8. Se algo falhar ou faltar neste README**, abra uma Issue neste repositório com: o comando executado, a mensagem de erro completa, a versão do Python, o sistema operacional e, em caso de divergência, os valores esperados e obtidos.

## Saídas

Ao final, o pipeline grava em `data/`:

| Arquivo | Conteúdo |
|---|---|
| `data/metricas.csv` | Dataset final: uma linha por repositório da amostra, com metadados, métricas DORA e classificação |
| `data/funil.csv` | Funil de seleção: quantos repositórios restaram em cada etapa e o motivo dos descartes |
| `data/elegiveis_sorteio.csv` | Repositórios elegíveis ao sorteio da amostra-ouro |
| `data/DICIONARIO.md` | Dicionário de dados: nome, tipo, unidade e fórmula/origem de cada coluna |

Unidades: lead time em **dias**, recuperação em **horas**, CFR como **fração de 0 a 1**, frequência em **unidades por semana**. Datas em UTC.

## Testes

```
pytest --cov=metricas --cov-report=term-missing
```

É o comando que o CI usa (cobertura mínima de 80% do módulo `metricas`). Não precisa de token nem de rede.
