"""Testes do cache em disco e do cliente HTTP. Nunca acessam a rede."""
import hashlib
import json

import pytest
import requests

from pipeline.cache import DiskCache
from pipeline.http import API_URL, GitHubClient, GitHubError, NotFoundError


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, headers=None):
        self.status_code = status_code
        self._json = json_data
        self.headers = headers or {}

    def json(self):
        if self._json is None:
            raise ValueError("sem corpo JSON")
        return self._json


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.headers = {}

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        resp = self.responses.pop(0)
        if isinstance(resp, Exception):
            raise resp
        return resp


def make_client(tmp_path, responses, max_retries=5, now=1_000_000.0):
    sleeps = []
    client = GitHubClient("tok", DiskCache(tmp_path / "cache"), sleep=sleeps.append, max_retries=max_retries)
    client.session = FakeSession(responses)
    client.clock = lambda: now
    return client, sleeps


# --------------------------------------------------------------------------- DiskCache

def test_cache_set_get_persiste_em_arquivo_sha1(tmp_path):
    cache = DiskCache(tmp_path / "cache")
    cache.set("https://api.github.com/x?a=1", {"v": 1})
    nome = hashlib.sha1("https://api.github.com/x?a=1".encode("utf-8")).hexdigest() + ".json"
    arquivo = tmp_path / "cache" / nome
    assert json.loads(arquivo.read_text(encoding="utf-8")) == {"v": 1}
    # nova instância lê do disco (retomada)
    assert DiskCache(tmp_path / "cache").get("https://api.github.com/x?a=1") == {"v": 1}


def test_cache_miss_retorna_none(tmp_path):
    assert DiskCache(tmp_path).get("inexistente") is None


def test_cache_arquivo_corrompido_e_miss(tmp_path):
    cache = DiskCache(tmp_path)
    cache.set("k", [1, 2])
    arquivo = next(tmp_path.glob("*.json"))
    arquivo.write_text('{"trunc', encoding="utf-8")
    assert cache.get("k") is None


# --------------------------------------------------------------------------- GitHubClient.get

def test_client_envia_token_e_headers_padrao(tmp_path):
    client = GitHubClient("abc", DiskCache(tmp_path))
    assert client.session.headers["Authorization"] == "Bearer abc"
    assert client.session.headers["Accept"] == "application/vnd.github+json"


def test_get_retorna_json_e_headers_e_monta_url(tmp_path):
    client, _ = make_client(tmp_path, [FakeResponse(200, {"a": 1}, {"X-Custom": "v"})])
    data, headers = client.get("/repos/o/r", {"x": 1})
    assert data == {"a": 1}
    assert headers["x-custom"] == "v"
    assert client.session.calls == [(f"{API_URL}/repos/o/r", {"x": 1})]


def test_cache_hit_nao_chama_rede(tmp_path):
    client, _ = make_client(tmp_path, [FakeResponse(200, [1, 2], {"Link": "l"})])
    client.get("/a", {"b": 2, "a": 1})
    client.session = FakeSession([])  # qualquer chamada de rede quebraria (pop em lista vazia)
    data, headers = client.get("/a", {"a": 1, "b": 2})  # params em outra ordem: mesma chave
    assert data == [1, 2]
    assert headers["link"] == "l"


def test_404_levanta_not_found_e_nao_cacheia(tmp_path):
    client, sleeps = make_client(tmp_path, [FakeResponse(404, {"message": "Not Found"}),
                                            FakeResponse(200, {"ok": True})])
    with pytest.raises(NotFoundError):
        client.get("/repos/o/r/compare/a...b")
    assert sleeps == []
    assert client.get("/repos/o/r/compare/a...b")[0] == {"ok": True}  # foi à rede de novo


def test_5xx_backoff_exponencial_ate_sucesso(tmp_path):
    client, sleeps = make_client(tmp_path, [FakeResponse(502), FakeResponse(503), FakeResponse(200, {"ok": 1})])
    assert client.get("/x")[0] == {"ok": 1}
    assert sleeps == [1, 2]


def test_5xx_esgota_tentativas_levanta_erro_e_nao_cacheia(tmp_path):
    client, sleeps = make_client(tmp_path, [FakeResponse(500)] * 4, max_retries=3)
    with pytest.raises(GitHubError):
        client.get("/x")
    assert sleeps == [1, 2, 4]
    assert len(client.session.calls) == 4
    assert list((tmp_path / "cache").glob("*.json")) == []


