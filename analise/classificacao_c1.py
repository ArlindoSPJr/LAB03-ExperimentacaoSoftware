"""Classificacao DORA de referencia (C1) para a RQ07.

C1 = release / lead time (a) / CFR (a). Le `score_*` e `dora_overall` de
`data/metricas.csv` (calculados na S01; aqui nao se reclassifica) e traduz as
notas em categorias Elite/High/Medium/Low. Repos sem classificacao (alguma
metrica ausente) ficam como "Nao classificado".
"""
import argparse
import pathlib

import pandas as pd

from metricas.classificacao import CATEGORIAS

ENTRADA_PADRAO = pathlib.Path("data/metricas.csv")
SAIDA_PADRAO = pathlib.Path("analise/saida")

# dimensao -> (coluna de nota, coluna de categoria)
DIMENSOES = {
    "freq": ("score_freq", "cat_freq"),
    "lead": ("score_lead", "cat_lead"),
    "cfr": ("score_cfr", "cat_cfr"),
    "rec": ("score_rec", "cat_rec"),
}
ORDEM = ["Elite", "High", "Medium", "Low"]
NAO_CLASSIFICADO = "Nao classificado"
COLUNAS_SAIDA = [
    "repo", "score_freq", "score_lead", "score_cfr", "score_rec",
    "cat_freq", "cat_lead", "cat_cfr", "cat_rec", "dora_overall", "classificado",
]


def _categoria(nota):
    return None if pd.isna(nota) else CATEGORIAS[int(nota)]


def classificar(df: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por repo: notas, categoria por metrica, `dora_overall` e `classificado`.

    `dora_overall` vem do CSV (sem recalculo). Coluna ausente vira vazia.
    """
    saida = pd.DataFrame({"repo": df["repo"].tolist() if "repo" in df.columns else []})
    n = len(saida)
    for nota, cat in DIMENSOES.values():
        notas = pd.to_numeric(df[nota], errors="coerce") if nota in df.columns else pd.Series([float("nan")] * n)
        saida[nota] = notas.reset_index(drop=True).astype("Int64")
    for nota, cat in DIMENSOES.values():
        saida[cat] = pd.Series([_categoria(v) for v in saida[nota]], dtype="object")
    geral = df["dora_overall"] if "dora_overall" in df.columns else pd.Series([None] * n)
    saida["dora_overall"] = pd.Series(
        [None if pd.isna(v) else v for v in geral], dtype="object")
    saida["classificado"] = saida["dora_overall"].notna()
    return saida[COLUNAS_SAIDA]


def distribuicao(classificacao: pd.DataFrame) -> pd.DataFrame:
    """Contagem e proporcao por dimensao (freq, lead, cfr, rec, geral) e categoria."""
    colunas = {d: cat for d, (_, cat) in DIMENSOES.items()}
    colunas["geral"] = "dora_overall"
    total = len(classificacao)
    linhas = []
    for dim, col in colunas.items():
        serie = classificacao[col]
        for categoria in ORDEM + [NAO_CLASSIFICADO]:
            n = int(serie.isna().sum()) if categoria == NAO_CLASSIFICADO else int((serie == categoria).sum())
            linhas.append({
                "dimensao": dim, "categoria": categoria, "n": n,
                "prop": n / total if total else None,
            })
    return pd.DataFrame(linhas).astype({"prop": float})


def executar(entrada: pathlib.Path, saida: pathlib.Path) -> dict:
    """Le o CSV e grava `classificacao_c1.csv` e `distribuicao_c1.csv` em `saida`."""
    df = pd.read_csv(entrada)
    saida = pathlib.Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    classificacao = classificar(df)
    dist = distribuicao(classificacao)
    classificacao.to_csv(saida / "classificacao_c1.csv", index=False)
    dist.to_csv(saida / "distribuicao_c1.csv", index=False)
    return {"classificacao": classificacao, "distribuicao": dist}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Classificacao DORA de referencia (C1)")
    ap.add_argument("--entrada", type=pathlib.Path, default=ENTRADA_PADRAO)
    ap.add_argument("--saida", type=pathlib.Path, default=SAIDA_PADRAO)
    args = ap.parse_args(argv)
    res = executar(args.entrada, args.saida)
    print(res["distribuicao"].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
