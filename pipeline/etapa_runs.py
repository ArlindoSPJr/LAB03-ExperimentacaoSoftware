"""Etapa de runs do orquestrador: CFR (a) (RQ03) e tempo de recuperação (RQ04).

Usa os runs de `event=push` do default branch dentro da janela. Runs que
`classify_conclusion` ignora (cancelled, skipped, ...) não contam em `n_runs_validos`.
"""
from __future__ import annotations

from datetime import datetime

from metricas.cfr import cfr_ci, classify_conclusion
from metricas.recuperacao import contar_falhas_iniciais, repo_recovery
from pipeline.runs import fetch_runs


def coletar_runs_e_metricas(client, meta: dict, janela: tuple[datetime, datetime]) -> dict:
    """Métricas de CI de um repositório.

    `meta` é o RepoMeta (usa `full_name` e `default_branch`); `janela` é `(start, end)` em UTC.
    Devolve `n_runs_validos`, `cfr_ci`, `recovery_median_h`, `n_episodes`, `n_censored`,
    `n_falhas_iniciais` e `meses_no_teto`.
    """
    start, end = janela
    runs, meses_no_teto = fetch_runs(client, meta["full_name"], meta["default_branch"], start, end)
    mediana, n_episodes, n_censored = repo_recovery(runs)
    return {
        "n_runs_validos": sum(1 for r in runs if classify_conclusion(r["conclusion"]) is not None),
        "cfr_ci": cfr_ci(runs),
        "recovery_median_h": mediana,
        "n_episodes": n_episodes,
        "n_censored": n_censored,
        "n_falhas_iniciais": contar_falhas_iniciais(runs),
        "meses_no_teto": meses_no_teto,
    }
