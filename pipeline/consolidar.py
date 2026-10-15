"""Consolidação do dataset final (S02-O1.3), sem chamar a API.

Lê as saídas do orquestrador (`data/metricas.csv` e `data/funil.csv`), valida a
integridade do dataset, acrescenta as colunas derivadas e regrava `data/metricas.csv`
na ordem do dicionário (`data/DICIONARIO.md`).
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import pandas as pd

from pipeline.etapa_releases import semanas_da_janela
from pipeline.orquestrador import (
    COLUNAS, COLUNAS_INTEIRAS, MIN_RELEASES, MIN_RUNS_VALIDOS, carregar_config, janela_da_config,
)

COLUNAS_TEXTO = ["repo", "language", "meses_no_teto", "dora_overall"]


# Colunas calculadas na consolidação, acrescentadas depois das colunas do orquestrador.
# PONTO DE EXTENSÃO (S02-O3.5, #36): acrescente aqui `cfr_entrega`, `rework_rate` e
# `tipo_projeto`, calcule-as em `derivar_colunas` (dados externos, como
# rotulos/consenso.csv, entram por `extras`) e documente-as em data/DICIONARIO.md
# na mesma ordem (tests/test_consolidar.py confere o dicionário).
COLUNAS_DERIVADAS = ["prop_censurados", "n_meses_no_teto"]
COLUNAS_FINAIS = COLUNAS + COLUNAS_DERIVADAS
COLUNAS_ELEGIVEIS = ["repo", "url_releases", "n_releases"]


class DatasetInvalido(ValueError):
    """O dataset não passou na validação; `problemas` lista cada falha encontrada."""

    def __init__(self, problemas: list[str]):
        super().__init__("dataset inválido:\n- " + "\n- ".join(problemas))
        self.problemas = problemas


def _estrutura(metricas: pd.DataFrame) -> list[str]:
    ausentes = [c for c in COLUNAS if c not in metricas.columns]
    if ausentes:
        return [f"colunas ausentes em metricas.csv: {', '.join(ausentes)}"]
    if list(metricas.columns[:len(COLUNAS)]) != COLUNAS:
        return ["colunas fora da ordem do orquestrador (pipeline.orquestrador.COLUNAS)"]
    return []


def _repos(metricas: pd.DataFrame) -> list[str]:
    problemas = []
    vazios = metricas["repo"].isna() | (metricas["repo"].astype(str).str.strip() == "")
    if vazios.any():
        problemas.append(f"repo vazio em {int(vazios.sum())} linha(s)")
    duplicados = sorted(metricas.loc[metricas["repo"].duplicated() & ~vazios, "repo"].unique())
    if duplicados:
        problemas.append(f"repositórios duplicados: {', '.join(duplicados)}")
    return problemas


def _repos_onde(metricas: pd.DataFrame, mascara: pd.Series) -> str:
    return ", ".join(str(r) for r in metricas.loc[mascara.fillna(False).astype(bool), "repo"])


def _inclusao(metricas: pd.DataFrame) -> list[str]:
    problemas = []
    for coluna, minimo in (("n_releases", MIN_RELEASES), ("n_runs_validos", MIN_RUNS_VALIDOS)):
        abaixo = ~(_num(metricas, coluna) >= minimo)  # vazio também não atende ao critério
        if abaixo.any():
            problemas.append(f"{coluna} vazio ou < {minimo} (critério de inclusão): "
                             f"{_repos_onde(metricas, abaixo)}")
    return problemas


NAO_NEGATIVAS = [
    "deploy_freq_week", "lead_time_a_days", "lead_time_b_days", "recovery_median_h",
    "deploy_freq_week_pre", "lead_time_b_days_pre", "deploy_freq_week_tag", "lead_time_b_days_tag",
]
NOTAS = ["score_freq", "score_lead", "score_cfr", "score_rec"]
CATEGORIAS_DORA = {"Elite", "High", "Medium", "Low"}
METRICAS_DORA = ["deploy_freq_week", "lead_time_a_days", "cfr_ci", "recovery_median_h"]
# (frequência, contagem de unidades na janela, teto de compares ou None)
UNIDADES = [
    ("deploy_freq_week", "n_releases", None),
    ("deploy_freq_week_pre", "n_releases_pre", "teto_compare_pre"),
    ("deploy_freq_week_tag", "n_tags", "teto_compare_tag"),
]
TOLERANCIA_FREQ = 1e-6


def _num(metricas: pd.DataFrame, coluna: str) -> pd.Series:
    return pd.to_numeric(metricas[coluna], errors="coerce")


def _faixas(metricas: pd.DataFrame) -> list[str]:
    """Faixas válidas; valores ausentes (métrica não calculável) não são checados."""
    problemas = []
    regras = [("cfr_ci", lambda s: (s < 0) | (s > 1), "fora de [0, 1]")]
    regras += [(c, lambda s: s < 0, "negativo") for c in NAO_NEGATIVAS]
    regras += [(c, lambda s: ~s.isin([1, 2, 3, 4]) & s.notna(), "fora de 1..4") for c in NOTAS]
    for coluna, fora, descricao in regras:
        mascara = fora(_num(metricas, coluna))
        if mascara.fillna(False).any():
            problemas.append(f"{coluna} {descricao}: {_repos_onde(metricas, mascara)}")
    acima = _num(metricas, "n_censored") > _num(metricas, "n_episodes")
    if acima.any():
        problemas.append(f"n_censored > n_episodes: {_repos_onde(metricas, acima)}")
    return problemas


def _classificacao(metricas: pd.DataFrame) -> list[str]:
    problemas = []
    categoria = metricas["dora_overall"]
    preenchida = categoria.notna() & (categoria.astype(str).str.strip() != "")
    desconhecida = preenchida & ~categoria.isin(CATEGORIAS_DORA)
    if desconhecida.any():
        problemas.append(f"dora_overall fora de {sorted(CATEGORIAS_DORA)}: {_repos_onde(metricas, desconhecida)}")
    completas = metricas[METRICAS_DORA].notna().all(axis=1)
    incoerente = preenchida != completas
    if incoerente.any():
        problemas.append("dora_overall deve ser vazio se e somente se alguma das 4 métricas for ausente: "
                         + _repos_onde(metricas, incoerente))
    return problemas


def _unidades(metricas: pd.DataFrame, semanas: float) -> list[str]:
    problemas = []
    abaixo = _num(metricas, "n_releases_pre") < _num(metricas, "n_releases")
    if abaixo.any():
        problemas.append(f"n_releases_pre < n_releases (release+pre inclui as releases): "
                         f"{_repos_onde(metricas, abaixo)}")
    for freq, contagem, teto in UNIDADES:
        esperada = _num(metricas, contagem) / semanas
        incoerente = (_num(metricas, freq) - esperada).abs() > TOLERANCIA_FREQ
        if incoerente.any():
            problemas.append(f"{freq} != {contagem} ÷ semanas da janela ({semanas:.4f}): "
                             f"{_repos_onde(metricas, incoerente)}")
        if teto is not None:
            excede = _num(metricas, teto) > _num(metricas, contagem)
            if excede.any():
                problemas.append(f"{teto} > {contagem}: {_repos_onde(metricas, excede)}")
    return problemas


def _funil(funil: pd.DataFrame, n_linhas: int) -> list[str]:
    problemas = []
    restantes = [int(r) for r in funil["restantes"]]
    descartados = [int(d) for d in funil["descartados"]]
    esperados = [0] + [a - b for a, b in zip(restantes[:-1], restantes[1:])]
    if descartados != esperados:
        problemas.append("funil: descartados != restantes da etapa anterior − restantes da etapa")
    if any(b > a for a, b in zip(restantes[:-1], restantes[1:])):
        problemas.append("funil: restantes cresce entre etapas")
    if list(funil["etapa"])[-1:] != ["amostra final"] or restantes[-1] != n_linhas:
        problemas.append(f"funil: 'amostra final' deve ser a última etapa e ter {n_linhas} repositórios "
                         f"(as linhas de metricas.csv)")
    return problemas


def validar(metricas: pd.DataFrame, funil: pd.DataFrame, semanas: float) -> list[str]:
    """Lista os problemas de integridade do dataset (vazia se ele é válido).

    `semanas` é a duração da janela em semanas (`semanas_da_janela`), usada para
    conferir as frequências.
    """
    problemas = _estrutura(metricas)
    if problemas:
        return problemas
    return (_repos(metricas) + _inclusao(metricas) + _faixas(metricas) + _classificacao(metricas)
            + _unidades(metricas, semanas) + _funil(funil, len(metricas)))


def _contar_meses(meses) -> int:
    if not isinstance(meses, str) or not meses.strip():
        return 0
    return len([m for m in meses.split(";") if m.strip()])


def derivar_colunas(metricas: pd.DataFrame, extras: dict | None = None) -> pd.DataFrame:
    """Cópia de `metricas` com as COLUNAS_DERIVADAS recalculadas, na ordem COLUNAS_FINAIS.

    Idempotente: derivadas já presentes (consolidação anterior) são descartadas e
    recalculadas. `extras` é reservado para dados externos ao CSV (ex.: o consenso
    da validação manual, S02-O3.5); a S02-O1.3 não o usa.
    """
    df = metricas[COLUNAS].copy()
    episodios = pd.to_numeric(df["n_episodes"], errors="coerce").astype("Float64")
    censurados = pd.to_numeric(df["n_censored"], errors="coerce").astype("Float64")
    df["prop_censurados"] = (censurados / episodios.where(episodios > 0)).astype(float)
    df["n_meses_no_teto"] = df["meses_no_teto"].map(_contar_meses).astype("Int64")
    return df[COLUNAS_FINAIS]


def elegiveis_sorteio(metricas: pd.DataFrame) -> pd.DataFrame:
    """Repositórios elegíveis ao sorteio da amostra-ouro (enunciado §6.1, S02-O2.2).

    Toda a amostra final é elegível (o enunciado sorteia "da amostra final" e todos
    têm ≥ 5 releases na janela, o que permite sortear 5 releases por repositório).
    A ordem alfabética (sem diferenciar maiúsculas) faz `df.sample(n=60, random_state=42)`
    sobre este arquivo independer da ordem de coleta e das colunas do dataset.
    """
    df = pd.DataFrame({
        "repo": metricas["repo"],
        "url_releases": "https://github.com/" + metricas["repo"].astype(str) + "/releases",
        "n_releases": pd.to_numeric(metricas["n_releases"]).astype("Int64"),
    })
    return df.sort_values("repo", key=lambda s: s.str.lower(), kind="stable").reset_index(drop=True)


def _ler_metricas(arquivo: pathlib.Path) -> pd.DataFrame:
    # round_trip: os decimais relidos são idênticos aos gravados (consolidação idempotente)
    return pd.read_csv(arquivo, float_precision="round_trip",
                       dtype={c: "string" for c in COLUNAS_TEXTO}).astype({c: object for c in COLUNAS_TEXTO})


def consolidar(dados: pathlib.Path, cfg: dict) -> pd.DataFrame:
    """Valida `dados/metricas.csv` + `dados/funil.csv` e grava o dataset final.

    Regrava `dados/metricas.csv` com COLUNAS_FINAIS e grava `dados/elegiveis_sorteio.csv`.
    Levanta `DatasetInvalido` (sem gravar nada) se a validação encontrar problemas.
    Não chama a API: a janela vem de `cfg` só para conferir as frequências.
    """
    dados = pathlib.Path(dados)
    metricas = _ler_metricas(dados / "metricas.csv")
    funil = pd.read_csv(dados / "funil.csv")
    problemas = validar(metricas, funil, semanas_da_janela(*janela_da_config(cfg)))
    if problemas:
        raise DatasetInvalido(problemas)

    final = derivar_colunas(metricas)
    final[COLUNAS_INTEIRAS] = final[COLUNAS_INTEIRAS].apply(pd.to_numeric).astype("Int64")
    final.to_csv(dados / "metricas.csv", index=False)
    elegiveis_sorteio(final).to_csv(dados / "elegiveis_sorteio.csv", index=False)
    return final


def main(argv: list[str] | None = None) -> int:
    """python -m pipeline.consolidar --config config.yaml [--dados data] (sem token, sem rede)."""
    parser = argparse.ArgumentParser(prog="python -m pipeline.consolidar",
                                     description="Valida e consolida o dataset final (sem chamar a API).")
    parser.add_argument("--config", default="config.yaml", help="arquivo de configuração (padrão: config.yaml)")
    parser.add_argument("--dados", default="data", help="pasta com metricas.csv e funil.csv (padrão: data)")
    args = parser.parse_args(argv)

    dados = pathlib.Path(args.dados)
    try:
        final = consolidar(dados, carregar_config(args.config))
    except FileNotFoundError as erro:
        print(f"erro: arquivo não encontrado: {erro.filename}. Rode antes `python -m pipeline`.",
              file=sys.stderr)
        return 1
    except DatasetInvalido as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 2
    print(f"{len(final)} repositórios consolidados em {dados / 'metricas.csv'}; "
          f"elegíveis ao sorteio em {dados / 'elegiveis_sorteio.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
