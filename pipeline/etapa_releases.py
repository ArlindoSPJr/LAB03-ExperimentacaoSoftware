"""Etapa de releases do orquestrador: frequência de deploy (RQ01) e lead time (RQ02).

Definição principal (C1): só releases não-pré-release. A release anterior à janela
(decisão 5 de docs/ISSUES.md) serve apenas de base para o `compare` da primeira
release da janela; ela não conta na frequência.
"""
from __future__ import annotations

from datetime import datetime

from metricas.lead_time import (
    contar_lead_negativos,
    lead_time_commits_days,
    lead_time_release_days,
    repo_lead_time_a,
    repo_lead_time_b,
)
from pipeline.releases import fetch_commits, fetch_releases


def semanas_da_janela(start: datetime, end: datetime) -> float:
    """Semanas da janela contando os dias inteiros (12 meses ≈ 52,1 semanas)."""
    return ((end.date() - start.date()).days + 1) / 7


def coletar_releases_e_lead_time(client, meta: dict, janela: tuple[datetime, datetime]) -> dict:
    """Métricas de entrega de um repositório.

    `meta` é o RepoMeta (usa `full_name`); `janela` é `(start, end)` em UTC.
    Devolve `n_releases`, `deploy_freq_week`, `lead_time_a_days`, `lead_time_b_days`,
    `compare_404` e `n_lead_negativos`.
    """
    start, end = janela
    full_name = meta["full_name"]
    releases = [r for r in fetch_releases(client, full_name, start, end) if not r["prerelease"]]
    na_janela = [r for r in releases if start <= r["published_at"] <= end]

    por_release: list[float | None] = []
    por_commit: list[float] = []
    compare_404 = 0
    n_lead_negativos = 0
    for anterior, release in zip(releases, releases[1:]):
        commits = fetch_commits(client, full_name, anterior["tag_name"], release["tag_name"])
        if commits is None:
            compare_404 += 1
            continue
        datas = [c["author_date"] for c in commits]
        por_release.append(lead_time_release_days(release["published_at"], datas))
        por_commit.extend(lead_time_commits_days(release["published_at"], datas))
        n_lead_negativos += contar_lead_negativos(release["published_at"], datas)

    return {
        "n_releases": len(na_janela),
        "deploy_freq_week": len(na_janela) / semanas_da_janela(start, end),
        "lead_time_a_days": repo_lead_time_a(por_release),
        "lead_time_b_days": repo_lead_time_b(por_commit),
        "compare_404": compare_404,
        "n_lead_negativos": n_lead_negativos,
    }
