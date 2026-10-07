from datetime import datetime, timezone

import pytest

from metricas.cfr import classify_conclusion


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


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
