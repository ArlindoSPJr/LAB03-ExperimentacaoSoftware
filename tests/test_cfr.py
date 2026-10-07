from datetime import datetime, timezone

import pytest

from metricas.cfr import cfr_ci, classify_conclusion


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


def run(conclusion, hora=0, workflow_id=1):
    inicio = utc(2026, 3, 1, hora)
    return {
        "workflow_id": workflow_id,
        "conclusion": conclusion,
        "run_started_at": inicio,
        "updated_at": inicio,
    }


@pytest.mark.parametrize("conclusion", ["success"])
def test_classify_conclusion_sucesso(conclusion):
    assert classify_conclusion(conclusion) == "success"


@pytest.mark.parametrize("conclusion", ["failure", "timed_out", "startup_failure"])
def test_classify_conclusion_falha(conclusion):
    assert classify_conclusion(conclusion) == "failure"


@pytest.mark.parametrize(
    "conclusion",
    ["cancelled", "skipped", "neutral", "action_required", "stale", "", None],
)
def test_classify_conclusion_ignorada(conclusion):
    assert classify_conclusion(conclusion) is None


def test_classify_conclusion_valor_desconhecido_e_ignorado():
    assert classify_conclusion("valor_novo_da_api") is None


def test_cfr_ci_tres_sucessos_e_uma_falha():
    runs = [run("success", 0), run("success", 1), run("failure", 2), run("success", 3)]
    assert cfr_ci(runs) == pytest.approx(0.25)


def test_cfr_ci_ignora_cancelled_skipped_e_none():
    runs = [
        run("success", 0),
        run("cancelled", 1),
        run("failure", 2),
        run("skipped", 3),
        run(None, 4),
    ]
    assert cfr_ci(runs) == pytest.approx(0.5)


def test_cfr_ci_conta_timed_out_e_startup_failure_como_falha():
    runs = [run("timed_out", 0), run("startup_failure", 1), run("success", 2), run("success", 3)]
    assert cfr_ci(runs) == pytest.approx(0.5)


def test_cfr_ci_sem_runs_validos_e_none():
    assert cfr_ci([run("cancelled"), run("skipped"), run(None)]) is None


def test_cfr_ci_lista_vazia_e_none():
    assert cfr_ci([]) is None


def test_cfr_ci_so_sucessos_e_zero():
    assert cfr_ci([run("success", 0), run("success", 1)]) == 0


def test_cfr_ci_so_falhas_e_um():
    assert cfr_ci([run("failure", 0), run("timed_out", 1)]) == 1


def test_cfr_ci_soma_todos_os_workflows():
    runs = [run("failure", 0, workflow_id=1), run("success", 1, workflow_id=2)]
    assert cfr_ci(runs) == pytest.approx(0.5)
