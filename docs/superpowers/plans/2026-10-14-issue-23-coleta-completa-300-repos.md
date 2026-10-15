# S02-O1.1 — Coleta completa ≥ 300 repos — Plano de Implementação

> Execução inline (superpowers:executing-plans) nesta mesma sessão, com TDD em cada tarefa.

**Goal:** deixar o pipeline configurado e verificado para a coleta de ≥ 300 repositórios válidos (config, retomada após `Ctrl+C`, log de progresso) e anexar `data/funil.csv` e `data/metricas.csv` da coleta real.

**Architecture:** nenhuma mudança de contrato. `config.yaml` passa a `sample_size: 300` com a janela definitiva do grupo; o orquestrador ganha uma linha de log no início de cada repositório; um teste ponta a ponta (cliente HTTP real + `DiskCache` + sessão fake) prova que, interrompida por `KeyboardInterrupt` em qualquer ponto, a reexecução termina sem repetir nenhuma chamada.

**Tech Stack:** Python 3.12, pytest, requests (só via `GitHubClient`), PyYAML, pandas.

**Spec:** Issue #23 (`docs/ISSUES.md`, S02-O1.1), `docs/superpowers/plans/2026-10-05-lab03-dora-pipeline.md`, enunciado §4, §7 e FAQ ("A coleta de 300+ repositórios vai estourar o rate limit?").

## Global Constraints

- Coleta só com `requests` direto; proibido PyGithub. Testes nunca acessam a rede nem usam token real.
- Cache em disco + retomada: reexecutar continua de onde parou, **sem repetir chamadas já feitas** (enunciado §7).
- `window.end` precisa estar no passado (senão o cache guarda respostas incompletas).
- Amostra final com **mínimo de 300 repositórios após os filtros** (enunciado, S02).
- Decisão 2 (`docs/ISSUES.md`): candidatos embaralhados com `random_state=42`, processados em ordem até N válidos.
- Commits `tipo(modulo): descrição (#23)`, sem co-autor.

## Decisões desta Issue

1. **Janela definitiva** (decisão do usuário, 2026-10-14): 2025-10-01 a 2026-09-30, escolhida pelo grupo (qualquer período de 12 meses é aceito). Sai o comentário "PLACEHOLDER"; fica o alerta de `window.end` no passado.
2. **`sample_size: 300`** (decisão do usuário).
3. **`star_ranges` não serão fatiadas nesta Issue.** As 4 faixas dão 4.000 candidatos (cada uma no teto de 1.000 da Search API). Na S01, 442 processados renderam 100 válidos (~23%); para 300 válidos bastam ~1.300 processados, menos de 1/3 dos candidatos. Fatiar mudaria o conjunto de candidatos e, pelo embaralhamento, a ordem e a amostra; a coleta real dos 300 já está rodando com as faixas atuais. O truncamento em 1.000 por faixa (a Search API devolve os primeiros por "best match") fica registrado como ameaça à validade e anotado no `config.yaml`.
4. **Teste de retomada com `Ctrl+C`:** automatizado (Task 2) + uma execução real mínima (Task 4) com `cache_dir` separado fora do repositório, para não disputar a cota com a coleta em curso.

## Review Focus

1. Interrupção no meio da paginação (página 1 cacheada, página 2 não): a retomada relê a página 1 do cache e só busca a 2. → Task 2 (interrupção em todos os pontos possíveis).
2. Interrupção na primeira chamada (busca) e na última (antes de gravar os CSVs): a retomada produz o mesmo resultado da execução sem interrupção. → Task 2.
3. Repositório pesado (milhares de `compare`) sem nenhuma linha de log por minutos: o log de início deixa claro qual repo está em processamento. → Task 1.
4. `config.yaml` com `window.end` no futuro ou `sample_size` < 300 voltando por engano. → Task 3.
5. Saída da execução real de teste gravada em `data/` do repositório (sobrescreveria o dataset). → Task 4 roda com `cwd` temporário.

---

### Task 1: Log de início de cada repositório

**Files:**
- Modify: `pipeline/orquestrador.py` (laço de `executar`)
- Test: `tests/test_orquestrador.py`

**Interfaces:** nenhuma pública nova. Mensagem de log (nível INFO, logger `pipeline.orquestrador`):
`"%s: iniciando (candidato %d de %d; válidos %d/%d)"` → ex.: `o/a: iniciando (candidato 1 de 3; válidos 0/10)`.

- [ ] **Step 1: teste falhando**

```python
def test_loga_o_inicio_de_cada_repositorio(tmp_path, caplog):
    client = FakeClient({"o/a": repo(actions=False), "o/b": repo()})
    with caplog.at_level(logging.INFO, logger="pipeline.orquestrador"):
        executar(client, config(repos=["o/a", "o/b"]), tmp_path)
    mensagens = [r.getMessage() for r in caplog.records]
    assert "o/a: iniciando (candidato 1 de 2; válidos 0/10)" in mensagens
    assert "o/b: iniciando (candidato 2 de 2; válidos 0/10)" in mensagens
    assert mensagens.index("o/a: iniciando (candidato 1 de 2; válidos 0/10)") < mensagens.index(
        "o/a: descartado em 'com GitHub Actions'")
```

