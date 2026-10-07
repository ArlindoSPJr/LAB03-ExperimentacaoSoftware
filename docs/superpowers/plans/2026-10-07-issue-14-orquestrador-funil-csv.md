# Issue #14 (S01-O3.4) — Orquestrador, funil e CSV

**Objetivo:** `python -m pipeline --config config.yaml` roda do começo ao fim: seleção → Actions → metadados → etapa de releases → etapa de runs → critério de inclusão → `classificar_repositorio` → `data/funil.csv` e `data/metricas.csv`.

**Especificação:** Issue #14, `docs/ISSUES.md` (S01-O3.4, decisões 1 e 2), plano geral (Task 8 e contratos), enunciado (seções 2, 7 e 10).

## Arquivos
- Criar `pipeline/orquestrador.py`, `pipeline/__main__.py`, `tests/test_orquestrador.py`.
- Atualizar `data/DICIONARIO.md` (colunas novas e funil real).

## Interfaces
```python
# pipeline/orquestrador.py
COLUNAS: list[str]   # ordem das colunas de data/metricas.csv
def carregar_config(path) -> dict
def janela_da_config(cfg: dict) -> tuple[datetime, datetime]   # start 00:00:00 UTC, end 23:59:59 UTC
def executar(client, cfg: dict, saida: pathlib.Path) -> tuple[DataFrame, DataFrame]   # (metricas, funil); grava os 2 CSVs

# pipeline/__main__.py
def main(argv: list[str] | None = None) -> int   # --config; token de GITHUB_TOKEN; cache em cfg["cache_dir"]
```

## Fluxo por candidato (em ordem, até `sample_size` válidos)
1. `uses_actions` — False ou 404 → descarte "sem GitHub Actions".
2. `collect_metadata` — 404 → descarte "repositório indisponível (404)".
3. `coletar_releases_e_lead_time` — `n_releases < 5` → descarte. A etapa de runs **não** é chamada (economiza cota).
4. `coletar_runs_e_metricas` — `n_runs_validos < 50` → descarte.
5. `classificar_repositorio(deploy_freq_week, lead_time_a_days, cfr_ci, recovery_median_h)` → linha do CSV.

Sem `repos` no config: candidatos de `search_candidates` (já embaralhados, decisão 2). Com `repos`: a lista na ordem dada, sem busca. Em ambos, o processamento para quando atinge `sample_size` válidos.

## Funil (`Funnel`, cumulativo)
| etapa | motivo dos descartes |
|---|---|
| `candidatos da busca` ou `lista fornecida` | — |
| `processados` | não processados: amostra completa (sample_size atingido) |
| `com GitHub Actions` | sem workflows do GitHub Actions |
| `metadados coletados` | repositório indisponível (404) |
| `>= 5 releases na janela` | menos de 5 releases não-pré-release na janela |
| `>= 50 runs válidos na janela` | menos de 50 runs válidos (push no default branch) |
| `amostra final` | — |

## CSV
Colunas do plano T8 + `n_runs_validos` e `meses_no_teto` (contadores úteis para o critério e para o teto de 1.000 runs/mês; `meses_no_teto` = meses `AAAA-MM` separados por `;`). `age_days` = dias inteiros entre `created_at` e o fim da janela. Métrica `None` → célula vazia; notas e `dora_overall` vazios (decisão 1).

## Testes (TDD, cliente fake roteando os endpoints)
1. `janela_da_config`: start 00:00:00 e end 23:59:59 UTC.
2. 3 repos fake (sem Actions / poucas releases / válido) → funil coerente e CSV com 1 linha.
3. `repos` no config → nenhuma chamada à Search API; funil começa em `lista fornecida`.
4. Para em `sample_size` válidos e registra os não processados.
5. Runs válidos < 50 → descarte no funil.
6. Repositório 404 em metadados → descarte.
7. Métrica `None` (sem episódios de recuperação) → notas e `dora_overall` vazios.
8. CSVs gravados com as colunas na ordem de `COLUNAS`.
9. `main` sem `GITHUB_TOKEN` → código de saída ≠ 0 e mensagem clara.
