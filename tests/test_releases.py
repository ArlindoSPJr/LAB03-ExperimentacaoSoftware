"""Testes da coleta de releases. Nunca acessam a rede."""
from datetime import datetime, timezone

from pipeline.http import NotFoundError
from pipeline.releases import fetch_commits, fetch_releases

START = datetime(2025, 10, 1, tzinfo=timezone.utc)
END = datetime(2026, 9, 30, 23, 59, 59, tzinfo=timezone.utc)
PATH = "/repos/octo/hello/releases"


class FakeClient:
    """Cliente fake: path -> lista já paginada; registra as chamadas a paginate."""

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def paginate(self, path, params=None, item_key=None):
        self.calls.append((path, dict(params or {}), item_key))
        resp = self.responses[path]
        if isinstance(resp, Exception):
            raise resp
        return resp


def rel(tag, published_at, draft=False, prerelease=False, body="notas"):
    return {"tag_name": tag, "published_at": published_at, "draft": draft,
            "prerelease": prerelease, "body": body}


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


def tags(releases):
    return [r["tag_name"] for r in releases]


def test_mapeia_campos_do_contrato_release():
    client = FakeClient({PATH: [rel("v1.0", "2026-03-15T12:00:00Z", body="Corrige X")]})
    assert fetch_releases(client, "octo/hello", START, END) == [
        {"tag_name": "v1.0", "published_at": utc(2026, 3, 15, 12), "prerelease": False, "body": "Corrige X"},
    ]
    assert client.calls == [(PATH, {}, None)]


def test_draft_descartado():
    client = FakeClient({PATH: [
        rel("v1.1", "2026-04-01T00:00:00Z", draft=True),
        rel("v1.0", "2026-03-01T00:00:00Z"),
    ]})
    assert tags(fetch_releases(client, "octo/hello", START, END)) == ["v1.0"]


def test_draft_sem_published_at_nao_quebra():
    client = FakeClient({PATH: [rel("v2.0", None, draft=True), rel("v1.0", "2026-03-01T00:00:00Z")]})
    assert tags(fetch_releases(client, "octo/hello", START, END)) == ["v1.0"]


def test_ordenadas_por_published_at_crescente():
    client = FakeClient({PATH: [
        rel("v1.2", "2026-05-01T00:00:00Z"),
        rel("v1.0", "2026-01-01T00:00:00Z"),
        rel("v1.1", "2026-03-01T00:00:00Z"),
    ]})
    assert tags(fetch_releases(client, "octo/hello", START, END)) == ["v1.0", "v1.1", "v1.2"]


def test_pre_releases_mantidas_com_flag():
    client = FakeClient({PATH: [
        rel("v2.0-rc1", "2026-04-01T00:00:00Z", prerelease=True),
        rel("v1.0", "2026-03-01T00:00:00Z"),
    ]})
    releases = fetch_releases(client, "octo/hello", START, END)
    assert [(r["tag_name"], r["prerelease"]) for r in releases] == [("v1.0", False), ("v2.0-rc1", True)]


def test_inclui_release_anterior_a_janela_nao_pre_release():
    client = FakeClient({PATH: [
        rel("v1.0", "2026-01-10T00:00:00Z"),
        rel("v0.9-rc1", "2025-09-20T00:00:00Z", prerelease=True),
        rel("v0.9", "2025-09-01T00:00:00Z"),
        rel("v0.8", "2025-06-01T00:00:00Z"),
    ]})
    assert tags(fetch_releases(client, "octo/hello", START, END)) == ["v0.9", "v1.0"]


def test_sem_release_anterior_a_janela():
    client = FakeClient({PATH: [rel("v1.0", "2026-01-10T00:00:00Z")]})
    assert tags(fetch_releases(client, "octo/hello", START, END)) == ["v1.0"]


def test_releases_depois_da_janela_ficam_de_fora():
    client = FakeClient({PATH: [
        rel("v2.0", "2026-10-01T00:00:00Z"),
        rel("v1.0", "2026-09-30T23:00:00Z"),
    ]})
    assert tags(fetch_releases(client, "octo/hello", START, END)) == ["v1.0"]


def test_limites_da_janela_inclusivos():
    client = FakeClient({PATH: [
        rel("fim", "2026-09-30T23:59:59Z"),
        rel("inicio", "2025-10-01T00:00:00Z"),
    ]})
    assert tags(fetch_releases(client, "octo/hello", START, END)) == ["inicio", "fim"]


def test_repositorio_sem_releases():
    assert fetch_releases(FakeClient({PATH: []}), "octo/hello", START, END) == []


def test_repositorio_com_uma_unica_release():
    client = FakeClient({PATH: [rel("v1.0", "2026-02-01T00:00:00Z", body=None)]})
    assert fetch_releases(client, "octo/hello", START, END) == [
        {"tag_name": "v1.0", "published_at": utc(2026, 2, 1), "prerelease": False, "body": None},
    ]


# --------------------------------------------------------------------------- fetch_commits

COMPARE = "/repos/octo/hello/compare/v1.0...v1.1"


def gh_commit(sha, date, message):
    return {"sha": sha, "commit": {"author": {"name": "x", "date": date}, "message": message}}


def test_commits_mapeados_para_contrato_commit():
    client = FakeClient({COMPARE: [
        gh_commit("a1", "2026-03-02T10:00:00Z", "fix: corrige bug\n\ncorpo"),
        gh_commit("b2", "2026-03-10T08:30:00-03:00", "feat: nova api"),
    ]})
    assert fetch_commits(client, "octo/hello", "v1.0", "v1.1") == [
        {"sha": "a1", "author_date": utc(2026, 3, 2, 10), "message": "fix: corrige bug\n\ncorpo"},
        {"sha": "b2", "author_date": utc(2026, 3, 10, 11, 30), "message": "feat: nova api"},
    ]


def test_compare_paginado_pela_chave_commits():
    client = FakeClient({COMPARE: []})
    fetch_commits(client, "octo/hello", "v1.0", "v1.1")
    assert client.calls == [(COMPARE, {}, "commits")]


def test_compare_com_mais_de_250_commits_traz_todos():
    commits = [gh_commit(f"s{i}", "2026-03-02T10:00:00Z", f"commit {i}") for i in range(300)]
    result = fetch_commits(FakeClient({COMPARE: commits}), "octo/hello", "v1.0", "v1.1")
    assert len(result) == 300
    assert result[-1]["sha"] == "s299"


def test_release_sem_commits_novos_devolve_lista_vazia():
    assert fetch_commits(FakeClient({COMPARE: []}), "octo/hello", "v1.0", "v1.1") == []


def test_compare_404_devolve_none_e_registra(caplog):
    client = FakeClient({COMPARE: NotFoundError(404, COMPARE, "Not Found")})
    assert fetch_commits(client, "octo/hello", "v1.0", "v1.1") is None
    assert "v1.0...v1.1" in caplog.text


def test_tag_com_caracteres_especiais_e_codificada():
    path = "/repos/octo/hello/compare/release/1.0%2Bbuild...release/1.1"
    client = FakeClient({path: []})
    assert fetch_commits(client, "octo/hello", "release/1.0+build", "release/1.1") == []
