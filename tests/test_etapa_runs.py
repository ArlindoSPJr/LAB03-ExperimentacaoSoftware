"""Testes da etapa de runs e métricas de CI do orquestrador. Nunca acessam a rede."""
from datetime import datetime, timezone

import pytest

from pipeline.etapa_runs import coletar_runs_e_metricas

START = datetime(2025, 10, 1, tzinfo=timezone.utc)
END = datetime(2026, 9, 30, 23, 59, 59, tzinfo=timezone.utc)
JANELA = (START, END)
META = {"full_name": "octo/hello", "default_branch": "trunk"}
PATH = "/repos/octo/hello/actions/runs"


class FakeClient:
    """Cliente fake: valor de `created` -> lista de runs; registra as chamadas a paginate."""

    def __init__(self, por_mes=None):
        self.por_mes = por_mes or {}
        self.calls = []

    def paginate(self, path, params=None, item_key=None):
        self.calls.append((path, dict(params or {})))
        return self.por_mes.get(params["created"], [])


def gh_run(conclusion, started, updated=None, workflow_id=7):
    return {"workflow_id": workflow_id, "conclusion": conclusion, "status": "completed",
            "run_started_at": started, "updated_at": updated or started, "created_at": started}


JANEIRO = "2026-01-01..2026-01-31"


def test_usa_default_branch_e_full_name_do_meta():
    client = FakeClient()
    coletar_runs_e_metricas(client, META, JANELA)
    assert len(client.calls) == 12
    assert all(path == PATH and params["branch"] == "trunk" and params["event"] == "push"
               for path, params in client.calls)


def test_metricas_do_exemplo_do_enunciado():
    client = FakeClient({JANEIRO: [
        gh_run("failure", "2026-01-10T08:00:00Z"),  # antes do 1º sucesso: falha inicial
        gh_run("success", "2026-01-10T09:00:00Z"),
        gh_run("failure", "2026-01-10T10:00:00Z"),
        gh_run("cancelled", "2026-01-10T10:10:00Z"),
        gh_run("failure", "2026-01-10T10:30:00Z"),
        gh_run("success", "2026-01-10T11:15:00Z", "2026-01-10T11:20:00Z"),
        gh_run("success", "2026-01-11T09:00:00Z", workflow_id=8),
        gh_run("failure", "2026-01-11T10:00:00Z", workflow_id=8),  # nunca recuperada
    ]})
    resultado = coletar_runs_e_metricas(client, META, JANELA)
    assert resultado == {
        "n_runs_validos": 7,
        "cfr_ci": pytest.approx(4 / 7),
        "recovery_median_h": pytest.approx(80 / 60),
        "n_episodes": 2,
        "n_censored": 1,
        "n_falhas_iniciais": 1,
        "meses_no_teto": [],
    }


def test_sem_runs_metricas_none_e_contadores_zerados():
    resultado = coletar_runs_e_metricas(FakeClient(), META, JANELA)
    assert resultado == {
        "n_runs_validos": 0,
        "cfr_ci": None,
        "recovery_median_h": None,
        "n_episodes": 0,
        "n_censored": 0,
        "n_falhas_iniciais": 0,
        "meses_no_teto": [],
    }


def test_meses_no_teto_repassados():
    cheio = [gh_run("success", "2026-01-10T09:00:00Z")] * 1000
    resultado = coletar_runs_e_metricas(FakeClient({JANEIRO: cheio}), META, JANELA)
    assert resultado["meses_no_teto"] == ["2026-01"]
    assert resultado["n_runs_validos"] == 1000
