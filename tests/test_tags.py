"""Testes da coleta de tags (variante da RQ07). Cliente fake: nunca acessam a rede."""
from datetime import datetime, timedelta, timezone

import pytest

from pipeline.http import GitHubError, NotFoundError
from pipeline.tags import (
    CANDIDATOS_BASE,
    MENOR_FATIA,
    coletar_tags,
    listar_datas_commits,
    data_do_commit,
    datas_commits_branch,
    fetch_tags,
    tags_com_data,
)

START = datetime(2025, 10, 1, tzinfo=timezone.utc)
END = datetime(2026, 9, 30, 23, 59, 59, tzinfo=timezone.utc)
TAGS = "/repos/octo/hello/tags"
COMMITS = "/repos/octo/hello/commits"


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


class FakeClient:
    """path -> resposta (lista para paginate, dict para get) ou exceção; registra as chamadas."""

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def _resposta(self, path):
        resp = self.responses[path]
        if isinstance(resp, Exception):
            raise resp
        return resp

    def paginate(self, path, params=None, item_key=None):
        self.calls.append((path, dict(params or {})))
        return self._resposta(path)

    def get(self, path, params=None):
        self.calls.append((path, dict(params or {})))
        return self._resposta(path), {}


def tag(name, sha):
    return {"name": name, "commit": {"sha": sha, "url": f"https://x/{sha}"}}


def commit_lista(sha, author_date):
    return {"sha": sha, "commit": {"author": {"date": author_date}, "committer": {"date": author_date},
                                   "message": "msg"}}


def git_commit(author_date):
    return {"author": {"date": author_date}, "committer": {"date": author_date}, "message": "msg"}


def paths(client):
    return [path for path, _ in client.calls]


def test_fetch_tags_mapeia_nome_e_sha_na_ordem_da_api():
    client = FakeClient({TAGS: [tag("v1.10", "c"), tag("v1.9", "b"), tag("v1.2", "a")]})
    assert fetch_tags(client, "octo/hello") == [
        {"name": "v1.10", "sha": "c"}, {"name": "v1.9", "sha": "b"}, {"name": "v1.2", "sha": "a"},
    ]
    assert client.calls == [(TAGS, {})]


def test_datas_commits_branch_filtra_branch_e_janela_e_usa_author_date():
    client = FakeClient({COMMITS: [commit_lista("a", "2026-01-02T03:04:05Z")]})
    assert datas_commits_branch(client, "octo/hello", "main", START, END) == {"a": utc(2026, 1, 2, 3, 4, 5)}
    assert client.calls == [(COMMITS, {"sha": "main", "since": "2025-10-01T00:00:00Z",
                                       "until": "2026-09-30T23:59:59Z"})]


def test_data_do_commit_usa_git_commits_e_author_date():
    client = FakeClient({"/repos/octo/hello/git/commits/abc": git_commit("2025-09-01T10:00:00Z")})
    assert data_do_commit(client, "octo/hello", "abc") == utc(2025, 9, 1, 10)


def test_data_do_commit_404_devolve_none():
    client = FakeClient({"/repos/octo/hello/git/commits/abc": NotFoundError(404, "x", "No commit")})
    assert data_do_commit(client, "octo/hello", "abc") is None


def test_repo_sem_tags_nao_lista_commits():
    client = FakeClient({TAGS: []})
    assert tags_com_data(client, "octo/hello", "main", START, END) == []
    assert paths(client) == [TAGS]


def test_so_tags_de_commits_do_default_branch_com_author_date_na_janela():
    client = FakeClient({
        TAGS: [tag("v3", "s3"), tag("v2", "s2"), tag("v2-hotfix", "outro-branch"), tag("v1", "s1")],
        COMMITS: [
            commit_lista("s3", "2026-03-01T00:00:00Z"),
            commit_lista("s2", "2025-12-01T00:00:00Z"),
            # listado pela data do committer, mas escrito antes da janela: não é tag da janela
            commit_lista("s1", "2025-09-15T00:00:00Z"),
        ],
        "/repos/octo/hello/git/commits/outro-branch": git_commit("2025-12-10T00:00:00Z"),
    })
    resultado = tags_com_data(client, "octo/hello", "main", START, END)
    na_janela = [t for t in resultado if t["data"] >= START]
    assert sorted((t["nome"], t["data"]) for t in na_janela) == [
        ("v2", utc(2025, 12, 1)), ("v3", utc(2026, 3, 1))]


