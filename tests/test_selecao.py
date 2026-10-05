"""Testes da seleção de candidatos e do filtro de Actions. Nunca acessam a rede."""
import random

import pytest

from pipeline.selecao import search_candidates


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
