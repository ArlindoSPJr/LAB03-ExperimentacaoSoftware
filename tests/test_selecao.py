"""Testes da seleção de candidatos e do filtro de Actions. Nunca acessam a rede."""
import random

import pytest

from pipeline.http import NotFoundError
from pipeline.selecao import search_candidates, uses_actions


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


# --------------------------------------------------------------------------- search_candidates

def test_search_uma_consulta_por_faixa_com_filtros():
    client = FakeClient(search={q(1000, 2000): repos("a/x"), q(2000, 5000): repos("b/y")})
    search_candidates(client, [[1000, 2000], [2000, 5000]])
    assert client.paginate_calls == [
        ("/search/repositories", {"q": q(1000, 2000)}, "items"),
        ("/search/repositories", {"q": q(2000, 5000)}, "items"),
    ]


def test_search_remove_duplicatas_entre_faixas():
    client = FakeClient(search={
        q(1000, 2000): repos("a/x", "c/borda"),
        q(2000, 5000): repos("c/borda", "b/y"),
    })
    nomes = search_candidates(client, [[1000, 2000], [2000, 5000]])
    assert sorted(nomes) == ["a/x", "b/y", "c/borda"]
    assert len(nomes) == 3


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


def test_search_faixa_abaixo_do_teto_nao_avisa(caplog):
    client = FakeClient(search={q(1, 2): repos("a/1")})
    with caplog.at_level("WARNING"):
        search_candidates(client, [[1, 2]])
    assert caplog.text == ""


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


def test_search_sem_faixas_ou_faixa_vazia():
    assert search_candidates(FakeClient(), []) == []
    assert search_candidates(FakeClient(), [[1, 2]]) == []


@pytest.mark.parametrize("faixas, limite", [([[5, 1]], 1000), ([[1]], 1000), ([[1, 2]], 0)])
def test_search_parametros_invalidos(faixas, limite):
    client = FakeClient()
    with pytest.raises(ValueError):
        search_candidates(client, faixas, per_range_limit=limite)
    assert client.paginate_calls == []


# --------------------------------------------------------------------------- uses_actions

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
