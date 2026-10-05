"""Testes do cache em disco e do cliente HTTP. Nunca acessam a rede."""
import hashlib
import json

from pipeline.cache import DiskCache


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
