"""Planilhas de rotulagem da amostra-ouro (S02-O2.2, enunciado seção 6).

Sorteia 60 repositórios de `data/elegiveis_sorteio.csv` com `df.sample(n=60,
random_state=42)` e, em cada um, 5 releases da janela (também com semente 42). Gera
três arquivos idênticos em branco, `rotulos/A.csv`, `rotulos/B.csv` e `rotulos/C.csv`,
um por avaliador. A planilha **não** traz nenhuma saída da heurística de release
corretiva, para que a rotulagem seja cega.

Formato: uma linha `nivel=repo` por repositório (preencher `tipo_projeto` e
`entregas_reais`) seguida de 5 linhas `nivel=release` (preencher `corretiva`).
Vocabulário de cada coluna: `validacao.concordancia.DIMENSOES`.

Uso: python -m validacao.gerar_planilhas --config config.yaml   (token em GITHUB_TOKEN)
"""
from __future__ import annotations

import argparse
import logging
import os
import pathlib
import sys
from datetime import datetime
from urllib.parse import quote

import pandas as pd

from pipeline.cache import DiskCache
from pipeline.http import GitHubClient
from pipeline.orquestrador import carregar_config, janela_da_config
from pipeline.releases import fetch_releases

SEMENTE = 42  # semente fixa do sorteio dos repositórios e das releases de cada repositório
N_REPOS = 60
N_RELEASES = 5
AVALIADORES = ("A", "B", "C")
COLUNAS_ROTULO = ["tipo_projeto", "entregas_reais", "corretiva", "observacao"]
COLUNAS_PLANILHA = ["nivel", "repo", "tag", "published_at", "url", "url_commits", *COLUNAS_ROTULO]


def sortear_repos(elegiveis: pd.DataFrame, n: int = N_REPOS) -> pd.DataFrame:
    """`elegiveis.sample(n=n, random_state=42)`, ordenado por `repo` para facilitar a leitura."""
    if len(elegiveis) < n:
        raise ValueError(f"só {len(elegiveis)} repositórios elegíveis; o sorteio precisa de {n}")
    return elegiveis.sample(n=n, random_state=SEMENTE).sort_values("repo").reset_index(drop=True)


def sortear_releases(releases: list[dict], start: datetime, end: datetime,
                     n: int = N_RELEASES) -> list[tuple[str | None, dict]]:
    """Sorteia `n` releases não-pré-release da janela; devolve `(tag_base, release)` por data.

    `tag_base` é a release não-pré-release imediatamente anterior (pode ser a anterior
    à janela), usada no link dos commits. O sorteio é feito sobre as posições em ordem
    cronológica, então não depende da ordem de entrada. Com menos de `n`, usa todas.
    """
    ordenadas = sorted((r for r in releases if not r["prerelease"]), key=lambda r: r["published_at"])
    posicoes = [i for i, r in enumerate(ordenadas) if start <= r["published_at"] <= end]
    if len(posicoes) > n:
        posicoes = sorted(pd.Series(posicoes).sample(n=n, random_state=SEMENTE))
    return [(ordenadas[i - 1]["tag_name"] if i > 0 else None, ordenadas[i]) for i in posicoes]


def _linhas_do_repo(repo: str, pares: list[tuple[str | None, dict]]) -> list[dict]:
    vazio = dict.fromkeys(COLUNAS_ROTULO, "")
    linhas = [{"nivel": "repo", "repo": repo, "tag": "", "published_at": "",
               "url": f"https://github.com/{repo}", "url_commits": "", **vazio}]
    for base, release in pares:
        tag = quote(release["tag_name"], safe="")
        commits = (f"https://github.com/{repo}/compare/{quote(base, safe='')}...{tag}" if base
                   else f"https://github.com/{repo}/commits/{tag}")
        linhas.append({
            "nivel": "release", "repo": repo, "tag": release["tag_name"],
            "published_at": release["published_at"].strftime("%Y-%m-%dT%H:%M:%SZ"),
            "url": f"https://github.com/{repo}/releases/tag/{tag}", "url_commits": commits, **vazio,
        })
    return linhas


def montar_planilha(client, elegiveis: pd.DataFrame, janela: tuple[datetime, datetime],
                    n_repos: int = N_REPOS) -> pd.DataFrame:
    """Planilha em branco: sorteio dos repositórios, releases via API (com cache) e links."""
    start, end = janela
    linhas = []
    for repo in sortear_repos(elegiveis, n_repos)["repo"]:
        releases = fetch_releases(client, repo, start, end)
        linhas.extend(_linhas_do_repo(repo, sortear_releases(releases, start, end)))
    return pd.DataFrame(linhas, columns=COLUNAS_PLANILHA)


def gravar_planilhas(planilha: pd.DataFrame, pasta: pathlib.Path,
                     avaliadores=AVALIADORES) -> list[pathlib.Path]:
    """Grava uma cópia por avaliador. Nunca sobrescreve: se algum arquivo existe, não grava nenhum."""
    caminhos = [pasta / f"{a}.csv" for a in avaliadores]
    existentes = [c.name for c in caminhos if c.exists()]
    if existentes:
        raise FileExistsError(f"planilhas já existem em {pasta}: {', '.join(existentes)} "
                              "(apague-as só se ainda estiverem em branco)")
    pasta.mkdir(parents=True, exist_ok=True)
    for caminho in caminhos:
        planilha.to_csv(caminho, index=False, encoding="utf-8", lineterminator="\n")
    return caminhos


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m validacao.gerar_planilhas",
                                     description="Gera as planilhas de rotulagem da amostra-ouro.")
    parser.add_argument("--config", default="config.yaml", help="arquivo de configuração (padrão: config.yaml)")
    parser.add_argument("--elegiveis", default="data/elegiveis_sorteio.csv", help="repositórios elegíveis")
    parser.add_argument("--saida", default="rotulos", help="pasta das planilhas (padrão: rotulos)")
    args = parser.parse_args(argv)

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("erro: defina a variável de ambiente GITHUB_TOKEN com um token do GitHub.", file=sys.stderr)
        return 1

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = carregar_config(args.config)
    client = GitHubClient(token, DiskCache(pathlib.Path(cfg.get("cache_dir", "cache"))))
    planilha = montar_planilha(client, pd.read_csv(args.elegiveis), janela_da_config(cfg))
    try:
        caminhos = gravar_planilhas(planilha, pathlib.Path(args.saida))
    except FileExistsError as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 2
    n_releases = int((planilha["nivel"] == "release").sum())
    print(f"{planilha['repo'].nunique()} repositórios e {n_releases} releases em "
          + ", ".join(str(c) for c in caminhos))
    return 0


if __name__ == "__main__":
    sys.exit(main())
