"""Etapa de CFR de entrega (RQ03 b) e rework rate (RQ08) do orquestrador.

Cada unidade de deploy da janela é classificada como corretiva pela heurística vigente
(`metricas.corretiva.eh_corretiva`), com as mensagens de commit do `compare` com a
unidade anterior (`fetch_commits`, mesmo cache das etapas de releases e variantes).
Unidades sem compare (primeira da história, compare 404 ou puladas pelo teto da
variante `release+pre`) são classificadas só pela tag.
"""
from __future__ import annotations

from datetime import datetime

from metricas.cfr import cfr_entrega
from metricas.corretiva import eh_corretiva
from metricas.variantes import pares_para_compare, separar_janela
from pipeline.etapa_variantes import MAX_COMPARES_PADRAO
from pipeline.releases import fetch_commits, fetch_releases


def _unidades(releases: list[dict]) -> list[dict]:
    return [{"nome": r["tag_name"], "data": r["published_at"]} for r in releases]


def classificar_unidades(client, full_name: str, unidades: list[dict],
                         janela: tuple[datetime, datetime], max_compares: int | None = None) -> list[dict]:
    """Unidades da janela, em ordem de data, com `published_at` e `corretiva` (bool)."""
    start, end = janela
    base, na_janela = separar_janela(unidades, start, end)
    pares, _ = pares_para_compare(base, na_janela, max_compares)
    anterior_de = {id(atual): anterior for anterior, atual in pares}
    classificadas = []
    for unidade in na_janela:
        anterior = anterior_de.get(id(unidade))
        commits = fetch_commits(client, full_name, anterior["nome"], unidade["nome"]) if anterior else None
        mensagens = [c["message"] for c in commits] if commits else []
        corretiva = eh_corretiva(anterior["nome"] if anterior else "", unidade["nome"], mensagens)
        classificadas.append({"published_at": unidade["data"], "corretiva": corretiva})
    return classificadas


def coletar_cfr_entrega(client, meta: dict, janela: tuple[datetime, datetime],
                        max_compares: int | None = MAX_COMPARES_PADRAO) -> dict:
    """CFR de entrega e rework rate de um repositório.

    Unidade `release` (C1, sem teto, como o lead time): `cfr_entrega`, `n_falhas_entrega`,
    `n_censuradas_entrega` e `rework_rate` (releases corretivas ÷ releases na janela).
    Unidade `release+pre` (C2, com o teto da variante): `cfr_entrega_pre`.
    """
    full_name, (start, end) = meta["full_name"], janela
    releases = [r for r in fetch_releases(client, full_name, start, end) if not r["prerelease"]]
    so_releases = classificar_unidades(client, full_name, _unidades(releases), janela)
    com_pre = classificar_unidades(
        client, full_name, _unidades(fetch_releases(client, full_name, start, end, base_inclui_pre=True)),
        janela, max_compares)
    c1, c2 = cfr_entrega(so_releases, end), cfr_entrega(com_pre, end)
    corretivas = sum(u["corretiva"] for u in so_releases)
    return {
        "cfr_entrega": c1["cfr"],
        "n_falhas_entrega": c1["falhas"],
        "n_censuradas_entrega": c1["censuradas"],
        "rework_rate": corretivas / len(so_releases) if so_releases else None,
        "cfr_entrega_pre": c2["cfr"],
    }