def test_5xx_padrao_espera_1_2_4_8_16(tmp_path):
    client, sleeps = make_client(tmp_path, [FakeResponse(500)] * 6)
    with pytest.raises(GitHubError):
        client.get("/x")
    assert sleeps == [1, 2, 4, 8, 16]


def test_erro_de_rede_usa_backoff(tmp_path):
    client, sleeps = make_client(tmp_path, [requests.ConnectionError("caiu"), FakeResponse(200, {"ok": 1})])
    assert client.get("/x")[0] == {"ok": 1}
    assert sleeps == [1]


# --------------------------------------------------------------------------- rate limit

NOW = 1_000_000.0


def test_remaining_zero_com_reset_futuro_espera_a_diferenca(tmp_path):
    headers = {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(int(NOW) + 120)}
    client, sleeps = make_client(tmp_path, [FakeResponse(200, {"ok": 1}, headers)], now=NOW)
    assert client.get("/x")[0] == {"ok": 1}
    assert sleeps == [120]


def test_remaining_positivo_ou_reset_passado_nao_espera(tmp_path):
    client, sleeps = make_client(tmp_path, [
        FakeResponse(200, [], {"X-RateLimit-Remaining": "10", "X-RateLimit-Reset": str(int(NOW) + 50)}),
        FakeResponse(200, [], {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(int(NOW) - 5)}),
    ], now=NOW)
    client.get("/a")
    client.get("/b")
    assert sleeps == []


def test_403_cota_esgotada_espera_reset_e_repete(tmp_path):
    headers = {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(int(NOW) + 30)}
    client, sleeps = make_client(tmp_path, [
        FakeResponse(403, {"message": "API rate limit exceeded"}, headers),
        FakeResponse(200, {"ok": 1}),
    ], now=NOW)
    assert client.get("/x")[0] == {"ok": 1}
    assert sleeps == [30]


@pytest.mark.parametrize("status", [403, 429])
def test_retry_after_espera_e_repete(tmp_path, status):
    client, sleeps = make_client(tmp_path, [
        FakeResponse(status, {"message": "secondary rate limit"}, {"Retry-After": "7"}),
        FakeResponse(200, {"ok": 1}),
    ])
    assert client.get("/search/repositories", {"q": "x"})[0] == {"ok": 1}
    assert sleeps == [7]


def test_429_sem_cabecalhos_espera_60s(tmp_path):
    client, sleeps = make_client(tmp_path, [FakeResponse(429), FakeResponse(200, {"ok": 1})])
    client.get("/x")
    assert sleeps == [60]


def test_403_secundario_sem_retry_after_espera_60s(tmp_path):
    client, sleeps = make_client(tmp_path, [
        FakeResponse(403, {"message": "You have exceeded a secondary rate limit."}),
        FakeResponse(200, {"ok": 1}),
    ])
    client.get("/x")
    assert sleeps == [60]


def test_403_de_permissao_falha_sem_esperar_e_nao_cacheia(tmp_path):
    client, sleeps = make_client(tmp_path, [FakeResponse(403, {"message": "Resource not accessible"})])
    with pytest.raises(GitHubError) as exc:
        client.get("/x")
    assert exc.value.status == 403
    assert sleeps == []
    assert list((tmp_path / "cache").glob("*.json")) == []


def test_rate_limit_persistente_esgota_tentativas(tmp_path):
    client, sleeps = make_client(tmp_path, [FakeResponse(429, None, {"Retry-After": "1"})] * 3, max_retries=2)
    with pytest.raises(GitHubError):
        client.get("/x")
    assert sleeps == [1, 1]


def test_rate_limit_endpoint_nao_usa_cache(tmp_path):
    client, _ = make_client(tmp_path, [FakeResponse(200, {"rate": {"remaining": 5}}),
                                       FakeResponse(200, {"rate": {"remaining": 4}})])
    assert client.rate_limit()["rate"]["remaining"] == 5
    assert client.rate_limit()["rate"]["remaining"] == 4
    assert client.session.calls[0][0] == f"{API_URL}/rate_limit"
