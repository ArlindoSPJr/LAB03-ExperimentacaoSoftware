# Issue #3 (S01-O1.3) — Seleção de candidatos e filtro de Actions — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task (execução inline, sem worktree). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar `search_candidates` (busca fatiada por faixas de estrelas, `fork:false archived:false`, sem duplicatas, no máximo 1.000 por consulta, saída embaralhada com `random_state=42`) e `uses_actions` (`total_count > 0` em `/actions/workflows`), testadas sem rede.

**Architecture:** Um único módulo `pipeline/selecao.py` que só conversa com o `GitHubClient` da Issue #2 (`get`/`paginate`). Para cada faixa `[lo, hi]` é feita uma consulta `stars:lo..hi fork:false archived:false` na Search API via `client.paginate(..., item_key="items")`; os `full_name` são truncados ao limite da faixa, deduplicados, ordenados alfabeticamente e embaralhados com `random.Random(42)`. `uses_actions` faz um `client.get` com `per_page=1` e lê `total_count`. Os testes usam um cliente fake que registra as chamadas.

**Tech Stack:** Python 3.12 (CI) / 3.13 (local), stdlib (`random`, `logging`), `pytest==8.3.3`. Nenhuma dependência nova.

**Spec:** Issue #3; `docs/ISSUES.md` (S01-O1.3 e "Decisões a confirmar", item 2); `docs/superpowers/plans/2026-10-05-lab03-dora-pipeline.md` (Contratos, Global Constraints, Task 5); `enunciado/03 - Mineração de Métricas DORA.md` (tabela de endpoints: Search API com teto de 1.000 resultados por consulta, fatiamento por faixas de estrelas; armadilha `total_count = 0`).

## Global Constraints
- Proibido PyGithub ou qualquer lib de acesso à API do GitHub; só o `GitHubClient` próprio (`requests` direto).
- Testes nunca acessam a rede nem usam token real.
- Contratos (nomes exatos, plano geral Task 5):
  - `search_candidates(client, star_ranges: list[list[int]], per_range_limit: int = 1000) -> list[str]` — full_names únicos, `fork:false archived:false`, embaralhados com `random_state=42`.
  - `uses_actions(client, full_name: str) -> bool` — `total_count > 0`.
