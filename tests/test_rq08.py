import math

import pandas as pd
import pytest

from analise.rq08 import comparar, executar, grafico, resumir


def _df():
    return pd.DataFrame({
        "rework_rate": [0.2, 0.4, 0.6, 0.8, None],
        "cfr_entrega": [0.1, 0.4, 0.3, 0.9, 0.5],
    })


def _linha(tabela, medida):
    return tabela[tabela["medida"] == medida].iloc[0]


def test_resumir_mediana_e_iqr_calculados_a_mao():
    t = resumir(_df())
    r = _linha(t, "rework_rate")
    # [0.2, 0.4, 0.6, 0.8]: mediana 0,5; q1 0,35; q3 0,65 (interpolação linear)
    assert r["n"] == 4 and r["mediana"] == pytest.approx(0.5)
    assert (r["q1"], r["q3"]) == (pytest.approx(0.35), pytest.approx(0.65))
    assert _linha(t, "cfr_entrega")["n"] == 5


def test_resumir_diferenca_pareada_ignora_ausentes():
    d = _linha(resumir(_df()), "rework_menos_cfr")
    # diferenças: 0,1; 0,0; 0,3; -0,1 -> mediana 0,05
    assert d["n"] == 4 and d["mediana"] == pytest.approx(0.05)


def test_comparar_conta_maior_igual_menor():
    c = comparar(_df())
    assert (c["n"], c["n_rework_maior"], c["n_igual"], c["n_rework_menor"]) == (4, 2, 1, 1)


def test_comparar_spearman_perfeito():
    df = pd.DataFrame({"rework_rate": [0.1, 0.2, 0.3, 0.4], "cfr_entrega": [0.0, 0.1, 0.15, 0.3]})
    c = comparar(df)
    assert c["rho"] == pytest.approx(1.0) and c["p"] < 0.1


def test_comparar_com_poucos_pares_tem_rho_nan():
    c = comparar(pd.DataFrame({"rework_rate": [0.1, 0.2], "cfr_entrega": [0.0, 0.1]}))
    assert c["n"] == 2 and math.isnan(c["rho"]) and math.isnan(c["p"])


def test_grafico_e_saidas(tmp_path):
    arq = grafico(_df(), tmp_path)
    assert arq.exists() and arq.name == "rq08_rework_vs_cfr.png"
    entrada = tmp_path / "metricas.csv"
    _df().to_csv(entrada, index=False)
    res = executar(entrada, tmp_path / "saida")
    assert (tmp_path / "saida" / "tabela_rq08.csv").exists()
    assert (tmp_path / "saida" / "tabela_rq08_comparacao.csv").exists()
    assert list(res["resumo"]["medida"]) == ["rework_rate", "cfr_entrega", "rework_menos_cfr"]
