# Lab03 DORA – Plano de Execução (Sprint 01 detalhada + roteiro S02/S03/Final)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Quem usa IA neste repositório: leia este arquivo inteiro e o `CLAUDE.md` antes de gerar qualquer código.**

**Goal:** Construir um pipeline reprodutível (um comando) que minera métricas DORA de repositórios open-source do GitHub e as classifica, entregue em 4 etapas (S01, S02, S03, Final).

**Architecture:** Pacote Python com um módulo por responsabilidade. `pipeline/` faz E/S (HTTP, cache, coleta); `metricas/` contém funções **puras** (sem rede) testadas com fixtures; `pipeline/__main__.py` apenas encadeia: seleção → metadados → releases/commits → runs → métricas → CSV + funil. Cada integrante é dono de arquivos distintos.

**Tech Stack:** Python 3.12, `requests`, `pyyaml`, `pandas`, `scipy`, `statsmodels`, `scikit-learn`, `matplotlib`, `pymannkendall`, `pytest`, `pytest-cov` (versões fixadas em `requirements.txt` desde a S01). **Proibido** PyGithub ou qualquer lib que consulte a API do GitHub.

**Spec:** `enunciado/03 - Mineração de Métricas DORA.md` (fonte de verdade; em caso de dúvida, ele vence este plano).

**Donos, ordem, escopo das Issues e decisões em aberto:** `docs/ISSUES.md` (fonte de verdade para isso; este plano traz contratos, restrições e detalhes técnicos das tarefas da S01).

## Global Constraints
- Token apenas em `GITHUB_TOKEN` (env); nunca commitado. Comando único: `python -m pipeline --config config.yaml`.
- Janela de observação: 12 meses, datas em `config.yaml` (`window.start`, `window.end`, com `window.end` no passado), fixadas pelo professor na abertura da S01. `config.yaml` aceita `repos: [...]` opcional (lista fixa, pula a busca).
- Só default branch; deploy = release com `draft=false`; data do commit = `commit.author.date`; CI = só runs com `event=push`.
- `conclusion`: `success` → sucesso; `failure|timed_out|startup_failure` → falha; `cancelled|skipped|neutral|action_required|stale|vazio` → **ignorar**.
- Inclusão: ≥ 5 releases e ≥ 50 runs válidos na janela; descartes entram no funil.
- Censura: contar e reportar, nunca descartar. Estatística: sempre **mediana e IQR**.
- Cache em disco com retomada; rate limit (`X-RateLimit-Remaining/Reset`) com espera; limite secundário (403/429 + `Retry-After`); 5xx com backoff exponencial 1,2,4,8s; paginação via `Link rel="next"`.
- Cobertura ≥ 80% do módulo `metricas` (`pytest --cov=metricas --cov-fail-under=80`).
- Todo commit referencia a Issue (`#N`). Mensagem: `feat(modulo): descrição (#N)`.
- Datas internas: `datetime` timezone-aware UTC. Tempos: lead time em **dias**, recuperação em **horas**, CFR em fração 0–1.

## Regras de colaboração (humanos e IAs)
1. **Cada onda pertence a um integrante (ver `docs/ISSUES.md`); o dono da onda edita os arquivos dela.** Precisa mudar arquivo de outra onda? PR pequeno avisando o autor original.
2. 1 Issue = 1 branch (`feat/N-slug`) = 1 PR curto para `main`. Assignee obrigatório. WIP: no máximo 1–2 cards "Em andamento" por pessoa.
3. **Contratos (abaixo) não mudam sem avisar os três.** Mudou? Atualize este arquivo no mesmo PR.
4. TDD: teste falhando → implementação mínima → passa → commit.
5. Cada integrante precisa ter commits de **código** em cada sprint (senão perde a parcela individual).
6. IA: não invente definições. Releia "Global Constraints". Não adicione bibliotecas de acesso à API do GitHub. Não commite tokens, `cache/` nem `data/raw/`.

