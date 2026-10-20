import math

import pandas as pd

from analise.rq01_rq04 import METRICAS, resumir


def _linha(res, nome):
    return res[res["nome"] == nome].iloc[0]


def test_resumir_mediana_e_iqr_calculados_a_mao():
    df = pd.DataFrame({"deploy_freq_week": [1, 2, 3, 4, 5]})
    r = _linha(resumir(df), "frequencia")
    assert (r["mediana"], r["q1"], r["q3"], r["iqr"], r["n"], r["n_ausentes"]) == (3, 2, 4, 2, 5, 0)


def test_resumir_ignora_vazios_e_conta_ausentes():
    df = pd.DataFrame({"recovery_median_h": [1.0, None, 3.0, float("nan")]})
    r = _linha(resumir(df), "recuperacao")
    assert r["n"] == 2 and r["n_ausentes"] == 2 and r["mediana"] == 2.0


def test_resumir_coluna_ausente_gera_linha_com_n_zero():
    res = resumir(pd.DataFrame({"deploy_freq_week": [1.0]}))
    assert len(res) == len(METRICAS) == 6
    r = _linha(res, "cfr_entrega")
    assert r["n"] == 0 and math.isnan(r["mediana"])


def test_resumir_ordem_das_rqs():
    assert list(resumir(pd.DataFrame())["rq"]) == ["RQ01", "RQ02a", "RQ02b", "RQ03a", "RQ03b", "RQ04"]


from analise.rq01_rq04 import censurados


def test_censurados_soma_e_proporcao_a_mao():
    df = pd.DataFrame({
        "n_episodes": [5, 5], "n_censored": [1, 0], "prop_censurados": [0.2, 0.0],
        "n_censuradas_entrega": [2, 3],
    })
    c = censurados(df).iloc[0]
    assert c["repos"] == 2 and c["episodios"] == 10 and c["episodios_censurados"] == 1
    assert c["prop_global"] == 0.1 and c["repos_com_censura"] == 1
    assert c["prop_repo_mediana"] == 0.1 and c["releases_censuradas_entrega"] == 5


def test_censurados_sem_episodios_nao_divide_por_zero():
    df = pd.DataFrame({"n_episodes": [0], "n_censored": [0], "prop_censurados": [None]})
    c = censurados(df).iloc[0]
    assert pd.isna(c["prop_global"]) and pd.isna(c["prop_repo_mediana"])


def test_censurados_sem_coluna_da_entrega():
    df = pd.DataFrame({"n_episodes": [1], "n_censored": [1], "prop_censurados": [1.0]})
    assert pd.isna(censurados(df).iloc[0]["releases_censuradas_entrega"])
