# Issue #2 (S01-O1.2) — Cache em disco e cliente HTTP — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task (execução inline, sem worktree). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar `DiskCache`, `GitHubClient` (`get`/`paginate`) e `NotFoundError`, com cache em disco (retomada), rate limit primário e secundário, backoff exponencial em 5xx e paginação por `Link rel="next"`, todos testados sem rede.

**Architecture:** `pipeline/cache.py` guarda um JSON por chave (nome = sha1 da chave) com escrita atômica. `pipeline/http.py` usa `requests.Session`; `get` consulta o cache antes da rede e só grava respostas 2xx (corpo + cabeçalhos, para que `paginate` e a contagem de contribuidores funcionem também em cache hit). Um laço único de tentativas trata 5xx/erro de rede (backoff `2**tentativa`), 403/429 de rate limit (espera e repete) e 404 (`NotFoundError`). `sleep` e o relógio (`client.clock`) são injetáveis; os testes trocam `client.session` por uma sessão fake.

**Tech Stack:** Python 3.12 (CI) / 3.13 (local), `requests==2.32.3`, `pytest==8.3.3`. Nenhuma dependência nova.

**Spec:** Issue #2; `docs/ISSUES.md` (S01-O1.2); `docs/superpowers/plans/2026-10-05-lab03-dora-pipeline.md` (Contratos, Global Constraints, Task 1); `enunciado/03 - Mineração de Métricas DORA.md` (seções de API, rate limit, paginação, cache e retomada).

## Global Constraints
- Proibido PyGithub ou qualquer lib de acesso à API do GitHub; só `requests` direto.
- Token só via parâmetro (vindo de `GITHUB_TOKEN`); nunca em teste nem commitado. Testes nunca acessam a rede.
- Contratos (nomes exatos):
  - `DiskCache(root: pathlib.Path)`, `.get(key: str) -> dict | list | None`, `.set(key: str, value) -> None`.
  - `GitHubClient(token: str, cache: DiskCache, sleep=time.sleep, max_retries: int = 5)`, `.get(path: str, params: dict | None = None) -> tuple[object, dict]` (404 → `NotFoundError`), `.paginate(path: str, params: dict | None = None, item_key: str | None = None) -> list`.
- Cache: arquivo JSON, nome = sha1 da chave; chave = URL + params ordenados.
- 5xx: backoff exponencial 1, 2, 4, 8 s… até `max_retries`, depois erro.
- Rate limit: ler `X-RateLimit-Remaining`/`X-RateLimit-Reset` e esperar; 403/429 com `Retry-After` → esperar e repetir.
- Paginação: seguir `Link rel="next"` até o fim.
- Respostas de erro não vão para o cache.
- Arquivos: apenas `pipeline/cache.py`, `pipeline/http.py`, `tests/test_http.py` (+ este plano).
- Commits `tipo(modulo): descrição (#2)`, sem linha de co-autoria; nunca commitar `__pycache__`/`.pyc`/`cache/`.

## Decisões internas (pequenas, reversíveis; registrar no PR)
1. **Injeção da sessão:** o contrato não tem parâmetro `session`; os testes substituem o atributo público `client.session`. Relógio injetável via atributo `client.clock` (padrão `time.time`).
2. **O cache guarda `{"json": corpo, "headers": cabeçalhos}`**, porque `paginate` (Link) e a contagem de contribuidores (O1.4) precisam dos cabeçalhos também em cache hit. Os cabeçalhos retornados são `requests.structures.CaseInsensitiveDict` (mapeamento; aceita `headers["link"]` ou `["Link"]`).
3. **Exceções:** `GitHubError(Exception)` com `.status` e `.url`; `NotFoundError(GitHubError)`. Esgotar tentativas, 4xx não tratável ou erro de rede persistente → `GitHubError`.
4. **Contador único de tentativas por chamada:** 5xx, erro de rede e esperas de rate limit consomem o mesmo `max_retries` (`max_retries + 1` requisições no total). Backoff de 5xx/rede = `2**tentativa` (1, 2, 4, 8, 16 com o padrão 5).
5. **Rate limit:**
   - resposta 2xx com `X-RateLimit-Remaining: 0` e `Reset` futuro → `sleep(reset - agora)` antes de devolver (a próxima chamada já encontra a cota renovada);
   - 403/429 com `Retry-After` → `sleep(Retry-After)` e repete;
   - 403/429 com `Remaining: 0` → `sleep(max(reset - agora, 1))` e repete;
   - 429 sem cabeçalhos, ou 403 cuja mensagem contém "rate limit" (limite secundário sem `Retry-After`) → `sleep(60)` e repete (recomendação da documentação do GitHub);
   - 403 sem nada disso (permissão) → `GitHubError` imediato.