## Contratos entre módulos (combinados no início)
```python
# pipeline/cache.py
class DiskCache:
    def __init__(self, root: pathlib.Path): ...
    def get(self, key: str) -> dict | list | None: ...
    def set(self, key: str, value) -> None: ...

# pipeline/http.py
class GitHubClient:
    def __init__(self, token: str, cache: DiskCache, sleep=time.sleep, max_retries: int = 5): ...
    def get(self, path: str, params: dict | None = None) -> tuple[object, dict]: ...   # (json, headers) ; 404 -> levanta NotFoundError
    def paginate(self, path: str, params: dict | None = None, item_key: str | None = None) -> list: ...

# Registros (dicts) trocados entre módulos
Release = {"tag_name": str, "published_at": datetime, "prerelease": bool, "body": str | None}
Commit  = {"sha": str, "author_date": datetime, "message": str}
Run     = {"workflow_id": int, "conclusion": str | None, "run_started_at": datetime, "updated_at": datetime}
RepoMeta= {"full_name": str, "stars": int, "language": str | None, "contributors": int | None,
           "created_at": datetime, "default_branch": str}
           # contributors = None só quando a API recusa a lista (403 "contributor list is too large"); ver #4
```

## Ordem de execução (dependências)
Ondas sequenciais, **1 onda = 1 integrante**, com rodízio entre sprints (S01: A→B→C; S02: C→A→B; S03: B→C→A; Final: A→B→C). A onda N+1 só começa quando a onda N está fechada (PRs mergeados, CI verde, nota de passagem). Detalhe de cada Issue, dono e dependência: **`docs/ISSUES.md`**.
Mapa da S01: Onda 1 (A) = T0, T1, T5, T4 · Onda 2 (B) = T6, T2, T7 · Onda 3 (C) = T3, T8 · T9 = docs livres de quem espera.

## Review Focus (casos que a spec implica e devem ter teste)
- Release sem commits novos no `compare` → lead time não calculável (ignorar, não quebrar).
- Primeira release da história (sem anterior) → ignorada no lead time.
- Falha nunca recuperada → episódio **censurado**, contado, não descartado.
- Runs `cancelled`/`skipped`/vazias → ignoradas em CFR e recuperação.
- Repositório com 1 release / 0 runs → métricas `None`, sem divisão por zero.
- `compare` retornando 404 (tag apagada) → registrar e contar; mês de runs com 1000 resultados (teto) → sinalizar.
- Release anterior à janela e pré-releases **não** contam na frequência (servem só de base para o `compare` / variantes).
- Falhas antes do primeiro sucesso da janela não abrem episódio de recuperação (contadas em `n_falhas_iniciais`).
- Lead time negativo (rebase/squash) → descartado e contado em `n_lead_negativos`.

---

# SPRINT 01 (5 pts) – 100 repositórios, testes, CI, hipóteses

### Task 0: Scaffold e CI (ver ISSUES.md)
**Files:** Create `requirements.txt`, `config.yaml`, `.gitignore`, `.github/workflows/testes.yml`, `pipeline/__init__.py`, `metricas/__init__.py`, `tests/__init__.py`, `tests/test_smoke.py`
**Produces:** repositório que roda `pytest` verde no GitHub Actions.
- [ ] Criar `requirements.txt` com versões fixadas (`requests`, `pyyaml`, `pandas`, `scipy`, `statsmodels`, `scikit-learn`, `matplotlib`, `pymannkendall`, `pytest`, `pytest-cov`) e `.gitignore` (`cache/`, `data/raw/`, `.env`, `__pycache__/`).
- [ ] `config.yaml`: `window: {start: "2025-10-01", end: "2026-09-30"}` (placeholder: substituir pelas datas do professor), `sample_size: 100`, `star_ranges: [[1000,2000],[2000,5000],[5000,20000],[20000,500000]]`, `cache_dir: cache`.
- [ ] `tests/test_smoke.py`: `def test_imports(): import pipeline, metricas`.
- [ ] Criar `.github/workflows/testes.yml` com o modelo do enunciado (checkout, setup-python 3.12, `pip install -r requirements.txt`, `pytest --cov=metricas --cov-fail-under=80`). Obs.: até existirem as métricas, usar `--cov-fail-under=0`; a volta para 80 é a Issue `S01-O3.5`.
- [ ] Run: `pytest -v` → PASS. Commit: `chore: scaffold e CI (#N)`.

