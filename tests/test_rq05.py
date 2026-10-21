import math

import pandas as pd
import pytest

from analise.rq05 import PARES, correlacionar, executar, graficos, main


def _linha(res, rq):
    return res[res["rq"] == rq].iloc[0]


def test_pares_frequencia_contra_cfr_a_e_b():
    assert [(p["rq"], p["x"], p["y"]) for p in PARES] == [
        ("RQ05a", "deploy_freq_week", "cfr_ci"),
        ("RQ05b", "deploy_freq_week", "cfr_entrega"),
    ]


def test_rho_calculado_a_mao():
    # postos de y: 1,3,2,4 -> d^2 = 0+1+1+0 = 2 -> rho = 1 - 6*2/(4*(16-1)) = 0,8
    df = pd.DataFrame({"deploy_freq_week": [1, 2, 3, 4], "cfr_ci": [0.1, 0.3, 0.2, 0.4]})
    r = _linha(correlacionar(df), "RQ05a")
    assert r["n"] == 4 and r["rho"] == pytest.approx(0.8)
    assert 0 < r["p"] < 1


def test_rho_negativo_perfeito():
    df = pd.DataFrame({"deploy_freq_week": [1, 2, 3, 4, 5], "cfr_entrega": [5, 4, 3, 2, 1]})
    r = _linha(correlacionar(df), "RQ05b")
    assert r["rho"] == pytest.approx(-1.0) and r["p"] < 0.05


def test_ignora_pares_com_ausente_e_conta_n():
    df = pd.DataFrame({
        "deploy_freq_week": [1, 2, None, 4, 5],
        "cfr_ci": [0.1, None, 0.3, 0.4, 0.5],
    })
    r = _linha(correlacionar(df), "RQ05a")
    assert r["n"] == 3 and r["rho"] == pytest.approx(1.0)


def test_menos_de_tres_pares_ou_coluna_ausente_da_nan():
    df = pd.DataFrame({"deploy_freq_week": [1, 2], "cfr_ci": [0.1, 0.2]})
    res = correlacionar(df)
    a, b = _linha(res, "RQ05a"), _linha(res, "RQ05b")
    assert a["n"] == 2 and math.isnan(a["rho"]) and math.isnan(a["p"])
    assert b["n"] == 0 and math.isnan(b["rho"])


def test_variavel_constante_da_nan_sem_erro():
    df = pd.DataFrame({"deploy_freq_week": [1, 2, 3], "cfr_ci": [0.0, 0.0, 0.0]})
    assert math.isnan(_linha(correlacionar(df), "RQ05a")["rho"])


def _df():
    return pd.DataFrame({
        "deploy_freq_week": [0.01, 0.5, 2.0, 5.0],
        "cfr_ci": [0.0, 0.1, 0.2, 0.4],
        "cfr_entrega": [0.0, 0.0, 0.3, 0.1],
    })


def test_graficos_dispersao_com_eixo_log(tmp_path):
    arquivos = graficos(_df(), tmp_path)
    assert [a.name for a in arquivos] == ["rq05a_freq_cfr_ci.png", "rq05b_freq_cfr_entrega.png"]
    assert all(a.exists() for a in arquivos)


def test_executar_e_main_gravam_tabela(tmp_path):
    entrada = tmp_path / "metricas.csv"
    _df().to_csv(entrada, index=False)
    res = executar(entrada, tmp_path / "s")
    tab = pd.read_csv(tmp_path / "s" / "tabela_rq05.csv")
    assert list(tab["rq"]) == ["RQ05a", "RQ05b"] and len(res["graficos"]) == 2
    assert main(["--entrada", str(entrada), "--saida", str(tmp_path / "s2")]) == 0