6. **`paginate`** acrescenta `per_page=100` quando o chamador não informa; se a página não for lista (endpoint embrulhado sem `item_key`), levanta `TypeError` em vez de concatenar chaves de dict silenciosamente.
7. **`rate_limit()`**: método extra que consulta `GET /rate_limit` **sem cache** (consultar o status não pode devolver um valor velho do disco). Não altera o contrato.
8. **Cache corrompido** (arquivo truncado por `Ctrl+C`) → tratado como miss; escrita atômica (`.tmp` + `os.replace`) evita o caso no caminho normal.

## Review Focus
- Cabeçalho `Link` vindo em minúsculas (`link`) ou lido de cache → paginação continua funcionando (teste em Task 4).
- Endpoint embrulhado (`{"total_count":…, "workflow_runs":[…]}`) chamado sem `item_key` → erro claro, não lista de chaves (teste em Task 4).
- 403 de permissão (sem sinal de rate limit) → falha imediata, sem esperar nem repetir (teste em Task 3).
- Arquivo de cache truncado após interrupção → miss, refaz a chamada sem quebrar (teste em Task 1).
- Erro de rede (`ConnectionError`) transitório → mesmo backoff do 5xx (teste em Task 2).

---

### Task 1: `DiskCache`

**Files:**
- Create: `pipeline/cache.py`
- Test: `tests/test_http.py`

**Interfaces:**
- Produces: `DiskCache(root)`, `.get(key) -> dict | list | None`, `.set(key, value) -> None`.

- [ ] **Step 1: Write the failing tests**

```python
import hashlib
import json

from pipeline.cache import DiskCache


def test_cache_set_get_persiste_em_arquivo_sha1(tmp_path):
    cache = DiskCache(tmp_path / "cache")
    cache.set("https://api.github.com/x?a=1", {"v": 1})
    nome = hashlib.sha1("https://api.github.com/x?a=1".encode("utf-8")).hexdigest() + ".json"
    arquivo = tmp_path / "cache" / nome
    assert json.loads(arquivo.read_text(encoding="utf-8")) == {"v": 1}
    # nova instância lê do disco (retomada)
    assert DiskCache(tmp_path / "cache").get("https://api.github.com/x?a=1") == {"v": 1}


def test_cache_miss_retorna_none(tmp_path):
    assert DiskCache(tmp_path).get("inexistente") is None


def test_cache_arquivo_corrompido_e_miss(tmp_path):
    cache = DiskCache(tmp_path)
    cache.set("k", [1, 2])
    arquivo = next(tmp_path.glob("*.json"))
    arquivo.write_text('{"trunc', encoding="utf-8")
    assert cache.get("k") is None
```

- [ ] **Step 2: Run** `pytest tests/test_http.py -v` → FAIL (`ModuleNotFoundError: pipeline.cache`).

- [ ] **Step 3: Implement**

```python
"""Cache em disco: um arquivo JSON por chave (nome = sha1 da chave)."""
from __future__ import annotations

import hashlib
import json
import os
import pathlib


class DiskCache:
    def __init__(self, root: pathlib.Path):
        self.root = pathlib.Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> pathlib.Path:
        return self.root / (hashlib.sha1(key.encode("utf-8")).hexdigest() + ".json")

    def get(self, key: str) -> dict | list | None:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None  # arquivo truncado (ex.: Ctrl+C): trata como miss

    def set(self, key: str, value) -> None:
        path = self._path(key)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)  # escrita atômica
```

- [ ] **Step 4: Run** `pytest tests/test_http.py -v` → PASS.
- [ ] **Step 5: Commit** `feat(cache): cache em disco com um JSON por chave (#2)` (`git add pipeline/cache.py tests/test_http.py`).

---

### Task 2: `GitHubClient.get` — cache, autenticação, 404 e backoff em 5xx

**Files:**
- Create: `pipeline/http.py`
- Test: `tests/test_http.py`

**Interfaces:**
- Consumes: `DiskCache` (Task 1).
- Produces: `GitHubClient(token, cache, sleep=time.sleep, max_retries=5)`, `.get(path, params=None) -> (json, headers)`, atributos `session`, `clock`; `GitHubError(status, url, message)`, `NotFoundError(GitHubError)`; constante `API_URL = "https://api.github.com"`.

