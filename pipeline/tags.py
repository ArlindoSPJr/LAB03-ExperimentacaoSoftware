"""Coleta de tags, a unidade de deploy da variante C3 da RQ07.

Tags não trazem data; o enunciado (§4) manda usar a data do commit apontado pela tag,
que aqui é o `commit.author.date` (definição comum de data de commit, §3).

A listagem `GET /repos/{o}/{r}/tags` vem ordenada por nome, em ordem de versão
decrescente, e não por data. Por isso a janela não é cortada pela posição na lista:
- tags da janela: o SHA apontado precisa estar entre os commits do default branch
  listados por `GET /repos/{o}/{r}/commits?sha=&since=&until=` (regra "só default
  branch" do §3), com `author.date` dentro da janela. O custo acompanha os commits da
  janela (≈ commits/100 chamadas), não o total histórico de tags (milhares em alguns repos);
- tag-base (anterior à janela, só para o `compare`): entre as até `CANDIDATOS_BASE` tags
  que aparecem na listagem logo depois da última tag da janela (as versões
  anteriores), a mais recente com data anterior ao início da janela. A data vem de
  `GET /repos/{o}/{r}/git/commits/{sha}`, que não traz arquivos nem patches (cache menor).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from pipeline.http import NotFoundError

log = logging.getLogger(__name__)

CANDIDATOS_BASE = 5


def _parse_date(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_tags(client, full_name: str) -> list[dict]:
    """Tags do repositório (`{"name", "sha"}`), na ordem devolvida pela API; paginado."""
    return [{"name": item["name"], "sha": item["commit"]["sha"]}
            for item in client.paginate(f"/repos/{full_name}/tags")]


def datas_commits_branch(client, full_name: str, branch: str, start: datetime, end: datetime) -> dict[str, datetime]:
    """SHA -> `commit.author.date` dos commits do `branch` listados para a janela."""
    params = {"sha": branch, "since": _iso(start), "until": _iso(end)}
    return {item["sha"]: _parse_date(item["commit"]["author"]["date"])
            for item in client.paginate(f"/repos/{full_name}/commits", params)}


def data_do_commit(client, full_name: str, sha: str) -> datetime | None:
    """`author.date` do commit (`git/commits/{sha}`); `None` se o commit não existe (404)."""
    try:
        data, _ = client.get(f"/repos/{full_name}/git/commits/{sha}")
    except NotFoundError:
        log.warning("%s: commit %s da tag não encontrado (404); tag ignorada como base", full_name, sha)
        return None
    return _parse_date(data["author"]["date"])


def tags_com_data(client, full_name: str, branch: str, start: datetime, end: datetime,
                  candidatos_base: int = CANDIDATOS_BASE) -> list[dict]:
    """Tags da janela (`{"nome", "data"}`) mais, se encontrada, a tag-base anterior à janela."""
    tags = fetch_tags(client, full_name)
    if not tags:
        return []
    datas = datas_commits_branch(client, full_name, branch, start, end)
    posicoes = [i for i, t in enumerate(tags) if t["sha"] in datas and start <= datas[t["sha"]] <= end]
    if not posicoes:
        return []
    unidades = [{"nome": tags[i]["name"], "data": datas[tags[i]["sha"]]} for i in posicoes]

    candidatas = tags[posicoes[-1] + 1:][:candidatos_base]
    base = None
    for candidata in candidatas:
        data = datas.get(candidata["sha"]) or data_do_commit(client, full_name, candidata["sha"])
        if data is not None and data < start and (base is None or data > base["data"]):
            base = {"nome": candidata["name"], "data": data}
    return unidades + ([base] if base else [])