- Consome (Issue #2, não alterar): `GitHubClient.get(path, params=None) -> (json, headers)`, `GitHubClient.paginate(path, params=None, item_key=None) -> list` (acrescenta `per_page=100`), `NotFoundError`.
- Search API: no máximo 1.000 resultados por consulta; fatiar por faixas de estrelas (`stars:1000..2000`).
- Arquivos: apenas `pipeline/selecao.py`, `tests/test_selecao.py` (+ este plano).
- Commits `tipo(modulo): descrição (#3)`, sem linha de co-autoria; nunca commitar `__pycache__`/`.pyc`/`cache/`.

## Decisão do grupo envolvida (decisão 2 de `docs/ISSUES.md`)
"Amostragem: busca com `fork:false archived:false`; candidatos embaralhados com `random_state=42` e processados em ordem até atingir N válidos." A Issue e o plano geral já especificam exatamente esse comportamento, então ele é implementado como está escrito (não há escolha em aberto para esta Issue). Continua pendente apenas a confirmação formal do grupo e o registro na Metodologia; se o grupo mudar a decisão, basta alterar a query/semente neste módulo. O "processar em ordem até N válidos" é do orquestrador (S01-O3.4), não desta Issue.

## Decisões internas (pequenas, reversíveis; registrar no PR)
1. **Embaralhamento:** `random.Random(42).shuffle` sobre a lista **ordenada alfabeticamente**. Ordenar antes torna o resultado independente da ordem em que a API devolve os itens (o "best match" da Search API não é estável), então a mesma coleção de candidatos sempre gera a mesma ordem. Semente exposta como constante `RANDOM_STATE = 42`.
2. **Query:** `q = "stars:{lo}..{hi} fork:false archived:false"`, sem `sort` (ordem padrão da API); a ordem final vem do embaralhamento.
3. **Teto de 1.000:** o limite efetivo por faixa é `min(per_range_limit, 1000)`. Se a faixa devolver 1.000 itens, registra `logging.warning` dizendo que a faixa pode estar saturada (convém fatiá-la mais). Sem erro.
4. **Faixas sobrepostas** (ex.: `[1000,2000]` e `[2000,5000]` incluem 2000 nas duas): duplicatas removidas pelo `full_name`.
5. **Validação:** faixa com `lo > hi`, faixa sem exatamente 2 valores ou `per_range_limit < 1` → `ValueError`. Lista de faixas vazia → `[]`.
6. **`uses_actions`:** `GET /repos/{full_name}/actions/workflows` com `per_page=1` (só precisamos do `total_count`). Corpo sem `total_count` → `False`. `NotFoundError` (repo apagado/renomeado entre a busca e o filtro) **é propagada**: não é "sem Actions", e o orquestrador decide como contar no funil.

## Review Focus
- Mesmo repositório em duas faixas com limite compartilhado (ex.: 2000 estrelas) → aparece uma vez só.
- Faixa que retorna 1.000 itens (teto da API) → não passa de 1.000 e emite aviso de saturação.
- Mesma coleção de candidatos devolvida em outra ordem pela API → mesma lista final (reprodutibilidade).
- Faixa sem resultados / lista de faixas vazia → não quebra.
- Repositório inexistente no filtro de Actions (404) → `NotFoundError` propagada, não `False` silencioso.

---

### Task 1: `search_candidates`

**Files:**
- Create: `pipeline/selecao.py`
- Test: `tests/test_selecao.py`

**Interfaces:**
- Consumes: `client.paginate(path: str, params: dict | None = None, item_key: str | None = None) -> list`
- Produces: `search_candidates(client, star_ranges: list[list[int]], per_range_limit: int = 1000) -> list[str]`; constantes `SEARCH_MAX = 1000`, `RANDOM_STATE = 42`.

Cliente fake (no topo de `tests/test_selecao.py`):

```python
class FakeClient:
    """Cliente fake: devolve respostas pré-definidas por (path, q) e registra as chamadas."""

    def __init__(self, search=None, gets=None):
        self.search = search or {}   # q -> lista de itens da Search API
        self.gets = gets or {}       # path -> json (ou exceção)
        self.paginate_calls = []
        self.get_calls = []

    def paginate(self, path, params=None, item_key=None):
        self.paginate_calls.append((path, dict(params or {}), item_key))
        return list(self.search.get(params["q"], []))

    def get(self, path, params=None):
        self.get_calls.append((path, dict(params or {})))
        resp = self.gets[path]
        if isinstance(resp, Exception):
            raise resp
        return resp, {}


def repos(*names):
    return [{"full_name": n} for n in names]


def q(lo, hi):
    return f"stars:{lo}..{hi} fork:false archived:false"
```

- [ ] **Step 1: Teste — uma consulta por faixa, com a query certa e `item_key="items"`**

```python
def test_search_uma_consulta_por_faixa_com_filtros():
    client = FakeClient(search={q(1000, 2000): repos("a/x"), q(2000, 5000): repos("b/y")})
    search_candidates(client, [[1000, 2000], [2000, 5000]])
    assert client.paginate_calls == [
        ("/search/repositories", {"q": q(1000, 2000)}, "items"),
        ("/search/repositories", {"q": q(2000, 5000)}, "items"),
    ]
```

- [ ] **Step 2:** `pytest tests/test_selecao.py::test_search_uma_consulta_por_faixa_com_filtros -v` → FAIL (`ModuleNotFoundError: pipeline.selecao`).
- [ ] **Step 3: Implementação mínima**

```python
"""Seleção de repositórios candidatos (Search API) e filtro de GitHub Actions."""
from __future__ import annotations

SEARCH_PATH = "/search/repositories"


def _query(lo: int, hi: int) -> str:
    return f"stars:{lo}..{hi} fork:false archived:false"


def search_candidates(client, star_ranges: list[list[int]], per_range_limit: int = 1000) -> list[str]:
    names = []
    for lo, hi in star_ranges:
        items = client.paginate(SEARCH_PATH, {"q": _query(lo, hi)}, item_key="items")
        names.extend(item["full_name"] for item in items)
    return names
```

- [ ] **Step 4:** rodar o teste → PASS. **Step 5:** commit `feat(selecao): busca fatiada por faixas de estrelas (#3)`.

- [ ] **Step 6: Teste — duplicatas removidas (faixas sobrepostas)**

```python
def test_search_remove_duplicatas_entre_faixas():
    client = FakeClient(search={
        q(1000, 2000): repos("a/x", "c/borda"),
        q(2000, 5000): repos("c/borda", "b/y"),
    })
    nomes = search_candidates(client, [[1000, 2000], [2000, 5000]])
    assert sorted(nomes) == ["a/x", "b/y", "c/borda"]
    assert len(nomes) == 3
```

- [ ] **Step 7: Teste — limite por faixa e teto de 1.000**

```python
def test_search_trunca_no_limite_por_faixa():
    client = FakeClient(search={q(1, 2): repos("a/1", "a/2", "a/3"), q(3, 4): repos("b/1", "b/2")})
    nomes = search_candidates(client, [[1, 2], [3, 4]], per_range_limit=2)
    assert sorted(nomes) == ["a/1", "a/2", "b/1", "b/2"]


def test_search_nunca_passa_de_1000_por_consulta_e_avisa_saturacao(caplog):
    itens = repos(*[f"o/r{i}" for i in range(1005)])
    client = FakeClient(search={q(1, 2): itens})
    with caplog.at_level("WARNING"):
        nomes = search_candidates(client, [[1, 2]], per_range_limit=5000)
    assert len(nomes) == 1000
    assert "stars:1..2" in caplog.text
```

- [ ] **Step 8: Teste — embaralhamento reproduzível e independente da ordem da API**

```python
def test_search_embaralha_com_random_state_42():
    nomes = [f"o/r{i:02d}" for i in range(20)]
    client = FakeClient(search={q(1, 2): repos(*nomes)})
    resultado = search_candidates(client, [[1, 2]])
    esperado = sorted(nomes)
    random.Random(42).shuffle(esperado)
    assert resultado == esperado
    assert resultado != sorted(nomes)


def test_search_mesma_colecao_em_outra_ordem_gera_mesma_lista():
    nomes = [f"o/r{i:02d}" for i in range(20)]
    a = search_candidates(FakeClient(search={q(1, 2): repos(*nomes)}), [[1, 2]])
    b = search_candidates(FakeClient(search={q(1, 2): repos(*reversed(nomes))}), [[1, 2]])
    assert a == b
```

- [ ] **Step 9: Teste — bordas e validação**

```python
def test_search_sem_faixas_ou_faixa_vazia():
    assert search_candidates(FakeClient(), []) == []
    assert search_candidates(FakeClient(), [[1, 2]]) == []


@pytest.mark.parametrize("faixas, limite", [([[5, 1]], 1000), ([[1]], 1000), ([[1, 2]], 0)])
def test_search_parametros_invalidos(faixas, limite):
    with pytest.raises(ValueError):
        search_candidates(FakeClient(), faixas, per_range_limit=limite)
```

- [ ] **Step 10:** rodar os testes novos → FAIL (duplicatas, truncamento, embaralhamento e validação não existem).
- [ ] **Step 11: Implementação completa**

```python
"""Seleção de repositórios candidatos (Search API) e filtro de GitHub Actions.

Decisão 2 de docs/ISSUES.md: busca com fork:false archived:false; candidatos
embaralhados com random_state=42 (amostra reproduzível e não enviesada para os
mais populares).
"""
from __future__ import annotations

import logging
import random

log = logging.getLogger(__name__)

SEARCH_PATH = "/search/repositories"
SEARCH_MAX = 1000  # teto da Search API por consulta
RANDOM_STATE = 42


def _query(lo: int, hi: int) -> str:
    return f"stars:{lo}..{hi} fork:false archived:false"


def search_candidates(client, star_ranges: list[list[int]], per_range_limit: int = 1000) -> list[str]:
    """full_names únicos das faixas de estrelas, embaralhados com random_state=42.

    Cada faixa [lo, hi] vira uma consulta `stars:lo..hi fork:false archived:false`
    limitada a min(per_range_limit, 1000) resultados. A lista é ordenada antes do
    embaralhamento, para não depender da ordem devolvida pela API.
    """
    if per_range_limit < 1:
        raise ValueError("per_range_limit precisa ser >= 1")
    limit = min(per_range_limit, SEARCH_MAX)
    unique: set[str] = set()
    for star_range in star_ranges:
        if len(star_range) != 2 or star_range[0] > star_range[1]:
            raise ValueError(f"faixa de estrelas inválida: {star_range!r}")
        lo, hi = star_range
        query = _query(lo, hi)
        items = client.paginate(SEARCH_PATH, {"q": query}, item_key="items")
        if len(items) >= SEARCH_MAX:
            log.warning("faixa %r atingiu o teto de %d resultados; considere fatiá-la", query, SEARCH_MAX)
        unique.update(item["full_name"] for item in items[:limit])
    names = sorted(unique)
    random.Random(RANDOM_STATE).shuffle(names)
    return names
```

- [ ] **Step 12:** `pytest tests/test_selecao.py -v` → PASS. **Step 13:** commit `feat(selecao): candidatos unicos, teto de 1000 e embaralhamento com random_state=42 (#3)` (pode ser dividido em mais de um commit, um por ciclo).

### Task 2: `uses_actions`

**Files:**
- Modify: `pipeline/selecao.py`
- Test: `tests/test_selecao.py`

**Interfaces:**
- Consumes: `client.get(path: str, params: dict | None = None) -> tuple[object, dict]`; `pipeline.http.NotFoundError`.
- Produces: `uses_actions(client, full_name: str) -> bool`.

- [ ] **Step 1: Testes**

```python
WF = "/repos/o/r/actions/workflows"


def test_uses_actions_true_quando_ha_workflows():
    client = FakeClient(gets={WF: {"total_count": 3, "workflows": [{}]}})
    assert uses_actions(client, "o/r") is True
    assert client.get_calls == [(WF, {"per_page": 1})]


def test_uses_actions_false_com_total_count_zero():
    assert uses_actions(FakeClient(gets={WF: {"total_count": 0, "workflows": []}}), "o/r") is False


def test_uses_actions_false_sem_total_count():
    assert uses_actions(FakeClient(gets={WF: {}}), "o/r") is False
    assert uses_actions(FakeClient(gets={WF: None}), "o/r") is False


def test_uses_actions_propaga_404():
    client = FakeClient(gets={WF: NotFoundError(404, WF, "Not Found")})
    with pytest.raises(NotFoundError):
        uses_actions(client, "o/r")
```

- [ ] **Step 2:** rodar → FAIL (`ImportError: uses_actions`).
- [ ] **Step 3: Implementação**

```python
def uses_actions(client, full_name: str) -> bool:
    """True se o repositório tem ao menos um workflow (total_count > 0).

    NotFoundError (repositório apagado/renomeado) é propagada para o chamador.
    """
    data, _ = client.get(f"/repos/{full_name}/actions/workflows", {"per_page": 1})
    return int((data or {}).get("total_count", 0)) > 0
```

- [ ] **Step 4:** rodar → PASS. **Step 5:** commit `feat(selecao): filtro de repositorios com GitHub Actions (#3)`.

### Task 3: Verificação final
- [ ] `pytest --cov=metricas --cov-report=term-missing --cov-fail-under=0` (mesmo comando do CI) → tudo verde.
- [ ] `git status --porcelain` sem `__pycache__`/`.pyc`; `git log main..` com `(#3)` em todos os commits.
