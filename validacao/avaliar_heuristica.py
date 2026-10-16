"""Avaliação da heurística de release corretiva contra o consenso (S02-O3.2).

Roda `metricas.corretiva.eh_corretiva` nas 300 releases da amostra-ouro e compara com a
coluna `corretiva` de `rotulos/consenso.csv`: precisão, recall e F1 da classe `sim`.
A tag anterior vem do `url_commits` das planilhas de rótulos e as mensagens de commit vêm
de `fetch_commits` (cache em disco). O consenso nunca é alterado aqui.

Uso:
  python -m validacao.avaliar_heuristica            # token em GITHUB_TOKEN; usa o cache
"""
from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys
from urllib.parse import unquote

import pandas as pd
from sklearn.metrics import precision_recall_fscore_support

from metricas.corretiva import HEURISTICA_VERSAO, eh_corretiva


def tags_do_compare(url_commits: str) -> tuple[str, str] | None:
    """(tag anterior, tag da release) a partir de .../compare/{base}...{head}; None sem compare."""
    m = re.search(r"/compare/(.+)\.\.\.(.+)$", url_commits or "")
    return (unquote(m.group(1)), unquote(m.group(2))) if m else None


def metricas(y_true: list[str], y_pred: list[str]) -> dict:
    """Precisão, recall e F1 da classe 'sim' (release corretiva)."""
    p, r, f1, _ = precision_recall_fscore_support(y_true, y_pred, pos_label="sim",
                                                  average="binary", zero_division=0)
    return {"n": len(y_true), "precisao": round(float(p), 3), "recall": round(float(r), 3),
            "f1": round(float(f1), 3)}


def avaliar(itens: pd.DataFrame, mensagens) -> pd.DataFrame:
    """Uma linha por release: consenso, predição e se o compare existia.

    `itens` tem repo, tag, url_commits e corretiva (consenso); `mensagens(repo, base, head)`
    devolve a lista de mensagens ou None (compare indisponível).
    """
    linhas = []
    for row in itens.itertuples(index=False):
        tags = tags_do_compare(row.url_commits)
        msgs = mensagens(row.repo, *tags) if tags else None
        anterior = tags[0] if tags else ""
        pred = eh_corretiva(anterior, row.tag, msgs or [])
        linhas.append({"repo": row.repo, "tag": row.tag, "consenso": row.corretiva,
                       "predicao": "sim" if pred else "nao", "com_commits": msgs is not None,
                       "versao": HEURISTICA_VERSAO})
    return pd.DataFrame(linhas)


def carregar_itens(pasta: pathlib.Path) -> pd.DataFrame:
    """Releases do consenso com o `url_commits` da planilha A (mesmos itens, mesma ordem)."""
    consenso = pd.read_csv(pasta / "consenso.csv", dtype=str).fillna("")
    planilha = pd.read_csv(pasta / "A.csv", dtype=str).fillna("")
    chave = ["nivel", "repo", "tag"]
    if not consenso[chave].equals(planilha[chave]):
        raise ValueError("consenso.csv e A.csv não têm os mesmos itens na mesma ordem")
    consenso["url_commits"] = planilha["url_commits"]
    return consenso[consenso["nivel"] == "release"].reset_index(drop=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m validacao.avaliar_heuristica",
                                     description=__doc__.splitlines()[0])
    parser.add_argument("--rotulos", default="rotulos", help="pasta com consenso.csv e A.csv")
    parser.add_argument("--cache", default="cache", help="diretório do cache (padrão: cache)")
    parser.add_argument("--saida", default="data/heuristica_avaliacao.csv")
    args = parser.parse_args(argv)

    from pipeline.cache import DiskCache
    from pipeline.http import GitHubClient
    from pipeline.releases import fetch_commits

    client = GitHubClient(os.environ.get("GITHUB_TOKEN", ""), DiskCache(pathlib.Path(args.cache)))

    def mensagens(repo, base, head):
        commits = fetch_commits(client, repo, base, head)
        return None if commits is None else [c["message"] for c in commits]

    resultado = avaliar(carregar_itens(pathlib.Path(args.rotulos)), mensagens)
    resultado.to_csv(args.saida, index=False, encoding="utf-8", lineterminator="\n")
    m = metricas(resultado["consenso"].tolist(), resultado["predicao"].tolist())
    print(f"heurística {HEURISTICA_VERSAO}: n={m['n']} precisão={m['precisao']} "
          f"recall={m['recall']} F1={m['f1']} (sem commits: {int((~resultado['com_commits']).sum())})")
    print(f"predições em {args.saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