- [ ] **Step 2:** `pytest tests/test_orquestrador.py::test_loga_o_inicio_de_cada_repositorio -v` → FAIL (mensagem ausente).
- [ ] **Step 3:** no laço de `executar`, logo após `processados += 1`:

```python
        log.info("%s: iniciando (candidato %d de %d; válidos %d/%d)",
                 full_name, processados, len(candidatos), len(linhas), sample_size)
```

- [ ] **Step 4:** teste passa; suíte de `tests/test_orquestrador.py` verde.
- [ ] **Step 5:** commits `test(orquestrador): log de início de cada repositório (#23)` e `feat(orquestrador): loga o início de cada repositório (#23)`.

### Task 2: Teste ponta a ponta da retomada após Ctrl+C

**Files:**
- Create: `tests/test_retomada.py`

**Interfaces:**
- Consome: `GitHubClient(token, cache, sleep)`, `DiskCache(root)`, `executar(client, cfg, saida)`; de `tests/test_orquestrador.py`: `FakeClient`, `repo`, `releases_validas`, `config`.
- Produz: `SessaoFake(api, interromper_na=None)` (só nos testes) que converte URL+params em respostas do `FakeClient` e levanta `KeyboardInterrupt` na chamada de número `interromper_na` (1-based), simulando `Ctrl+C`.

Teste de caracterização (o comportamento já existe). Para ver o teste falhar pelo motivo certo, roda-se uma vez a retomada com um `cache_dir` diferente (simula "cache perdido"): as chamadas se repetem e a asserção de disjunção falha. Depois volta-se ao cache correto.

```python
"""Retomada após Ctrl+C: cliente HTTP real + cache em disco + sessão fake (sem rede)."""
import pandas as pd
import pytest

from pipeline.cache import DiskCache
from pipeline.http import API_URL, GitHubClient
from pipeline.orquestrador import executar
from tests.test_orquestrador import FakeClient, config, releases_validas, repo


POR_PAGINA = 3  # releases por página: força paginação via Link rel="next"


class Resposta:
    def __init__(self, dados, headers=None):
        self.status_code = 200
        self.headers = headers or {}
        self._dados = dados

    def json(self):
        return self._dados


class SessaoFake:
    """Responde como a API a partir de um FakeClient; `interromper_na` simula Ctrl+C."""

    def __init__(self, api, interromper_na=None):
        self.api = api
        self.interromper_na = interromper_na
        self.headers = {}
        self.chamadas = []

    def get(self, url, params=None, timeout=None):
        chave = (url, tuple(sorted((params or {}).items())))
        if self.interromper_na is not None and len(self.chamadas) + 1 == self.interromper_na:
            raise KeyboardInterrupt
        self.chamadas.append(chave)
        path, _, query = url.removeprefix(API_URL).partition("?")
        if path == "/search/repositories":
            return Resposta({"items": self.api.paginate(path, params)})
        partes = path.strip("/").split("/")
        resto = partes[3:]
        if resto == ["actions", "runs"]:
            return Resposta({"workflow_runs": self.api.paginate(path, params)})
        if resto and resto[0] == "compare":
            return Resposta({"commits": self.api.paginate(path, params)})
        if resto == ["releases"]:
            itens = self.api.paginate(path, params)
            if "page=2" in query:
                return Resposta(itens[POR_PAGINA:])
            proxima = f'<{API_URL}{path}?per_page=100&page=2>; rel="next"'
            return Resposta(itens[:POR_PAGINA], {"Link": proxima} if len(itens) > POR_PAGINA else {})
        return Resposta(self.api.get(path, params)[0])


def api_fake():
    return FakeClient({
        "o/sem-actions": repo(actions=False),
        "o/poucas": repo(releases=releases_validas(3)),
        "o/a": repo(),
        "o/b": repo(),
    })


def rodar(cache_dir, saida, interromper_na=None):
    sessao = SessaoFake(api_fake(), interromper_na)
    client = GitHubClient("tok", DiskCache(cache_dir), sleep=lambda s: None)
    client.session = sessao
    resultado = executar(client, config(), saida)
    return resultado, sessao.chamadas


def test_execucao_completa_nao_repete_chamadas(tmp_path):
    _, chamadas = rodar(tmp_path / "cache", tmp_path / "saida")
    assert len(chamadas) == len(set(chamadas))
    assert any("page=2" in url for url, _ in chamadas)  # houve paginação


def test_reexecucao_com_cache_completo_nao_chama_a_rede(tmp_path):
    rodar(tmp_path / "cache", tmp_path / "saida")
    _, chamadas = rodar(tmp_path / "cache", tmp_path / "saida")
    assert chamadas == []


def test_retomada_apos_ctrl_c_em_qualquer_ponto(tmp_path):
    (metricas_ref, funil_ref), referencia = rodar(tmp_path / "ref", tmp_path / "saida_ref")
    total = len(referencia)
    assert total > 10
    for k in range(1, total + 1):
        cache = tmp_path / f"cache{k}"
        sessao = SessaoFake(api_fake(), interromper_na=k)
        client = GitHubClient("tok", DiskCache(cache), sleep=lambda s: None)
        client.session = sessao
        with pytest.raises(KeyboardInterrupt):
            executar(client, config(), tmp_path / f"saida{k}")
        feitas = sessao.chamadas
        assert len(feitas) == k - 1

        (metricas, funil), retomada = rodar(cache, tmp_path / f"saida{k}")
        assert set(feitas).isdisjoint(retomada), f"chamada repetida ao retomar após {k - 1}"
        assert len(feitas) + len(retomada) == total
        pd.testing.assert_frame_equal(metricas, metricas_ref)
        pd.testing.assert_frame_equal(funil, funil_ref)
```

