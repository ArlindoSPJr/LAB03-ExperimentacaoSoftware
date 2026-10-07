"""Orquestrador do pipeline: seleção → Actions → metadados → releases → runs → critério → CSV.

Candidatos vêm da busca (já embaralhados, decisão 2 de docs/ISSUES.md) ou da lista
fixa `repos` do config. São processados em ordem até `sample_size` repositórios
válidos (≥ 5 releases e ≥ 50 runs válidos na janela). Cada descarte entra no funil.
"""
from __future__ import annotations

import logging
import pathlib
from datetime import datetime, time, timezone

import pandas as pd
import yaml

from metricas.classificacao import classificar_repositorio
from pipeline.etapa_releases import coletar_releases_e_lead_time
from pipeline.etapa_runs import coletar_runs_e_metricas
from pipeline.funil import Funnel
from pipeline.http import NotFoundError
from pipeline.metadados import collect_metadata
from pipeline.selecao import search_candidates, uses_actions

log = logging.getLogger(__name__)

MIN_RELEASES = 5
MIN_RUNS_VALIDOS = 50

COLUNAS = [
    "repo", "stars", "language", "contributors", "age_days",
    "n_releases", "n_runs_validos", "deploy_freq_week", "lead_time_a_days", "lead_time_b_days",
    "cfr_ci", "recovery_median_h", "n_episodes", "n_censored", "n_falhas_iniciais",
    "n_lead_negativos", "compare_404", "meses_no_teto",
    "score_freq", "score_lead", "score_cfr", "score_rec", "dora_overall",
]
COLUNAS_INTEIRAS = [
    "stars", "contributors", "age_days", "n_releases", "n_runs_validos", "n_episodes",
    "n_censored", "n_falhas_iniciais", "n_lead_negativos", "compare_404",
    "score_freq", "score_lead", "score_cfr", "score_rec",
]

ETAPA_PROCESSADOS = "processados"
ETAPA_ACTIONS = "com GitHub Actions"
ETAPA_METADADOS = "metadados coletados"
ETAPA_RELEASES = f">= {MIN_RELEASES} releases na janela"
ETAPA_RUNS = f">= {MIN_RUNS_VALIDOS} runs válidos na janela"
MOTIVOS = {
    ETAPA_PROCESSADOS: "não processados: amostra completa (sample_size atingido)",
    ETAPA_ACTIONS: "sem workflows do GitHub Actions",
    ETAPA_METADADOS: "repositório indisponível (404)",
    ETAPA_RELEASES: f"menos de {MIN_RELEASES} releases não-pré-release na janela",
    ETAPA_RUNS: f"menos de {MIN_RUNS_VALIDOS} runs válidos (push no default branch)",
}


def carregar_config(path) -> dict:
    with open(path, encoding="utf-8") as arquivo:
        return yaml.safe_load(arquivo)


def janela_da_config(cfg: dict) -> tuple[datetime, datetime]:
    """(start 00:00:00, end 23:59:59) em UTC a partir de `window.start` e `window.end`."""
    inicio = datetime.fromisoformat(str(cfg["window"]["start"])).date()
    fim = datetime.fromisoformat(str(cfg["window"]["end"])).date()
    return (datetime.combine(inicio, time.min, timezone.utc),
            datetime.combine(fim, time(23, 59, 59), timezone.utc))


def _processar(client, full_name: str, janela) -> tuple[dict | None, str]:
    """(linha do CSV, "") se o repositório é válido; (None, etapa em que foi descartado) senão."""
    try:
        if not uses_actions(client, full_name):
            return None, ETAPA_ACTIONS
    except NotFoundError:
        log.warning("%s: 404 ao consultar workflows", full_name)
        return None, ETAPA_ACTIONS
    try:
        meta = collect_metadata(client, full_name)
    except NotFoundError:
        log.warning("%s: 404 ao coletar metadados", full_name)
        return None, ETAPA_METADADOS

    entrega = coletar_releases_e_lead_time(client, meta, janela)
    if entrega["n_releases"] < MIN_RELEASES:
        return None, ETAPA_RELEASES
    ci = coletar_runs_e_metricas(client, meta, janela)
    if ci["n_runs_validos"] < MIN_RUNS_VALIDOS:
        return None, ETAPA_RUNS

    notas = classificar_repositorio(entrega["deploy_freq_week"], entrega["lead_time_a_days"],
                                    ci["cfr_ci"], ci["recovery_median_h"])
    linha = {
        "repo": meta["full_name"],
        "stars": meta["stars"],
        "language": meta["language"],
        "contributors": meta["contributors"],
        "age_days": (janela[1].date() - meta["created_at"].date()).days,
        **entrega,
        **ci,
        "meses_no_teto": ";".join(ci["meses_no_teto"]),
        **notas,
    }
    return linha, ""


def executar(client, cfg: dict, saida: pathlib.Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Roda o pipeline e grava `metricas.csv` e `funil.csv` em `saida`; devolve (metricas, funil)."""
    janela = janela_da_config(cfg)
    sample_size = int(cfg.get("sample_size", 100))
    if cfg.get("repos"):
        candidatos, primeira_etapa = list(cfg["repos"]), "lista fornecida"
    else:
        candidatos, primeira_etapa = search_candidates(client, cfg["star_ranges"]), "candidatos da busca"

    linhas: list[dict] = []
    descartes = {etapa: 0 for etapa in MOTIVOS if etapa != ETAPA_PROCESSADOS}
    processados = 0
    for full_name in candidatos:
        if len(linhas) >= sample_size:
            break
        processados += 1
        linha, etapa = _processar(client, full_name, janela)
        if linha is None:
            descartes[etapa] += 1
            log.info("%s: descartado em '%s'", full_name, etapa)
        else:
            linhas.append(linha)
            log.info("%s: válido (%d/%d)", full_name, len(linhas), sample_size)

    funil = Funnel()
    funil.add(primeira_etapa, len(candidatos))
    funil.add(ETAPA_PROCESSADOS, processados, MOTIVOS[ETAPA_PROCESSADOS] if processados < len(candidatos) else "")
    restantes = processados
    for etapa, n in descartes.items():
        restantes -= n
        funil.add(etapa, restantes, MOTIVOS[etapa] if n else "")
    funil.add("amostra final", restantes)

    metricas = pd.DataFrame(linhas, columns=COLUNAS)
    metricas[COLUNAS_INTEIRAS] = metricas[COLUNAS_INTEIRAS].astype("Int64")
    funil_df = funil.to_dataframe()

    saida = pathlib.Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    metricas.to_csv(saida / "metricas.csv", index=False)
    funil_df.to_csv(saida / "funil.csv", index=False)
    return metricas, funil_df
