"""Metadados de repositório: estrelas, linguagem, contribuidores, criação e default branch."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

from pipeline.http import GitHubError

log = logging.getLogger(__name__)

_LAST_RE = re.compile(r'<([^>]+)>\s*;\s*rel="last"')


def _parse_date(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _last_page(headers) -> int | None:
    """Número da última página no cabeçalho Link, ou None se não houver rel="last"."""
    match = _LAST_RE.search(headers.get("Link", "") if headers else "")
    if not match:
        return None
    return int(parse_qs(urlparse(match.group(1)).query)["page"][0])


def _too_large(exc: GitHubError) -> bool:
    return exc.status == 403 and "too large" in str(exc).lower()


def _contributors(client, full_name: str) -> int | None:
    """Contribuidores (incluindo anônimos) lendo a última página com per_page=1.

    None quando a API recusa a lista por ser grande demais (403 "too large").
    """
    try:
        data, headers = client.get(f"/repos/{full_name}/contributors", {"per_page": 1, "anon": "true"})
    except GitHubError as exc:
        if not _too_large(exc):
            raise
        log.warning("%s: lista de contribuidores grande demais para a API; contributors=None", full_name)
        return None
    last = _last_page(headers)
    if last is not None:
        return last
    return len(data) if isinstance(data, list) else 0  # sem Link: 0 ou 1 item; 204 sem corpo -> 0


def collect_metadata(client, full_name: str) -> dict:
    """RepoMeta do repositório. NotFoundError (repositório apagado/renomeado) é propagada."""
    repo, _ = client.get(f"/repos/{full_name}")
    return {
        "full_name": repo["full_name"],
        "stars": int(repo["stargazers_count"]),
        "language": repo.get("language"),
        "contributors": _contributors(client, full_name),
        "created_at": _parse_date(repo["created_at"]),
        "default_branch": repo["default_branch"],
    }
