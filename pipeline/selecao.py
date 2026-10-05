"""Seleção de repositórios candidatos (Search API) e filtro de GitHub Actions."""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)

SEARCH_PATH = "/search/repositories"
SEARCH_MAX = 1000  # teto da Search API por consulta


def _query(lo: int, hi: int) -> str:
    return f"stars:{lo}..{hi} fork:false archived:false"


def search_candidates(client, star_ranges: list[list[int]], per_range_limit: int = 1000) -> list[str]:
    limit = min(per_range_limit, SEARCH_MAX)
    names: list[str] = []
    seen: set[str] = set()
    for lo, hi in star_ranges:
        query = _query(lo, hi)
        items = client.paginate(SEARCH_PATH, {"q": query}, item_key="items")
        if len(items) >= SEARCH_MAX:
            log.warning("faixa %r atingiu o teto de %d resultados; considere fatiá-la", query, SEARCH_MAX)
        for item in items[:limit]:
            if item["full_name"] not in seen:
                seen.add(item["full_name"])
                names.append(item["full_name"])
    return names
