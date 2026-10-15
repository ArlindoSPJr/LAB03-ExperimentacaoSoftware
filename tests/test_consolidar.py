"""Consolidação do dataset (S02-O1.3): validação, colunas derivadas e elegíveis ao sorteio."""
import math
import pathlib
import re

import pandas as pd
import pytest

from pipeline.consolidar import COLUNAS_DERIVADAS, COLUNAS_FINAIS, derivar_colunas, validar
from pipeline.orquestrador import COLUNAS

DICIONARIO = pathlib.Path(__file__).resolve().parents[1] / "data" / "DICIONARIO.md"

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


@pytest.mark.parametrize("campo, valor", [
    ("cfr_ci", 1.2), ("cfr_ci", -0.1), ("lead_time_a_days", -1.0), ("lead_time_b_days", -0.5),
    ("recovery_median_h", -2.0), ("lead_time_b_days_pre", -1.0), ("lead_time_b_days_tag", -1.0),
    ("score_freq", 5), ("score_rec", 0),
])
def test_valor_fora_da_faixa_e_problema(campo, valor):
    problemas = problemas_de(dataset(linha(**{campo: valor})))
    assert any(campo in p and "octo/hello" in p for p in problemas)


def test_metricas_ausentes_nao_sao_fora_da_faixa():
    vazio = linha(lead_time_a_days=None, score_lead=None, dora_overall=None)
    assert problemas_de(dataset(vazio)) == []


def test_censurados_acima_dos_episodios_e_problema():
    problemas = problemas_de(dataset(linha(n_episodes=1, n_censored=2)))
    assert any("n_censored" in p for p in problemas)


def test_categoria_dora_desconhecida_e_problema():
    assert any("dora_overall" in p for p in problemas_de(dataset(linha(dora_overall="Top"))))


def test_dora_overall_preenchido_com_metrica_ausente_e_problema():
    problemas = problemas_de(dataset(linha(recovery_median_h=None)))
    assert any("dora_overall" in p for p in problemas)


def test_dora_overall_vazio_com_todas_as_metricas_e_problema():
    problemas = problemas_de(dataset(linha(dora_overall=None)))
    assert any("dora_overall" in p for p in problemas)


def test_release_mais_pre_abaixo_das_releases_e_problema():
    problemas = problemas_de(dataset(linha(n_releases_pre=4, deploy_freq_week_pre=4 / SEMANAS)))
    assert any("n_releases_pre" in p for p in problemas)


@pytest.mark.parametrize("teto, unidades", [("teto_compare_pre", "n_releases_pre"),
                                            ("teto_compare_tag", "n_tags")])
def test_teto_acima_das_unidades_e_problema(teto, unidades):
    campos = {"n_releases_pre": 10, "deploy_freq_week_pre": 10 / SEMANAS, unidades: 10, teto: 11}
    problemas = problemas_de(dataset(linha(**campos)))
    assert any(teto in p for p in problemas)


@pytest.mark.parametrize("freq", ["deploy_freq_week", "deploy_freq_week_pre", "deploy_freq_week_tag"])
def test_frequencia_incoerente_com_a_contagem_e_problema(freq):
    problemas = problemas_de(dataset(linha(**{freq: 99.0})))
    assert any(freq in p for p in problemas)


def test_funil_que_nao_fecha_com_a_amostra_e_problema():
    problemas = problemas_de(dataset(), funil_de(2))
    assert any("amostra final" in p for p in problemas)


def test_funil_com_descartados_errados_e_problema():
    funil = funil_de(1)
    funil.loc[2, "descartados"] = 3
    assert any("descartados" in p for p in problemas_de(dataset(), funil))


def test_funil_que_cresce_e_problema():
    funil = funil_de(1)
    funil.loc[3, "restantes"] = 20
    restantes = list(funil["restantes"])
    funil["descartados"] = [0] + [a - b for a, b in zip(restantes[:-1], restantes[1:])]
    assert any("restantes" in p for p in problemas_de(dataset(), funil))


def colunas_do_dicionario(arquivo: str) -> list[str]:
    """Colunas da tabela de `arquivo` em data/DICIONARIO.md, na ordem em que aparecem."""
    secao = DICIONARIO.read_text(encoding="utf-8").split(f"## `{arquivo}`")[1].split("\n## ")[0]
    return re.findall(r"^\| `([^`]+)` \|", secao, flags=re.MULTILINE)


def test_prop_censurados_e_a_fracao_de_episodios_censurados():
    resultado = derivar_colunas(dataset(linha(n_episodes=4, n_censored=1)))
    assert resultado.loc[0, "prop_censurados"] == pytest.approx(0.25)


def test_sem_episodios_prop_censurados_fica_vazia():
    resultado = derivar_colunas(dataset(linha(n_episodes=0, n_censored=0)))
    assert math.isnan(resultado.loc[0, "prop_censurados"])


@pytest.mark.parametrize("meses, esperado", [("2025-11;2026-01", 2), ("2026-03", 1), ("", 0), (None, 0)])
def test_n_meses_no_teto_conta_os_meses(meses, esperado):
    resultado = derivar_colunas(dataset(linha(meses_no_teto=meses)))
    assert resultado.loc[0, "n_meses_no_teto"] == esperado


def test_derivar_poe_as_colunas_na_ordem_final():
    assert list(derivar_colunas(dataset()).columns) == COLUNAS_FINAIS
    assert COLUNAS_FINAIS == COLUNAS + COLUNAS_DERIVADAS


def test_derivar_duas_vezes_e_igual_a_derivar_uma():
    uma = derivar_colunas(dataset(linha(), linha(repo="octo/world", n_episodes=0, n_censored=0)))
    pd.testing.assert_frame_equal(derivar_colunas(uma), uma)


def test_derivar_nao_altera_a_entrada():
    entrada = dataset()
    derivar_colunas(entrada)
    assert list(entrada.columns) == COLUNAS


def test_dicionario_documenta_todas_as_colunas_finais_na_ordem():
    assert colunas_do_dicionario("data/metricas.csv") == COLUNAS_FINAIS
