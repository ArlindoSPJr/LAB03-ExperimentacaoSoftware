"""RQ05: correlacao de Spearman entre frequencia de deploy e CFR (a) e (b).

Le apenas `data/metricas.csv`. Para cada par reporta rho, p e n (repos com os
dois valores presentes); com menos de 3 pares ou variavel constante, rho e p
ficam NaN.
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

PARES = [
    {"rq": "RQ05a", "nome": "freq_cfr_ci", "x": "deploy_freq_week", "y": "cfr_ci"},
    {"rq": "RQ05b", "nome": "freq_cfr_entrega", "x": "deploy_freq_week", "y": "cfr_entrega"},
]

ENTRADA_PADRAO = pathlib.Path("data/metricas.csv")
SAIDA_PADRAO = pathlib.Path("analise/saida")


def _pares_validos(df: pd.DataFrame, x: str, y: str) -> pd.DataFrame:
    if x not in df.columns or y not in df.columns:
        return pd.DataFrame(columns=[x, y], dtype=float)
    return df[[x, y]].apply(pd.to_numeric, errors="coerce").dropna()


def correlacionar(df: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por par com rq, x, y, n, rho e p."""
    linhas = []
    for par in PARES:
        v = _pares_validos(df, par["x"], par["y"])
        rho = p = math.nan
        if len(v) >= 3 and v[par["x"]].nunique() > 1 and v[par["y"]].nunique() > 1:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                res = spearmanr(v[par["x"]], v[par["y"]])
            rho, p = float(res.statistic), float(res.pvalue)
        linhas.append({"rq": par["rq"], "x": par["x"], "y": par["y"], "n": len(v), "rho": rho, "p": p})
    return pd.DataFrame(linhas, columns=["rq", "x", "y", "n", "rho", "p"])


def graficos(df: pd.DataFrame, saida: pathlib.Path) -> list[pathlib.Path]:
    """Dispersao por par; eixo x em log quando todos > 0 e max/min > 100."""
    saida = pathlib.Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    arquivos = []
    for par in PARES:
        v = _pares_validos(df, par["x"], par["y"])
        if v.empty:
            continue
        fig, ax = plt.subplots(figsize=(5, 4))
        ax.scatter(v[par["x"]], v[par["y"]], s=12, alpha=0.6)
        x = v[par["x"]]
        if (x > 0).all() and x.max() / x.min() > 100:
            ax.set_xscale("log")
        ax.set_xlabel(f"{par['x']} (releases/semana)")
        ax.set_ylabel(f"{par['y']} (fracao 0-1)")
        ax.set_title(f"{par['rq']} (n={len(v)})")
        arq = saida / f"{par['rq'].lower()}_{par['nome']}.png"
        fig.tight_layout()
        fig.savefig(arq, dpi=150)
        plt.close(fig)
        arquivos.append(arq)
    return arquivos


def executar(entrada: pathlib.Path, saida: pathlib.Path) -> dict:
    """Le o CSV, grava `tabela_rq05.csv` e os graficos em `saida`."""
    df = pd.read_csv(entrada)
    saida = pathlib.Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    tabela = correlacionar(df)
    tabela.to_csv(saida / "tabela_rq05.csv", index=False)
    return {"tabela": tabela, "graficos": graficos(df, saida)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="RQ05: Spearman entre frequencia e CFR")
    ap.add_argument("--entrada", type=pathlib.Path, default=ENTRADA_PADRAO)
    ap.add_argument("--saida", type=pathlib.Path, default=SAIDA_PADRAO)
    args = ap.parse_args(argv)
    res = executar(args.entrada, args.saida)
    print(res["tabela"].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
