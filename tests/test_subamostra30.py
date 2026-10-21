"""Confere config.subamostra30.yaml, usado na replicação cruzada (README, passo 5)."""
import pathlib

import pandas as pd
import yaml

RAIZ = pathlib.Path(__file__).resolve().parents[1]


def _yaml(nome):
    return yaml.safe_load((RAIZ / nome).read_text(encoding="utf-8"))


def test_subamostra_tem_30_repos_distintos_e_sample_size_30():
    cfg = _yaml("config.subamostra30.yaml")
    assert cfg["sample_size"] == 30
    assert len(cfg["repos"]) == 30 and len(set(cfg["repos"])) == 30


def test_subamostra_usa_a_mesma_configuracao_do_config_principal():
    sub, principal = _yaml("config.subamostra30.yaml"), _yaml("config.yaml")
    for chave in ("window", "star_ranges", "max_compares_variante", "cache_dir"):
        assert sub[chave] == principal[chave], chave


def test_subamostra_e_o_sorteio_com_semente_42_do_dataset():
    sorteio = pd.read_csv(RAIZ / "data" / "metricas.csv").sample(n=30, random_state=42)["repo"].tolist()
    assert _yaml("config.subamostra30.yaml")["repos"] == sorteio
