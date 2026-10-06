# Dicionário de dados

Versão inicial (S01-D1), com as colunas previstas no plano (`docs/superpowers/plans/2026-10-05-lab03-dora-pipeline.md`, Task 8). Toda coluna nova dos CSVs finais deve ser adicionada aqui com nome, tipo, unidade e fórmula/origem.

Convenções: datas em UTC; janela de 12 meses definida em `config.yaml` (`window.start`, `window.end`); célula vazia = valor ausente (`None`).

## `data/metricas.csv` — uma linha por repositório da amostra final

| Coluna | Tipo | Unidade | Fórmula / origem |
|---|---|---|---|
| `repo` | texto | — | `full_name` de `GET /repos/{owner}/{repo}` (ex.: `octo/hello`) |
| `stars` | inteiro | estrelas | `stargazers_count` de `GET /repos/{owner}/{repo}` |
| `language` | texto | — | `language` de `GET /repos/{owner}/{repo}` (linguagem principal; pode ser vazia) |
| `contributors` | inteiro | pessoas | Última página do cabeçalho `Link` de `GET /repos/{owner}/{repo}/contributors?per_page=1&anon=true` (inclui anônimos); vazio quando a API recusa a lista por ser grande demais |
| `age_days` | inteiro | dias | Fim da janela − `created_at` do repositório (a confirmar na S01-O3.4) |
| `n_releases` | inteiro | releases | Releases com `draft=false`, `prerelease=false` e `published_at` dentro da janela (`GET /repos/{owner}/{repo}/releases`) |
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
| `score_freq` | inteiro | nota 1–4 | Nota DORA da frequência: ≥ 7/sem = 4; ≥ 1/sem = 3; ≥ 1/mês = 2; senão 1 |
| `score_lead` | inteiro | nota 1–4 | Nota DORA do lead time (a): < 1 dia = 4; < 7 dias = 3; < 30 dias = 2; senão 1 |
| `score_cfr` | inteiro | nota 1–4 | Nota DORA do CFR (a): ≤ 15% = 4; ≤ 30% = 3; ≤ 45% = 2; senão 1 |
| `score_rec` | inteiro | nota 1–4 | Nota DORA da recuperação: < 1 h = 4; < 24 h = 3; < 168 h = 2; senão 1 |
| `dora_overall` | texto | categoria | Mediana das 4 notas arredondada para baixo: 4 Elite, 3 High, 2 Medium, 1 Low. Vazio se alguma métrica for ausente |

## `data/funil.csv` — funil de seleção

| Coluna | Tipo | Unidade | Fórmula / origem |
|---|---|---|---|
| `etapa` | texto | — | Nome da etapa (ex.: candidatos, com Actions, ≥ 5 releases e ≥ 50 runs, amostra final) |
| `restantes` | inteiro | repositórios | Repositórios que passaram pela etapa |
| `descartados` | inteiro | repositórios | `restantes` da etapa anterior − `restantes` desta etapa (0 na primeira) |
| `motivo` | texto | — | Motivo do descarte nesta etapa |
