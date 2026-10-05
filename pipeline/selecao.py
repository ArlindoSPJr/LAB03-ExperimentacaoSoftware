"""Seleção de repositórios candidatos (Search API) e filtro de GitHub Actions."""
from __future__ import annotations

SEARCH_PATH = "/search/repositories"


def _query(lo: int, hi: int) -> str:
    return f"stars:{lo}..{hi} fork:false archived:false"


def search_candidates(client, star_ranges: list[list[int]], per_range_limit: int = 1000) -> list[str]:
    names = []
    for lo, hi in star_ranges:
        items = client.paginate(SEARCH_PATH, {"q": _query(lo, hi)}, item_key="items")
        names.extend(item["full_name"] for item in items)
    return names
