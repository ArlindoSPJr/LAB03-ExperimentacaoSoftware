"""Heurística de release corretiva (RQ03, CFR variante b).

Enunciado (seção 3): uma release é corretiva quando a versão muda apenas no número de
patch do versionamento semântico (2.3.0 -> 2.3.1) e/ou há commits com `revert`,
`hotfix` ou `fix` na mensagem entre ela e a release anterior. As versões testadas ficam
em `VERSOES` e em docs/HEURISTICA_VERSOES.md; `eh_corretiva` aponta para a vigente.
"""
from __future__ import annotations

import re

HEURISTICA_VERSAO = "v3"

_SEMVER = re.compile(r"^(?P<prefixo>.*?)v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(?:[-+].*)?$", re.I)
_PALAVRAS = re.compile(r"\b(revert|hotfix|fix)", re.I)
# Commits que não mudam o comportamento para o usuário: CI, docs, manutenção, dependências, merges.
_RUIDO = re.compile(r"^(ci|docs|chore|test|build|style)(\(.*?\))?!?:|^bump |^merge |dependabot|renovate"
                    r"|update dependenc", re.I)
_FUNCIONALIDADE = re.compile(r"^(feat|feature)(\(.*?\))?!?:|^add |^added |^implement|^new |^support ", re.I)


def versao_semver(tag: str) -> tuple[str, int, int, int] | None:
    """(prefixo, major, minor, patch) da tag, ou None se não seguir semver."""
    m = _SEMVER.match(tag or "")
    if not m:
        return None
    return m["prefixo"].lower(), int(m["major"]), int(m["minor"]), int(m["patch"])


def bump_so_de_patch(tag_anterior: str, tag_atual: str) -> bool:
    """True se só o patch aumentou (mesmo prefixo, major e minor)."""
    anterior, atual = versao_semver(tag_anterior), versao_semver(tag_atual)
    if anterior is None or atual is None:
        return False
    return anterior[:3] == atual[:3] and atual[3] > anterior[3]


def tag_de_patch(tag: str) -> bool:
    """True se a tag é uma versão de patch (x.y.z com z > 0), seja qual for a anterior."""
    versao = versao_semver(tag)
    return versao is not None and versao[3] > 0


def tem_commit_corretivo(mensagens: list[str]) -> bool:
    """True se alguma mensagem de commit contém revert, hotfix ou fix."""
    return any(_PALAVRAS.search(m or "") for m in mensagens)


def eh_corretiva_v1(tag_anterior: str, tag_atual: str, mensagens: list[str]) -> bool:
    """v1 (regra literal): bump só de patch OU commit com revert/hotfix/fix."""
    return bump_so_de_patch(tag_anterior, tag_atual) or tem_commit_corretivo(mensagens)


def eh_corretiva_v2(tag_anterior: str, tag_atual: str, mensagens: list[str]) -> bool:
    """v2: a própria tag é de patch; cobre backports, cuja anterior por data é de outra linha."""
    return tag_de_patch(tag_atual)


def eh_corretiva_v3(tag_anterior: str, tag_atual: str, mensagens: list[str]) -> bool:
    """v3: tag de patch E (nenhum commit de funcionalidade OU maioria dos commits corretivos).

    Considera só a primeira linha de cada mensagem e ignora commits de ruído (_RUIDO).
    """
    if not tag_de_patch(tag_atual):
        return False
    titulos = [(m or "").splitlines()[0] if m else "" for m in mensagens]
    uteis = [t for t in titulos if not _RUIDO.search(t)]
    funcionalidades = sum(bool(_FUNCIONALIDADE.search(t)) for t in uteis)
    correcoes = sum(bool(_PALAVRAS.search(t)) for t in uteis)
    return funcionalidades == 0 or (bool(uteis) and correcoes / len(uteis) >= 0.5)


VERSOES = {"v1": eh_corretiva_v1, "v2": eh_corretiva_v2, "v3": eh_corretiva_v3}
eh_corretiva = VERSOES[HEURISTICA_VERSAO]
