"""Testes dos metadados de repositório e do funil de seleção. Nunca acessam a rede."""
from datetime import datetime, timezone

import pytest
from requests.structures import CaseInsensitiveDict

from pipeline.funil import Funnel
from pipeline.http import GitHubError, NotFoundError
from pipeline.metadados import collect_metadata


class FakeClient:
    """Cliente fake: path -> (json, headers) ou exceção; registra as chamadas a get."""

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get(self, path, params=None):
        self.calls.append((path, dict(params or {})))
        resp = self.responses[path]
        if isinstance(resp, Exception):
            raise resp
        data, headers = resp
        return data, CaseInsensitiveDict(headers)


REPO = {
    "full_name": "octo/hello",
    "stargazers_count": 1234,
    "language": "Python",
    "created_at": "2015-03-10T12:34:56Z",
    "default_branch": "develop",
}
CONTRIB = "/repos/octo/hello/contributors"


def link_last(last):
    base = "https://api.github.com/repositories/42/contributors?per_page=1&anon=true"
    return {"Link": f'<{base}&page=2>; rel="next", <{base}&page={last}>; rel="last"'}


def client_with(contrib, repo=REPO):
    return FakeClient({"/repos/octo/hello": (repo, {}), CONTRIB: contrib})


# --------------------------------------------------------------------------- Funnel

def test_funil_calcula_descartados_entre_etapas():
    funil = Funnel()
    funil.add("candidatos", 4000)
    funil.add("com Actions", 2900, "sem workflows")
    funil.add(">=5 releases e >=50 runs", 610, "poucas releases ou runs")
    funil.add("amostra final", 350, "amostra atingida")
    df = funil.to_dataframe()
    assert list(df.columns) == ["etapa", "restantes", "descartados", "motivo"]
    assert df.to_dict("records") == [
        {"etapa": "candidatos", "restantes": 4000, "descartados": 0, "motivo": ""},
        {"etapa": "com Actions", "restantes": 2900, "descartados": 1100, "motivo": "sem workflows"},
        {"etapa": ">=5 releases e >=50 runs", "restantes": 610, "descartados": 2290,
         "motivo": "poucas releases ou runs"},
        {"etapa": "amostra final", "restantes": 350, "descartados": 260, "motivo": "amostra atingida"},
    ]


def test_funil_vazio_tem_colunas_e_nenhuma_linha():
    df = Funnel().to_dataframe()
    assert list(df.columns) == ["etapa", "restantes", "descartados", "motivo"]
    assert df.empty


# --------------------------------------------------------------------------- collect_metadata

def test_metadados_campos_do_repositorio():
    meta = collect_metadata(client_with(([{"login": "a"}], link_last(87))), "octo/hello")
    assert meta == {
        "full_name": "octo/hello",
        "stars": 1234,
        "language": "Python",
        "contributors": 87,
        "created_at": datetime(2015, 3, 10, 12, 34, 56, tzinfo=timezone.utc),
        "default_branch": "develop",
    }
    assert meta["created_at"].utcoffset().total_seconds() == 0


def test_metadados_contributors_pede_uma_por_pagina_com_anonimos():
    client = client_with(([{"login": "a"}], link_last(5)))
    collect_metadata(client, "octo/hello")
    assert (CONTRIB, {"per_page": 1, "anon": "true"}) in client.calls


@pytest.mark.parametrize("corpo, esperado", [
    ([{"login": "unico"}], 1),   # um único contribuidor: sem Link
    ([], 0),                     # lista vazia
    (None, 0),                   # 204 sem corpo (repositório vazio)
])
def test_metadados_contributors_sem_link_conta_itens(corpo, esperado):
    meta = collect_metadata(client_with((corpo, {})), "octo/hello")
    assert meta["contributors"] == esperado


def test_metadados_language_nula():
    repo = {**REPO, "language": None}
    meta = collect_metadata(client_with(([], {}), repo=repo), "octo/hello")
    assert meta["language"] is None


MSG_GRANDE = ("The history or contributor list is too large to list contributors "
              "for this repository via the API.")


def test_metadados_lista_grande_demais_vira_none_e_avisa(caplog):
    erro = GitHubError(403, "https://api.github.com" + CONTRIB, MSG_GRANDE)
    with caplog.at_level("WARNING"):
        meta = collect_metadata(client_with(erro), "octo/hello")
    assert meta["contributors"] is None
    assert meta["stars"] == 1234
    assert "octo/hello" in caplog.text


def test_metadados_outro_403_e_propagado():
    erro = GitHubError(403, "https://api.github.com" + CONTRIB, "Resource not accessible")
    with pytest.raises(GitHubError):
        collect_metadata(client_with(erro), "octo/hello")


def test_metadados_repositorio_inexistente_propaga_not_found():
    client = FakeClient({"/repos/octo/hello": NotFoundError(404, "url", "Not Found")})
    with pytest.raises(NotFoundError):
        collect_metadata(client, "octo/hello")
