"""Consolidação do dataset final (S02-O1.3), sem chamar a API.

Lê as saídas do orquestrador (`data/metricas.csv` e `data/funil.csv`), valida a
integridade do dataset, acrescenta as colunas derivadas e regrava `data/metricas.csv`
na ordem do dicionário (`data/DICIONARIO.md`).
"""
from __future__ import annotations

import pandas as pd

from pipeline.orquestrador import COLUNAS, MIN_RELEASES, MIN_RUNS_VALIDOS


class DatasetInvalido(ValueError):
    """O dataset não passou na validação; `problemas` lista cada falha encontrada."""

    def __init__(self, problemas: list[str]):
        super().__init__("dataset inválido:\n- " + "\n- ".join(problemas))
        self.problemas = problemas


def _estrutura(metricas: pd.DataFrame) -> list[str]:
    ausentes = [c for c in COLUNAS if c not in metricas.columns]
    if ausentes:
        return [f"colunas ausentes em metricas.csv: {', '.join(ausentes)}"]
    if list(metricas.columns[:len(COLUNAS)]) != COLUNAS:
        return ["colunas fora da ordem do orquestrador (pipeline.orquestrador.COLUNAS)"]
    return []


def _repos(metricas: pd.DataFrame) -> list[str]:
    problemas = []
    vazios = metricas["repo"].isna() | (metricas["repo"].astype(str).str.strip() == "")
    if vazios.any():
        problemas.append(f"repo vazio em {int(vazios.sum())} linha(s)")
    duplicados = sorted(metricas.loc[metricas["repo"].duplicated() & ~vazios, "repo"].unique())
    if duplicados:
        problemas.append(f"repositórios duplicados: {', '.join(duplicados)}")
    return problemas


def _repos_onde(metricas: pd.DataFrame, mascara: pd.Series) -> str:
    return ", ".join(str(r) for r in metricas.loc[mascara.fillna(False).astype(bool), "repo"])


def _inclusao(metricas: pd.DataFrame) -> list[str]:
    problemas = []
    for coluna, minimo in (("n_releases", MIN_RELEASES), ("n_runs_validos", MIN_RUNS_VALIDOS)):
        abaixo = pd.to_numeric(metricas[coluna]) < minimo
        if abaixo.any():
            problemas.append(f"{coluna} < {minimo} (critério de inclusão): {_repos_onde(metricas, abaixo)}")
    return problemas


def validar(metricas: pd.DataFrame, funil: pd.DataFrame, semanas: float) -> list[str]:
    """Lista os problemas de integridade do dataset (vazia se ele é válido).

    `semanas` é a duração da janela em semanas (`semanas_da_janela`), usada para
    conferir as frequências.
    """
    problemas = _estrutura(metricas)
    if problemas:
        return problemas
    return _repos(metricas) + _inclusao(metricas)
