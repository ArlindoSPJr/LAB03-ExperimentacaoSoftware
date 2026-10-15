"""Etapa de variantes da unidade de deploy (RQ07): `release+pre` (C2) e `tag` (C3).

Para cada variante: unidades na janela, frequência semanal e lead time (b) pelos
commits do `compare` entre unidades consecutivas do mesmo tipo (`fetch_commits` da S01).
O CFR(b) por unidade fica com a S02-O3.4.

Custo de cota: repositórios com centenas ou milhares de unidades na janela (ex.: uma tag
por build) fariam um `compare` por unidade. `max_compares` limita os compares de cada
variante; acima dele o lead time (b) usa uma amostra sistemática espalhada pela janela
(`metricas.variantes.pares_para_compare`), a frequência continua exata e as unidades
puladas são contadas em `teto_compare_<variante>`.
"""
from __future__ import annotations

from datetime import datetime

from metricas.variantes import lead_time_b_variante, pares_para_compare, separar_janela
from pipeline.etapa_releases import semanas_da_janela
from pipeline.releases import fetch_commits, fetch_releases
from pipeline.tags import tags_com_data

MAX_COMPARES_PADRAO = 100


def _variante(client, full_name: str, unidades: list[dict], janela, max_compares, sufixo: str,
              chave_n: str) -> dict:
    start, end = janela
    base, na_janela = separar_janela(unidades, start, end)
    pares, pulados = pares_para_compare(base, na_janela, max_compares)
    resultados = []
    for anterior, atual in pares:
        commits = fetch_commits(client, full_name, anterior["nome"], atual["nome"])
        datas = None if commits is None else [c["author_date"] for c in commits]
        resultados.append((atual["data"], datas))
    lead = lead_time_b_variante(resultados)
    return {
        chave_n: len(na_janela),
        f"deploy_freq_week_{sufixo}": len(na_janela) / semanas_da_janela(start, end),
        f"lead_time_b_days_{sufixo}": lead["lead_time_b_days"],
        f"compare_404_{sufixo}": lead["compare_404"],
        f"n_lead_negativos_{sufixo}": lead["n_lead_negativos"],
        f"teto_compare_{sufixo}": pulados,
    }


def coletar_variantes(client, meta: dict, janela: tuple[datetime, datetime],
                      max_compares: int | None = MAX_COMPARES_PADRAO) -> dict:
    """Colunas das variantes `release+pre` (sufixo `_pre`) e `tag` (sufixo `_tag`) de um repositório.

    Chaves: `n_releases_pre`, `deploy_freq_week_pre`, `lead_time_b_days_pre`, `compare_404_pre`,
    `n_lead_negativos_pre`, `teto_compare_pre`, `n_tags`, `deploy_freq_week_tag`,
    `lead_time_b_days_tag`, `compare_404_tag`, `n_lead_negativos_tag`, `teto_compare_tag`.
    """
    start, end = janela
    full_name = meta["full_name"]
    releases = fetch_releases(client, full_name, start, end, base_inclui_pre=True)
    com_pre = [{"nome": r["tag_name"], "data": r["published_at"]} for r in releases]
    tags = tags_com_data(client, full_name, meta["default_branch"], start, end)
    return {
        **_variante(client, full_name, com_pre, janela, max_compares, "pre", "n_releases_pre"),
        **_variante(client, full_name, tags, janela, max_compares, "tag", "n_tags"),
    }
