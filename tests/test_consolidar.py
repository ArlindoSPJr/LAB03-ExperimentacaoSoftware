"""Consolidação do dataset (S02-O1.3): validação, colunas derivadas e elegíveis ao sorteio."""
import pandas as pd
import pytest

from pipeline.consolidar import validar
from pipeline.orquestrador import COLUNAS

SEMANAS = 365 / 7  # janela 2025-10-01..2026-09-30


def linha(**kw) -> dict:
    """Um repositório válido, coerente em todas as checagens; `kw` sobrescreve campos."""
    base = {
        "repo": "octo/hello", "stars": 1500, "language": "Python", "contributors": 30,
        "age_days": 1000, "n_releases": 5, "n_runs_validos": 60,
        "deploy_freq_week": 5 / SEMANAS, "lead_time_a_days": 13.0, "lead_time_b_days": 6.5,
        "cfr_ci": 0.1, "recovery_median_h": 1 + 20 / 60, "n_episodes": 4, "n_censored": 1,
        "n_falhas_iniciais": 0, "n_lead_negativos": 0, "compare_404": 0, "meses_no_teto": "",
        "n_releases_pre": 6, "deploy_freq_week_pre": 6 / SEMANAS, "lead_time_b_days_pre": 5.0,
        "compare_404_pre": 0, "n_lead_negativos_pre": 0, "teto_compare_pre": 0,
        "n_tags": 10, "deploy_freq_week_tag": 10 / SEMANAS, "lead_time_b_days_tag": 3.0,
        "compare_404_tag": 0, "n_lead_negativos_tag": 0, "teto_compare_tag": 0,
        "score_freq": 1, "score_lead": 2, "score_cfr": 4, "score_rec": 3, "dora_overall": "Medium",
    }
    base.update(kw)
    return base


def dataset(*linhas: dict) -> pd.DataFrame:
    return pd.DataFrame(list(linhas) or [linha()], columns=COLUNAS)


def funil_de(n: int, candidatos: int = 10) -> pd.DataFrame:
    """Funil coerente com `n` repositórios na amostra final."""
    linhas = [("candidatos da busca", candidatos), ("processados", candidatos),
              ("com GitHub Actions", candidatos), ("metadados coletados", candidatos),
              (">= 5 releases na janela", n + 1), (">= 50 runs válidos na janela", n),
              ("amostra final", n)]
    anteriores = [linhas[0][1]] + [r for _, r in linhas[:-1]]
    return pd.DataFrame({
        "etapa": [e for e, _ in linhas],
        "restantes": [r for _, r in linhas],
        "descartados": [a - r for a, (_, r) in zip(anteriores, linhas)],
        "motivo": [""] * len(linhas),
    })


def problemas_de(metricas: pd.DataFrame, funil: pd.DataFrame | None = None) -> list[str]:
    return validar(metricas, funil_de(len(metricas)) if funil is None else funil, SEMANAS)


def test_dataset_valido_nao_tem_problemas():
    assert problemas_de(dataset(linha(), linha(repo="octo/world"))) == []


def test_coluna_ausente_e_problema():
    metricas = dataset().drop(columns=["n_tags"])
    problemas = problemas_de(metricas)
    assert any("n_tags" in p for p in problemas)


def test_colunas_fora_de_ordem_e_problema():
    metricas = dataset()
    metricas = metricas[["stars", "repo"] + COLUNAS[2:]]
    assert any("ordem" in p for p in problemas_de(metricas))


def test_repositorio_duplicado_e_problema():
    problemas = problemas_de(dataset(linha(), linha()))
    assert any("duplicad" in p and "octo/hello" in p for p in problemas)


def test_repo_vazio_e_problema():
    assert any("repo" in p for p in problemas_de(dataset(linha(repo=None))))


@pytest.mark.parametrize("campo, valor", [("n_releases", 4), ("n_runs_validos", 49)])
def test_abaixo_do_criterio_de_inclusao_e_problema(campo, valor):
    extra = {"deploy_freq_week": 4 / SEMANAS} if campo == "n_releases" else {}
    problemas = problemas_de(dataset(linha(**{campo: valor}, **extra)))
    assert any(campo in p and "octo/hello" in p for p in problemas)
