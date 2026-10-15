# S02-O1.3 — Consolidação do dataset e dicionário (#25) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task (execução inline nesta sessão). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ler as saídas do pipeline (`data/metricas.csv`, `data/funil.csv`), validar a integridade do dataset, acrescentar colunas derivadas, regravar `data/metricas.csv` como dataset final documentado e gerar `data/elegiveis_sorteio.csv` para o sorteio da amostra-ouro, sem chamar a API.

**Architecture:** Novo módulo `pipeline/consolidar.py` com funções puras sobre `DataFrame` (`validar`, `derivar_colunas`, `elegiveis_sorteio`) e uma função de E/S (`consolidar(dados, cfg)`), executável por `python -m pipeline.consolidar --config config.yaml` e chamada automaticamente no fim de `python -m pipeline`. A ordem final das colunas (`COLUNAS_FINAIS = COLUNAS + COLUNAS_DERIVADAS`) é a ordem da tabela de `data/DICIONARIO.md`, verificada por teste.

**Tech Stack:** Python 3.12, pandas, pyyaml, pytest (sem dependência nova).

**Spec:** Issue #25; `docs/ISSUES.md` (S02-O1.3 e S02-O3.5); `docs/superpowers/plans/2026-10-05-lab03-dora-pipeline.md`; `enunciado/03 - Mineração de Métricas DORA.md` §3, §6, §7.

## Global Constraints
- Sem acesso à API do GitHub na consolidação (só lê CSVs e `config.yaml`).
- Inclusão: ≥ 5 releases e ≥ 50 runs válidos na janela (`MIN_RELEASES`, `MIN_RUNS_VALIDOS` de `pipeline/orquestrador.py`).
- Unidades: lead time em dias, recuperação em horas, CFR fração 0–1, frequência por semana (semanas = dias da janela ÷ 7, `semanas_da_janela`).
- Censura: contar e reportar (proporção de episódios censurados por repositório, enunciado §5 RQ04).
- Sorteio da amostra-ouro: 60 repositórios **da amostra final**, `df.sample(n=60, random_state=42)` (enunciado §6.1).
- Toda coluna dos CSVs finais no dicionário com nome, tipo, unidade, fórmula/origem (enunciado §7).
- Janela: 2025-10-01 a 2026-09-30, escolhida pelo grupo (o professor aceita qualquer período de 12 meses), lida de `config.yaml`.

