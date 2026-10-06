"""Coleta de workflow runs do default branch (event=push), um mês por consulta.

Com filtros, `actions/runs` devolve no máximo 1.000 resultados por consulta; por isso
a janela é dividida em meses e os meses que atingem o teto são sinalizados.
"""
from __future__ import annotations

import calendar
import logging
from datetime import date, datetime, timezone

log = logging.getLogger(__name__)

TETO_RUNS = 1000


def _parse_date(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def meses_da_janela(start: datetime, end: datetime) -> list[str]:
    """Faixas `created=AAAA-MM-DD..AAAA-MM-DD`, uma por mês, cortadas em start e end."""
    inicio, fim = start.date(), end.date()
    faixas = []
    atual = inicio.replace(day=1)
    while atual <= fim:
        ultimo = date(atual.year, atual.month, calendar.monthrange(atual.year, atual.month)[1])
        faixas.append(f"{max(atual, inicio).isoformat()}..{min(ultimo, fim).isoformat()}")
        atual = date(atual.year + atual.month // 12, atual.month % 12 + 1, 1)
    return faixas


def _run(item: dict) -> dict:
    return {
        "workflow_id": item["workflow_id"],
        "conclusion": item.get("conclusion"),
        "run_started_at": _parse_date(item.get("run_started_at") or item["created_at"]),
        "updated_at": _parse_date(item["updated_at"]),
    }


def fetch_runs(client, full_name: str, branch: str, start: datetime, end: datetime) -> tuple[list[dict], list[str]]:
    """(runs, meses no teto): runs de `event=push` no `branch`, ordenados por `run_started_at`.

    `meses no teto` lista os meses (`AAAA-MM`) que devolveram 1.000 resultados e
    podem estar incompletos.
    """
    runs: list[dict] = []
    teto: list[str] = []
    for faixa in meses_da_janela(start, end):
        params = {"branch": branch, "event": "push", "created": faixa}
        items = client.paginate(f"/repos/{full_name}/actions/runs", params, item_key="workflow_runs")
        if len(items) >= TETO_RUNS:
            teto.append(faixa[:7])
            log.warning("%s: mês %s atingiu o teto de %d runs", full_name, faixa[:7], TETO_RUNS)
        runs.extend(_run(item) for item in items)
    runs.sort(key=lambda r: r["run_started_at"])
    return runs, teto
