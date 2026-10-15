# S02-O1.2 — Variantes de deploy: tags e pré-releases — Plano de Implementação

> Execução inline (superpowers:executing-plans) nesta mesma sessão, com TDD em cada tarefa. Branch `feat/24-variantes-deploy-tags-pre-releases`, criada a partir de `feat/23-coleta-completa-300-repos` (PR #78 ainda não mergeado; autorizado pelo usuário).

**Goal:** para cada repositório válido, calcular frequência de deploy e lead time (b) nas unidades `release+pre` e `tag` (entradas das combinações C2 e C3 da RQ07) e gravar as colunas novas em `data/metricas.csv`, com teto de custo de cota configurável e nunca silencioso.

**Architecture:** `metricas/variantes.py` tem só funções puras (separar base/janela, escolher os pares do `compare` com teto, agregar o lead time (b)). `pipeline/tags.py` faz a coleta das tags e das datas dos commits apontados. `pipeline/etapa_variantes.py` encadeia as duas unidades e devolve um dict de colunas; o orquestrador a chama só para repositórios já válidos (o funil não muda).

**Tech Stack:** Python 3.12, pytest, `requests` só via `GitHubClient`, pandas, PyYAML.

**Spec:** Issue #24; `docs/ISSUES.md` (S02-O1.2, decisões 4 e 5); `docs/superpowers/plans/2026-10-05-lab03-dora-pipeline.md`; enunciado §3 (definições), §4 (tabela de endpoints: "Tags não trazem data: use a data do commit apontado pela tag"), RQ02 e RQ07.

## Global Constraints

- Proibido PyGithub; testes nunca acessam a rede nem usam token real.
- Datas `datetime` UTC; data de commit = `commit.author.date`; lead time em **dias**.
- Janela: só unidades com data em `[window.start, window.end]` contam na frequência; a unidade anterior à janela serve só de base do `compare` (decisão 5: "nas variantes da RQ07 é a unidade anterior do mesmo tipo").
- Primeira unidade da história (sem anterior) é ignorada no lead time; `compare` 404 → registrar, ignorar a unidade e contar; lead time negativo → descartar e contar (decisão 4).
- Frequência = unidades na janela ÷ semanas da janela (`semanas_da_janela`, ≈ 52,1).
- Censura/descartes nunca silenciosos: todo corte vira contador no CSV.
- Commits `tipo(modulo): descrição (#24)`, sem co-autor. Cobertura de `metricas` ≥ 80%.

## Decisões desta Issue (o usuário pediu para decidir e registrar, sem perguntar)

1. **A listagem `GET /repos/{o}/{r}/tags` não vem em ordem cronológica.** Conferido em 2026-10-15: vem por nome em ordem de versão decrescente (`v0.2.10` antes de `v0.2.9`), com prefixos misturados (llama.cpp: `v*`, `tmp-*`, `master-*`, `b*`, ~8.000 tags em 80 páginas). Não dá para cortar a janela pela posição na lista.
2. **Data e janela das tags via commits do default branch na janela.** Em vez de uma chamada por tag (milhares no llama.cpp, quase todas fora da janela), a data vem de `GET /repos/{o}/{r}/commits?sha={default_branch}&since={start}&until={end}` (paginado, 100 por página): uma tag está na janela se o SHA para o qual aponta está nessa listagem e o `commit.author.date` dele cai dentro da janela. O custo depende dos commits da janela (≈ commits/100 chamadas), não do total histórico de tags. Isso aplica às tags a regra global "considere apenas o default branch" (§3): tags de branches de manutenção ficam de fora da unidade `tag`. Essa diferença em relação à unidade `release` (que não filtra branch) é parte do que a RQ07 mede e entra em ameaças à validade.
3. **Tag-base anterior à janela** (para o `compare` da primeira tag da janela): os candidatos são as tags que aparecem na listagem logo depois da última tag da janela (na ordem de versão, as próximas são as versões anteriores), até `CANDIDATOS_BASE = 5` tags. A data de cada uma vem de `GET /repos/{o}/{r}/git/commits/{sha}` (`author.date`). Usei o endpoint Git Database e não `commits/{sha}` porque devolve só metadados, sem `files`/patches (o cache fica bem menor). A base é a candidata mais recente com data anterior ao início da janela. Sem candidata válida, a primeira tag da janela fica sem base e é ignorada no lead time, como a primeira release da história.
4. **Base de `release+pre`:** a unidade anterior à janela pode ser uma pré-release. `fetch_releases` (arquivo de B, S01) ganha o parâmetro opcional `base_inclui_pre: bool = False`, compatível com o contrato atual. Com `True`, a base é a última release **ou** pré-release antes da janela. O PR avisa o autor original.
5. **Teto de compares (`max_compares_variante`, padrão 100, por unidade e por repositório):** se a sequência (base + unidades da janela) gera mais pares consecutivos que o teto, o lead time (b) usa uma amostra **sistemática e determinística** de pares espalhados pela janela (`pares[i*n//teto]`, para i = 0..teto−1), não só os mais recentes. A frequência continua exata (contagem completa). As unidades sem `compare` por causa do teto entram em `teto_compare_pre` / `teto_compare_tag` (0 quando o teto não foi aplicado). `max_compares_variante: null` desliga o teto. O teto vale para as duas variantes (repos com pré-release diária também explodiriam).
6. **Colunas extras de transparência:** além das 4 colunas da Issue, o CSV ganha `n_releases_pre`, `n_tags`, `compare_404_pre`, `compare_404_tag`, `n_lead_negativos_pre`, `n_lead_negativos_tag`, `teto_compare_pre` e `teto_compare_tag`. Ficam depois de `meses_no_teto` e antes das notas.
7. **Só repositórios válidos** (que passaram pelo critério de ≥ 5 releases e ≥ 50 runs) coletam variantes. O funil não muda.
8. **Duas tags no mesmo commit** (ou tag sem commits novos): o `compare` devolve 0 commits; a unidade não contribui para o lead time (b), mas conta na frequência. É o mesmo comportamento das releases na S01.

## Review Focus

1. Repositório sem nenhuma tag: nenhuma chamada além da listagem de tags; frequência 0, lead time vazio. → Task 3/4.
2. Tag sem commits novos (mesmo SHA da anterior): não quebra; conta na frequência e não no lead time. → Task 4.
3. Pré-release como primeira unidade (antes da janela, ela é a base; na janela, sem base, é ignorada no lead time). → Tasks 2 e 4.
4. `compare` 404 numa variante: unidade ignorada e contada em `compare_404_<variante>`. → Task 4.
5. Teto aplicado: amostra espalhada, determinística, e contada em `teto_compare_*`. → Tasks 1 e 4.

---

### Task 1: Funções puras de variantes (`metricas/variantes.py`)

**Files:** Create `metricas/variantes.py`; Test `tests/test_variantes.py`.

**Interfaces (Produces):**
```python
Unidade = {"nome": str, "data": datetime}   # nome = tag_name/tag; data = published_at ou author.date
def separar_janela(unidades: list[dict], start: datetime, end: datetime) -> tuple[dict | None, list[dict]]
def pares_para_compare(base: dict | None, na_janela: list[dict], max_compares: int | None = None) -> tuple[list[tuple[dict, dict]], int]
def lead_time_b_variante(resultados: list[tuple[datetime, list[datetime] | None]]) -> dict
    # {"lead_time_b_days": float | None, "compare_404": int, "n_lead_negativos": int}
```

- [ ] Step 1: testes falhando:
```python
def test_separar_janela_base_e_ordem():
    u = [un("v3", utc(2026, 2, 1)), un("v0", utc(2025, 8, 1)), un("v1", utc(2025, 9, 1)),
         un("v2", utc(2025, 11, 1)), un("v4", utc(2026, 10, 2))]
    base, na_janela = separar_janela(u, START, END)
    assert base["nome"] == "v1"
    assert [x["nome"] for x in na_janela] == ["v2", "v3"]

def test_separar_janela_sem_unidades(): assert separar_janela([], START, END) == (None, [])

def test_pares_com_base_e_sem_base():
    a, b, c = un("a", utc(2025, 9, 1)), un("b", utc(2025, 11, 1)), un("c", utc(2025, 12, 1))
    assert pares_para_compare(a, [b, c]) == ([(a, b), (b, c)], 0)
    assert pares_para_compare(None, [b, c]) == ([(b, c)], 0)   # primeira da história ignorada
    assert pares_para_compare(None, [b]) == ([], 0)

def test_teto_amostra_pares_espalhados_e_conta_os_pulados():
    seq = [un(f"t{i}", utc(2025, 10, 1) + timedelta(days=i)) for i in range(11)]  # 10 pares
    pares, pulados = pares_para_compare(None, seq, max_compares=4)
    assert [p[1]["nome"] for p in pares] == ["t1", "t3", "t6", "t8"]   # i*10//4 = 0, 2, 5, 7
    assert pulados == 6

def test_teto_maior_que_pares_nao_amostra(): ...  # max_compares=50 -> todos, 0 pulados

def test_lead_time_b_variante_exemplo_do_enunciado():
    r = utc(2026, 3, 15)
    out = lead_time_b_variante([(r, [utc(2026, 3, 2), utc(2026, 3, 10), utc(2026, 3, 14)])])
    assert out == {"lead_time_b_days": 5, "compare_404": 0, "n_lead_negativos": 0}

def test_lead_time_b_variante_404_negativo_e_sem_commits():
    r = utc(2026, 3, 15)
    out = lead_time_b_variante([(r, None), (r, []), (r, [utc(2026, 3, 16), utc(2026, 3, 14)])])
    assert out == {"lead_time_b_days": 1, "compare_404": 1, "n_lead_negativos": 1}

def test_lead_time_b_variante_vazio():
    assert lead_time_b_variante([]) == {"lead_time_b_days": None, "compare_404": 0, "n_lead_negativos": 0}
```
- [ ] Step 2: `pytest tests/test_variantes.py -v` → FAIL (`ModuleNotFoundError: metricas.variantes`).
- [ ] Step 3: implementação mínima:
```python
def separar_janela(unidades, start, end):
    ordenadas = sorted(unidades, key=lambda u: u["data"])
    anteriores = [u for u in ordenadas if u["data"] < start]
    return (anteriores[-1] if anteriores else None), [u for u in ordenadas if start <= u["data"] <= end]

def pares_para_compare(base, na_janela, max_compares=None):
    sequencia = ([base] if base is not None else []) + list(na_janela)
    pares = list(zip(sequencia, sequencia[1:]))
    n = len(pares)
    if max_compares is None or n <= max_compares:
        return pares, 0
    return [pares[i * n // max_compares] for i in range(max_compares)], n - max_compares

def lead_time_b_variante(resultados):
    por_commit, compare_404, negativos = [], 0, 0
    for data_unidade, datas in resultados:
        if datas is None:
            compare_404 += 1
            continue
        por_commit.extend(lead_time_commits_days(data_unidade, datas))
        negativos += contar_lead_negativos(data_unidade, datas)
    return {"lead_time_b_days": repo_lead_time_b(por_commit), "compare_404": compare_404,
            "n_lead_negativos": negativos}
```
- [ ] Step 4: testes passam. Step 5: commits `test(variantes): ... (#24)` e `feat(variantes): ... (#24)`.

### Task 2: Base `release+pre` em `fetch_releases`

**Files:** Modify `pipeline/releases.py` (`fetch_releases`); Test `tests/test_releases.py`.

**Interfaces:** `fetch_releases(client, full_name, start, end, base_inclui_pre: bool = False) -> list[dict]` (padrão igual ao contrato da S01).

- [ ] Step 1: teste falhando:
```python
def test_base_inclui_pre_usa_a_ultima_unidade_antes_da_janela():
    client = FakeClient({PATH: [
        rel("v1.0", "2025-08-01T00:00:00Z"),
        rel("v2.0-rc1", "2025-09-20T00:00:00Z", prerelease=True),
        rel("v2.0", "2025-11-01T00:00:00Z"),
    ]})
    assert tags(fetch_releases(client, "octo/hello", START, END, base_inclui_pre=True)) == ["v2.0-rc1", "v2.0"]
    assert tags(fetch_releases(client, "octo/hello", START, END)) == ["v1.0", "v2.0"]
```
- [ ] Step 2: FAIL (`unexpected keyword argument`). Step 3: `anteriores = [r for r in releases if r["published_at"] < start and (base_inclui_pre or not r["prerelease"])]`. Step 4: PASS. Step 5: commit `feat(releases): base do compare pode ser pré-release na variante release+pre (#24)`.

### Task 3: Coleta de tags (`pipeline/tags.py`)

**Files:** Create `pipeline/tags.py`; Test `tests/test_tags.py`.

**Interfaces (Produces):**
```python
CANDIDATOS_BASE = 5
def fetch_tags(client, full_name: str) -> list[dict]                  # [{"name", "sha"}] na ordem da API
def datas_commits_branch(client, full_name: str, branch: str, start: datetime, end: datetime) -> dict[str, datetime]
def data_do_commit(client, full_name: str, sha: str) -> datetime | None   # git/commits/{sha}; 404 -> None
def tags_com_data(client, full_name: str, branch: str, start: datetime, end: datetime,
                  candidatos_base: int = CANDIDATOS_BASE) -> list[dict]    # [{"nome", "data"}]: tags da janela + base
```
Chamadas: `paginate("/repos/{fn}/tags")`; `paginate("/repos/{fn}/commits", params={"sha": branch, "since": "2025-10-01T00:00:00Z", "until": "2026-09-30T23:59:59Z"})`; `get("/repos/{fn}/git/commits/{sha}")`.

- [ ] Step 1: testes falhando (FakeClient com `paginate` e `get` por path, registrando chamadas):
  - `fetch_tags` mapeia `name` e `commit.sha` e preserva a ordem;
  - `datas_commits_branch` envia `sha/since/until` e mapeia `sha -> commit.author.date`;
  - `data_do_commit` lê `author.date` de `git/commits/{sha}`; 404 → `None`;
  - repo sem tags → `[]` e nenhuma chamada a `/commits`;
  - tags fora do default branch ou da janela ficam de fora; tag com `author.date` antes da janela, mas listada pelo committer date, fica de fora;
  - base: primeira candidata, depois da última tag da janela na ordem da API, com data < start; candidata em data ≥ start é ignorada; candidata 404 é ignorada; no máximo `candidatos_base` chamadas;
  - nenhuma tag na janela → `[]` e nenhuma chamada a `git/commits`.
- [ ] Step 2: FAIL. Step 3: implementação. Step 4: PASS. Step 5: commits `test(tags)`/`feat(tags)` `(#24)`.

### Task 4: Etapa de variantes (`pipeline/etapa_variantes.py`)

**Files:** Create `pipeline/etapa_variantes.py`; Test `tests/test_etapa_variantes.py`.

**Interfaces (Produces):**
```python
MAX_COMPARES_PADRAO = 100
def coletar_variantes(client, meta: dict, janela: tuple[datetime, datetime],
                      max_compares: int | None = MAX_COMPARES_PADRAO) -> dict
# chaves: n_releases_pre, deploy_freq_week_pre, lead_time_b_days_pre, compare_404_pre, n_lead_negativos_pre, teto_compare_pre,
#         n_tags, deploy_freq_week_tag, lead_time_b_days_tag, compare_404_tag, n_lead_negativos_tag, teto_compare_tag
```
**Consumes:** `fetch_releases(..., base_inclui_pre=True)`, `fetch_commits`, `tags_com_data`, `separar_janela`, `pares_para_compare`, `lead_time_b_variante`, `semanas_da_janela`.

- [ ] Step 1: testes falhando (FakeClient roteando releases, tags, commits, git/commits, compare):
  - `release+pre`: conta releases e pré-releases da janela; compare entre unidades consecutivas incluindo pré-releases; base pré-release antes da janela;
  - pré-release como primeira unidade da história (dentro da janela): ignorada no lead time, contada na frequência;
  - tag: exemplo do enunciado (lead time (b) = 5); tag sem commits novos; compare 404 contado em `compare_404_tag`;
  - repo sem tags: `n_tags=0`, `deploy_freq_week_tag=0`, `lead_time_b_days_tag=None`;
  - teto: 12 tags na janela, sem base (11 pares), `max_compares=3` → 3 compares chamados e `teto_compare_tag == 8`; `max_compares=None` → 11.
- [ ] Step 2: FAIL. Step 3: implementação. Step 4: PASS. Step 5: commits `(#24)`.

### Task 5: Orquestrador, config e dicionário

**Files:** Modify `pipeline/orquestrador.py`, `config.yaml`, `data/DICIONARIO.md`; Test `tests/test_orquestrador.py`, `tests/test_config.py`.

- [ ] Step 1: testes falhando:
  - `COLUNAS` contém as 12 colunas novas, nessa ordem, depois de `meses_no_teto`; a linha do repo válido do FakeClient (5 releases, sem tags) tem `n_releases_pre == 5`, `deploy_freq_week_pre == deploy_freq_week`, `n_tags == 0`, `deploy_freq_week_tag == 0`;
  - repositórios descartados não chamam `/tags`;
  - `max_compares_variante` do config chega a `coletar_variantes` (teste com tags no FakeClient e teto 1 → `teto_compare_tag` > 0);
  - `config.yaml` versionado tem `max_compares_variante` inteiro positivo.
- [ ] Step 2: FAIL. Step 3: `_processar(client, full_name, janela, max_compares)` chama `coletar_variantes` depois do critério de runs; `executar` lê `cfg.get("max_compares_variante", MAX_COMPARES_PADRAO)` (`null` → `None`); colunas inteiras novas em `COLUNAS_INTEIRAS`; `config.yaml` com `max_compares_variante: 100` comentado; `DICIONARIO.md` com as 12 colunas (nome, tipo, unidade, fórmula/origem). Step 4: PASS. Step 5: commits `(#24)`.

### Task 6: Execução real pequena e verificação

- [ ] Rodar `python -m pipeline --config <scratchpad>/config.yaml` com `repos: [jasmine/jasmine, jeffbski/wait-on, nginx-proxy/nginx-proxy]`, `cache_dir` no scratchpad e `cwd` no scratchpad (a saída `data/` fica fora do repositório). Conferir as colunas novas e medir as chamadas por repo (contagem de arquivos novos no cache).
- [ ] `pytest --cov=metricas --cov-report=term-missing` verde, cobertura ≥ 80%.

---

## Registro da execução (2026-10-15)

- **Decisões tomadas durante a execução:**
  - Testes de `tests/test_retomada.py`: a `SessaoFake` passou a responder `/tags` e `/commits`, e o repo `o/b` ganhou tags. Assim a retomada após `Ctrl+C` também cobre as chamadas novas.
  - Tag-base: as até 5 candidatas são sempre consultadas (custo ≤ 5 chamadas por repo) e vence a mais recente antes da janela. Parar na primeira candidata pularia o caso de prefixos misturados na listagem.
- **Execução real** (`repos:` = jasmine/jasmine, jeffbski/wait-on, nginx-proxy/nginx-proxy, Jackett/Jackett). Cache em camadas: leitura do `cache/` do repositório sem alterá-lo, escrita só no scratchpad, saída fora de `data/`. Resultado: 108 chamadas novas no total.
  - jasmine: 10 releases, 16 release+pre, 18 tags. Lead time (b): 63,4 / 33,3 / 33,8 dias.
  - wait-on: 13 / 14 / 15 unidades.
  - nginx-proxy: 11 / 11 / 11 unidades; lead time (b) da tag ≈ o da release.
  - Jackett: 368 unidades em cada variante. O teto foi aplicado (`teto_compare_pre = teto_compare_tag = 268`). Custou 35 páginas de tags, 25 páginas de commits e 5 `git/commits`; os compares já estavam em cache (mesmos pares da unidade release).