- [ ] **Step 1: Write the failing tests** (helpers fake no topo do arquivo de testes)

```python
import pytest
import requests

from pipeline.http import API_URL, GitHubClient, GitHubError, NotFoundError


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, headers=None):
        self.status_code = status_code
        self._json = json_data
        self.headers = headers or {}

    def json(self):
        if self._json is None:
            raise ValueError("sem corpo JSON")
        return self._json


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.headers = {}

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        resp = self.responses.pop(0)
        if isinstance(resp, Exception):
            raise resp
        return resp


def make_client(tmp_path, responses, max_retries=5, now=1_000_000.0):
    sleeps = []
    client = GitHubClient("tok", DiskCache(tmp_path / "cache"), sleep=sleeps.append, max_retries=max_retries)
    client.session = FakeSession(responses)
    client.clock = lambda: now
    return client, sleeps


def test_client_envia_token_e_headers_padrao(tmp_path):
    client = GitHubClient("abc", DiskCache(tmp_path))
    assert client.session.headers["Authorization"] == "Bearer abc"
    assert client.session.headers["Accept"] == "application/vnd.github+json"


def test_get_retorna_json_e_headers_e_monta_url(tmp_path):
    client, _ = make_client(tmp_path, [FakeResponse(200, {"a": 1}, {"X-Custom": "v"})])
    data, headers = client.get("/repos/o/r", {"x": 1})
    assert data == {"a": 1}
    assert headers["x-custom"] == "v"
    assert client.session.calls == [(f"{API_URL}/repos/o/r", {"x": 1})]


def test_cache_hit_nao_chama_rede(tmp_path):
    client, _ = make_client(tmp_path, [FakeResponse(200, [1, 2], {"Link": "l"})])
    client.get("/a", {"b": 2, "a": 1})
    client.session = FakeSession([])  # qualquer chamada de rede quebraria (pop em lista vazia)
    data, headers = client.get("/a", {"a": 1, "b": 2})  # params em outra ordem: mesma chave
    assert data == [1, 2]
    assert headers["link"] == "l"


def test_404_levanta_not_found_e_nao_cacheia(tmp_path):
    client, sleeps = make_client(tmp_path, [FakeResponse(404, {"message": "Not Found"}),
                                            FakeResponse(200, {"ok": True})])
    with pytest.raises(NotFoundError):
        client.get("/repos/o/r/compare/a...b")
    assert sleeps == []
    assert client.get("/repos/o/r/compare/a...b")[0] == {"ok": True}  # foi à rede de novo


def test_5xx_backoff_exponencial_ate_sucesso(tmp_path):
    client, sleeps = make_client(tmp_path, [FakeResponse(502), FakeResponse(503), FakeResponse(200, {"ok": 1})])
    assert client.get("/x")[0] == {"ok": 1}
    assert sleeps == [1, 2]


def test_5xx_esgota_tentativas_levanta_erro_e_nao_cacheia(tmp_path):
    client, sleeps = make_client(tmp_path, [FakeResponse(500)] * 4, max_retries=3)
    with pytest.raises(GitHubError):
        client.get("/x")
    assert sleeps == [1, 2, 4]
    assert len(client.session.calls) == 4
    assert list((tmp_path / "cache").glob("*.json")) == []


def test_5xx_padrao_espera_1_2_4_8_16(tmp_path):
    client, sleeps = make_client(tmp_path, [FakeResponse(500)] * 6)
    with pytest.raises(GitHubError):
        client.get("/x")
    assert sleeps == [1, 2, 4, 8, 16]


def test_erro_de_rede_usa_backoff(tmp_path):
    client, sleeps = make_client(tmp_path, [requests.ConnectionError("caiu"), FakeResponse(200, {"ok": 1})])
    assert client.get("/x")[0] == {"ok": 1}
    assert sleeps == [1]
```

- [ ] **Step 2: Run** `pytest tests/test_http.py -v` → FAIL (`ModuleNotFoundError: pipeline.http`).

- [ ] **Step 3: Implement** (versão desta task; Task 3 completa o tratamento de 403/429)