def test_base_e_a_candidata_mais_recente_antes_da_janela_sem_chamada_extra_se_ja_tem_data():
    client = FakeClient({
        TAGS: [tag("v3", "s3"), tag("v2", "s2"), tag("v1", "s1"), tag("v0", "s0")],
        COMMITS: [commit_lista("s3", "2026-03-01T00:00:00Z"), commit_lista("s2", "2025-12-01T00:00:00Z"),
                  commit_lista("s1", "2025-09-15T00:00:00Z")],
        "/repos/octo/hello/git/commits/s0": git_commit("2025-06-01T00:00:00Z"),
    })
    resultado = tags_com_data(client, "octo/hello", "main", START, END)
    assert {"nome": "v1", "data": utc(2025, 9, 15)} in resultado
    assert {"nome": "v0", "data": utc(2025, 6, 1)} not in resultado  # só a base mais recente entra
    assert len(resultado) == 3
    assert "/repos/octo/hello/git/commits/s1" not in paths(client)


def test_base_ignora_candidatas_na_janela_fora_do_branch_e_404():
    client = FakeClient({
        TAGS: [tag("v2", "s2"), tag("v2-rc", "rc"), tag("v1.9", "sumiu"), tag("v1", "s1")],
        COMMITS: [commit_lista("s2", "2025-12-01T00:00:00Z")],
        "/repos/octo/hello/git/commits/rc": git_commit("2025-11-20T00:00:00Z"),
        "/repos/octo/hello/git/commits/sumiu": NotFoundError(404, "x", "No commit"),
        "/repos/octo/hello/git/commits/s1": git_commit("2025-08-01T00:00:00Z"),
    })
    resultado = tags_com_data(client, "octo/hello", "main", START, END)
    assert sorted(t["nome"] for t in resultado) == ["v1", "v2"]


def test_base_consulta_no_maximo_candidatos_base_tags():
    antigas = [tag(f"v0.{i}", f"old{i}") for i in range(10, 0, -1)]
    responses = {
        TAGS: [tag("v1", "s1")] + antigas,
        COMMITS: [commit_lista("s1", "2025-12-01T00:00:00Z")],
    }
    for i in range(1, 11):  # todas fora do default branch e dentro da janela: nenhuma serve de base
        responses[f"/repos/octo/hello/git/commits/old{i}"] = git_commit("2025-11-01T00:00:00Z")
    client = FakeClient(responses)
    resultado = tags_com_data(client, "octo/hello", "main", START, END)
    assert [t["nome"] for t in resultado] == ["v1"]
    assert sum("/git/commits/" in p for p in paths(client)) == CANDIDATOS_BASE


def test_nenhuma_tag_na_janela_nao_busca_base():
    client = FakeClient({TAGS: [tag("v1", "s1")], COMMITS: []})
    assert tags_com_data(client, "octo/hello", "main", START, END) == []
    assert paths(client) == [TAGS, COMMITS]


# --------------------------------------------------------------------------- 5xx em paginação profunda (#81)
# Cliente real (`GitHubClient`) sobre uma sessão HTTP falsa que simula
# `GET /repos/{o}/{r}/commits?sha=&since=&until=&per_page=&page=` com `Link rel="next"`.

class FakeResponse:
    def __init__(self, status_code, json_data=None, headers=None):
        self.status_code = status_code
        self._json = json_data
        self.headers = headers or {}

    def json(self):
        if self._json is None:
            raise ValueError("sem corpo JSON")
        return self._json


