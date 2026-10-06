import pytest

from metricas.classificacao import UMA_POR_MES_POR_SEMANA, score_deploy_freq


@pytest.mark.parametrize("per_week, esperado", [
    (7, 4), (30, 4), (6.99, 3), (1, 3), (0.99, 2),
    (UMA_POR_MES_POR_SEMANA, 2), (UMA_POR_MES_POR_SEMANA - 1e-9, 1), (0, 1),
])
def test_score_deploy_freq_limites(per_week, esperado):
    assert score_deploy_freq(per_week) == esperado


def test_score_deploy_freq_um_por_mes_na_janela_da_rq01():
    # RQ01: releases na janela / ~52,1 semanas; 12 releases = 1 por mês.
    assert score_deploy_freq(12 / 52.1) == 2
    assert score_deploy_freq(11 / 52.1) == 1
