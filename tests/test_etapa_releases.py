"""Testes da etapa de releases e lead time do orquestrador. Nunca acessam a rede."""
from datetime import datetime, timezone

import pytest

from pipeline.etapa_releases import coletar_releases_e_lead_time, semanas_da_janela
from pipeline.http import NotFoundError

START = datetime(2025, 10, 1, tzinfo=timezone.utc)
END = datetime(2026, 9, 30, 23, 59, 59, tzinfo=timezone.utc)
JANELA = (START, END)
META = {"full_name": "octo/hello", "default_branch": "main"}
RELEASES = "/repos/octo/hello/releases"


class FakeClient:
    """Cliente fake: path -> lista já paginada ou exceção; registra os paths chamados."""

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def paginate(self, path, params=None, item_key=None):
        self.calls.append(path)
        resp = self.responses.get(path, [])
        if isinstance(resp, Exception):
            raise resp
        return resp


def rel(tag, published_at, prerelease=False):
    return {"tag_name": tag, "published_at": published_at, "draft": False,
            "prerelease": prerelease, "body": ""}


def commit(date):
    return {"sha": date, "commit": {"author": {"date": date}, "message": "fix"}}


def compare(base, head):
    return f"/repos/octo/hello/compare/{base}...{head}"


def test_semanas_da_janela_de_12_meses():
    assert semanas_da_janela(START, END) == pytest.approx(52.14, abs=0.01)


def test_conta_so_releases_nao_pre_release_dentro_da_janela():
    client = FakeClient({RELEASES: [
        rel("v0.9", "2025-09-01T00:00:00Z"),            # anterior à janela: só base do compare
        rel("v1.0", "2025-11-01T00:00:00Z"),
        rel("v1.1-rc1", "2025-11-20T00:00:00Z", prerelease=True),
        rel("v1.1", "2025-12-01T00:00:00Z"),
        rel("v2.0", "2026-10-05T00:00:00Z"),            # depois da janela
    ]})
    resultado = coletar_releases_e_lead_time(client, META, JANELA)
    assert resultado["n_releases"] == 2
    assert resultado["deploy_freq_week"] == pytest.approx(2 / (365 / 7))


def test_lead_time_exemplo_do_enunciado_com_release_anterior_fora_da_janela():
    client = FakeClient({
        RELEASES: [rel("v1.0", "2025-09-01T00:00:00Z"), rel("v1.1", "2026-03-15T00:00:00Z")],
        compare("v1.0", "v1.1"): [commit("2026-03-02T00:00:00Z"), commit("2026-03-10T00:00:00Z"),
                                  commit("2026-03-14T00:00:00Z")],
    })
    resultado = coletar_releases_e_lead_time(client, META, JANELA)
    assert resultado["lead_time_a_days"] == 13
    assert resultado["lead_time_b_days"] == 5
    assert resultado["compare_404"] == 0
    assert resultado["n_lead_negativos"] == 0


def test_compare_entre_releases_consecutivas_ignorando_pre_releases():
    client = FakeClient({RELEASES: [
        rel("v1.0", "2025-11-01T00:00:00Z"),
        rel("v1.1-rc1", "2025-11-20T00:00:00Z", prerelease=True),
        rel("v1.1", "2025-12-01T00:00:00Z"),
        rel("v1.2", "2026-01-01T00:00:00Z"),
    ]})
    coletar_releases_e_lead_time(client, META, JANELA)
    assert client.calls == [RELEASES, compare("v1.0", "v1.1"), compare("v1.1", "v1.2")]


def test_medianas_entre_releases():
    client = FakeClient({
        RELEASES: [rel("v1", "2025-11-01T00:00:00Z"), rel("v2", "2025-11-11T00:00:00Z"),
                   rel("v3", "2025-11-21T00:00:00Z")],
        compare("v1", "v2"): [commit("2025-11-01T00:00:00Z"), commit("2025-11-10T00:00:00Z")],  # 10 e 1
        compare("v2", "v3"): [commit("2025-11-19T00:00:00Z")],                                   # 2
    })
    resultado = coletar_releases_e_lead_time(client, META, JANELA)
    assert resultado["lead_time_a_days"] == 6     # mediana de [10, 2]
    assert resultado["lead_time_b_days"] == 2     # mediana de [10, 1, 2]


def test_primeira_release_da_historia_e_ignorada_no_lead_time():
    client = FakeClient({
        RELEASES: [rel("v1.0", "2025-11-01T00:00:00Z"), rel("v1.1", "2025-11-11T00:00:00Z")],
        compare("v1.0", "v1.1"): [commit("2025-11-10T00:00:00Z")],
    })
    resultado = coletar_releases_e_lead_time(client, META, JANELA)
    assert resultado["n_releases"] == 2
    assert resultado["lead_time_a_days"] == 1
    assert client.calls == [RELEASES, compare("v1.0", "v1.1")]


def test_repositorio_com_uma_unica_release():
    client = FakeClient({RELEASES: [rel("v1.0", "2026-01-01T00:00:00Z")]})
    resultado = coletar_releases_e_lead_time(client, META, JANELA)
    assert resultado == {
        "n_releases": 1,
        "deploy_freq_week": pytest.approx(1 / (365 / 7)),
        "lead_time_a_days": None,
        "lead_time_b_days": None,
        "compare_404": 0,
        "n_lead_negativos": 0,
    }
    assert client.calls == [RELEASES]


def test_repositorio_sem_releases():
    resultado = coletar_releases_e_lead_time(FakeClient({RELEASES: []}), META, JANELA)
    assert resultado["n_releases"] == 0
    assert resultado["deploy_freq_week"] == 0
    assert resultado["lead_time_a_days"] is None


def test_compare_404_ignora_a_release_e_conta():
    client = FakeClient({
        RELEASES: [rel("v1", "2025-11-01T00:00:00Z"), rel("v2", "2025-11-11T00:00:00Z"),
                   rel("v3", "2025-11-21T00:00:00Z")],
        compare("v1", "v2"): NotFoundError(404, "compare", "Not Found"),
        compare("v2", "v3"): [commit("2025-11-19T00:00:00Z")],
    })
    resultado = coletar_releases_e_lead_time(client, META, JANELA)
    assert resultado["compare_404"] == 1
    assert resultado["lead_time_a_days"] == 2


def test_release_sem_commits_novos_nao_quebra():
    client = FakeClient({RELEASES: [rel("v1", "2025-11-01T00:00:00Z"), rel("v2", "2025-11-11T00:00:00Z")]})
    resultado = coletar_releases_e_lead_time(client, META, JANELA)
    assert resultado["lead_time_a_days"] is None
    assert resultado["lead_time_b_days"] is None


def test_lead_negativos_somados_entre_releases():
    client = FakeClient({
        RELEASES: [rel("v1", "2025-11-01T00:00:00Z"), rel("v2", "2025-11-11T00:00:00Z"),
                   rel("v3", "2025-11-21T00:00:00Z")],
        compare("v1", "v2"): [commit("2025-11-12T00:00:00Z"), commit("2025-11-10T00:00:00Z")],
        compare("v2", "v3"): [commit("2025-11-22T00:00:00Z")],
    })
    resultado = coletar_releases_e_lead_time(client, META, JANELA)
    assert resultado["n_lead_negativos"] == 2
    assert resultado["lead_time_a_days"] == 1