### Task 1: Cache e cliente HTTP (ver ISSUES.md) — **bloqueia T5, T6, T7**
**Files:** Create `pipeline/cache.py`, `pipeline/http.py`; Test `tests/test_http.py`
**Produces:** `DiskCache`, `GitHubClient`, `NotFoundError` conforme contratos.
- [ ] Teste: cache hit não chama a rede; `set`/`get` persistem em arquivo (JSON, nome = sha1 da chave).
- [ ] Teste: resposta 5xx é repetida com esperas 1,2,4 (injetar `sleep` falso e verificar a lista de esperas); após `max_retries` levanta erro.
- [ ] Teste: `X-RateLimit-Remaining: 0` + `X-RateLimit-Reset` futuro → chama `sleep` com a diferença; 403/429 com `Retry-After` → espera e repete; 404 → `NotFoundError`; respostas de erro não entram no cache.
- [ ] Teste: `paginate` segue `Link rel="next"` até o fim e concatena (use `item_key` para endpoints que embrulham em `{"total_count":..,"workflow_runs":[..]}`).
- [ ] Implementar com `requests.Session`, header `Authorization: Bearer $GITHUB_TOKEN`, chave de cache = `url+params ordenados`. Testar com `requests` mockado manualmente (classe fake de sessão), sem rede.
- [ ] Run: `pytest tests/test_http.py -v` → PASS. Commit: `feat(http): cliente com cache, rate limit e backoff (#N)`.
- Entrega rápida: se demorar, publicar primeiro só `get`/`paginate` sem rate limit para destravar a Onda 2.

### Task 2: Lead time (ver ISSUES.md)
**Files:** Create `metricas/lead_time.py`; Test `tests/test_lead_time.py`
**Produces:**
```python
def lead_time_release_days(release_date: datetime, commit_dates: list[datetime]) -> float | None
def lead_time_commits_days(release_date: datetime, commit_dates: list[datetime]) -> list[float]
def repo_lead_time_a(per_release: list[float | None]) -> float | None   # mediana ignorando None
def repo_lead_time_b(all_commit_values: list[float]) -> float | None    # mediana
```
- [ ] Testes (exemplo do enunciado, v1.1 em 15/03 com commits 02/03, 10/03, 14/03): (a) = 13; (b) = [13,5,1]; lista vazia → `None`/`[]`; mediana entre releases.
- [ ] Implementar: (a) = `(release_date - min(commit_dates)).total_seconds()/86400`; (b) lista análoga; medianas com `statistics.median`.
- [ ] Run → PASS. Commit: `feat(metricas): lead time por release e por commit (#N)`.

### Task 3: CFR (a) e recuperação (ver ISSUES.md)
**Files:** Create `metricas/cfr.py`, `metricas/recuperacao.py`; Test `tests/test_cfr.py`, `tests/test_recuperacao.py`
**Produces:**
```python
def classify_conclusion(c: str | None) -> str | None   # "success" | "failure" | None (ignorar)
def cfr_ci(runs: list[dict]) -> float | None            # falhas / (falhas+sucessos)
def recovery_episodes(runs: list[dict]) -> tuple[list[float], int]  # (horas por episódio recuperado, nº censurados) para UM workflow
def repo_recovery(runs: list[dict]) -> tuple[float | None, int, int]  # (mediana h, nº episódios, nº censurados) agrupando por workflow_id
```
- [ ] Testes CFR: 3 success+1 failure → 0,25; `cancelled`/`skipped`/`None` ignorados; sem runs válidos → `None`.
- [ ] Testes recuperação (tabela do enunciado: success 09:00, failure 10:00, failure 10:30, success 11:15 com `updated_at` 11:20) → `[1.3333]`, 0 censurados; falha sem sucesso posterior → `([], 1)`; dois workflows independentes não se misturam; runs `cancelled` entre falha e sucesso não encerram nem iniciam episódio.
- [ ] Implementar: ordenar por `run_started_at`; filtrar `classify_conclusion` ≠ None; episódio abre na 1ª falha após sucesso (ou falha inicial) e fecha no próximo sucesso (`updated_at − run_started_at` da 1ª falha, em horas).
- [ ] Run → PASS. Commit: `feat(metricas): CFR(a) e tempo de recuperação (#N)`.

