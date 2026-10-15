"""Variantes da unidade de deploy para a RQ07: `release+pre` (C2) e `tag` (C3).

Funções puras. Cada unidade é `{"nome": str, "data": datetime}`: `nome` é a tag usada
no `compare` e `data` é `published_at` (releases e pré-releases) ou o
`commit.author.date` do commit apontado (tags).

Mesmas regras da unidade `release` da S01: a unidade anterior à janela, do mesmo
tipo, serve só de base do `compare` (decisão 5 de docs/ISSUES.md); a primeira
unidade da história fica sem lead time; `compare` 404 é contado; lead time
negativo é descartado e contado (decisão 4).
"""
from __future__ import annotations

from datetime import datetime

from metricas.lead_time import contar_lead_negativos, lead_time_commits_days, repo_lead_time_b

UNIDADES = ("release", "release+pre", "tag")


def separar_janela(unidades: list[dict], start: datetime, end: datetime) -> tuple[dict | None, list[dict]]:
    """(base, na_janela): a última unidade antes de `start` e as unidades em [start, end], por data."""
    ordenadas = sorted(unidades, key=lambda u: u["data"])
    anteriores = [u for u in ordenadas if u["data"] < start]
    na_janela = [u for u in ordenadas if start <= u["data"] <= end]
    return (anteriores[-1] if anteriores else None), na_janela


def pares_para_compare(base: dict | None, na_janela: list[dict],
                       max_compares: int | None = None) -> tuple[list[tuple[dict, dict]], int]:
    """Pares (anterior, atual) de unidades consecutivas para o `compare` e quantos o teto pulou.

    Sem base, a primeira unidade da janela não tem par (primeira da história). Se há
    mais pares que `max_compares`, usa uma amostra sistemática e determinística,
    espalhada pela janela: os pares de índice `i * n // max_compares`. `None` = sem teto.
    """
    sequencia = ([base] if base is not None else []) + list(na_janela)
    pares = list(zip(sequencia, sequencia[1:]))
    n = len(pares)
    if max_compares is None or n <= max_compares:
        return pares, 0
    return [pares[i * n // max_compares] for i in range(max_compares)], n - max_compares


def lead_time_b_variante(resultados: list[tuple[datetime, list[datetime] | None]]) -> dict:
    """Lead time (b) da variante a partir de (data da unidade, datas dos commits do compare).

    `None` no lugar das datas = `compare` 404: a unidade é ignorada e contada.
    """
    por_commit: list[float] = []
    compare_404 = 0
    n_lead_negativos = 0
    for data_unidade, datas in resultados:
        if datas is None:
            compare_404 += 1
            continue
        por_commit.extend(lead_time_commits_days(data_unidade, datas))
        n_lead_negativos += contar_lead_negativos(data_unidade, datas)
    return {
        "lead_time_b_days": repo_lead_time_b(por_commit),
        "compare_404": compare_404,
        "n_lead_negativos": n_lead_negativos,
    }
