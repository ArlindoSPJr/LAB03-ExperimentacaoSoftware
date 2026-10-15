"""Testes da etapa de variantes (release+pre e tag) do orquestrador. Nunca acessam a rede."""
from datetime import datetime, timedelta, timezone

import pytest

from pipeline.etapa_releases import semanas_da_janela
from pipeline.etapa_variantes import MAX_COMPARES_PADRAO, coletar_variantes
from pipeline.http import NotFoundError

START = datetime(2025, 10, 1, tzinfo=timezone.utc)
END = datetime(2026, 9, 30, 23, 59, 59, tzinfo=timezone.utc)
JANELA = (START, END)
SEMANAS = semanas_da_janela(START, END)
META = {"full_name": "octo/hello", "default_branch": "main"}
R = "/repos/octo/hello"


class FakeClient:
    """path -> resposta ou exceção. Compare sem resposta definida devolve []."""

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def _resposta(self, path, padrao):
        resp = self.responses.get(path, padrao)
        if isinstance(resp, Exception):
            raise resp
        return resp

    def paginate(self, path, params=None, item_key=None):
        self.calls.append(path)
        return self._resposta(path, [])

    def get(self, path, params=None):
        self.calls.append(path)
        return self._resposta(path, None), {}


def rel(tag, published_at, prerelease=False):
    return {"tag_name": tag, "published_at": published_at, "draft": False, "prerelease": prerelease, "body": ""}


def tag(name, sha):
    return {"name": name, "commit": {"sha": sha}}


def commit(sha, date):
    return {"sha": sha, "commit": {"author": {"date": date}, "message": "feat: x"}}


def compare(base, head):
    return f"{R}/compare/{base}...{head}"


def compares(client):
    return [c for c in client.calls if "/compare/" in c]


def test_release_mais_pre_conta_pre_releases_e_compara_unidades_consecutivas():
    client = FakeClient({
        f"{R}/releases": [
            rel("v1.0", "2025-08-01T00:00:00Z"),
            rel("v2.0-rc1", "2025-09-20T00:00:00Z", prerelease=True),  # base: unidade anterior do mesmo tipo
            rel("v2.0", "2025-11-01T00:00:00Z"),
            rel("v2.1-rc1", "2026-03-10T00:00:00Z", prerelease=True),
            rel("v2.1", "2026-03-15T00:00:00Z"),
        ],
        compare("v2.1-rc1", "v2.1"): [commit("a", "2026-03-02T00:00:00Z"), commit("b", "2026-03-10T00:00:00Z"),
                                      commit("c", "2026-03-14T00:00:00Z")],
    })
    resultado = coletar_variantes(client, META, JANELA)
    assert resultado["n_releases_pre"] == 3
    assert resultado["deploy_freq_week_pre"] == pytest.approx(3 / SEMANAS)
    assert compares(client) == [compare("v2.0-rc1", "v2.0"), compare("v2.0", "v2.1-rc1"),
                                compare("v2.1-rc1", "v2.1")]
    assert resultado["lead_time_b_days_pre"] == 5  # exemplo do enunciado: [13, 5, 1]
    assert resultado["compare_404_pre"] == 0
    assert resultado["teto_compare_pre"] == 0


def test_pre_release_como_primeira_unidade_da_historia_fica_sem_lead_time():
    client = FakeClient({f"{R}/releases": [
        rel("v1.0-beta", "2025-10-10T00:00:00Z", prerelease=True),
        rel("v1.0", "2025-11-01T00:00:00Z"),
    ]})
    resultado = coletar_variantes(client, META, JANELA)
    assert resultado["n_releases_pre"] == 2
    assert compares(client) == [compare("v1.0-beta", "v1.0")]
    assert resultado["lead_time_b_days_pre"] is None  # compare sem commits novos


def test_repo_sem_tags():
    resultado = coletar_variantes(FakeClient({f"{R}/tags": []}), META, JANELA)
    assert resultado["n_tags"] == 0
    assert resultado["deploy_freq_week_tag"] == 0
    assert resultado["lead_time_b_days_tag"] is None
    assert resultado["compare_404_tag"] == 0
    assert resultado["teto_compare_tag"] == 0


def test_tags_exemplo_do_enunciado_tag_sem_commits_novos_e_compare_404():
    client = FakeClient({
        f"{R}/tags": [tag("v1.3", "s3"), tag("v1.2", "s2"), tag("v1.1", "s1"), tag("v1.0", "s0")],
        f"{R}/commits": [commit("s3", "2026-05-01T00:00:00Z"), commit("s2", "2026-04-01T00:00:00Z"),
                         commit("s1", "2026-03-15T00:00:00Z")],
        f"{R}/git/commits/s0": {"author": {"date": "2025-09-01T00:00:00Z"}},
        compare("v1.0", "v1.1"): [commit("a", "2026-03-02T00:00:00Z"), commit("b", "2026-03-10T00:00:00Z"),
                                  commit("c", "2026-03-14T00:00:00Z")],
        compare("v1.1", "v1.2"): [],                               # tag sem commits novos
        compare("v1.2", "v1.3"): NotFoundError(404, "x", "Not Found"),
    })
    resultado = coletar_variantes(client, META, JANELA)
    assert resultado["n_tags"] == 3
    assert resultado["deploy_freq_week_tag"] == pytest.approx(3 / SEMANAS)
    # data da tag v1.1 = author.date do commit s1 (2026-03-15): exemplo do enunciado [13, 5, 1]
    assert resultado["lead_time_b_days_tag"] == 5
    assert resultado["compare_404_tag"] == 1
    assert resultado["n_lead_negativos_tag"] == 0


def test_teto_de_compares_amostra_e_conta_unidades_puladas():
    datas = [START + timedelta(days=10 * i) for i in range(12)]
    responses = {
        f"{R}/tags": [tag(f"b{i}", f"s{i}") for i in reversed(range(12))],
        f"{R}/commits": [commit(f"s{i}", d.strftime("%Y-%m-%dT%H:%M:%SZ")) for i, d in enumerate(datas)],
    }
    for i in range(12):  # nenhuma base: as candidatas não existem
        responses[f"{R}/git/commits/s{i}"] = NotFoundError(404, "x", "")
    client = FakeClient(responses)
    resultado = coletar_variantes(client, META, JANELA, max_compares=3)
    assert resultado["n_tags"] == 12
    assert len(compares(client)) == 3
    assert resultado["teto_compare_tag"] == 8  # 11 pares, 3 comparados

    sem_teto = FakeClient(responses)
    assert coletar_variantes(sem_teto, META, JANELA, max_compares=None)["teto_compare_tag"] == 0
    assert len(compares(sem_teto)) == 11


def test_teto_padrao():
    assert MAX_COMPARES_PADRAO == 100
