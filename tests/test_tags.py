"""Testes da coleta de tags (variante da RQ07). Cliente fake: nunca acessam a rede."""
from datetime import datetime, timezone

from pipeline.http import NotFoundError
from pipeline.tags import (
    CANDIDATOS_BASE,
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
