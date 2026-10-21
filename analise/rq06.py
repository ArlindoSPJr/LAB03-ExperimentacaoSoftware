"""RQ06: as metricas DORA variam com caracteristicas do projeto?

Le apenas `data/metricas.csv`. Fatores: linguagem (menos de CORTE_LINGUAGEM
repos vira "Outras"), estrelas, contribuidores e idade em quartis, e tipo de
projeto (so os 60 repos rotulados na S02). Para cada fator x metrica:
Mann-Whitney + Cliff's delta com 2 grupos, Kruskal-Wallis + epsilon quadrado
com 3 ou mais. Correcao de Holm sobre a familia inteira de testes.
"""
import argparse
import math
import pathlib

import pandas as pd
from scipy.stats import kruskal, mannwhitneyu
from statsmodels.stats.multitest import multipletests

from analise.estatistica import cliffs_delta, epsilon_quadrado, mediana_iqr, quartis_grupos

FATORES = ["linguagem", "estrelas", "contribuidores", "idade", "tipo_projeto"]
METRICAS = ["deploy_freq_week", "lead_time_a_days", "cfr_ci", "recovery_median_h"]
CORTE_LINGUAGEM = 10

# |delta| de Romano et al. (2006); epsilon quadrado de Rea e Parker (1992)
_CORTES_EFEITO = {
    "cliffs_delta": (0.147, 0.33, 0.474),
    "epsilon_quadrado": (0.01, 0.08, 0.26),
}

ENTRADA_PADRAO = pathlib.Path("data/metricas.csv")
SAIDA_PADRAO = pathlib.Path("analise/saida")


def agrupar_linguagem(linguagens: pd.Series, corte: int = CORTE_LINGUAGEM) -> pd.Series:
    """Linguagens com menos de `corte` repos viram "Outras"; ausentes ficam None."""
    contagem = linguagens.value_counts()
    raras = set(contagem[contagem < corte].index)
    return linguagens.map(lambda v: None if pd.isna(v) else ("Outras" if v in raras else v))


def _quartis(serie: pd.Series) -> list:
    return quartis_grupos(pd.to_numeric(serie, errors="coerce").tolist())


def montar_fatores(df: pd.DataFrame, corte: int = CORTE_LINGUAGEM) -> pd.DataFrame:
    """Uma coluna por fator, alinhada ao indice de `df`."""
    tipo = df["tipo_projeto"] if "tipo_projeto" in df.columns else pd.Series(None, index=df.index)
    return pd.DataFrame({
        "linguagem": agrupar_linguagem(df["language"], corte),
        "estrelas": _quartis(df["stars"]),
        "contribuidores": _quartis(df["contributors"]),
        "idade": _quartis(df["age_days"]),
        "tipo_projeto": tipo.where(tipo.notna(), None),
    }, index=df.index)


def _magnitude(efeito: str, valor: float):
    if valor is None or math.isnan(valor):
        return None
    p, m, g = _CORTES_EFEITO[efeito]
    v = abs(valor)
    return "desprezivel" if v < p else "pequeno" if v < m else "medio" if v < g else "grande"


def comparar_grupos(valores: pd.Series, grupos: pd.Series) -> dict:
    """Teste de uma metrica entre grupos, ignorando pares com ausente.

    Devolve teste, efeito, n, k (grupos), estatistica (U1 ou H), p, valor_efeito
    e magnitude; com menos de 2 grupos ou valores todos iguais, p fica NaN.
    """
    d = pd.DataFrame({"v": pd.to_numeric(valores, errors="coerce").values, "g": grupos.values}).dropna()
    amostras = [g["v"].tolist() for _, g in sorted(d.groupby("g"), key=lambda t: str(t[0]))]
    r = {"teste": None, "efeito": None, "n": len(d), "k": len(amostras),
         "estatistica": math.nan, "p": math.nan, "valor_efeito": math.nan, "magnitude": None}
    if len(amostras) < 2:
        return r
    if len(amostras) == 2:
        a, b = amostras
        res = mannwhitneyu(a, b, alternative="two-sided")
        r.update(teste="mann-whitney", efeito="cliffs_delta", estatistica=float(res.statistic),
                 p=float(res.pvalue), valor_efeito=cliffs_delta(res.statistic, len(a), len(b)))
    else:
        r.update(teste="kruskal-wallis", efeito="epsilon_quadrado")
        if d["v"].nunique() == 1:  # todos os valores iguais: H indefinido
            return r
        res = kruskal(*amostras)
        r.update(estatistica=float(res.statistic), p=float(res.pvalue),
                 valor_efeito=epsilon_quadrado(res.statistic, len(d)))
    r["magnitude"] = _magnitude(r["efeito"], r["valor_efeito"])
    return r


def tabela_testes(df: pd.DataFrame, corte: int = CORTE_LINGUAGEM) -> pd.DataFrame:
    """Uma linha por fator x metrica, com p ajustado por Holm na familia inteira."""
    fatores = montar_fatores(df, corte)
    linhas = [
        {"fator": f, "metrica": m, **comparar_grupos(df[m], fatores[f])}
        for f in FATORES for m in METRICAS
    ]
    tab = pd.DataFrame(linhas)
    tab["p_holm"] = math.nan
    validos = tab["p"].notna()
    if validos.any():
        tab.loc[validos, "p_holm"] = multipletests(tab.loc[validos, "p"], method="holm")[1]
    tab["significativo"] = tab["p_holm"] < 0.05
    return tab


def resumo_grupos(df: pd.DataFrame, corte: int = CORTE_LINGUAGEM) -> pd.DataFrame:
    """Mediana e IQR de cada metrica por grupo de cada fator."""
    fatores = montar_fatores(df, corte)
    linhas = []
    for f in FATORES:
        for grupo in sorted(fatores[f].dropna().unique(), key=str):
            mascara = fatores[f] == grupo
            for m in METRICAS:
                s = mediana_iqr(pd.to_numeric(df.loc[mascara, m], errors="coerce").tolist())
                linhas.append({"fator": f, "grupo": grupo, "metrica": m, "n": s["n"],
                               "mediana": s["mediana"], "q1": s["q1"], "q3": s["q3"]})
    return pd.DataFrame(linhas, columns=["fator", "grupo", "metrica", "n", "mediana", "q1", "q3"])


def executar(entrada: pathlib.Path, saida: pathlib.Path) -> dict:
    """Le o CSV e grava `tabela_rq06.csv` e `rq06_grupos.csv` em `saida`."""
    df = pd.read_csv(entrada)
    saida = pathlib.Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    tab, grupos = tabela_testes(df), resumo_grupos(df)
    tab.to_csv(saida / "tabela_rq06.csv", index=False)
    grupos.to_csv(saida / "rq06_grupos.csv", index=False)
    return {"tabela": tab, "grupos": grupos}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="RQ06: fatores x metricas com Holm")
    ap.add_argument("--entrada", type=pathlib.Path, default=ENTRADA_PADRAO)
    ap.add_argument("--saida", type=pathlib.Path, default=SAIDA_PADRAO)
    args = ap.parse_args(argv)
    res = executar(args.entrada, args.saida)
    colunas = ["fator", "metrica", "teste", "n", "k", "p", "p_holm", "efeito", "valor_efeito", "magnitude"]
    print(res["tabela"][colunas].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
