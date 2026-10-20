"""RQ01 a RQ04: mediana e IQR de frequencia, lead time, CFR e recuperacao.

Le apenas `data/metricas.csv`. Sempre mediana e IQR (nunca media/desvio).
"""
import pandas as pd

from analise.estatistica import mediana_iqr

METRICAS = [
    {"rq": "RQ01", "nome": "frequencia", "coluna": "deploy_freq_week", "unidade": "releases/semana"},
    {"rq": "RQ02a", "nome": "lead_time_a", "coluna": "lead_time_a_days", "unidade": "dias"},
    {"rq": "RQ02b", "nome": "lead_time_b", "coluna": "lead_time_b_days", "unidade": "dias"},
    {"rq": "RQ03a", "nome": "cfr_ci", "coluna": "cfr_ci", "unidade": "fracao 0-1"},
    {"rq": "RQ03b", "nome": "cfr_entrega", "coluna": "cfr_entrega", "unidade": "fracao 0-1"},
    {"rq": "RQ04", "nome": "recuperacao", "coluna": "recovery_median_h", "unidade": "horas"},
]


def resumir(df: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por metrica com n, n_ausentes, mediana, q1, q3 e iqr.

    Coluna ausente do CSV gera linha com n=0 (mediana NaN), sem erro.
    """
    linhas = []
    for m in METRICAS:
        if m["coluna"] in df.columns:
            valores = pd.to_numeric(df[m["coluna"]], errors="coerce")
            ausentes = int(valores.isna().sum())
            valores = valores.tolist()
        else:
            valores, ausentes = [], 0
        s = mediana_iqr(valores)
        linhas.append({
            **m, "n": s["n"], "n_ausentes": ausentes, "mediana": s["mediana"],
            "q1": s["q1"], "q3": s["q3"], "iqr": s["iqr"],
        })
    colunas = ["rq", "nome", "coluna", "unidade", "n", "n_ausentes", "mediana", "q1", "q3", "iqr"]
    return pd.DataFrame(linhas, columns=colunas).astype({"mediana": float, "q1": float, "q3": float, "iqr": float})
