"""Heurística de release corretiva (RQ03, CFR variante b).

Enunciado (seção 3): uma release é corretiva quando a versão muda apenas no número de
patch do versionamento semântico (2.3.0 -> 2.3.1) e/ou há commits com `revert`,
`hotfix` ou `fix` na mensagem entre ela e a release anterior. Cada versão da
heurística fica registrada em `HEURISTICA_VERSAO` e em docs/HEURISTICA_VERSOES.md.
"""
from __future__ import annotations

import re

HEURISTICA_VERSAO = "v1"

_SEMVER = re.compile(r"^(?P<prefixo>.*?)v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(?:[-+].*)?$", re.I)
_PALAVRAS = re.compile(r"\b(revert|hotfix|fix)", re.I)


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


def tem_commit_corretivo(mensagens: list[str]) -> bool:
    """True se alguma mensagem de commit contém revert, hotfix ou fix."""
    return any(_PALAVRAS.search(m or "") for m in mensagens)


def eh_corretiva(tag_anterior: str, tag_atual: str, mensagens: list[str]) -> bool:
    """v1: bump só de patch OU commit com revert/hotfix/fix desde a release anterior."""
    return bump_so_de_patch(tag_anterior, tag_atual) or tem_commit_corretivo(mensagens)