### Task 4: Classificação DORA (ver ISSUES.md)
**Files:** Create `metricas/classificacao.py`; Test `tests/test_classificacao.py`
**Produces:**
```python
def score_deploy_freq(per_week: float) -> int    # >=7:4, >=1:3, >=1/4.345 (≈1/mês):2, senão 1
def score_lead_time(days: float) -> int          # <1:4, <7:3, <30:2, senão 1
def score_cfr(rate: float) -> int                # <=.15:4, <=.30:3, <=.45:2, senão 1
def score_recovery(hours: float) -> int          # <1:4, <24:3, <168:2, senão 1
def overall(scores: list[int]) -> str            # mediana arredondada p/ baixo -> "Elite|High|Medium|Low"
def classificar_repositorio(deploy_freq_week, lead_time_a_days, cfr_ci, recovery_median_h) -> dict
    # chaves score_freq, score_lead, score_cfr, score_rec, dora_overall; qualquer métrica None -> tudo None
```
- [ ] Testes nos limites de cada faixa (6,99 vs 7 por semana; 0,15 vs 0,1501; 24h exatas) e `overall([4,3,3,1]) == "High"`, `overall([4,4,1,1]) == "Medium"` (mediana 2,5 → 2).
- [ ] Teste de `classificar_repositorio` com métrica `None`. Implementar e rodar. Commit: `feat(metricas): classificação DORA (#N)`.

### Task 5: Seleção, funil e metadados (ver ISSUES.md) — depende de T1
**Files:** Create `pipeline/selecao.py`, `pipeline/metadados.py`, `pipeline/funil.py`; Test `tests/test_selecao.py`, `tests/test_metadados.py`
**Produces:**
```python
def search_candidates(client, star_ranges: list[list[int]], per_range_limit: int = 1000) -> list[str]  # full_names únicos, fork:false archived:false, embaralhados com random_state=42
def uses_actions(client, full_name: str) -> bool                       # total_count > 0
def collect_metadata(client, full_name: str) -> RepoMeta
class Funnel:  # em pipeline/funil.py; add(stage: str, remaining: int, reason: str = ""); to_dataframe() -> DataFrame
```
- [ ] Testes com cliente fake: faixas de estrelas fatiam a busca (`stars:1000..2000`), duplicatas removidas; `total_count=0` → `False`; contributors lido do `Link` last page (`per_page=1&anon=true`); `Funnel.to_dataframe()` tem colunas `etapa,restantes,descartados,motivo`.
- [ ] Implementar e rodar. Commit: `feat(selecao): candidatos, filtro Actions, metadados e funil (#N)`.

### Task 6: Releases e commits entre releases (ver ISSUES.md) — depende de T1
**Files:** Create `pipeline/releases.py`; Test `tests/test_releases.py`
**Produces:**
```python
def fetch_releases(client, full_name: str, start: datetime, end: datetime) -> list[Release]   # draft=False, ordenadas por published_at; inclui a release não-pré-release imediatamente anterior à janela (base do compare)
def fetch_commits(client, full_name: str, base_tag: str, head_tag: str) -> list[Commit] | None   # None se 404 (registrar); paginado; author.date + message
```
- [ ] Testes: draft descartado; pré-releases mantidas com `prerelease=True` (para RQ07); 404 do compare → `None`; paginação do compare >250 commits concatena páginas; mensagens de commit presentes; repo com uma única release.
- [ ] Implementar e rodar. Commit: `feat(releases): coleta de releases e commits (#N)`.

