# Dicionário de dados

Versão inicial (S01-D1), atualizada na S01-O3.4 com as colunas que o orquestrador (`pipeline/orquestrador.py`) realmente grava e na S02-O1.3 com a consolidação (`pipeline/consolidar.py`). As tabelas seguem a ordem das colunas nos CSVs. Toda coluna nova dos CSVs finais deve ser adicionada aqui com nome, tipo, unidade e fórmula/origem (o teste `tests/test_consolidar.py` confere que a tabela de `data/metricas.csv` lista exatamente as colunas do dataset final, na mesma ordem).

Convenções:
- **Janela de observação:** 12 meses, de **2025-10-01 00:00:00 a 2026-09-30 23:59:59 UTC** (365 dias ≈ 52,14 semanas). O enunciado permite qualquer período de 12 meses; este foi escolhido pelo grupo e é o mesmo na S01 e na S02. As datas ficam em `config.yaml` (`window.start`, `window.end`).
- Datas em UTC; só o default branch; célula vazia = valor ausente (`None`).
- **Dataset final:** `data/metricas.csv` depois da consolidação. O orquestrador grava as colunas de `repo` a `dora_overall`; a consolidação (`python -m pipeline.consolidar`, também executada no fim de `python -m pipeline`) valida o arquivo e acrescenta as colunas derivadas do fim da tabela, sem chamar a API.

## `data/metricas.csv` — uma linha por repositório da amostra final

| Coluna | Tipo | Unidade | Fórmula / origem |
|---|---|---|---|
| `repo` | texto | — | `full_name` de `GET /repos/{owner}/{repo}` (ex.: `octo/hello`) |
| `stars` | inteiro | estrelas | `stargazers_count` de `GET /repos/{owner}/{repo}` |
| `language` | texto | — | `language` de `GET /repos/{owner}/{repo}` (linguagem principal; pode ser vazia) |
| `contributors` | inteiro | pessoas | Última página do cabeçalho `Link` de `GET /repos/{owner}/{repo}/contributors?per_page=1&anon=true` (inclui anônimos); vazio quando a API recusa a lista por ser grande demais |
| `age_days` | inteiro | dias | Dias inteiros entre a data de `created_at` do repositório e `window.end` |
| `n_releases` | inteiro | releases | Releases com `draft=false`, `prerelease=false` e `published_at` dentro da janela (`GET /repos/{owner}/{repo}/releases`) |
| `n_runs_validos` | inteiro | runs | Workflow runs do default branch com `event=push` na janela cuja `conclusion` é sucesso ou falha (os ignorados pela tabela de `conclusion` não contam). Critério de inclusão: ≥ 50 |
| `deploy_freq_week` | decimal | releases/semana | `n_releases` ÷ semanas da janela (dias da janela ÷ 7 ≈ 52,1) — RQ01 |
| `lead_time_a_days` | decimal | dias | RQ02 (a): para cada release R da janela, `published_at(R)` − `commit.author.date` do commit mais antigo de `compare/{anterior}...{R}`; mediana entre as releases. Primeira release da história ignorada |
| `lead_time_b_days` | decimal | dias | RQ02 (b): `published_at(R)` − `commit.author.date` de cada commit de cada release; mediana de todos os commits |
| `cfr_ci` | decimal | fração 0–1 | RQ03 (a): falhas ÷ (falhas + sucessos) dos workflow runs do default branch com `event=push` na janela. Sucesso = `success`; falha = `failure`, `timed_out`, `startup_failure`; demais ignorados |
| `recovery_median_h` | decimal | horas | RQ04: mediana dos episódios de recuperação de todos os workflows; episódio = primeira falha após um sucesso até o próximo sucesso do mesmo workflow; `updated_at` do sucesso − `run_started_at` da primeira falha |
| `n_episodes` | inteiro | episódios | Episódios de falha abertos na janela, incluindo os censurados |
| `n_censored` | inteiro | episódios | Episódios sem sucesso posterior dentro da janela (censurados) |
| `n_falhas_iniciais` | inteiro | runs | Falhas antes do primeiro sucesso do workflow na janela (não abrem episódio) |
| `n_lead_negativos` | inteiro | commits | Commits com `commit.author.date` posterior à release (rebase/squash), descartados do lead time |
| `compare_404` | inteiro | releases | Releases ignoradas no lead time porque `compare/{anterior}...{R}` retornou 404 |
| `meses_no_teto` | texto | meses | Meses (`AAAA-MM`, separados por `;`) em que a consulta de runs devolveu 1.000 resultados, o teto da API: os runs desses meses podem estar incompletos. Vazio se nenhum |
| `n_releases_pre` | inteiro | unidades | Variante `release+pre` (C2 da RQ07): releases **e** pré-releases (`draft=false`) com `published_at` dentro da janela |
| `deploy_freq_week_pre` | decimal | unidades/semana | `n_releases_pre` ÷ semanas da janela (≈ 52,1) — RQ01 na variante C2 |
| `lead_time_b_days_pre` | decimal | dias | RQ02 (b) na variante C2: `published_at(U)` − `commit.author.date` de cada commit de `compare/{anterior}...{U}`, em que a anterior é a release ou pré-release imediatamente anterior (mesmo fora da janela); mediana de todos os commits. Primeira unidade da história ignorada; amostra de pares se houver teto (ver `teto_compare_pre`) |
| `compare_404_pre` | inteiro | unidades | Unidades `release+pre` ignoradas no lead time porque o `compare` retornou 404 |
| `n_lead_negativos_pre` | inteiro | commits | Commits com `commit.author.date` posterior à unidade `release+pre`, descartados do lead time |
| `teto_compare_pre` | inteiro | unidades | Unidades `release+pre` sem `compare` porque o teto `max_compares_variante` (config, padrão 100) foi atingido; o lead time usa uma amostra sistemática de pares espalhados pela janela. 0 = teto não aplicado |
| `n_tags` | inteiro | tags | Variante `tag` (C3 da RQ07): tags de `GET /repos/{owner}/{repo}/tags` cujo commit apontado está no default branch (`GET /repos/{owner}/{repo}/commits?sha={default_branch}&since&until`) e tem `commit.author.date` dentro da janela. Tags não têm data: a data da tag é a do commit apontado |
| `deploy_freq_week_tag` | decimal | tags/semana | `n_tags` ÷ semanas da janela (≈ 52,1) — RQ01 na variante C3 |
| `lead_time_b_days_tag` | decimal | dias | RQ02 (b) na variante C3: data da tag − `commit.author.date` de cada commit de `compare/{tag anterior}...{tag}`; mediana de todos os commits. Tag anterior à janela (base) = entre as 5 tags seguintes na listagem da API (ordem de versão decrescente), a mais recente com data anterior à janela (data por `GET /repos/{owner}/{repo}/git/commits/{sha}`). Primeira tag sem base ignorada; tag sem commits novos não entra; amostra de pares se houver teto (ver `teto_compare_tag`) |
| `compare_404_tag` | inteiro | tags | Tags ignoradas no lead time porque o `compare` retornou 404 |
| `n_lead_negativos_tag` | inteiro | commits | Commits com `commit.author.date` posterior à data da tag, descartados do lead time |
| `teto_compare_tag` | inteiro | tags | Tags sem `compare` porque o teto `max_compares_variante` foi atingido (amostra sistemática de pares; a contagem `n_tags` continua completa). 0 = teto não aplicado |
| `score_freq` | inteiro | nota 1–4 | Nota DORA da frequência: ≥ 7/sem = 4; ≥ 1/sem = 3; ≥ 1/mês = 2; senão 1 |
| `score_lead` | inteiro | nota 1–4 | Nota DORA do lead time (a): < 1 dia = 4; < 7 dias = 3; < 30 dias = 2; senão 1 |
| `score_cfr` | inteiro | nota 1–4 | Nota DORA do CFR (a): ≤ 15% = 4; ≤ 30% = 3; ≤ 45% = 2; senão 1 |
| `score_rec` | inteiro | nota 1–4 | Nota DORA da recuperação: < 1 h = 4; < 24 h = 3; < 168 h = 2; senão 1 |
| `dora_overall` | texto | categoria | Mediana das 4 notas arredondada para baixo: 4 Elite, 3 High, 2 Medium, 1 Low. Vazio se alguma métrica for ausente |
| `prop_censurados` | decimal | fração 0–1 | Derivada na consolidação: `n_censored` ÷ `n_episodes` — proporção de episódios de recuperação censurados no repositório (RQ04). Vazio se `n_episodes` = 0 |
| `n_meses_no_teto` | inteiro | meses | Derivada na consolidação: número de meses listados em `meses_no_teto` (0 se nenhum). Permite filtrar repositórios cujos runs podem estar incompletos |