```python
"""Cliente da API REST do GitHub: cache em disco, rate limit, backoff e paginação.

Usa `requests` diretamente (bibliotecas de acesso à API do GitHub são proibidas).
"""
from __future__ import annotations

import re
import time
from urllib.parse import urlencode

import requests
from requests.structures import CaseInsensitiveDict

from pipeline.cache import DiskCache

API_URL = "https://api.github.com"
TIMEOUT = 30


class GitHubError(Exception):
    def __init__(self, status: int | None, url: str, message: str = ""):
        super().__init__(f"HTTP {status} em {url}: {message}")
        self.status = status
        self.url = url


class NotFoundError(GitHubError):
    """404: recurso inexistente (ex.: tag apagada no compare)."""


def _json(resp):
    try:
        return resp.json()
    except ValueError:
        return None


def _message(resp) -> str:
    data = _json(resp)
    return data.get("message", "") if isinstance(data, dict) else ""


class GitHubClient:
    def __init__(self, token: str, cache: DiskCache, sleep=time.sleep, max_retries: int = 5):
        self.cache = cache
        self.sleep = sleep
        self.max_retries = max_retries
        self.clock = time.time
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    @staticmethod
    def _url(path: str) -> str:
        return path if path.startswith("http") else f"{API_URL}/{path.lstrip('/')}"

    @staticmethod
    def _key(url: str, params: dict | None) -> str:
        return f"{url}?{urlencode(sorted(params.items()))}" if params else url

    def get(self, path: str, params: dict | None = None) -> tuple[object, dict]:
        url = self._url(path)
        key = self._key(url, params)
        cached = self.cache.get(key)
        if cached is not None:
            return cached["json"], CaseInsensitiveDict(cached["headers"])
        data, headers = self._request(url, params)
        self.cache.set(key, {"json": data, "headers": dict(headers)})
        return data, headers

    def _request(self, url: str, params: dict | None):
        for attempt in range(self.max_retries + 1):
            last = attempt == self.max_retries
            try:
                resp = self.session.get(url, params=params, timeout=TIMEOUT)
            except (requests.ConnectionError, requests.Timeout) as exc:
                if last:
                    raise GitHubError(None, url, f"erro de rede: {exc}") from exc
                self.sleep(2 ** attempt)
                continue
            status = resp.status_code
            headers = CaseInsensitiveDict(resp.headers)
            if status == 404:
                raise NotFoundError(status, url, _message(resp))
            if status >= 500:
                if last:
                    raise GitHubError(status, url, _message(resp))
                self.sleep(2 ** attempt)
                continue
            if status >= 400:
                raise GitHubError(status, url, _message(resp))
            return _json(resp), headers
```

- [ ] **Step 4: Run** `pytest tests/test_http.py -v` → PASS.
- [ ] **Step 5: Commit** `feat(http): get com cache, 404 e backoff exponencial em 5xx (#2)`.

---

### Task 3: Rate limit primário e secundário

**Files:**
- Modify: `pipeline/http.py`
- Test: `tests/test_http.py`

**Interfaces:**
- Consumes: `GitHubClient._request`, `client.clock` (Task 2).
- Produces: constante `SECONDARY_WAIT = 60`; método `rate_limit() -> dict` (sem cache).

- [ ] **Step 1: Write the failing tests**

