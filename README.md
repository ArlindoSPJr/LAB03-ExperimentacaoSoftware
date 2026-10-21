# Lab03 — Mineração de Métricas DORA

Pipeline que minera métricas DORA (frequência de deploy, lead time, change failure rate e tempo de recuperação) de repositórios open-source do GitHub que usam GitHub Actions.

## Pré-requisitos

- **Python 3.12** (versão usada pelo CI do projeto). A suíte também foi executada com sucesso em Python 3.13.1, mas a versão de referência é a 3.12.
- **git** e **pip**.
- Uma **conta no GitHub** para gerar um token de acesso (próxima seção).
- Conexão com a internet e disco livre para o cache. A coleta da amostra de 300 repositórios deste projeto gerou cerca de 77 mil arquivos em `cache/`; uma execução com 30 repositórios é bem menor.
- Nenhuma biblioteca de acesso à API do GitHub é usada: a coleta usa `requests` direto (as demais dependências estão em `requirements.txt`).

## Token

O pipeline lê o token da variável de ambiente `GITHUB_TOKEN`. Sem ela, o comando termina na hora com `erro: defina a variável de ambiente GITHUB_TOKEN com um token do GitHub.` (código de saída `1`). O token **nunca** é lido de arquivo nem gravado em disco (o cache guarda só as respostas da API) e **nunca deve ser commitado**.

**Como gerar:** em GitHub > *Settings* > *Developer settings* > *Personal access tokens*, crie um token. Qualquer um destes serve:

- *Fine-grained token* com acesso a **"Public repositories (read-only)"** e nenhuma permissão adicional; ou
- *Token (classic)* com **nenhum escopo marcado**.

O pipeline só lê dados públicos (busca de repositórios, metadados, releases, tags, comparações de commits e execuções do Actions), então não precisa de escopo de escrita nem de acesso a repositórios privados. O token serve para elevar o limite de requisições: com ele a API REST permite **5.000 requisições por hora**; sem ele, apenas 60, o que inviabiliza a coleta.

**Como definir** (vale só para o terminal aberto; use o seu token no lugar do texto de exemplo):

```
# Linux / macOS / Git Bash
export GITHUB_TOKEN="<seu-token>"

# Windows PowerShell
$env:GITHUB_TOKEN = "<seu-token>"
```

## Instalação

A partir da raiz do repositório, crie um ambiente virtual e instale as dependências, que estão com versão fixada em `requirements.txt`:

