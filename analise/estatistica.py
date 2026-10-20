"""Utilitarios estatisticos da Sprint 3 (funcoes puras, sem I/O).

Sempre mediana e IQR (nunca media/desvio). Quartis por interpolacao linear
(padrao do numpy), usados tanto no IQR quanto na formacao de grupos.
"""
import math

import numpy as np


def _validos(valores):
    return [
        float(v)
        for v in valores
        if v is not None and not (isinstance(v, float) and math.isnan(v))
    ]


def mediana_iqr(valores):
    """Mediana e IQR ignorando None/NaN.

    Devolve {"mediana", "q1", "q3", "iqr", "n"}; sem valores validos, os
    quatro primeiros sao None e n = 0.
    """
    v = _validos(valores)
    if not v:
        return {"mediana": None, "q1": None, "q3": None, "iqr": None, "n": 0}
    q1, med, q3 = (float(x) for x in np.percentile(v, [25, 50, 75]))
    return {"mediana": med, "q1": q1, "q3": q3, "iqr": q3 - q1, "n": len(v)}


def cliffs_delta(U, n1, n2):
    """Cliff's delta a partir de U1 de Mann-Whitney: 2*U1/(n1*n2) - 1."""
    if n1 <= 0 or n2 <= 0:
        raise ValueError("n1 e n2 devem ser positivos")
    return 2 * U / (n1 * n2) - 1


def epsilon_quadrado(H, n):
    """Epsilon quadrado de Kruskal-Wallis: H / (n - 1)."""
    if n < 2:
        raise ValueError("n deve ser >= 2")
    return H / (n - 1)


def quartis_grupos(valores):
    """Rotula cada valor com "Q1".."Q4" pelos quartis dos valores validos.

    Preserva a ordem da entrada; None/NaN viram None. Valor igual a um
    corte fica no grupo inferior.
    """
    v = _validos(valores)
    if not v:
        return [None for _ in valores]
    c1, c2, c3 = np.percentile(v, [25, 50, 75])
    saida = []
    for x in valores:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            saida.append(None)
        elif x <= c1:
            saida.append("Q1")
        elif x <= c2:
            saida.append("Q2")
        elif x <= c3:
            saida.append("Q3")
        else:
            saida.append("Q4")
    return saida
