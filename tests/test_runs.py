"""Testes da coleta mensal de workflow runs. Nunca acessam a rede."""
from datetime import datetime, timezone

from pipeline.runs import fetch_runs, meses_da_janela

START = datetime(2025, 10, 1, tzinfo=timezone.utc)
END = datetime(2026, 9, 30, 23, 59, 59, tzinfo=timezone.utc)
PATH = "/repos/octo/hello/actions/runs"


class FakeClient:
    """Cliente fake: valor de `created` -> lista de runs; registra as chamadas a paginate."""

    def __init__(self, por_mes=None):
        self.por_mes = por_mes or {}
        self.calls = []

    def paginate(self, path, params=None, item_key=None):
        self.calls.append((path, dict(params or {}), item_key))
        return self.por_mes.get(params["created"], [])


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


def gh_run(run_id, conclusion="success", started="2026-01-10T10:00:00Z", updated="2026-01-10T10:05:00Z",
           workflow_id=7):
    return {"id": run_id, "workflow_id": workflow_id, "conclusion": conclusion, "status": "completed",
            "run_started_at": started, "updated_at": updated, "created_at": started}


def test_janela_de_12_meses_vira_12_consultas_mensais():
    assert meses_da_janela(START, END) == [
        "2025-10-01..2025-10-31", "2025-11-01..2025-11-30", "2025-12-01..2025-12-31",
        "2026-01-01..2026-01-31", "2026-02-01..2026-02-28", "2026-03-01..2026-03-31",
        "2026-04-01..2026-04-30", "2026-05-01..2026-05-31", "2026-06-01..2026-06-30",
        "2026-07-01..2026-07-31", "2026-08-01..2026-08-31", "2026-09-01..2026-09-30",
    ]


def test_janela_que_nao_comeca_no_dia_1_e_cortada_nas_pontas():
    assert meses_da_janela(utc(2025, 10, 15), utc(2025, 12, 10)) == [
        "2025-10-15..2025-10-31", "2025-11-01..2025-11-30", "2025-12-01..2025-12-10",
    ]


def test_consultas_filtram_branch_event_push_e_mes():
    client = FakeClient()
    fetch_runs(client, "octo/hello", "develop", START, END)
    assert len(client.calls) == 12
    path, params, item_key = client.calls[0]
    assert path == PATH
    assert item_key == "workflow_runs"
    assert params == {"branch": "develop", "event": "push", "created": "2025-10-01..2025-10-31"}


def test_runs_mapeados_para_contrato_run():
    client = FakeClient({"2026-01-01..2026-01-31": [
        gh_run(1, "failure", "2026-01-10T10:00:00Z", "2026-01-10T10:30:00Z", workflow_id=99),
        gh_run(2, None, "2026-01-11T10:00:00-03:00", "2026-01-11T10:10:00-03:00"),
    ]})
    runs, teto = fetch_runs(client, "octo/hello", "main", START, END)
    assert runs == [
        {"workflow_id": 99, "conclusion": "failure",
         "run_started_at": utc(2026, 1, 10, 10), "updated_at": utc(2026, 1, 10, 10, 30)},
        {"workflow_id": 7, "conclusion": None,
         "run_started_at": utc(2026, 1, 11, 13), "updated_at": utc(2026, 1, 11, 13, 10)},
    ]
    assert teto == []


def test_runs_de_varios_meses_concatenados_em_ordem_cronologica():
    client = FakeClient({
        "2026-02-01..2026-02-28": [gh_run(3, started="2026-02-02T00:00:00Z")],
        "2025-10-01..2025-10-31": [gh_run(2, started="2025-10-20T00:00:00Z"),
                                   gh_run(1, started="2025-10-05T00:00:00Z")],
    })
    runs, _ = fetch_runs(client, "octo/hello", "main", START, END)
    assert [r["run_started_at"] for r in runs] == [utc(2025, 10, 5), utc(2025, 10, 20), utc(2026, 2, 2)]


def test_run_sem_run_started_at_usa_created_at():
    run = gh_run(1, started="2026-01-10T10:00:00Z")
    run["run_started_at"] = None
    runs, _ = fetch_runs(FakeClient({"2026-01-01..2026-01-31": [run]}), "octo/hello", "main", START, END)
    assert runs[0]["run_started_at"] == utc(2026, 1, 10, 10)


def test_mes_com_1000_resultados_e_sinalizado_no_teto():
    cheio = [gh_run(i) for i in range(1000)]
    quase = [gh_run(i) for i in range(999)]
    client = FakeClient({"2026-03-01..2026-03-31": cheio, "2026-04-01..2026-04-30": quase})
    runs, teto = fetch_runs(client, "octo/hello", "main", START, END)
    assert teto == ["2026-03"]
    assert len(runs) == 1999


def test_repositorio_sem_runs():
    assert fetch_runs(FakeClient(), "octo/hello", "main", START, END) == ([], [])
