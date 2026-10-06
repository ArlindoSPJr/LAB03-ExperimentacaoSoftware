import pytest

from metricas.classificacao import (
    UMA_POR_MES_POR_SEMANA,
    overall,
    score_deploy_freq,
    score_cfr,
    score_lead_time,
    score_recovery,
)


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


@pytest.mark.parametrize("days, esperado", [
    (0, 4), (0.99, 4), (1, 3), (6.99, 3), (7, 2), (29.99, 2), (30, 1), (400, 1),
])
def test_score_lead_time_limites(days, esperado):
    assert score_lead_time(days) == esperado


@pytest.mark.parametrize("rate, esperado", [
    (0, 4), (0.15, 4), (0.1501, 3), (0.30, 3), (0.3001, 2), (0.45, 2), (0.4501, 1), (1, 1),
])
def test_score_cfr_limites(rate, esperado):
    assert score_cfr(rate) == esperado


@pytest.mark.parametrize("hours, esperado", [
    (0, 4), (0.99, 4), (1, 3), (23.99, 3), (24, 2), (167.99, 2), (168, 1), (1000, 1),
])
def test_score_recovery_limites(hours, esperado):
    assert score_recovery(hours) == esperado


@pytest.mark.parametrize("scores, esperado", [
    ([4, 3, 3, 1], "High"),      # exemplo do enunciado
    ([4, 4, 1, 1], "Medium"),    # mediana 2,5 -> 2
    ([4, 4, 4, 4], "Elite"),
    ([1, 1, 1, 1], "Low"),
    ([4, 4, 3, 1], "High"),      # mediana 3,5 -> 3
    ([2, 1, 1, 4], "Low"),       # mediana 1,5 -> 1 (ordem não importa)
])
def test_overall_mediana_arredondada_para_baixo(scores, esperado):
    assert overall(scores) == esperado
