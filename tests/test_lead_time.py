from datetime import datetime, timezone

import pytest

from metricas.lead_time import (
    contar_lead_negativos,
    lead_time_commits_days,
    lead_time_release_days,
    repo_lead_time_a,
    repo_lead_time_b,
)


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


# Exemplo do enunciado: v1.1 publicada em 15/03 com commits de 02/03, 10/03 e 14/03.
V11 = utc(2026, 3, 15)
COMMITS_V11 = [utc(2026, 3, 10), utc(2026, 3, 2), utc(2026, 3, 14)]


def test_lead_time_por_release_exemplo_do_enunciado():
    assert lead_time_release_days(V11, COMMITS_V11) == 13


def test_lead_time_por_commit_exemplo_do_enunciado():
    assert sorted(lead_time_commits_days(V11, COMMITS_V11), reverse=True) == [13, 5, 1]


def test_lead_time_em_dias_fracionarios():
    assert lead_time_release_days(utc(2026, 3, 15, 12), [utc(2026, 3, 15)]) == 0.5


def test_release_sem_commits_novos():
    assert lead_time_release_days(V11, []) is None
    assert lead_time_commits_days(V11, []) == []


def test_commit_na_mesma_hora_da_release_vale_zero():
    assert lead_time_release_days(V11, [V11]) == 0
    assert lead_time_commits_days(V11, [V11]) == [0]


def test_lead_negativo_descartado_por_commit():
    depois = utc(2026, 3, 16)
    assert lead_time_commits_days(V11, [utc(2026, 3, 14), depois]) == [1]


def test_lead_negativo_nao_entra_no_mais_antigo():
    assert lead_time_release_days(V11, [utc(2026, 3, 14), utc(2026, 3, 16)]) == 1


def test_release_so_com_commits_posteriores_nao_tem_lead_time():
    assert lead_time_release_days(V11, [utc(2026, 3, 16)]) is None
    assert lead_time_commits_days(V11, [utc(2026, 3, 16)]) == []


def test_contar_lead_negativos():
    assert contar_lead_negativos(V11, [utc(2026, 3, 16), V11, utc(2026, 3, 2), utc(2026, 4, 1)]) == 2
    assert contar_lead_negativos(V11, []) == 0


def test_repo_lead_time_a_mediana_ignorando_none():
    assert repo_lead_time_a([13, None, 5, 1]) == 5
    assert repo_lead_time_a([13, 5, 1, 3]) == 4


def test_repo_lead_time_a_sem_valores():
    assert repo_lead_time_a([]) is None
    assert repo_lead_time_a([None, None]) is None


def test_repo_lead_time_b_mediana_de_todos_os_commits():
    valores = [13, 5, 1] + [2, 4]
    assert repo_lead_time_b(valores) == 4


def test_repo_lead_time_b_sem_commits():
    assert repo_lead_time_b([]) is None


def test_um_commit_antigo_explode_a_mas_pouco_afeta_b():
    release = utc(2026, 3, 15)
    commits = [utc(2025, 3, 15)] + [utc(2026, 3, 14)] * 9
    assert lead_time_release_days(release, commits) == 365
    assert repo_lead_time_b(lead_time_commits_days(release, commits)) == pytest.approx(1)
