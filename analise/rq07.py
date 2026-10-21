"""RQ07: sensibilidade da classificacao DORA a definicao operacional.

Tres combinacoes (enunciado, RQ07); o tempo de recuperacao e o mesmo nas tres:
- C1 (referencia): release / lead time (a) / CFR (a), lida de `classificacao_c1.csv`;
- C2: release + pre-release / lead time (b) / CFR (b);
- C3: tag / lead time (b) / CFR (a).
C2 e C3 sao classificadas com os cortes fixos de `metricas/classificacao.py`; repo com
alguma metrica ausente fica sem classificacao naquela combinacao. Para cada par:
% de repos que mudaram de categoria e kappa de Cohen com ponderacao linear, so entre
os repos classificados nas duas combinacoes.
"""
import argparse
import pathlib

import pandas as pd
from sklearn.metrics import cohen_kappa_score

from metricas.classificacao import classificar_repositorio

ENTRADA_PADRAO = pathlib.Path("data/metricas.csv")
C1_PADRAO = pathlib.Path("analise/saida/classificacao_c1.csv")
SAIDA_PADRAO = pathlib.Path("analise/saida")

# combinacao -> (frequencia, lead time, CFR, recuperacao)
COMBINACOES = {
    "C1": ("deploy_freq_week", "lead_time_a_days", "cfr_ci", "recovery_median_h"),
    "C2": ("deploy_freq_week_pre", "lead_time_b_days_pre", "cfr_entrega_pre", "recovery_median_h"),
    "C3": ("deploy_freq_week_tag", "lead_time_b_days_tag", "cfr_ci", "recovery_median_h"),
}
PARES = [("C1", "C2"), ("C1", "C3"), ("C2", "C3")]
ORDEM = ["Elite", "High", "Medium", "Low"]
NOTA = {"Low": 1, "Medium": 2, "High": 3, "Elite": 4}
NAO_CLASSIFICADO = "Nao classificado"


def _valor(v):
    return None if pd.isna(v) else float(v)


def classificar_combinacao(df: pd.DataFrame, nome: str) -> pd.Series:
    """Categoria geral (ou None) de cada repo na combinacao `nome`."""
    colunas = COMBINACOES[nome]
    categorias = [classificar_repositorio(*(_valor(linha[c]) for c in colunas))["dora_overall"]
                  for _, linha in df.iterrows()]
    return pd.Series(categorias, index=df.index, dtype="object")


def montar_classificacao(metricas: pd.DataFrame, c1: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por repo com a categoria em C1 (do CSV de referencia), C2 e C3."""
    referencia = dict(zip(c1["repo"], c1["dora_overall"]))
    saida = pd.DataFrame({"repo": metricas["repo"]})
    saida["C1"] = [None if pd.isna(referencia.get(r)) else referencia.get(r) for r in metricas["repo"]]
    saida["C2"] = classificar_combinacao(metricas, "C2")
    saida["C3"] = classificar_combinacao(metricas, "C3")
    return saida.astype({"C1": object})


def _par(classificacao: pd.DataFrame, a: str, b: str) -> pd.DataFrame:
    return classificacao[classificacao[a].notna() & classificacao[b].notna()]


def comparar(classificacao: pd.DataFrame, a: str, b: str) -> dict:
    """n, quantos mudaram de categoria, % que mudou e kappa linear entre `a` e `b`."""
    par = _par(classificacao, a, b)
    n = len(par)
    mudou = int((par[a] != par[b]).sum())
    if n == 0:
        kappa = float("nan")
    else:
        kappa = float(cohen_kappa_score(par[a].map(NOTA), par[b].map(NOTA),
                                        labels=[1, 2, 3, 4], weights="linear"))
    return {"par": f"{a}x{b}", "n": n, "n_mudou": mudou,
            "pct_mudou": 100 * mudou / n if n else float("nan"), "kappa_linear": kappa}


def transicoes(classificacao: pd.DataFrame, a: str, b: str) -> pd.DataFrame:
    """Matriz de-para (linhas: categoria em `a`; colunas: em `b`), na ordem Elite..Low."""
    par = _par(classificacao, a, b)
    tabela = pd.crosstab(pd.Categorical(par[a], categories=ORDEM),
                         pd.Categorical(par[b], categories=ORDEM), dropna=False)
    tabela.index, tabela.columns = list(ORDEM), list(ORDEM)
    return tabela


def distribuicao(classificacao: pd.DataFrame) -> pd.DataFrame:
    """Contagem e proporcao de cada categoria por combinacao."""
    total = len(classificacao)
    linhas = []
    for nome in COMBINACOES:
        serie = classificacao[nome]
        for categoria in ORDEM + [NAO_CLASSIFICADO]:
            n = int(serie.isna().sum()) if categoria == NAO_CLASSIFICADO else int((serie == categoria).sum())
            linhas.append({"combinacao": nome, "categoria": categoria, "n": n,
                           "prop": n / total if total else None})
    return pd.DataFrame(linhas).astype({"prop": float})


def executar(entrada: pathlib.Path, c1: pathlib.Path, saida: pathlib.Path) -> dict:
    """Le o dataset e a C1 de referencia e grava as saidas da RQ07 em `saida`."""
    classificacao = montar_classificacao(pd.read_csv(entrada), pd.read_csv(c1))
    pares = pd.DataFrame([comparar(classificacao, a, b) for a, b in PARES])
    dist = distribuicao(classificacao)
    saida = pathlib.Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    classificacao.to_csv(saida / "rq07_classificacao.csv", index=False)
    pares.to_csv(saida / "rq07_pares.csv", index=False)
    dist.to_csv(saida / "rq07_distribuicao.csv", index=False)
    for a, b in PARES:
        transicoes(classificacao, a, b).to_csv(saida / f"rq07_transicoes_{a}_{b}.csv")
    return {"classificacao": classificacao, "pares": pares, "distribuicao": dist}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="RQ07: sensibilidade da classificacao DORA (C1, C2, C3)")
    ap.add_argument("--entrada", type=pathlib.Path, default=ENTRADA_PADRAO)
    ap.add_argument("--c1", type=pathlib.Path, default=C1_PADRAO)
    ap.add_argument("--saida", type=pathlib.Path, default=SAIDA_PADRAO)
    args = ap.parse_args(argv)
    res = executar(args.entrada, args.c1, args.saida)
    print(res["pares"].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
