"""Concordância entre os três avaliadores (kappa de Fleiss) e rótulo de consenso (S02-O2.1).

Entrada comum: um `DataFrame` com uma linha por item rotulado (repositório ou release)
e uma coluna por avaliador (ex.: `A`, `B`, `C`). Os rótulos são normalizados
(minúsculas, sem espaços nas pontas) antes de qualquer cálculo.
"""
from __future__ import annotations

import math
from collections import Counter

import numpy as np
import pandas as pd
from statsmodels.stats.inter_rater import aggregate_raters, fleiss_kappa

# Vocabulário fixo de cada dimensão (enunciado, seção 6.2), usado nas planilhas e no kappa.
DIMENSOES: dict[str, list[str]] = {
    "tipo_projeto": ["biblioteca/framework", "aplicacao/servico", "ferramenta CLI", "outro"],
    "entregas_reais": ["sim", "nao", "incerto"],
    "corretiva": ["sim", "nao"],
}


def _normalizar(valor) -> str | None:
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return None
    texto = str(valor).strip().lower()
    return texto or None


def fleiss_kappa_dimensao(rotulos: pd.DataFrame, categorias: list[str]) -> float:
    """Kappa de Fleiss de uma dimensão (`aggregate_raters` + `fleiss_kappa`).

    Todo item precisa ter rótulo de todos os avaliadores e todo rótulo precisa estar em
    `categorias`; caso contrário levanta `ValueError` (nada é descartado em silêncio).
    Se todos os rótulos caem numa só categoria o kappa é 0/0 e a função devolve NaN.
    """
    codigos = {c.lower(): i for i, c in enumerate(categorias)}
    normalizados = rotulos.map(_normalizar)
    if normalizados.isna().to_numpy().any():
        raise ValueError(f"{int(normalizados.isna().to_numpy().sum())} rótulo(s) vazio(s)")
    desconhecidos = sorted(set(normalizados.to_numpy().ravel()) - set(codigos))
    if desconhecidos:
        raise ValueError(f"rótulos fora das categorias {categorias}: {desconhecidos}")
    matriz = normalizados.apply(lambda col: col.map(codigos)).to_numpy(dtype=int)
    contagens, _ = aggregate_raters(matriz, n_cat=len(categorias))
    with np.errstate(divide="ignore", invalid="ignore"):
        return float(fleiss_kappa(contagens, method="fleiss"))


def consenso(rotulos: pd.DataFrame) -> pd.DataFrame:
    """Rótulo de consenso por maioria simples, preservando o índice de `rotulos`.

    Colunas: `consenso` (rótulo mais votado, ou NA sem maioria), `reuniao` (True no
    empate 1-1-1, decidido em reunião pelo protocolo de desempate) e `votos`
    (`A=sim; B=nao; C=sim`, para registrar a decisão).
    """
    normalizados = rotulos.map(_normalizar)
    linhas = []
    for _, item in normalizados.iterrows():
        contagem = Counter(v for v in item if v is not None).most_common()
        tem_maioria = bool(contagem) and contagem[0][1] > 1 and (
            len(contagem) == 1 or contagem[0][1] > contagem[1][1])
        linhas.append({
            "consenso": contagem[0][0] if tem_maioria else pd.NA,
            "reuniao": not tem_maioria,
            "votos": "; ".join(f"{avaliador}={valor}" for avaliador, valor in item.items()),
        })
    return pd.DataFrame(linhas, index=rotulos.index)