## Decisões (registradas também no PR)
1. **Papel do `consolidar.py`:** o orquestrador continua gravando `data/metricas.csv` e `data/funil.csv`; a consolidação lê os dois, valida e **regrava `data/metricas.csv` no lugar** com as colunas derivadas no fim. É idempotente: colunas derivadas já presentes são descartadas e recalculadas. Se a validação falhar, nada é gravado e o erro lista todos os problemas (`DatasetInvalido`).
2. **Comando:** `python -m pipeline.consolidar --config config.yaml` (sem token, sem rede); também roda automaticamente no fim de `python -m pipeline` (sai com código 2 se o dataset for inválido, mantendo os CSVs brutos do orquestrador para inspeção).
3. **Colunas derivadas (S02-O1.3):** `prop_censurados = n_censored / n_episodes` (vazio se `n_episodes = 0`), exigida pelo enunciado (RQ04: "reporte a proporção de episódios censurados por repositório"); `n_meses_no_teto` = nº de meses em `meses_no_teto` (filtro de sensibilidade para runs possivelmente incompletos). Quartis da RQ06 ficam para a S03 (análise), fora do escopo.
4. **Ponto de extensão para a S02-O3.5 (#36):** lista `COLUNAS_DERIVADAS` + função `derivar_colunas(metricas, extras=None)`. A #36 acrescenta `cfr_entrega`, `rework_rate`, `tipo_projeto` em `COLUNAS_DERIVADAS`, calcula-as em `derivar_colunas` (os dados externos, como `rotulos/consenso.csv`, entram por `extras`) e documenta no dicionário; o teste que compara `COLUNAS_FINAIS` com o dicionário obriga a documentação.
5. **Elegíveis para o sorteio:** `data/elegiveis_sorteio.csv` = **toda a amostra final** consolidada (o enunciado manda sortear "da amostra final"; todos têm ≥ 5 releases na janela, então dá para sortear 5 releases por repositório), **ordenada por `repo`**, com `repo`, `url_releases`, `n_releases`. A ordem alfabética torna `df.sample(n=60, random_state=42)` independente da ordem de coleta e das colunas que a #36 acrescentar. A S02-O2.2 deve sortear sobre esse arquivo.
6. **Checagens de integridade (`validar`)**: colunas do orquestrador presentes na ordem; `repo` não vazio e sem duplicatas; critério de inclusão; funil fecha (`descartados` = diferença, `restantes` não cresce, `amostra final` = nº de linhas); faixas (`cfr_ci` em [0,1], lead times/recuperação/frequências ≥ 0, scores em 1..4, `dora_overall` em Elite/High/Medium/Low/vazio); `n_censored ≤ n_episodes`; `n_releases_pre ≥ n_releases`; `teto_compare_pre ≤ n_releases_pre`, `teto_compare_tag ≤ n_tags`; frequência = contagem ÷ semanas da janela (tolerância 1e-6) para as 3 unidades; `dora_overall` vazio sse alguma das 4 métricas for ausente.

## Review Focus
- Rodar a consolidação duas vezes → mesmo arquivo (idempotência; derivadas não duplicam).
- `n_episodes = 0` → `prop_censurados` vazio, sem divisão por zero.
- CSV antigo sem as colunas das variantes → erro claro listando as colunas ausentes, nada é gravado.
- Repositório duplicado (retomada mal feita) → erro, não silencioso.
- Coluna nova sem documentação no dicionário → teste falha.

---

### Task 1: `validar` — estrutura, unicidade e inclusão

**Files:** Create `pipeline/consolidar.py`; Test `tests/test_consolidar.py`

**Interfaces — Produces:**
```python
class DatasetInvalido(ValueError): problemas: list[str]
def validar(metricas: pd.DataFrame, funil: pd.DataFrame, semanas: float) -> list[str]
```

- [ ] Fixture `linha(**kw)` com um repositório válido (todas as colunas de `COLUNAS`, 5 releases em 52,14 semanas etc.) e `funil_de(n)` coerente; `test_dataset_valido_nao_tem_problemas`.
- [ ] Testes: coluna ausente (`n_tags`) → problema citando a coluna; repo duplicado → problema citando o repo; `n_releases=4` → problema; `n_runs_validos=49` → problema.
- [ ] Implementar e commitar `test(consolidar)` / `feat(consolidar)`.

### Task 2: `validar` — faixas, consistência e funil

- [ ] Testes: `cfr_ci=1.2`; `lead_time_a_days=-1`; `n_censored > n_episodes`; `score_freq=5`; `dora_overall="Top"`; `dora_overall` preenchido com `recovery_median_h` vazio; `n_releases_pre < n_releases`; `teto_compare_tag > n_tags`; `deploy_freq_week` incoerente com `n_releases`; funil cuja `amostra final` ≠ nº de linhas; funil com `descartados` errado.
- [ ] Implementar; commit.

### Task 3: `derivar_colunas`, `COLUNAS_FINAIS` e dicionário

**Interfaces — Produces:**
```python
COLUNAS_DERIVADAS: list[str] = ["prop_censurados", "n_meses_no_teto"]
COLUNAS_FINAIS: list[str] = COLUNAS + COLUNAS_DERIVADAS
def derivar_colunas(metricas: pd.DataFrame, extras: dict | None = None) -> pd.DataFrame
```
- [ ] Testes: `prop_censurados` (1 de 4 → 0,25; 0 episódios → NaN); `n_meses_no_teto` (`"2025-11;2026-01"` → 2, vazio → 0); idempotência (derivar duas vezes = uma); colunas na ordem `COLUNAS_FINAIS`; `COLUNAS_FINAIS` igual à lista de colunas da tabela `data/metricas.csv` em `data/DICIONARIO.md`.
- [ ] Implementar, atualizar `data/DICIONARIO.md` (derivadas, janela, consolidação); commit.

### Task 4: `elegiveis_sorteio`

```python
def elegiveis_sorteio(metricas: pd.DataFrame) -> pd.DataFrame  # colunas repo, url_releases, n_releases; ordenado por repo
```
- [ ] Testes: todos os repos da amostra entram; ordem alfabética; URL `https://github.com/{repo}/releases`; sorteio reprodutível independe da ordem de entrada.
- [ ] Implementar; documentar `data/elegiveis_sorteio.csv` no dicionário; commit.

### Task 5: `consolidar` (E/S), CLI e integração com `python -m pipeline`

```python
def consolidar(dados: pathlib.Path, cfg: dict) -> pd.DataFrame  # levanta DatasetInvalido; grava metricas.csv e elegiveis_sorteio.csv
def main(argv: list[str] | None = None) -> int                 # python -m pipeline.consolidar --config config.yaml [--dados data]
```
- [ ] Testes (tmp_path): grava `metricas.csv` com `COLUNAS_FINAIS` e `elegiveis_sorteio.csv`; segunda execução produz arquivo idêntico; dataset inválido levanta `DatasetInvalido` e não altera o arquivo; inteiros continuam sem `.0`; `main` devolve 0/2 e imprime os problemas; `pipeline.__main__.main` chama a consolidação após `executar` (executar falso via monkeypatch) e devolve 2 se inválido.
- [ ] Implementar `pipeline/consolidar.py:main`, `if __name__ == "__main__"` e a chamada em `pipeline/__main__.py`; README (seção Saídas + janela); commit.

### Task 6: Verificação
- [x] `pytest --cov=metricas --cov-report=term-missing` verde, metricas ≥ 80%.

## Registro da execução (2026-10-15)
- Tasks 1–5 executadas em TDD; 312 testes verdes, `metricas` 100%, `pipeline/consolidar.py` 99% (só o `sys.exit` do `__main__`).
- Desvio: `validar` também acusa `n_releases`/`n_runs_validos` **vazios** (antes passavam silenciosamente pelo critério de inclusão); teste `test_contagem_do_criterio_vazia_e_problema`.
- README também foi alterado (seções Janela, Saídas e Consolidação), por pedido do dono da Issue.
- Conferência sem rede: `data/metricas.csv` da S02 (300 repos, ainda sem as colunas das variantes) é recusado com a lista das 12 colunas ausentes; com as variantes simuladas, os 300 repositórios passam em todas as demais checagens.
- Retomada após o merge do PR #82 (#81) na `main`: merge de `origin/main` (sem conflito; `commits_omitidos_tag` e `erro_tags` já estavam no dicionário na ordem de `COLUNAS_FINAIS`). `validar` ganhou `_variante_tag`: `erro_tags` ∈ {0, 1} (vazio é problema); `erro_tags = 1` ⇒ todas as `COLUNAS_TAG` vazias; `erro_tags = 0` ⇒ `COLUNAS_TAG` preenchidas, exceto `lead_time_b_days_tag` (pode faltar sem compare utilizável). Daí `commits_omitidos_tag` vazio ⇔ `erro_tags = 1`. As regras de frequência e de teto da unidade tag já ignoravam vazios (teste `test_variante_tag_ausente_por_erro_e_valida`). Suíte: 348 testes, `metricas` 100%.
- Os dados finais (com as variantes, coleta da #24 em andamento) são gerados com `python -m pipeline.consolidar --config config.yaml` e commitados neste mesmo PR pelo dono da Issue.
