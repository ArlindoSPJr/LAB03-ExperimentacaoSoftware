from datetime import datetime, timedelta, timezone

import pytest

from metricas.recuperacao import contar_falhas_iniciais, recovery_episodes, repo_recovery


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


def run(conclusion, inicio, fim=None, workflow_id=1):
    return {
        "workflow_id": workflow_id,
        "conclusion": conclusion,
        "run_started_at": inicio,
        "updated_at": fim or inicio + timedelta(minutes=5),
    }


# Tabela do enunciado (RQ04): workflow CI, branch main.
TABELA_ENUNCIADO = [
    run("success", utc(2026, 3, 1, 9, 0)),
    run("failure", utc(2026, 3, 1, 10, 0)),
    run("failure", utc(2026, 3, 1, 10, 30)),
    run("success", utc(2026, 3, 1, 11, 15), fim=utc(2026, 3, 1, 11, 20)),
]


def test_recovery_episodes_exemplo_do_enunciado_1h20():
    horas, censurados = recovery_episodes(TABELA_ENUNCIADO)
    assert horas == [pytest.approx(80 / 60)]
    assert censurados == 0


def test_recovery_episodes_ordena_por_run_started_at():
    horas, _ = recovery_episodes(list(reversed(TABELA_ENUNCIADO)))
    assert horas == [pytest.approx(80 / 60)]


def test_recovery_episodes_falha_nunca_recuperada_e_censurada():
    runs = [run("success", utc(2026, 3, 1, 9)), run("failure", utc(2026, 3, 1, 10))]
    assert recovery_episodes(runs) == ([], 1)


def test_recovery_episodes_cancelled_no_meio_nao_afeta():
    runs = [
        run("success", utc(2026, 3, 1, 9)),
        run("failure", utc(2026, 3, 1, 10)),
        run("cancelled", utc(2026, 3, 1, 10, 15)),
        run("skipped", utc(2026, 3, 1, 10, 20)),
        run(None, utc(2026, 3, 1, 10, 25)),
        run("success", utc(2026, 3, 1, 11), fim=utc(2026, 3, 1, 12)),
    ]
    assert recovery_episodes(runs) == ([pytest.approx(2.0)], 0)


def test_recovery_episodes_cancelled_nao_abre_episodio():
    runs = [
        run("success", utc(2026, 3, 1, 9)),
        run("cancelled", utc(2026, 3, 1, 10)),
        run("success", utc(2026, 3, 1, 11)),
    ]
    assert recovery_episodes(runs) == ([], 0)


def test_recovery_episodes_falhas_antes_do_primeiro_sucesso_nao_abrem_episodio():
    runs = [
        run("failure", utc(2026, 3, 1, 8)),
        run("timed_out", utc(2026, 3, 1, 8, 30)),
        run("success", utc(2026, 3, 1, 9)),
    ]
    assert recovery_episodes(runs) == ([], 0)


def test_recovery_episodes_varios_episodios_e_um_censurado():
    runs = [
        run("success", utc(2026, 3, 1, 0)),
        run("failure", utc(2026, 3, 1, 1)),
        run("success", utc(2026, 3, 1, 2), fim=utc(2026, 3, 1, 3)),
        run("startup_failure", utc(2026, 3, 2, 0)),
        run("success", utc(2026, 3, 2, 0, 30), fim=utc(2026, 3, 2, 0, 30)),
        run("failure", utc(2026, 3, 3, 0)),
    ]
    horas, censurados = recovery_episodes(runs)
    assert horas == [pytest.approx(2.0), pytest.approx(0.5)]
    assert censurados == 1


def test_recovery_episodes_lista_vazia():
    assert recovery_episodes([]) == ([], 0)


def test_contar_falhas_iniciais_por_workflow():
    runs = [
        run("failure", utc(2026, 3, 1, 8), workflow_id=1),
        run("timed_out", utc(2026, 3, 1, 8, 30), workflow_id=1),
        run("success", utc(2026, 3, 1, 9), workflow_id=1),
        run("failure", utc(2026, 3, 1, 10), workflow_id=1),
        run("failure", utc(2026, 3, 1, 8), workflow_id=2),
        run("success", utc(2026, 3, 1, 7), workflow_id=3),
        run("failure", utc(2026, 3, 1, 8), workflow_id=3),
    ]
    # wf1: 2 falhas antes do 1º sucesso; wf2: nunca teve sucesso (1); wf3: 0.
    assert contar_falhas_iniciais(runs) == 3


def test_contar_falhas_iniciais_ignora_cancelled():
    runs = [run("cancelled", utc(2026, 3, 1, 8)), run("success", utc(2026, 3, 1, 9))]
    assert contar_falhas_iniciais(runs) == 0


def test_repo_recovery_workflows_independentes_nao_se_misturam():
    runs = [
        run("success", utc(2026, 3, 1, 9), workflow_id=1),
        run("failure", utc(2026, 3, 1, 10), workflow_id=1),
        # sucesso do workflow 2 não encerra o episódio do workflow 1
        run("success", utc(2026, 3, 1, 10, 30), workflow_id=2),
        run("success", utc(2026, 3, 1, 13), fim=utc(2026, 3, 1, 14), workflow_id=1),
    ]
    assert repo_recovery(runs) == (pytest.approx(4.0), 1, 0)


def test_repo_recovery_mediana_de_todos_os_workflows():
    runs = [
        run("success", utc(2026, 3, 1, 0), workflow_id=1),
        run("failure", utc(2026, 3, 1, 1), workflow_id=1),
        run("success", utc(2026, 3, 1, 2), fim=utc(2026, 3, 1, 2), workflow_id=1),  # 1h
        run("failure", utc(2026, 3, 1, 3), workflow_id=1),
        run("success", utc(2026, 3, 1, 6), fim=utc(2026, 3, 1, 6), workflow_id=1),  # 3h
        run("success", utc(2026, 3, 1, 0), workflow_id=2),
        run("failure", utc(2026, 3, 1, 1), workflow_id=2),
        run("success", utc(2026, 3, 1, 11), fim=utc(2026, 3, 1, 11), workflow_id=2),  # 10h
    ]
    assert repo_recovery(runs) == (pytest.approx(3.0), 3, 0)


def test_repo_recovery_n_episodes_inclui_censurados():
    runs = [
        run("success", utc(2026, 3, 1, 0), workflow_id=1),
        run("failure", utc(2026, 3, 1, 1), workflow_id=1),
        run("success", utc(2026, 3, 1, 2), fim=utc(2026, 3, 1, 2), workflow_id=1),
        run("success", utc(2026, 3, 1, 0), workflow_id=2),
        run("failure", utc(2026, 3, 1, 1), workflow_id=2),
    ]
    assert repo_recovery(runs) == (pytest.approx(1.0), 2, 1)


def test_repo_recovery_so_censurados_mediana_none():
    runs = [run("success", utc(2026, 3, 1, 0)), run("failure", utc(2026, 3, 1, 1))]
    assert repo_recovery(runs) == (None, 1, 1)


def test_repo_recovery_sem_runs():
    assert repo_recovery([]) == (None, 0, 0)