```python
NOW = 1_000_000.0


def test_remaining_zero_com_reset_futuro_espera_a_diferenca(tmp_path):
    headers = {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(int(NOW) + 120)}
    client, sleeps = make_client(tmp_path, [FakeResponse(200, {"ok": 1}, headers)], now=NOW)
    assert client.get("/x")[0] == {"ok": 1}
    assert sleeps == [120]


def test_remaining_positivo_ou_reset_passado_nao_espera(tmp_path):
    client, sleeps = make_client(tmp_path, [
        FakeResponse(200, [], {"X-RateLimit-Remaining": "10", "X-RateLimit-Reset": str(int(NOW) + 50)}),
        FakeResponse(200, [], {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(int(NOW) - 5)}),
    ], now=NOW)
    client.get("/a")
    client.get("/b")
    assert sleeps == []


def test_403_cota_esgotada_espera_reset_e_repete(tmp_path):
    headers = {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(int(NOW) + 30)}
    client, sleeps = make_client(tmp_path, [
        FakeResponse(403, {"message": "API rate limit exceeded"}, headers),
        FakeResponse(200, {"ok": 1}),
    ], now=NOW)
    assert client.get("/x")[0] == {"ok": 1}
    assert sleeps == [30]


@pytest.mark.parametrize("status", [403, 429])
def test_retry_after_espera_e_repete(tmp_path, status):
    client, sleeps = make_client(tmp_path, [
        FakeResponse(status, {"message": "secondary rate limit"}, {"Retry-After": "7"}),
        FakeResponse(200, {"ok": 1}),
    ])
    assert client.get("/search/repositories", {"q": "x"})[0] == {"ok": 1}
    assert sleeps == [7]


def test_429_sem_cabecalhos_espera_60s(tmp_path):
    client, sleeps = make_client(tmp_path, [FakeResponse(429), FakeResponse(200, {"ok": 1})])
    client.get("/x")
    assert sleeps == [60]


def test_403_secundario_sem_retry_after_espera_60s(tmp_path):
    client, sleeps = make_client(tmp_path, [
        FakeResponse(403, {"message": "You have exceeded a secondary rate limit."}),
        FakeResponse(200, {"ok": 1}),
    ])
    client.get("/x")
    assert sleeps == [60]


def test_403_de_permissao_falha_sem_esperar_e_nao_cacheia(tmp_path):
    client, sleeps = make_client(tmp_path, [FakeResponse(403, {"message": "Resource not accessible"})])
    with pytest.raises(GitHubError) as exc:
        client.get("/x")
    assert exc.value.status == 403
    assert sleeps == []
    assert list((tmp_path / "cache").glob("*.json")) == []


def test_rate_limit_persistente_esgota_tentativas(tmp_path):
    client, sleeps = make_client(tmp_path, [FakeResponse(429, None, {"Retry-After": "1"})] * 3, max_retries=2)
    with pytest.raises(GitHubError):
        client.get("/x")
    assert sleeps == [1, 1]


def test_rate_limit_endpoint_nao_usa_cache(tmp_path):
    client, _ = make_client(tmp_path, [FakeResponse(200, {"rate": {"remaining": 5}}),
                                       FakeResponse(200, {"rate": {"remaining": 4}})])
    assert client.rate_limit()["rate"]["remaining"] == 5
    assert client.rate_limit()["rate"]["remaining"] == 4
    assert client.session.calls[0][0] == f"{API_URL}/rate_limit"
```

- [ ] **Step 2: Run** `pytest tests/test_http.py -v` → os novos testes FALHAM (403/429 viram `GitHubError` imediato; não há espera; `rate_limit` não existe).

- [ ] **Step 3: Implement** — adicionar ao `pipeline/http.py`:

```python
SECONDARY_WAIT = 60  # s; recomendação do GitHub para limite secundário sem Retry-After
```

Métodos novos em `GitHubClient`:

```python
    def _reset_wait(self, headers) -> float | None:
        if headers.get("X-RateLimit-Remaining") != "0" or "X-RateLimit-Reset" not in headers:
            return None
        return float(headers["X-RateLimit-Reset"]) - self.clock()

    def _rate_limit_wait(self, status: int, headers, resp) -> float | None:
        if "Retry-After" in headers:
            try:
                return int(headers["Retry-After"])
            except ValueError:
                return SECONDARY_WAIT
        reset = self._reset_wait(headers)
        if reset is not None:
            return max(reset, 1)
        if status == 429 or "rate limit" in _message(resp).lower():
            return SECONDARY_WAIT
        return None  # 403 de permissão: não é rate limit

    def rate_limit(self) -> dict:
        """GET /rate_limit (não consome cota); nunca usa o cache."""
        data, _ = self._request(self._url("/rate_limit"), None)
        return data
```

No laço de `_request`, antes de `if status >= 400:`:

```python
            if status in (403, 429):
                wait = self._rate_limit_wait(status, headers, resp)
                if wait is None:
                    raise GitHubError(status, url, _message(resp))
                if last:
                    raise GitHubError(status, url, "limite de requisições persistente")
                self.sleep(wait)
                continue
```

E trocar o retorno de sucesso por:

```python
            reset = self._reset_wait(headers)
            if reset is not None and reset > 0:
                self.sleep(reset)  # cota acabou: espera renovar antes da próxima chamada
            return _json(resp), headers
```

- [ ] **Step 4: Run** `pytest tests/test_http.py -v` → PASS.
- [ ] **Step 5: Commit** `feat(http): espera por X-RateLimit-Reset e Retry-After (#2)`.

---

### Task 4: `paginate` por `Link rel="next"`

**Files:**
- Modify: `pipeline/http.py`
- Test: `tests/test_http.py`

