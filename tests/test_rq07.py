import math

import pandas as pd
import pytest

from analise.rq07 import (COMBINACOES, PARES, classificar_combinacao, comparar, distribuicao, executar,
                          montar_classificacao, transicoes)


def _metricas(**kw):
    """Repo 'a/a' Elite em C1/C2/C3 por padrão; `kw` sobrescreve colunas (listas de 1 valor)."""
    base = {
        "repo": ["a/a"],
        "deploy_freq_week": [10.0], "lead_time_a_days": [0.5], "cfr_ci": [0.1], "recovery_median_h": [0.5],
        "deploy_freq_week_pre": [10.0], "lead_time_b_days_pre": [0.5], "cfr_entrega_pre": [0.1],
        "deploy_freq_week_tag": [10.0], "lead_time_b_days_tag": [0.5],
    }
    base.update(kw)
    return pd.DataFrame(base)


def _classif(c1, c2, c3):
    return pd.DataFrame({"repo": [f"r{i}" for i in range(len(c1))], "C1": c1, "C2": c2, "C3": c3})


def test_combinacoes_do_enunciado():
    assert list(COMBINACOES) == ["C1", "C2", "C3"]
    assert COMBINACOES["C2"] == ("deploy_freq_week_pre", "lead_time_b_days_pre", "cfr_entrega_pre",
                                 "recovery_median_h")
    assert COMBINACOES["C3"] == ("deploy_freq_week_tag", "lead_time_b_days_tag", "cfr_ci", "recovery_median_h")
    assert PARES == [("C1", "C2"), ("C1", "C3"), ("C2", "C3")]


def test_classificar_combinacao_usa_os_cortes_fixos():
    # C2: freq 2/sem (High=3), lead 10 dias (Medium=2), CFR 0,5 (Low=1), rec 0,5 h (Elite=4)
    # notas (3, 2, 1, 4): mediana 2,5 -> arredonda para baixo -> Medium
    df = _metricas(deploy_freq_week_pre=[2.0], lead_time_b_days_pre=[10.0], cfr_entrega_pre=[0.5])
    assert classificar_combinacao(df, "C2").tolist() == ["Medium"]


def test_metrica_ausente_deixa_sem_classificacao():
    df = _metricas(lead_time_b_days_tag=[float("nan")])
    assert classificar_combinacao(df, "C3").tolist() == [None]
    assert classificar_combinacao(df, "C2").tolist() == ["Elite"]


def test_c1_vem_do_csv_de_referencia_sem_reclassificar():
    df = _metricas()
    c1 = pd.DataFrame({"repo": ["a/a"], "dora_overall": ["Low"]})  # diferente do que daria recalcular
    out = montar_classificacao(df, c1)
    assert out.loc[0, ["C1", "C2", "C3"]].tolist() == ["Low", "Elite", "Elite"]


def test_classificacao_identica_nao_muda_e_kappa_um():
    cl = _classif(["Elite", "High", "Low"], ["Elite", "High", "Low"], ["Elite", "High", "Low"])
    r = comparar(cl, "C1", "C2")
    assert (r["n"], r["n_mudou"], r["pct_mudou"]) == (3, 0, 0.0)
    assert r["kappa_linear"] == pytest.approx(1.0)


def test_mudanca_calculada_a_mao():
    cl = _classif(["Elite", "High", "Medium", "Low"], ["High", "High", "Medium", "Low"], [None] * 4)
    r = comparar(cl, "C1", "C2")
    assert (r["n"], r["n_mudou"]) == (4, 1)
    assert r["pct_mudou"] == pytest.approx(25.0)


def test_repo_nao_classificado_fica_fora_do_par():
    cl = _classif(["Elite", None, "Low"], ["Elite", "High", None], [None] * 3)
    assert comparar(cl, "C1", "C2")["n"] == 1


def test_kappa_ponderado_pune_mais_saltos_maiores():
    perto = _classif(["Elite", "High", "Medium", "Low"], ["High", "High", "Medium", "Low"], [None] * 4)
    longe = _classif(["Elite", "High", "Medium", "Low"], ["Low", "High", "Medium", "Low"], [None] * 4)
    assert comparar(perto, "C1", "C2")["kappa_linear"] > comparar(longe, "C1", "C2")["kappa_linear"]


def test_par_sem_repos_em_comum_tem_kappa_nan():
    cl = _classif(["Elite", None], [None, "Low"], [None, None])
    r = comparar(cl, "C1", "C2")
    assert r["n"] == 0 and math.isnan(r["kappa_linear"]) and math.isnan(r["pct_mudou"])


def test_transicoes_conta_de_para():
    cl = _classif(["Elite", "Elite", "Low"], ["High", "Elite", "Low"], [None] * 3)
    t = transicoes(cl, "C1", "C2")
    assert t.loc["Elite", "High"] == 1 and t.loc["Elite", "Elite"] == 1 and t.loc["Low", "Low"] == 1
    assert list(t.index) == ["Elite", "High", "Medium", "Low"]


def test_distribuicao_por_combinacao():
    cl = _classif(["Elite", "Low"], ["Elite", None], ["High", "High"])
    d = distribuicao(cl)
    linha = d[(d["combinacao"] == "C2") & (d["categoria"] == "Nao classificado")]
    assert int(linha["n"].iloc[0]) == 1


def test_executar_grava_as_saidas(tmp_path):
    entrada = tmp_path / "metricas.csv"
    _metricas().to_csv(entrada, index=False)
    c1 = tmp_path / "classificacao_c1.csv"
    pd.DataFrame({"repo": ["a/a"], "dora_overall": ["Elite"]}).to_csv(c1, index=False)
    res = executar(entrada, c1, tmp_path / "saida")
    for nome in ["rq07_classificacao.csv", "rq07_pares.csv", "rq07_distribuicao.csv",
                 "rq07_transicoes_C1_C2.csv", "rq07_transicoes_C1_C3.csv", "rq07_transicoes_C2_C3.csv"]:
        assert (tmp_path / "saida" / nome).exists()
    assert res["pares"]["par"].tolist() == ["C1xC2", "C1xC3", "C2xC3"]
