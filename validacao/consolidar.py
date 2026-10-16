"""Kappa de Fleiss, rótulo de consenso e decisões de reunião (S02-O2.4).

Lê `rotulos/A.csv`, `rotulos/B.csv` e `rotulos/C.csv` (gerados por
`validacao.gerar_planilhas` e preenchidos por cada avaliador) e grava:

- `rotulos/kappa.csv`: kappa de Fleiss, concordância observada e contagens por dimensão;
- `rotulos/consenso.csv`: rótulo de consenso de cada item, com a origem e os votos.

Protocolo (docs/PROTOCOLO_DESEMPATE.md): maioria simples; empates 1-1-1 são decididos
em reunião e registrados em `rotulos/decisoes_reuniao.csv`. Sem decisão, o item fica
`pendente` e o comando sai com código 2.

Uso: python -m validacao.consolidar [--rotulos rotulos]   (sem token, sem rede)
"""
from __future__ import annotations

import argparse
import pathlib
import sys
from collections import Counter

import pandas as pd

from validacao.concordancia import DIMENSOES, consenso, fleiss_kappa_dimensao

AVALIADORES = ("A", "B", "C")
CHAVE = ["nivel", "repo", "tag"]
NIVEL_DA_DIMENSAO = {"tipo_projeto": "repo", "entregas_reais": "repo", "corretiva": "release"}
COLUNAS_KAPPA = ["dimensao", "nivel", "n_itens", "kappa", "concordancia_observada", "n_unanimes",
                 "n_maioria", "n_reuniao"]
COLUNAS_CONSENSO = [*CHAVE, "url", *[c for d in DIMENSOES for c in (d, f"origem_{d}", f"votos_{d}")]]
COLUNAS_DECISOES = [*CHAVE, "dimensao", "rotulo", "justificativa"]


class RotulosInvalidos(Exception):
    """Planilhas de rótulos incompletas, desalinhadas ou com valores fora do vocabulário."""


def _ler(caminho: pathlib.Path) -> pd.DataFrame:
    return pd.read_csv(caminho, keep_default_na=False, dtype=str)


def carregar_rotulos(pasta: pathlib.Path, avaliadores=AVALIADORES) -> dict[str, pd.DataFrame]:
    """Lê e valida uma planilha por avaliador: mesmos itens, na mesma ordem, todos rotulados."""
    rotulos = {a: _ler(pasta / f"{a}.csv") for a in avaliadores}
    referencia = rotulos[avaliadores[0]][CHAVE]
    problemas = []
    for avaliador, df in rotulos.items():
        if not df[CHAVE].equals(referencia):
            problemas.append(f"{avaliador}: itens diferentes dos de {avaliadores[0]}")
            continue
        for dimensao, categorias in DIMENSOES.items():
            valores = df.loc[df["nivel"] == NIVEL_DA_DIMENSAO[dimensao], dimensao].str.strip()
            vazios = int((valores == "").sum())
            if vazios:
                problemas.append(f"{avaliador}: {vazios} {dimensao} vazio(s)")
            fora = sorted(set(valores[valores != ""]) - set(categorias))
            if fora:
                problemas.append(f"{avaliador}: {dimensao} fora do vocabulário {fora}")
    if problemas:
        raise RotulosInvalidos("; ".join(problemas))
    return rotulos


def _tabela(rotulos: dict[str, pd.DataFrame], dimensao: str) -> pd.DataFrame:
    """Uma linha por item da dimensão (índice = posição na planilha), uma coluna por avaliador."""
    referencia = next(iter(rotulos.values()))
    mascara = referencia["nivel"] == NIVEL_DA_DIMENSAO[dimensao]
    return pd.DataFrame({a: df.loc[mascara, dimensao].str.strip() for a, df in rotulos.items()})


def _concordancia_observada(tabela: pd.DataFrame) -> float:
    """P-barra de Fleiss: média, por item, da fração de pares de avaliadores que concordam."""
    n = tabela.shape[1]
    return float(tabela.apply(
        lambda item: sum(c * (c - 1) for c in Counter(item).values()) / (n * (n - 1)), axis=1).mean())


