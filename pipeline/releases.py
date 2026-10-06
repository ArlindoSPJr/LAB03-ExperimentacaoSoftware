"""Coleta de releases (unidade de deploy) de um repositório."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import quote

from pipeline.http import NotFoundError

log = logging.getLogger(__name__)


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


def fetch_commits(client, full_name: str, base_tag: str, head_tag: str) -> list[dict] | None:
    """Commits incluídos em `head_tag` desde `base_tag` (`compare/{base}...{head}`, paginado).

    Sem paginação o compare traz no máximo 250 commits; aqui todas as páginas são lidas.
    Devolve `None` quando o compare dá 404 (tag apagada ou reescrita): o caso é
    registrado no log e o chamador ignora a release e a conta em `compare_404`.
    """
    path = f"/repos/{full_name}/compare/{quote(base_tag, safe='/')}...{quote(head_tag, safe='/')}"
    try:
        items = client.paginate(path, item_key="commits")
    except NotFoundError:
        log.warning("%s: compare %s...%s retornou 404; release ignorada no lead time",
                    full_name, base_tag, head_tag)
        return None
    return [
        {
            "sha": item["sha"],
            "author_date": _parse_date(item["commit"]["author"]["date"]),
            "message": item["commit"]["message"],
        }
        for item in items
    ]