- [ ] **Step 1:** escrever o arquivo; rodar `pytest tests/test_retomada.py -v`.
- [ ] **Step 2 (ver falhar):** trocar temporariamente `rodar(cache, ...)` por `rodar(tmp_path / "outro", ...)` na retomada → FAIL "chamada repetida". Desfazer.
- [ ] **Step 3:** todos verdes.
- [ ] **Step 4:** commit `test(pipeline): retomada após Ctrl+C sem repetir chamadas (#23)`.

### Task 3: config.yaml para a S02

**Files:**
- Modify: `config.yaml`
- Test: `tests/test_config.py` (novo)

- [ ] **Step 1: teste falhando**

```python
"""Conferência do config.yaml versionado (o que a coleta da S02 usa)."""
import pathlib
from datetime import datetime, timezone

from pipeline.orquestrador import carregar_config, janela_da_config

CONFIG = pathlib.Path(__file__).resolve().parent.parent / "config.yaml"


def test_config_pede_pelo_menos_300_repositorios():
    assert carregar_config(CONFIG)["sample_size"] >= 300


def test_janela_tem_12_meses_e_ja_terminou():
    inicio, fim = janela_da_config(carregar_config(CONFIG))
    assert 364 <= (fim - inicio).days <= 366
    assert fim < datetime.now(timezone.utc)


def test_faixas_de_estrelas_validas():
    for lo, hi in carregar_config(CONFIG)["star_ranges"]:
        assert 0 <= lo <= hi
```

- [ ] **Step 2:** `pytest tests/test_config.py -v` → FAIL em `sample_size` (100).
- [ ] **Step 3:** `config.yaml`: `sample_size: 300`; comentário da janela sem "PLACEHOLDER" (janela definida pelo grupo; alerta de `window.end` no passado mantido); comentário das `star_ranges` explicando o teto de 1.000 e por que não foram fatiadas (Decisão 3).
- [ ] **Step 4:** teste passa.
- [ ] **Step 5:** commits `test(config): ... (#23)` e `chore(config): sample_size 300 e janela definitiva do grupo (#23)`.

### Task 4: execução real mínima com Ctrl+C (sem commit de dados)

- Script no scratchpad (fora do repo), `cwd` temporário, `cache_dir` temporário, `config` com `repos: [2 repositórios pequenos]` e `sample_size: 2`; token via `GITHUB_TOKEN=$(gh auth token)`.
- Rodada 1: `main()` no thread principal e `_thread.interrupt_main()` após alguns segundos (gera o mesmo `KeyboardInterrupt` do `Ctrl+C`). Contar as chamadas HTTP feitas (contador em volta de `requests.Session.get`).
- Rodada 2: mesmo cache; contar chamadas; conferir que nenhuma URL+params da rodada 1 é repetida e que os CSVs são gerados.
- Registrar a saída no PR (seção Testes). Nada desta execução é commitado.

### Task 5: dados da coleta real (após o término da execução em segundo plano)

- Copiar `data/metricas.csv` e `data/funil.csv` gerados pela coleta dos 300 (sobrescrevem os da S01), conferir `len(metricas) >= 300`, commit `data: coleta completa com N repositórios e funil (#23)`.
- Tabela do funil e resumo (mediana/IQR) no corpo do PR. Abrir o PR só depois disso.

---

## Registro da execução (2026-10-14)

- **Task 1, ajuste:** o teste usa `config(repos=["o/a", "o/b"])`. Com a busca, os candidatos são embaralhados (decisão 2) e a ordem `o/a, o/b` não é garantida.
- **Task 2:** com a retomada apontando para outro `cache_dir`, o teste falhou com "chamada repetida ao retomar após 1 chamadas"; com o mesmo cache, 3/3 verdes.
- **Task 4 (execução real, `repos: [pallets/click, psf/requests]`, `sample_size: 2`, cache e `cwd` temporários):**
  - rodada 1 interrompida com `_thread.interrupt_main()` (mesmo `KeyboardInterrupt` do Ctrl+C) após 4 s: 5 chamadas HTTP, 4 gravadas no cache;
  - rodada 2 (retomada): 41 chamadas, 2/2 válidos, CSVs gerados; a única chamada repetida foi a 5ª da rodada 1 (`compare/8.3.0...8.3.1`), que estava em andamento quando veio a interrupção e por isso nunca foi gravada;
  - rodada 3: 0 chamadas HTTP (tudo do cache).