```
git clone https://github.com/ArlindoSPJr/LAB03-ExperimentacaoSoftware.git
cd LAB03-ExperimentacaoSoftware

python3.12 -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

(No Windows, se `python3.12` não existir, use `py -3.12 -m venv .venv`.)

Para conferir a instalação sem token e sem rede, rode a suíte de testes (veja a seção **Testes**):

```
python -m pytest
```

Em ambiente limpo (venv novo, `pip install -r requirements.txt`), a suíte passou com 509 testes em cerca de 2 minutos.

## Comando único

```
python -m pipeline --config config.yaml
```

Esse comando executa tudo, do começo ao fim: busca de candidatos, filtro de GitHub Actions, metadados, releases, lead time, workflow runs (CFR e recuperação), variantes da RQ07 (release + pré-release e tag), critério de inclusão, classificação DORA e consolidação. Ao final grava `data/metricas.csv`, `data/funil.csv` e `data/elegiveis_sorteio.csv` e imprime o funil de seleção no terminal. Os arquivos têm o formato descrito na seção **Saídas** e no dicionário `data/DICIONARIO.md`.

Códigos de saída: `0` sucesso; `1` variável `GITHUB_TOKEN` ausente; `2` consolidação reprovou o dataset (os problemas são listados). Um erro da API (por exemplo, falha persistente depois das tentativas) interrompe a execução com a mensagem do erro; basta executar de novo (veja *Retomada*).

### Configuração (`config.yaml`)

| Chave | O que faz |
|---|---|
| `window.start`, `window.end` | Janela de 12 meses (datas UTC). **`window.end` precisa estar no passado**; do contrário, o cache guarda respostas incompletas e a retomada as reaproveita |
| `sample_size` | Quantos repositórios **válidos** coletar. O pipeline processa candidatos em ordem até atingir esse número |
| `star_ranges` | Faixas de estrelas que fatiam a busca (a API de busca devolve no máximo 1.000 resultados por consulta) |
| `max_compares_variante` | Teto de comparações de commits por repositório nas variantes da RQ07 (`null` desliga) |
| `cache_dir` | Pasta do cache em disco (padrão `cache`) |
| `repos` | Opcional: lista fixa de repositórios (`owner/repo`); quando presente, **pula a busca** |

### Replicação cruzada: subamostra de 30 repositórios

<!-- S03-O3.3 (#47) precisa deixar isto verdadeiro antes da Entrega Final:
     - existe `config.subamostra30.yaml` na raiz, com `repos:` de 30 repositórios sorteados do dataset em `data/metricas.csv`, `sample_size: 30` e a MESMA janela do `config.yaml`;
     - `requirements.txt` com versões fixadas (já está);
     - os passos abaixo foram executados em clone limpo (inclusive em Python 3.12), com tempo medido e anotado na seção "Tempo de execução";
     - `data/metricas.csv` do commit de entrega é o dataset final.
     Se o nome do arquivo mudar, atualize esta seção. -->

Esta seção é para quem vai **executar o nosso pipeline do zero** sobre 30 repositórios do dataset original, usando só este README. A lista dos 30 repositórios já está pronta em `config.subamostra30.yaml`; não é preciso escolher nem sortear nada.

1. **Clone e instale** (seções *Pré-requisitos*, *Token* e *Instalação*, acima). Use um clone **novo**, sem a pasta `cache/`.
2. **Guarde o dataset original.** O pipeline sobrescreve `data/metricas.csv`, `data/funil.csv` e `data/elegiveis_sorteio.csv`. Antes de rodar, copie o original para fora do repositório (é com ele que você vai comparar):

   ```
   # Linux / macOS / Git Bash
   cp data/metricas.csv ../metricas_original.csv

   # Windows PowerShell
   Copy-Item data\metricas.csv ..\metricas_original.csv
   ```

3. **Defina o token** (`GITHUB_TOKEN`, seção *Token*).
4. **Rode o comando único** com a configuração da subamostra:

   ```
   python -m pipeline --config config.subamostra30.yaml
   ```

   Como o cache começa vazio, todas as respostas vêm da API: a cota de 5.000 requisições por hora pode se esgotar e o terminal parece parado enquanto o pipeline espera a renovação. Isso é normal (veja *Tempo de execução e limite de requisições*). Se interromper, rode o mesmo comando de novo: ele continua a partir do cache.
5. **Confira a saída.** O resultado fica em `data/metricas.csv` (uma linha por repositório) e `data/funil.csv`. Como os repositórios passam de novo pelos critérios de inclusão (≥ 5 releases e ≥ 50 workflow runs válidos na janela), a amostra final pode ter menos de 30 linhas; os descartes aparecem no funil.
6. **Compare com o original**, repositório a repositório (chave `repo`), usando as mesmas colunas nos dois arquivos:
   - **diferença relativa** de cada métrica: `deploy_freq_week`, `lead_time_a_days`, `lead_time_b_days`, `cfr_ci`, `cfr_entrega` e `recovery_median_h`;
   - **% de repositórios com a mesma classificação DORA** (`dora_overall`).

   Pequenas diferenças são esperadas: os repositórios continuam recebendo commits e as datas de coleta diferem. O significado, a unidade e a fórmula de cada coluna estão em `data/DICIONARIO.md`.
7. **Se algo falhar ou faltar na documentação**, anote o comando executado, a mensagem de erro completa, a versão do Python e o sistema operacional. Cada problema (falha de execução, documentação faltante ou divergência de resultado) deve virar uma Issue neste repositório com esses dados e os valores esperados e obtidos.

#### Alternativa: usar a sua própria lista de repositórios

Só se quiser testar com outros repositórios. Copie `config.yaml` e edite a cópia: descomente `repos` e liste os repositórios; ajuste `sample_size` para um valor **maior ou igual** ao tamanho da lista (o padrão do arquivo, 300, já serve):

```yaml
sample_size: 30
repos:
  - owner1/repo1
  - owner2/repo2
  # ...
```

Depois rode `python -m pipeline --config <sua-copia>.yaml`. Os repositórios da lista passam pelos mesmos critérios de inclusão e os descartes aparecem no funil. A janela de `config.yaml` e todas as definições operacionais seguem o enunciado e não devem ser alteradas. A saída também vai para `data/` e sobrescreve os arquivos (veja o passo 2 acima).

### Tempo de execução e limite de requisições

- O pipeline lê `X-RateLimit-Remaining` e `X-RateLimit-Reset` em cada resposta. Quando a cota acaba, **pausa sozinho** até a renovação (o terminal parece parado, mas está esperando). Para um limite secundário sem indicação de espera, aguarda 60 s.
- Respostas 5xx e falhas de conexão têm novas tentativas com espera exponencial (1 s, 2 s, 4 s, 8 s, 16 s); depois da quinta tentativa o erro é levantado.
- A busca de candidatos pagina pelo cabeçalho `Link` (`rel="next"`).
- Ordem de grandeza (estimativa, não é garantia): a amostra de 300 repositórios deste projeto (1.328 candidatos processados) gerou cerca de 77 mil respostas; com a cota de 5.000 por hora, isso leva muitas horas. Uma lista de 30 repositórios custa algumas milhares de requisições, ou seja, de dezenas de minutos a poucas horas, conforme o número de releases e de runs de cada um.
- O andamento aparece no terminal (uma linha por repositório: iniciando, descartado em qual etapa, ou válido).
- A situação da cota pode ser consultada sem custo em `GET https://api.github.com/rate_limit`.

