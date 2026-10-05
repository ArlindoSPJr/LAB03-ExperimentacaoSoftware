"""Seleção de repositórios candidatos (Search API) e filtro de GitHub Actions.

Decisão 2 de docs/ISSUES.md: busca com fork:false archived:false; candidatos
embaralhados com random_state=42 (amostra reproduzível e não enviesada para os
mais populares).
"""
from __future__ import annotations

import logging
import random

log = logging.getLogger(__name__)

SEARCH_PATH = "/search/repositories"
SEARCH_MAX = 1000  # teto da Search API por consulta
RANDOM_STATE = 42


def _query(lo: int, hi: int) -> str:
    return f"stars:{lo}..{hi} fork:false archived:false"


def search_candidates(client, star_ranges: list[list[int]], per_range_limit: int = 1000) -> list[str]:
    """full_names únicos das faixas de estrelas, embaralhados com random_state=42.

    Cada faixa [lo, hi] vira uma consulta `stars:lo..hi fork:false archived:false`
    limitada a min(per_range_limit, 1000) resultados. A lista é ordenada antes do
    embaralhamento, para não depender da ordem devolvida pela API.
    """
    if per_range_limit < 1:
        raise ValueError("per_range_limit precisa ser >= 1")
    for star_range in star_ranges:
        if len(star_range) != 2 or star_range[0] > star_range[1]:
            raise ValueError(f"faixa de estrelas inválida: {star_range!r}")
    limit = min(per_range_limit, SEARCH_MAX)
    unique: set[str] = set()
    for lo, hi in star_ranges:
        query = _query(lo, hi)
        items = client.paginate(SEARCH_PATH, {"q": query}, item_key="items")
        if len(items) >= SEARCH_MAX:
            log.warning("faixa %r atingiu o teto de %d resultados; considere fatiá-la", query, SEARCH_MAX)
        unique.update(item["full_name"] for item in items[:limit])
    names = sorted(unique)
    random.Random(RANDOM_STATE).shuffle(names)
    return names
