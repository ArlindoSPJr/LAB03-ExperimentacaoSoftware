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
from datetime import datetime, timedelta, timezone

from pipeline.http import GitHubError, NotFoundError

log = logging.getLogger(__name__)

CANDIDATOS_BASE = 5
MENOR_FATIA = timedelta(days=1)
PER_PAGE = 100


def _parse_date(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_tags(client, full_name: str) -> list[dict]:
    """Tags do repositório (`{"name", "sha"}`), na ordem devolvida pela API; paginado."""
    return [{"name": item["name"], "sha": item["commit"]["sha"]}
            for item in client.paginate(f"/repos/{full_name}/tags")]


def _erro_de_servidor(erro: GitHubError) -> bool:
    """5xx persistente (já esgotou as tentativas do cliente)."""
    return erro.status is not None and erro.status >= 500


def _listar_commits(client, full_name: str, branch: str, start: datetime, end: datetime) -> dict[str, datetime]:
    params = {"sha": branch, "since": _iso(start), "until": _iso(end)}
    return {item["sha"]: _parse_date(item["commit"]["author"]["date"])
            for item in client.paginate(f"/repos/{full_name}/commits", params)}


def fatias_mensais(start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    """[start, end] em meses de calendário contíguos; cada fatia termina 1 s antes da seguinte."""
    fatias = []
    inicio = start
    while inicio <= end:
        proximo = (inicio.replace(day=1, hour=0, minute=0, second=0, microsecond=0) + timedelta(days=32)).replace(day=1)
        fim = min(proximo - timedelta(seconds=1), end)
        fatias.append((inicio, fim))
        inicio = proximo
    return fatias


class _Paginas:
    """Lista uma fatia página a página; página com 5xx persistente é refinada (`per_page` 100 → 10 → 1).

    Alguns commits fazem a API devolver 500 em qualquer página que os contenha, mesmo
    com `per_page=1` (caso real: 3 commits de NousResearch/hermes-agent em 2026-09-05).
    Esses itens são pulados e contados em `omitidos`. Se um bloco inteiro de
    `PER_PAGE` itens falhar mesmo item a item, a API está fora do ar: o erro é propagado.
    """

    def __init__(self, client, full_name: str, branch: str, start: datetime, end: datetime):
        self.client = client
        self.path = f"/repos/{full_name}/commits"
        self.params = {"sha": branch, "since": _iso(start), "until": _iso(end)}
        self.datas: dict[str, datetime] = {}
        self.omitidos = 0

    def _bloco(self, per_page: int, page: int) -> tuple[int, bool]:
        """(itens lidos com sucesso, bloco cheio = pode haver mais itens depois)."""
        try:
            data, _ = self.client.get(self.path, {**self.params, "per_page": per_page, "page": page})
        except GitHubError as erro:
            if not _erro_de_servidor(erro):
                raise
            if per_page == 1:
                self.omitidos += 1
                return 0, True
            sub = max(per_page // 10, 1)
            lidos = 0
            for k in range(per_page // sub):
                n, cheio = self._bloco(sub, (page - 1) * (per_page // sub) + k + 1)
                lidos += n
                if not cheio:
                    return lidos, False
            if lidos == 0 and per_page == PER_PAGE:
                raise
            return lidos, True
        for item in data or []:
            self.datas[item["sha"]] = _parse_date(item["commit"]["author"]["date"])
        return len(data or []), len(data or []) == per_page

    def listar(self) -> tuple[dict[str, datetime], int]:
        page = 1
        while self._bloco(PER_PAGE, page)[1]:
            page += 1
        return self.datas, self.omitidos


def _listar_fatiado(client, full_name: str, branch: str, start: datetime, end: datetime,
                    menor_fatia: timedelta) -> tuple[dict[str, datetime], int]:
    """Lista [start, end]; em 5xx persistente divide a fatia ao meio até `menor_fatia`.

    Na menor fatia, a listagem passa a ser feita página a página (`_Paginas`).
    """
    try:
        return _listar_commits(client, full_name, branch, start, end), 0
    except GitHubError as erro:
        if not _erro_de_servidor(erro):
            raise
    if end - start <= menor_fatia:
        log.warning("%s: HTTP 5xx nos commits de %s a %s; refinando as páginas", full_name, _iso(start), _iso(end))
        datas, omitidos = _Paginas(client, full_name, branch, start, end).listar()
        if omitidos:
            log.warning("%s: %d commit(s) de %s a %s que a API não consegue listar (HTTP 5xx) foram omitidos",
                        full_name, omitidos, _iso(start), _iso(end))
        return datas, omitidos
    meio = (start + (end - start) / 2).replace(microsecond=0)
    log.warning("%s: HTTP 5xx nos commits de %s a %s; dividindo a fatia ao meio", full_name, _iso(start), _iso(end))
    esquerda, om_esq = _listar_fatiado(client, full_name, branch, start, meio, menor_fatia)
    direita, om_dir = _listar_fatiado(client, full_name, branch, meio + timedelta(seconds=1), end, menor_fatia)
    return {**esquerda, **direita}, om_esq + om_dir


def listar_datas_commits(client, full_name: str, branch: str, start: datetime, end: datetime,
                         menor_fatia: timedelta = MENOR_FATIA) -> tuple[dict[str, datetime], int]:
    """(SHA -> `commit.author.date`, commits omitidos) dos commits do `branch` na janela.

    Primeiro tenta a consulta única da janela (mesmas URLs e chaves de cache de sempre).
    Se a API devolver 5xx persistente (depois das tentativas do cliente), refaz por mês;
    mês que ainda falhe é dividido ao meio até `menor_fatia`, e a menor fatia é lida
    página a página, refinando a página que falha até `per_page=1`. Os resultados são
    unidos por SHA (sem duplicatas). Commits que a API não serve nem um a um são
    omitidos e contados; se nada puder ser lido, o `GitHubError` é propagado.
    """
    try:
        return _listar_commits(client, full_name, branch, start, end), 0
    except GitHubError as erro:
        if not _erro_de_servidor(erro):
            raise
        log.warning("%s: HTTP %s na listagem de commits da janela (%s); refazendo por mês",
                    full_name, erro.status, erro.url)
    datas: dict[str, datetime] = {}
    omitidos = 0
    for inicio, fim in fatias_mensais(start, end):
        parte, n = _listar_fatiado(client, full_name, branch, inicio, fim, menor_fatia)
        datas.update(parte)
        omitidos += n
    return datas, omitidos


def datas_commits_branch(client, full_name: str, branch: str, start: datetime, end: datetime,
                         menor_fatia: timedelta = MENOR_FATIA) -> dict[str, datetime]:
    """SHA -> `commit.author.date` dos commits do `branch` listados para a janela (ver `listar_datas_commits`)."""
    return listar_datas_commits(client, full_name, branch, start, end, menor_fatia)[0]


def data_do_commit(client, full_name: str, sha: str) -> datetime | None:
    """`author.date` do commit (`git/commits/{sha}`); `None` se o commit não existe (404)."""
    try:
        data, _ = client.get(f"/repos/{full_name}/git/commits/{sha}")
    except NotFoundError:
        log.warning("%s: commit %s da tag não encontrado (404); tag ignorada como base", full_name, sha)
        return None
    return _parse_date(data["author"]["date"])


def coletar_tags(client, full_name: str, branch: str, start: datetime, end: datetime,
                 candidatos_base: int = CANDIDATOS_BASE) -> tuple[list[dict], int]:
    """(tags da janela mais a tag-base, como em `tags_com_data`; commits da janela omitidos).

    Commits omitidos são os que a API não consegue listar (`listar_datas_commits`); uma
    tag que aponte para um deles não é reconhecida como tag da janela.
    """
    tags = fetch_tags(client, full_name)
    if not tags:
        return [], 0
    datas, omitidos = listar_datas_commits(client, full_name, branch, start, end)
    posicoes = [i for i, t in enumerate(tags) if t["sha"] in datas and start <= datas[t["sha"]] <= end]
    if not posicoes:
        return [], omitidos
    unidades = [{"nome": tags[i]["name"], "data": datas[tags[i]["sha"]]} for i in posicoes]

    candidatas = tags[posicoes[-1] + 1:][:candidatos_base]
    base = None
    for candidata in candidatas:
        data = datas.get(candidata["sha"]) or data_do_commit(client, full_name, candidata["sha"])
        if data is not None and data < start and (base is None or data > base["data"]):
            base = {"nome": candidata["name"], "data": data}
    return unidades + ([base] if base else []), omitidos


def tags_com_data(client, full_name: str, branch: str, start: datetime, end: datetime,
                  candidatos_base: int = CANDIDATOS_BASE) -> list[dict]:
    """Tags da janela (`{"nome", "data"}`) mais, se encontrada, a tag-base anterior à janela."""
    return coletar_tags(client, full_name, branch, start, end, candidatos_base)[0]