## `data/funil.csv` — funil de seleção

| Coluna | Tipo | Unidade | Fórmula / origem |
|---|---|---|---|
| `etapa` | texto | — | Nome da etapa, em ordem: `candidatos da busca` (ou `lista fornecida`, quando o config tem `repos`), `processados`, `com GitHub Actions`, `metadados coletados`, `>= 5 releases na janela`, `>= 50 runs válidos na janela`, `amostra final` |
| `restantes` | inteiro | repositórios | Repositórios que passaram pela etapa |
| `descartados` | inteiro | repositórios | `restantes` da etapa anterior − `restantes` desta etapa (0 na primeira) |
| `motivo` | texto | — | Motivo do descarte nesta etapa (vazio se ninguém foi descartado). Em `processados`, os descartados são os candidatos que nem foram processados porque a amostra já tinha `sample_size` repositórios válidos |

## `data/elegiveis_sorteio.csv` — repositórios elegíveis ao sorteio da amostra-ouro

Gerado pela consolidação. Critério: **toda a amostra final** é elegível (enunciado §6.1: "sortear 60 repositórios da amostra final"); todos têm ≥ 5 releases na janela, o que permite sortear 5 releases por repositório. Linhas em ordem alfabética de `repo` (sem diferenciar maiúsculas), para que o sorteio `pd.read_csv("data/elegiveis_sorteio.csv").sample(n=60, random_state=42)` (S02-O2.2) não dependa da ordem de coleta nem das colunas acrescentadas depois ao dataset.

| Coluna | Tipo | Unidade | Fórmula / origem |
|---|---|---|---|
| `repo` | texto | — | `repo` de `data/metricas.csv` (`owner/nome`) |
| `url_releases` | texto | URL | `https://github.com/{repo}/releases`, página das releases para a rotulagem |
| `n_releases` | inteiro | releases | `n_releases` de `data/metricas.csv` (releases não-pré-release na janela) |