### Task 7: Workflow runs por mês (ver ISSUES.md) — depende de T1
**Files:** Create `pipeline/runs.py`; Test `tests/test_runs.py`
**Produces:** `def fetch_runs(client, full_name: str, branch: str, start: datetime, end: datetime) -> tuple[list[Run], list[str]]` (runs, meses que atingiram o teto de 1.000).
- [ ] Testes: janela de 12 meses vira 12 consultas `created=AAAA-MM-DD..AAAA-MM-DD` com `event=push`; mês com 1000 resultados entra na lista de teto; campos mapeados para o contrato `Run`.
- [ ] Implementar e rodar. Commit: `feat(runs): coleta mensal de workflow runs (#N)`.

### Task 8: Orquestração, funil e CSV (ver ISSUES.md: Onda 3 da S01)
**Files:** Create `pipeline/__main__.py`, `pipeline/orquestrador.py`; Test `tests/test_orquestrador.py`
- [ ] Teste de integração com cliente fake: 3 repos (1 sem Actions, 1 com <5 releases, 1 válido) → funil com 3 linhas coerentes e CSV com 1 linha.
- [ ] Implementar: lê `config.yaml` (com `repos` opcional, que pula a busca), cria `DiskCache`/`GitHubClient`, executa seleção → filtro Actions → metadados → releases → runs → critério (≥5 releases, ≥50 runs válidos) → métricas → grava `data/funil.csv` e `data/metricas.csv` (colunas: `repo, stars, language, contributors, age_days, n_releases, deploy_freq_week, lead_time_a_days, lead_time_b_days, cfr_ci, recovery_median_h, n_episodes, n_censored, n_falhas_iniciais, n_lead_negativos, compare_404, score_freq, score_lead, score_cfr, score_rec, dora_overall`; repositório com alguma métrica `None` fica com notas e `dora_overall` vazios).
- [ ] Reexecutar o comando duas vezes: a segunda deve ser quase instantânea (cache). Commit: `feat(pipeline): orquestração, funil e CSV (#N)`.

### Task 9: README e introdução do artigo (os três)
**Files:** Create `README.md`, `artigo/introducao.md`
- [ ] README: pré-requisitos, `export GITHUB_TOKEN=...`, `pip install -r requirements.txt`, `python -m pipeline --config config.yaml`, como rodar testes/cobertura, onde ficam saídas. (Outro grupo vai replicar só com isso.)
- [ ] Introdução no **template SBC (Overleaf)**: uma hipótese informal por RQ01–RQ07 (e RQ08, se houver bônus), **escrita antes de olhar os dados**; divisão em `docs/ISSUES.md` (S01-D1 a D3).
- [ ] Commit: `docs: README e hipóteses (#N)`.

### Execução real e conferência
Ver `S01-O3.6` e o portão `S01-G` em `docs/ISSUES.md`.

---

# Próximas sprints
S02, S03 e Entrega Final estão detalhadas (donos por onda, dependências, arquivos) em **`docs/ISSUES.md`**. Detalhar um plano técnico como este ao abrir cada sprint.

## Self-Review
- Cobertura da spec: seleção/funil (T5, T8), releases/commits/runs (T6, T7), cache/rate limit (T1), lead time (T2), CFR(a)/recuperação (T3), classificação (T4), CI (T0), hipóteses (T9). CFR(b), heurística, validação manual, variantes da RQ07, RQ05–RQ08, replicação: `docs/ISSUES.md`.
- Gap conhecido: datas da janela dependem do professor (T0 usa placeholder).
- Consistência de nomes: `Release/Run/RepoMeta`, `GitHubClient.get/paginate`, `fetch_*` usados igualmente nos contratos e tarefas.

