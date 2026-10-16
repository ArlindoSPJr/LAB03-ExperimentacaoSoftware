from datetime import datetime, timezone

import pytest

from metricas.cfr import cfr_ci, cfr_entrega, classify_conclusion


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


# --- CFR (b): release seguida em até 7 dias por release corretiva ---------------------

FIM = utc(2026, 9, 30)


def rel(mes, dia, corretiva=False, hora=0):
    return {"published_at": utc(2026, mes, dia, hora), "corretiva": corretiva}


def test_cfr_entrega_exemplos_do_enunciado():
    # v2.3.0 (10/05) seguida por v2.3.1 corretiva (12/05): falhou.
    # v2.4.0 (01/06) seguida por v2.5.0 (20/06): não falhou.
    releases = [rel(5, 10), rel(5, 12, corretiva=True), rel(6, 1), rel(6, 20)]
    r = cfr_entrega(releases, FIM)
    assert (r["falhas"], r["avaliadas"], r["censuradas"]) == (1, 4, 0)
    assert r["cfr"] == pytest.approx(0.25)


def test_cfr_entrega_corretiva_com_exatamente_7_dias_conta():
    r = cfr_entrega([rel(5, 1), rel(5, 8, corretiva=True)], FIM)
    assert r["falhas"] == 1


def test_cfr_entrega_corretiva_com_mais_de_7_dias_nao_conta():
    r = cfr_entrega([rel(5, 1), rel(5, 8, corretiva=True, hora=1)], FIM)
    assert r["falhas"] == 0


def test_cfr_entrega_ultimos_7_dias_sao_censurados():
    releases = [rel(9, 1), rel(9, 24), rel(9, 29, corretiva=True)]
    r = cfr_entrega(releases, FIM)
    assert (r["avaliadas"], r["censuradas"], r["falhas"]) == (1, 2, 0)
    assert r["cfr"] == 0


def test_cfr_entrega_release_unica():
    r = cfr_entrega([rel(3, 1)], FIM)
    assert (r["cfr"], r["avaliadas"], r["falhas"]) == (0, 1, 0)


def test_cfr_entrega_lista_vazia_e_none():
    assert cfr_entrega([], FIM) == {"cfr": None, "falhas": 0, "avaliadas": 0, "censuradas": 0}


def test_cfr_entrega_so_censuradas_e_none():
    r = cfr_entrega([rel(9, 28)], FIM)
    assert r["cfr"] is None and r["censuradas"] == 1


def test_cfr_entrega_ordena_por_data():
    releases = [rel(5, 12, corretiva=True), rel(5, 10)]
    assert cfr_entrega(releases, FIM)["falhas"] == 1


def test_cfr_entrega_so_a_proxima_release_conta():
    # a corretiva vem depois de outra release não corretiva: só a do meio falha
    releases = [rel(5, 1), rel(5, 3), rel(5, 5, corretiva=True)]
    r = cfr_entrega(releases, FIM)
    assert r["falhas"] == 1 and r["avaliadas"] == 3