def tabela_kappa(rotulos: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Kappa de Fleiss e concordância observada de cada dimensão."""
    linhas = []
    for dimensao, categorias in DIMENSOES.items():
        tabela = _tabela(rotulos, dimensao)
        unanimes = tabela.nunique(axis=1) == 1
        reuniao = consenso(tabela, categorias)["reuniao"]
        linhas.append({
            "dimensao": dimensao, "nivel": NIVEL_DA_DIMENSAO[dimensao], "n_itens": len(tabela),
            "kappa": fleiss_kappa_dimensao(tabela, categorias),
            "concordancia_observada": _concordancia_observada(tabela),
            "n_unanimes": int(unanimes.sum()),
            "n_maioria": int((~unanimes & ~reuniao).sum()),
            "n_reuniao": int(reuniao.sum()),
        })
    return pd.DataFrame(linhas, columns=COLUNAS_KAPPA)


def montar_consenso(rotulos: dict[str, pd.DataFrame], decisoes: pd.DataFrame | None = None) -> pd.DataFrame:
    """Rótulo de consenso por item: unânime, maioria, reunião (de `decisoes`) ou pendente."""
    referencia = next(iter(rotulos.values()))
    saida = referencia[[*CHAVE, "url"]].copy()
    for dimensao, categorias in DIMENSOES.items():
        origem, votos = f"origem_{dimensao}", f"votos_{dimensao}"
        saida[[dimensao, origem, votos]] = ""
        tabela = _tabela(rotulos, dimensao)
        resultado = consenso(tabela, categorias)
        unanime = tabela.nunique(axis=1) == 1
        saida.loc[tabela.index, dimensao] = resultado["consenso"].fillna("")
        saida.loc[tabela.index, origem] = (
            unanime.map({True: "unanime", False: "maioria"}).where(~resultado["reuniao"], "pendente"))
        saida.loc[tabela.index, votos] = resultado["votos"]

    if decisoes is None:
        decisoes = pd.DataFrame(columns=COLUNAS_DECISOES)
    for _, decisao in decisoes.iterrows():
        dimensao = decisao["dimensao"]
        if dimensao not in DIMENSOES or decisao["rotulo"] not in DIMENSOES[dimensao]:
            raise RotulosInvalidos(f"decisão inválida: {dimensao}={decisao['rotulo']}")
        alvo = ((saida["nivel"] == decisao["nivel"]) & (saida["repo"] == decisao["repo"])
                & (saida["tag"] == decisao["tag"]))
        if alvo.sum() != 1 or saida.loc[alvo, f"origem_{dimensao}"].iloc[0] != "pendente":
            raise RotulosInvalidos("decisão de reunião para item sem empate 1-1-1: "
                                   f"{decisao['repo']} {decisao['tag']} {dimensao}")
        saida.loc[alvo, dimensao] = decisao["rotulo"]
        saida.loc[alvo, f"origem_{dimensao}"] = "reuniao"
    return saida[COLUNAS_CONSENSO].reset_index(drop=True)


def consolidar(pasta: pathlib.Path) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    """Grava `kappa.csv` e `consenso.csv` em `pasta`; devolve (kappa, consenso, nº de pendentes)."""
    rotulos = carregar_rotulos(pasta)
    caminho_decisoes = pasta / "decisoes_reuniao.csv"
    decisoes = _ler(caminho_decisoes) if caminho_decisoes.exists() else None
    kappa = tabela_kappa(rotulos)
    resultado = montar_consenso(rotulos, decisoes)
    pendentes = int(sum((resultado[f"origem_{d}"] == "pendente").sum() for d in DIMENSOES))
    kappa.to_csv(pasta / "kappa.csv", index=False, float_format="%.4f", lineterminator="\n")
    resultado.to_csv(pasta / "consenso.csv", index=False, encoding="utf-8", lineterminator="\n")
    return kappa, resultado, pendentes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m validacao.consolidar",
                                     description="Kappa de Fleiss e consenso da amostra-ouro.")
    parser.add_argument("--rotulos", default="rotulos", help="pasta com A.csv, B.csv e C.csv (padrão: rotulos)")
    args = parser.parse_args(argv)

    pasta = pathlib.Path(args.rotulos)
    try:
        kappa, _, pendentes = consolidar(pasta)
    except FileNotFoundError as erro:
        print(f"erro: arquivo não encontrado: {erro.filename}", file=sys.stderr)
        return 1
    except RotulosInvalidos as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 2
    print(kappa.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print(f"\nkappa em {pasta / 'kappa.csv'}; consenso em {pasta / 'consenso.csv'}")
    if pendentes:
        print(f"{pendentes} empate(s) 1-1-1 sem decisão: registre-os em {pasta / 'decisoes_reuniao.csv'} "
              "(docs/PROTOCOLO_DESEMPATE.md)", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
