"""RQ01 a RQ04: mediana e IQR de frequencia, lead time, CFR e recuperacao.

Le apenas `data/metricas.csv`. Sempre mediana e IQR (nunca media/desvio).
"""
import argparse
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

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


def _soma(df: pd.DataFrame, coluna: str):
    if coluna not in df.columns:
        return None
    return int(pd.to_numeric(df[coluna], errors="coerce").fillna(0).sum())


def censurados(df: pd.DataFrame) -> pd.DataFrame:
    """Censura de recuperacao (episodios) e de CFR (b) (releases dos ultimos 7 dias).

    prop_global = episodios censurados / episodios (None sem episodios);
    prop_repo_* = mediana e IQR de `prop_censurados` entre os repos.
    """
    episodios = _soma(df, "n_episodes") or 0
    cens = _soma(df, "n_censored") or 0
    prop_repo = mediana_iqr(
        pd.to_numeric(df["prop_censurados"], errors="coerce").tolist()
        if "prop_censurados" in df.columns else []
    )
    repos_com = (
        int((pd.to_numeric(df["n_censored"], errors="coerce").fillna(0) > 0).sum())
        if "n_censored" in df.columns else 0
    )
    return pd.DataFrame([{
        "repos": len(df),
        "episodios": episodios,
        "episodios_censurados": cens,
        "prop_global": cens / episodios if episodios else None,
        "repos_com_censura": repos_com,
        "prop_repo_mediana": prop_repo["mediana"],
        "prop_repo_q1": prop_repo["q1"],
        "prop_repo_q3": prop_repo["q3"],
        "releases_censuradas_entrega": _soma(df, "n_censuradas_entrega"),
    }])


ENTRADA_PADRAO = pathlib.Path("data/metricas.csv")
SAIDA_PADRAO = pathlib.Path("analise/saida")


def graficos(df: pd.DataFrame, saida: pathlib.Path) -> list[pathlib.Path]:
    """Boxplot (mediana e IQR) por metrica em PNG; pula colunas ausentes ou vazias.

    Escala log so quando todos os valores sao > 0 e max/min > 100.
    """
    saida = pathlib.Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    arquivos = []
    for m in METRICAS:
        if m["coluna"] not in df.columns:
            continue
        v = pd.to_numeric(df[m["coluna"]], errors="coerce").dropna()
        if v.empty:
            continue
        fig, ax = plt.subplots(figsize=(4, 4))
        ax.boxplot(v, showfliers=True)
        if (v > 0).all() and v.max() / v.min() > 100:
            ax.set_yscale("log")
        ax.set_xticks([])
        ax.set_ylabel(m["unidade"])
        ax.set_title(f"{m['rq']} - {m['nome']} (n={len(v)})")
        arq = saida / f"{m['rq'].lower()}_{m['nome']}.png"
        fig.tight_layout()
        fig.savefig(arq, dpi=150)
        plt.close(fig)
        arquivos.append(arq)
    return arquivos


def executar(entrada: pathlib.Path, saida: pathlib.Path) -> dict:
    """Le o CSV, grava tabela, censurados e graficos em `saida`."""
    df = pd.read_csv(entrada)
    saida = pathlib.Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    tabela = resumir(df)
    cens = censurados(df)
    tabela.to_csv(saida / "tabela_rq01_rq04.csv", index=False)
    cens.to_csv(saida / "censurados.csv", index=False)
    return {"tabela": tabela, "censurados": cens, "graficos": graficos(df, saida)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="RQ01 a RQ04 (mediana e IQR)")
    ap.add_argument("--entrada", type=pathlib.Path, default=ENTRADA_PADRAO)
    ap.add_argument("--saida", type=pathlib.Path, default=SAIDA_PADRAO)
    args = ap.parse_args(argv)
    res = executar(args.entrada, args.saida)
    sem = res["tabela"][res["tabela"]["n"] == 0]["coluna"].tolist()
    if sem:
        print(f"AVISO: sem dados para: {', '.join(sem)}")
    print(res["tabela"].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
