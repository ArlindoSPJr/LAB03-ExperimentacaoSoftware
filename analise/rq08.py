"""RQ08 (bonus): rework rate comparado ao CFR de entrega (RQ03 b).

Le apenas `data/metricas.csv`. `rework_rate` = releases corretivas / releases da janela
(heuristica vigente, sem censura); `cfr_entrega` = releases seguidas em ate 7 dias por
uma corretiva / releases avaliadas. Reporta mediana e IQR de cada uma e da diferenca
pareada, Spearman entre as duas e quantos repos tem rework maior, igual ou menor.
"""
import argparse
import math
import pathlib
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

from analise.estatistica import mediana_iqr  # noqa: E402

ENTRADA_PADRAO = pathlib.Path("data/metricas.csv")
SAIDA_PADRAO = pathlib.Path("analise/saida")
X, Y = "rework_rate", "cfr_entrega"


def _numerico(df: pd.DataFrame, coluna: str) -> pd.Series:
    return pd.to_numeric(df[coluna], errors="coerce") if coluna in df.columns else pd.Series(dtype=float)


def _pares(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({X: _numerico(df, X), Y: _numerico(df, Y)}).dropna()


def resumir(df: pd.DataFrame) -> pd.DataFrame:
    """Mediana e IQR de rework_rate, cfr_entrega e da diferenca pareada (rework - CFR)."""
    pares = _pares(df)
    series = {X: _numerico(df, X), Y: _numerico(df, Y), "rework_menos_cfr": pares[X] - pares[Y]}
    linhas = []
    for medida, valores in series.items():
        s = mediana_iqr(valores.tolist())
        linhas.append({"medida": medida, "n": s["n"], "mediana": s["mediana"], "q1": s["q1"],
                       "q3": s["q3"], "iqr": s["iqr"]})
    return pd.DataFrame(linhas, columns=["medida", "n", "mediana", "q1", "q3", "iqr"])


def comparar(df: pd.DataFrame) -> dict:
    """Spearman (rho, p) e contagem de repos com rework maior, igual ou menor que o CFR (b)."""
    pares = _pares(df)
    rho = p = math.nan
    if len(pares) >= 3 and pares[X].nunique() > 1 and pares[Y].nunique() > 1:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = spearmanr(pares[X], pares[Y])
        rho, p = float(res.statistic), float(res.pvalue)
    return {"n": len(pares), "rho": rho, "p": p,
            "n_rework_maior": int((pares[X] > pares[Y]).sum()),
            "n_igual": int((pares[X] == pares[Y]).sum()),
            "n_rework_menor": int((pares[X] < pares[Y]).sum())}


def grafico(df: pd.DataFrame, saida: pathlib.Path) -> pathlib.Path:
    """Dispersao rework rate x CFR (b) com a reta y = x."""
    saida = pathlib.Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    pares = _pares(df)
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.scatter(pares[Y], pares[X], s=12, alpha=0.6)
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", linewidth=1, label="y = x")
    ax.set_xlabel("cfr_entrega (fracao 0-1)")
    ax.set_ylabel("rework_rate (fracao 0-1)")
    ax.set_title(f"RQ08 (n={len(pares)})")
    ax.legend(loc="lower right")
    arq = saida / "rq08_rework_vs_cfr.png"
    fig.tight_layout()
    fig.savefig(arq, dpi=150)
    plt.close(fig)
    return arq


def executar(entrada: pathlib.Path, saida: pathlib.Path) -> dict:
    """Le o CSV e grava `tabela_rq08.csv`, `tabela_rq08_comparacao.csv` e o grafico em `saida`."""
    df = pd.read_csv(entrada)
    saida = pathlib.Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    resumo = resumir(df)
    comparacao = pd.DataFrame([comparar(df)])
    resumo.to_csv(saida / "tabela_rq08.csv", index=False)
    comparacao.to_csv(saida / "tabela_rq08_comparacao.csv", index=False)
    return {"resumo": resumo, "comparacao": comparacao, "grafico": grafico(df, saida)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="RQ08: rework rate comparado ao CFR de entrega")
    ap.add_argument("--entrada", type=pathlib.Path, default=ENTRADA_PADRAO)
    ap.add_argument("--saida", type=pathlib.Path, default=SAIDA_PADRAO)
    args = ap.parse_args(argv)
    res = executar(args.entrada, args.saida)
    print(res["resumo"].to_string(index=False))
    print(res["comparacao"].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