**Interfaces:**
- Consumes: `GitHubClient.get` (Tasks 2–3).
- Produces: `GitHubClient.paginate(path, params=None, item_key=None) -> list`; função `next_link(headers) -> str | None`.

- [ ] **Step 1: Write the failing tests**

```python
def _link(url):
    return {"Link": f'<{url}>; rel="next", <{API_URL}/last>; rel="last"'}


def test_paginate_segue_link_next_e_concatena(tmp_path):
    p2 = f"{API_URL}/repos/o/r/releases?per_page=100&page=2"
    client, _ = make_client(tmp_path, [
        FakeResponse(200, [1, 2], _link(p2)),
        FakeResponse(200, [3], {"Link": f'<{API_URL}/repos/o/r/releases?per_page=100&page=1>; rel="prev"'}),
    ])
    assert client.paginate("/repos/o/r/releases") == [1, 2, 3]
    assert client.session.calls == [(f"{API_URL}/repos/o/r/releases", {"per_page": 100}), (p2, None)]


def test_paginate_item_key_e_link_minusculo(tmp_path):
    p2 = f"{API_URL}/repos/o/r/actions/runs?page=2"
    client, _ = make_client(tmp_path, [
        FakeResponse(200, {"total_count": 3, "workflow_runs": [{"id": 1}, {"id": 2}]},
                     {"link": f'<{p2}>; rel="next"'}),
        FakeResponse(200, {"total_count": 3, "workflow_runs": [{"id": 3}]}),
    ])
    runs = client.paginate("/repos/o/r/actions/runs", {"per_page": 50}, item_key="workflow_runs")
    assert [r["id"] for r in runs] == [1, 2, 3]
    assert client.session.calls[0][1] == {"per_page": 50}


def test_paginate_retoma_do_cache(tmp_path):
    p2 = f"{API_URL}/x?page=2"
    client, _ = make_client(tmp_path, [FakeResponse(200, ["a"], _link(p2)), FakeResponse(200, ["b"])])
    client.paginate("/x")
    client.session = FakeSession([])
    assert client.paginate("/x") == ["a", "b"]


def test_paginate_sem_item_key_em_endpoint_embrulhado_levanta_type_error(tmp_path):
    client, _ = make_client(tmp_path, [FakeResponse(200, {"total_count": 0, "workflows": []})])
    with pytest.raises(TypeError):
        client.paginate("/repos/o/r/actions/workflows")


def test_paginate_lista_vazia(tmp_path):
    client, _ = make_client(tmp_path, [FakeResponse(200, [])])
    assert client.paginate("/x") == []
```

- [ ] **Step 2: Run** `pytest tests/test_http.py -v` → FAIL (`AttributeError: 'GitHubClient' object has no attribute 'paginate'`).

- [ ] **Step 3: Implement** — em `pipeline/http.py`:

```python
_NEXT_RE = re.compile(r'<([^>]+)>\s*;\s*rel="next"')


def next_link(headers) -> str | None:
    """URL da próxima página no cabeçalho Link, ou None na última página."""
    match = _NEXT_RE.search(CaseInsensitiveDict(headers).get("Link", ""))
    return match.group(1) if match else None
```

Método em `GitHubClient`:

```python
    def paginate(self, path: str, params: dict | None = None, item_key: str | None = None) -> list:
        params = {"per_page": 100, **(params or {})}
        items: list = []
        data, headers = self.get(path, params)
        while True:
            page = (data or {}).get(item_key, []) if item_key else (data or [])
            if not isinstance(page, list):
                raise TypeError(f"página de {path} não é lista; informe item_key")
            items.extend(page)
            url = next_link(headers)
            if url is None:
                return items
            data, headers = self.get(url)  # a URL do Link já traz os parâmetros
```

- [ ] **Step 4: Run** `pytest tests/test_http.py -v` → PASS.
- [ ] **Step 5: Commit** `feat(http): cliente com cache, rate limit e backoff (#2)` (mensagem pedida pela Issue).

---

### Task 5: Verificação final

- [ ] `python -m pytest --cov=metricas --cov-report=term-missing --cov-fail-under=0 -v` → todos verdes.
- [ ] `python -m pytest --cov=pipeline --cov-report=term-missing tests/test_http.py` → conferir linhas não cobertas de `cache.py`/`http.py` (informativo).
- [ ] `git status --porcelain` e `git ls-files | grep -E "pycache|\.pyc|^cache/"` → nada indevido.
