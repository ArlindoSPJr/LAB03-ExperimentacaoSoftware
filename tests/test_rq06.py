import math

import pandas as pd
import pytest
from statsmodels.stats.multitest import multipletests

from analise.rq06 import (
    CORTE_LINGUAGEM,
    FATORES,
    METRICAS,
    agrupar_linguagem,
    executar,
    main,
    montar_fatores,
    resumo_grupos,
    testar,
    testes,
)


def test_fatores_e_metricas():
    assert FATORES == ["linguagem", "estrelas", "contribuidores", "idade", "tipo_projeto"]
    assert METRICAS == ["deploy_freq_week", "lead_time_a_days", "cfr_ci", "recovery_median_h"]
    assert CORTE_LINGUAGEM == 10


def test_linguagem_com_poucos_repos_vira_outras():
    s = pd.Series(["Go"] * 3 + ["Rust"] * 2 + ["C", None])
    assert agrupar_linguagem(s, corte=3).tolist() == ["Go"] * 3 + ["Outras"] * 3 + [None]


def test_montar_fatores_quartis_e_tipo():
    df = pd.DataFrame({
        "language": ["Go"] * 8, "stars": [1, 2, 3, 4, 5, 6, 7, 8],
        "contributors": [8, 7, 6, 5, 4, 3, 2, 1], "age_days": [10] * 8,
        "tipo_projeto": ["outro", None] * 4,
    })
    f = montar_fatores(df, corte=1)
    assert f["linguagem"].tolist() == ["Go"] * 8
    assert f["estrelas"].tolist() == ["Q1", "Q1", "Q2", "Q2", "Q3", "Q3", "Q4", "Q4"]
    assert f["contribuidores"].tolist()[0] == "Q4"
    assert f["tipo_projeto"].isna().sum() == 4


def test_dois_grupos_usa_mann_whitney_e_cliffs_delta():
    # g1 todo abaixo de g2: U1 = 0 -> delta = 2*0/(3*3) - 1 = -1
    r = testar(pd.Series([1, 2, 3, 4, 5, 6]), pd.Series(["a", "a", "a", "b", "b", "b"]))
    assert r["teste"] == "mann-whitney" and r["efeito"] == "cliffs_delta"
    assert r["estatistica"] == 0 and r["valor_efeito"] == pytest.approx(-1.0)
    assert r["n"] == 6 and r["k"] == 2 and r["magnitude"] == "grande"


def test_tres_grupos_usa_kruskal_wallis_e_epsilon_quadrado():
    # somas de postos 6, 15, 24 -> H = 12/(9*10) * (36+225+576)/3 - 3*10 = 7,2; eps2 = 7,2/8 = 0,9
    r = testar(pd.Series(range(1, 10)), pd.Series(["a"] * 3 + ["b"] * 3 + ["c"] * 3))
    assert r["teste"] == "kruskal-wallis" and r["efeito"] == "epsilon_quadrado"
    assert r["estatistica"] == pytest.approx(7.2) and r["valor_efeito"] == pytest.approx(0.9)
    assert r["magnitude"] == "grande"


def test_ignora_ausentes_e_grupo_unico_nao_testa():
    r = testar(pd.Series([1.0, None, 3.0]), pd.Series(["a", "b", None]))
    assert r["n"] == 1 and r["teste"] is None and math.isnan(r["p"])


def test_valores_todos_iguais_nao_quebra():
    r = testar(pd.Series([1.0] * 6), pd.Series(["a", "b", "c"] * 2))
    assert math.isnan(r["p"])


def _df(n=40):
    linguas = (["Go", "Python"] * n)[:n]
    return pd.DataFrame({
        "repo": [f"o/r{i}" for i in range(n)], "language": linguas,
        "stars": range(n), "contributors": range(n, 0, -1), "age_days": [i % 7 for i in range(n)],
        "tipo_projeto": (["biblioteca/framework", "outro", None, None] * n)[:n],
        "deploy_freq_week": [i / 10 for i in range(n)], "lead_time_a_days": [i % 5 for i in range(n)],
        "cfr_ci": [(i % 3) / 10 for i in range(n)], "recovery_median_h": [None] + list(range(1, n)),
    })


def test_testes_aplica_holm_em_toda_a_familia():
    tab = testes(_df())
    assert len(tab) == len(FATORES) * len(METRICAS)
    validos = tab.dropna(subset=["p"])
    esperado = multipletests(validos["p"], method="holm")[1]
    assert validos["p_holm"].tolist() == pytest.approx(list(esperado))
    assert (validos["p_holm"] >= validos["p"]).all()
    assert tab.loc[tab["fator"] == "tipo_projeto", "n"].max() <= 20


def test_resumo_grupos_mediana_por_grupo():
    res = resumo_grupos(pd.DataFrame({
        "language": ["Go"] * 3, "stars": [1, 2, 3], "contributors": [1, 2, 3], "age_days": [1, 2, 3],
        "tipo_projeto": [None] * 3, "deploy_freq_week": [1, 2, 9],
        "lead_time_a_days": [1, 1, 1], "cfr_ci": [0, 0, 0], "recovery_median_h": [1, 2, 3],
    }), corte=1)
    go = res[(res["fator"] == "linguagem") & (res["metrica"] == "deploy_freq_week")].iloc[0]
    assert (go["grupo"], go["n"], go["mediana"], go["q1"], go["q3"]) == ("Go", 3, 2, 1.5, 5.5)


def test_executar_e_main_gravam_saidas(tmp_path):
    entrada = tmp_path / "metricas.csv"
    _df().to_csv(entrada, index=False)
    executar(entrada, tmp_path / "s")
    assert (tmp_path / "s" / "tabela_rq06.csv").exists()
    assert (tmp_path / "s" / "rq06_grupos.csv").exists()
    assert main(["--entrada", str(entrada), "--saida", str(tmp_path / "s2")]) == 0