class CommitsSession:
    """Lista de commits paginada; `falha(since, until, page)` decide quando responder 500."""

    def __init__(self, commits, falha=lambda since, until, page: False, per_page=2, ruins=()):
        self.commits = sorted(commits, key=lambda c: c["commit"]["author"]["date"], reverse=True)
        self.falha = falha
        self.per_page = per_page
        self.ruins = set(ruins)  # SHAs que a API não consegue servir: 500 em qualquer página que os contenha
        self.calls = []
        self.headers = {}

    def get(self, url, params=None, timeout=None):
        from urllib.parse import parse_qsl, urlencode, urlsplit
        partes = urlsplit(url)
        query = dict(parse_qsl(partes.query))
        query.update({k: str(v) for k, v in (params or {}).items()})
        self.calls.append(query)
        since, until = _parse(query["since"]), _parse(query["until"])
        page = int(query.get("page", 1))
        if self.falha(since, until, page):
            return FakeResponse(500, {"message": "Server Error"})
        selecionados = [c for c in self.commits if since <= _parse(c["commit"]["author"]["date"]) <= until]
        per_page = int(query["per_page"]) if "per_page" in (params or {}) and "page" in (params or {})             else self.per_page
        inicio = (page - 1) * per_page
        pagina = selecionados[inicio:inicio + per_page]
        if any(c["sha"] in self.ruins for c in pagina):
            return FakeResponse(500, {"message": "Server Error"})
        headers = {}
        if inicio + per_page < len(selecionados):
            proxima = urlencode({**{k: v for k, v in query.items() if k != "page"}, "page": page + 1})
            headers["Link"] = f'<https://api.github.com{partes.path}?{proxima}>; rel="next"'
        return FakeResponse(200, pagina, headers)


def _parse(valor):
    return datetime.fromisoformat(valor.replace("Z", "+00:00"))


def cliente_real(tmp_path, session):
    from pipeline.cache import DiskCache
    from pipeline.http import GitHubClient
    client = GitHubClient("tok", DiskCache(tmp_path / "cache"), sleep=lambda s: None, max_retries=1)
    client.session = session
    return client


def commits_da_janela():
    """Dois commits por mês da janela (24) e um fora dela."""
    commits = [commit_lista("fora", "2025-09-15T00:00:00Z")]
    for i in range(12):
        ano, mes = (2025, 10 + i) if i < 3 else (2026, i - 2)
        commits.append(commit_lista(f"m{i}a", f"{ano}-{mes:02d}-03T10:00:00Z"))
        commits.append(commit_lista(f"m{i}b", f"{ano}-{mes:02d}-25T22:00:00Z"))
    return commits


def esperado():
    return {item["sha"]: _parse(item["commit"]["author"]["date"])
            for item in commits_da_janela() if item["sha"] != "fora"}


def janela_inteira(since, until):
    return since == START and until == END


def test_consulta_unica_sem_falha_nao_fatia(tmp_path):
    session = CommitsSession(commits_da_janela())
    datas = datas_commits_branch(cliente_real(tmp_path, session), "octo/hello", "main", START, END)
    assert datas == esperado()
    assert all(janela_inteira(_parse(c["since"]), _parse(c["until"])) for c in session.calls)
    assert len(session.calls) == 12  # 24 commits, 2 por página


def test_500_persistente_em_pagina_profunda_refaz_fatiando_por_mes(tmp_path):
    session = CommitsSession(commits_da_janela(), falha=lambda s, u, p: janela_inteira(s, u) and p >= 5)
    datas = datas_commits_branch(cliente_real(tmp_path, session), "octo/hello", "main", START, END)
    assert datas == esperado()
    # primeira tentativa: a mesma consulta única de antes (chaves de cache preservadas)
    assert session.calls[0] == {"sha": "main", "since": "2025-10-01T00:00:00Z",
                                "until": "2026-09-30T23:59:59Z", "per_page": "100"}
    fatias = {(c["since"], c["until"]) for c in session.calls[1:]
              if not janela_inteira(_parse(c["since"]), _parse(c["until"]))}
    assert len(fatias) == 12
    assert ("2025-10-01T00:00:00Z", "2025-10-31T23:59:59Z") in fatias
    assert ("2026-09-01T00:00:00Z", "2026-09-30T23:59:59Z") in fatias