### Cache e retomada

Cada resposta 2xx da API é gravada em `cache/` (um arquivo JSON por requisição, escrita atômica). Se a execução for interrompida (`Ctrl+C`, queda de rede, erro persistente), **rode o mesmo comando de novo**: as requisições já feitas saem do cache, sem nova chamada, e a coleta continua de onde parou. Os CSVs de `data/` só são gravados ao final da coleta.

- Não troque `window`, `star_ranges` nem `repos` no meio de uma coleta; para recomeçar com outra configuração, apague a pasta `cache/`.
- `cache/` não é versionado. Respostas guardadas no cache não são atualizadas: para dados novos, apague a pasta.


## Janela de observação

12 meses, de **2025-10-01 a 2026-09-30** (UTC), definidos em `config.yaml` (`window.start`, `window.end`). O enunciado aceita qualquer período de 12 meses; este foi escolhido pelo grupo e vale para todas as sprints. Mudar a janela exige refazer a coleta.

## Saídas

Ao final da execução, o pipeline grava em `data/`:

| Arquivo | Conteúdo |
|---|---|
| `data/metricas.csv` | **Dataset final**: uma linha por repositório da amostra final, com metadados, métricas DORA (RQ01–RQ04), as variantes de unidade de deploy da RQ07 (release, release+pré-release, tag), contadores de casos censurados/descartados, a classificação DORA e as colunas derivadas da consolidação |
| `data/funil.csv` | Funil de seleção: quantos repositórios restaram em cada etapa e o motivo dos descartes |
| `data/elegiveis_sorteio.csv` | Repositórios elegíveis ao sorteio da amostra-ouro (toda a amostra final, em ordem alfabética), com o link das releases |
| `data/DICIONARIO.md` | Dicionário de dados: nome, tipo, unidade e fórmula/origem de cada coluna dos CSVs acima |

Unidades: lead time em **dias**, recuperação em **horas**, CFR como **fração de 0 a 1**, frequência em **unidades (releases, releases+pré-releases ou tags) por semana**. Datas em UTC.

### Consolidação do dataset

A última etapa de `python -m pipeline` é a consolidação (`pipeline/consolidar.py`). Ela não chama a API: lê `data/metricas.csv` e `data/funil.csv`, confere a integridade do dataset, acrescenta as colunas derivadas e grava `data/elegiveis_sorteio.csv`. Para refazer só a consolidação (por exemplo, depois de atualizar o código ou o dicionário), sem token e sem rede:

```
python -m pipeline.consolidar --config config.yaml
```

Opções: `--dados <pasta>` (padrão `data`). Códigos de saída: `0` sucesso; `1` falta `metricas.csv`/`funil.csv`; `2` dataset inválido (os problemas são listados e nada é regravado). A consolidação é idempotente: rodar de novo produz os mesmos arquivos.

Checagens: colunas na ordem do dicionário; `repo` sem duplicatas; critério de inclusão (≥ 5 releases e ≥ 50 runs válidos); funil fechando com o número de linhas; CFR entre 0 e 1, tempos e frequências não negativos, notas de 1 a 4, `dora_overall` vazio só quando falta métrica; censurados ≤ episódios; release+pré ≥ releases; frequência de cada unidade = contagem ÷ semanas da janela; `erro_tags` 0 ou 1, com as colunas da variante tag todas vazias quando `erro_tags = 1` e as contagens dela (inclusive `commits_omitidos_tag`) preenchidas quando `erro_tags = 0`.

O sorteio da validação manual usa `pd.read_csv("data/elegiveis_sorteio.csv").sample(n=60, random_state=42)`.

As respostas da API ficam em cache em `cache/` (não versionado). Reexecutar o comando reaproveita o cache e continua de onde parou.

## Validação manual (amostra-ouro)

As planilhas de rotulagem são geradas por `validacao/gerar_planilhas.py` (usa o token e o cache, como o pipeline):

```
python -m validacao.gerar_planilhas --config config.yaml
```

