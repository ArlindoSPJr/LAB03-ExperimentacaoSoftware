"""Coleta de releases (unidade de deploy) de um repositório."""
from __future__ import annotations

from datetime import datetime, timezone


def _parse_date(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def fetch_releases(client, full_name: str, start: datetime, end: datetime) -> list[dict]:
    """Releases publicadas (draft=false) em [start, end], ordenadas por published_at.

    Pré-releases são mantidas com `prerelease=True` (variantes da RQ07). Inclui também
    a release não-pré-release imediatamente anterior à janela (decisão 5 de
    docs/ISSUES.md), que serve só de base para o `compare` do lead time.
    """
    releases = []
    for item in client.paginate(f"/repos/{full_name}/releases"):
        if item.get("draft") or not item.get("published_at"):
            continue
        releases.append({
            "tag_name": item["tag_name"],
            "published_at": _parse_date(item["published_at"]),
            "prerelease": bool(item.get("prerelease")),
            "body": item.get("body"),
        })
    releases.sort(key=lambda r: r["published_at"])
    na_janela = [r for r in releases if start <= r["published_at"] <= end]
    anteriores = [r for r in releases if r["published_at"] < start and not r["prerelease"]]
    return anteriores[-1:] + na_janela
