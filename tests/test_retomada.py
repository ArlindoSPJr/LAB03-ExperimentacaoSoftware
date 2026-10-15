"""Retomada após Ctrl+C: cliente HTTP real + cache em disco + sessão fake (sem rede).

A sessão fake responde como a API a partir do `FakeClient` de test_orquestrador e
levanta `KeyboardInterrupt` (o mesmo efeito do Ctrl+C) na chamada escolhida.
"""
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
        resto = path.strip("/").split("/")[3:]
        if resto == ["actions", "runs"]:
            return Resposta({"workflow_runs": self.api.paginate(path, params)})
        if resto and resto[0] == "compare":
            return Resposta({"commits": self.api.paginate(path, params)})
        if resto in (["tags"], ["commits"]):
            return Resposta(self.api.paginate(path, params))
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
        "o/b": repo(tags=[("t0", "2025-11-03T00:00:00Z"), ("t1", "2025-12-01T00:00:00Z")]),
    })


def cliente(cache_dir, sessao):
    client = GitHubClient("tok", DiskCache(cache_dir), sleep=lambda s: None)
    client.session = sessao
    return client


def rodar(cache_dir, saida, interromper_na=None):
    sessao = SessaoFake(api_fake(), interromper_na)
    resultado = executar(cliente(cache_dir, sessao), config(), saida)
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
        with pytest.raises(KeyboardInterrupt):
            executar(cliente(cache, sessao), config(), tmp_path / f"saida{k}")
        feitas = sessao.chamadas
        assert len(feitas) == k - 1

        (metricas, funil), retomada = rodar(cache, tmp_path / f"saida{k}")
        assert set(feitas).isdisjoint(retomada), f"chamada repetida ao retomar após {k - 1} chamadas"
        assert len(feitas) + len(retomada) == total
        pd.testing.assert_frame_equal(metricas, metricas_ref)
        pd.testing.assert_frame_equal(funil, funil_ref)