- **Sorteio:** 60 repositórios de `data/elegiveis_sorteio.csv` com `df.sample(n=60, random_state=42)`; em cada um, 5 releases não-pré-release da janela sorteadas com a mesma semente (`SEMENTE = 42`) sobre as posições em ordem cronológica (com menos de 5, entram todas).
- **Saída:** `rotulos/A.csv`, `rotulos/B.csv` e `rotulos/C.csv`, idênticos e em branco. O script nunca sobrescreve uma planilha existente (código de saída `2`). Nenhuma coluna traz a saída da heurística de release corretiva.
- **Formato:** uma linha `nivel=repo` por repositório, seguida das linhas `nivel=release`. Colunas `url` (página do repositório ou da release) e `url_commits` (`compare` da release anterior até a sorteada) servem para ler as *release notes* e os commits.
- **Como preencher** (cada avaliador só o seu arquivo, sem consultar os outros):

| Coluna | Linhas | Valores aceitos |
|---|---|---|
| `tipo_projeto` | `repo` | `biblioteca/framework`, `aplicacao/servico`, `ferramenta CLI`, `outro` |
| `entregas_reais` | `repo` | `sim`, `nao`, `incerto` |
| `corretiva` | `release` | `sim`, `nao` |
| `observacao` | qualquer | texto livre (opcional) |

Depois que os três avaliadores preenchem as planilhas, o kappa e o consenso são calculados sem token e sem rede:

```
python -m validacao.consolidar
```

- **Saídas:** `rotulos/kappa.csv` (kappa de Fleiss, concordância observada e contagens por dimensão) e `rotulos/consenso.csv` (rótulo de consenso de cada item, com `origem_<dimensao>` = `unanime`/`maioria`/`reuniao`/`pendente` e os votos de cada avaliador).
- **Desempate:** maioria simples; empates 1-1-1 são decididos em reunião e registrados em `rotulos/decisoes_reuniao.csv` (`nivel,repo,tag,dimensao,rotulo,justificativa`). Com empate sem decisão, o comando sai com código `2`. O protocolo e os resultados estão em `docs/PROTOCOLO_DESEMPATE.md`.

## Testes

Os testes usam [pytest](https://docs.pytest.org/) e ficam em `tests/`. A partir da raiz do repositório, com as dependências de `requirements.txt` instaladas:

```
pytest
```

Para rodar com a cobertura do módulo de métricas (é o comando que o CI usa):

```
pytest --cov=metricas --cov-report=term-missing
```

Para rodar só um arquivo ou um teste:

```
pytest tests/test_lead_time.py -v
pytest tests/test_lead_time.py::test_lead_time_por_release_exemplo_do_enunciado -v
```

Como os testes são escritos:

- **Sem rede e sem token.** As funções de coleta recebem um cliente HTTP com sessão falsa (*fake*) e uma função `sleep` injetada, então nenhum teste acessa a API do GitHub nem espera de verdade. O token real nunca é usado nos testes.
- **Fixtures construídas à mão**, com resultado conhecido no papel. Os exemplos numéricos do enunciado viram testes (ex.: lead time de 13 dias da `v1.1`, recuperação de 1h20, `overall([4,3,3,1]) == "High"`).
- **Casos de borda** exigidos pelo enunciado: release sem commits novos, repositório com uma única release, `compare` com 404, runs `cancelled`/`skipped` ignoradas, falha nunca recuperada (censurada), métrica ausente (`None`).

| Área | Arquivos de teste |
|---|---|
| Cliente HTTP, cache, rate limit e backoff | `tests/test_http.py` |
| Seleção de candidatos, metadados e funil | `tests/test_selecao.py`, `tests/test_metadados.py` |
| Releases, commits entre releases e workflow runs | `tests/test_releases.py`, `tests/test_runs.py`, `tests/test_etapa_releases.py` |
| Consolidação do dataset, colunas derivadas, elegíveis ao sorteio e conferência do dicionário | `tests/test_consolidar.py` |
| Validação manual: kappa de Fleiss, consenso, desempate e planilhas de rotulagem | `tests/test_concordancia.py`, `tests/test_consolidar_rotulos.py`, `tests/test_gerar_planilhas.py` |
| Métricas: lead time, CFR, recuperação e classificação DORA | `tests/test_lead_time.py`, `tests/test_classificacao.py`; `tests/test_cfr.py` e `tests/test_recuperacao.py` entram com as Issues S01-O3.1 e S01-O3.2 |

**CI:** o workflow `.github/workflows/testes.yml` roda a suíte no GitHub Actions a cada push e pull request. Um PR só é mergeado com os testes verdes. A meta é **cobertura mínima de 80% do módulo `metricas`** (`--cov-fail-under=80`); enquanto as métricas da S01 não estão completas, o limite fica em 0 e sobe para 80 na Issue S01-O3.5.

<!-- Rascunho (S01-D2): atualizar a tabela quando entrarem os testes do orquestrador e das etapas de runs (Onda 3). -->