def test_fatia_mensal_que_tambem_falha_e_subdividida(tmp_path):
    def falha(since, until, page):
        return janela_inteira(since, until) or (since.month == 1 and until - since > timedelta(days=10))

    session = CommitsSession(commits_da_janela(), falha=falha)
    datas = datas_commits_branch(cliente_real(tmp_path, session), "octo/hello", "main", START, END)
    assert datas == esperado()
    janeiro = [c for c in session.calls if c["since"].startswith("2026-01")]
    assert any(_parse(c["until"]) - _parse(c["since"]) <= timedelta(days=10) for c in janeiro)


def test_tudo_falhando_levanta_github_error_depois_do_limite_de_subdivisao(tmp_path):
    session = CommitsSession(commits_da_janela(), falha=lambda s, u, p: True)
    with pytest.raises(GitHubError) as erro:
        datas_commits_branch(cliente_real(tmp_path, session), "octo/hello", "main", START, END)
    assert erro.value.status == 500
    menor = min(_parse(c["until"]) - _parse(c["since"]) for c in session.calls)
    assert menor >= MENOR_FATIA / 2 - timedelta(seconds=1)  # só fatias maiores que MENOR_FATIA são divididas


def test_erro_que_nao_e_5xx_nao_fatia(tmp_path):
    class Sessao422(CommitsSession):
        def get(self, url, params=None, timeout=None):
            self.calls.append(params)
            return FakeResponse(422, {"message": "Validation Failed"})

    session = Sessao422([])
    with pytest.raises(GitHubError) as erro:
        datas_commits_branch(cliente_real(tmp_path, session), "octo/hello", "main", START, END)
    assert erro.value.status == 422
    assert len(session.calls) == 1


def muitos_commits_em_um_dia(n=250):
    """n commits em 2026-09-05 (um por minuto), mais rápidos que MENOR_FATIA."""
    base = datetime(2026, 9, 5, 0, 0, tzinfo=timezone.utc)
    return [commit_lista(f"d{i:03d}", (base + timedelta(minutes=i)).strftime("%Y-%m-%dT%H:%M:%SZ"))
            for i in range(n)]


def test_commits_que_a_api_nao_serve_sao_pulados_e_contados_refinando_a_pagina(tmp_path):
    commits = muitos_commits_em_um_dia()
    ruins = {"d203", "d198", "d195"}  # como no hermes-agent: 3 commits vizinhos
    session = CommitsSession(commits, per_page=100, ruins=ruins)
    datas, omitidos = listar_datas_commits(cliente_real(tmp_path, session), "octo/hello", "main", START, END)
    assert omitidos == 3
    assert datas == {c["sha"]: _parse(c["commit"]["author"]["date"]) for c in commits if c["sha"] not in ruins}
    # páginas refinadas: per_page 10 e depois 1 só onde ainda falha
    assert {c.get("per_page") for c in session.calls} >= {"100", "10", "1"}
    assert sum(1 for c in session.calls if c.get("per_page") == "1") <= 30


def test_datas_commits_branch_devolve_so_as_datas(tmp_path):
    session = CommitsSession(muitos_commits_em_um_dia(30), per_page=100, ruins={"d010"})
    datas = datas_commits_branch(cliente_real(tmp_path, session), "octo/hello", "main", START, END)
    assert len(datas) == 29 and "d010" not in datas


def test_coletar_tags_devolve_commits_omitidos():
    client = FakeClient({TAGS: [tag("v1", "a")], COMMITS: [commit_lista("a", "2026-01-02T03:04:05Z")]})
    unidades, omitidos = coletar_tags(client, "octo/hello", "main", START, END)
    assert unidades == [{"nome": "v1", "data": utc(2026, 1, 2, 3, 4, 5)}]
    assert omitidos == 0
