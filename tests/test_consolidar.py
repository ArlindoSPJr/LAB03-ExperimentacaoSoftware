"""Consolidação do dataset (S02-O1.3): validação, colunas derivadas e elegíveis ao sorteio."""
import math
import pathlib
import re

import pandas as pd
import pytest

import pipeline.__main__ as pipeline_main
from pipeline.consolidar import (
    COLUNAS_DERIVADAS, COLUNAS_ELEGIVEIS, COLUNAS_FINAIS, DatasetInvalido, consolidar, derivar_colunas,
    elegiveis_sorteio, validar,
)
from pipeline.consolidar import main as consolidar_main
from pipeline.etapa_variantes import COLUNAS_TAG
from pipeline.orquestrador import COLUNAS, COLUNAS_INTEIRAS, executar

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
        "commits_omitidos_tag": 0, "erro_tags": 0,
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


@pytest.mark.parametrize("campo", ["n_releases", "n_runs_validos"])
def test_contagem_do_criterio_vazia_e_problema(campo):
    problemas = problemas_de(dataset(linha(**{campo: None})))
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


def sem_tags(**kw) -> dict:
    """Repositório com a variante tag ausente (5xx/rede persistente, #81)."""
    return linha(**{**dict.fromkeys(COLUNAS_TAG), "erro_tags": 1, **kw})


def test_variante_tag_ausente_por_erro_e_valida():
    assert problemas_de(dataset(sem_tags())) == []


@pytest.mark.parametrize("valor", [2, -1])
def test_erro_tags_fora_de_zero_ou_um_e_problema(valor):
    assert any("erro_tags" in p for p in problemas_de(dataset(linha(erro_tags=valor))))


def test_erro_tags_vazio_e_problema():
    assert any("erro_tags" in p for p in problemas_de(dataset(linha(erro_tags=None))))


def test_commits_omitidos_vazio_sem_erro_de_tags_e_problema():
    problemas = problemas_de(dataset(linha(commits_omitidos_tag=None)))
    assert any("commits_omitidos_tag" in p and "octo/hello" in p for p in problemas)


@pytest.mark.parametrize("coluna", [c for c in COLUNAS_TAG])
def test_erro_de_tags_com_coluna_da_variante_preenchida_e_problema(coluna):
    problemas = problemas_de(dataset(sem_tags(**{coluna: 0})))
    assert any(coluna in p and "erro_tags" in p for p in problemas)


@pytest.mark.parametrize("coluna", [c for c in COLUNAS_TAG if c != "lead_time_b_days_tag"])
def test_contagem_da_variante_tag_vazia_sem_erro_e_problema(coluna):
    problemas = problemas_de(dataset(linha(**{coluna: None})))
    assert any(coluna in p for p in problemas)


def test_lead_time_de_tag_vazio_sem_erro_e_valido():
    # sem compare utilizável o lead time é ausente, mas a variante foi coletada
    assert problemas_de(dataset(linha(lead_time_b_days_tag=None))) == []


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


def amostra(*repos: str) -> pd.DataFrame:
    return derivar_colunas(dataset(*[linha(repo=r, n_releases=5 + i, deploy_freq_week=(5 + i) / SEMANAS,
                                           n_releases_pre=6 + i, deploy_freq_week_pre=(6 + i) / SEMANAS)
                                     for i, r in enumerate(repos)]))


def test_elegiveis_sao_toda_a_amostra_final_ordenada_por_repo():
    elegiveis = elegiveis_sorteio(amostra("zeta/z", "alpha/a", "Mid/m"))
    assert list(elegiveis["repo"]) == ["alpha/a", "Mid/m", "zeta/z"]
    assert list(elegiveis.columns) == COLUNAS_ELEGIVEIS


def test_elegiveis_tem_link_das_releases_e_contagem():
    elegiveis = elegiveis_sorteio(amostra("octo/hello", "octo/world")).set_index("repo")
    assert elegiveis.loc["octo/world", "url_releases"] == "https://github.com/octo/world/releases"
    assert elegiveis.loc["octo/world", "n_releases"] == 6


def test_sorteio_sobre_os_elegiveis_nao_depende_da_ordem_de_coleta():
    repos = [f"org/repo{i:03d}" for i in range(80)]
    direto = elegiveis_sorteio(amostra(*repos))
    invertido = elegiveis_sorteio(amostra(*reversed(repos)))
    sorteio = direto.sample(n=60, random_state=42)["repo"].tolist()
    assert invertido.sample(n=60, random_state=42)["repo"].tolist() == sorteio


def test_dicionario_documenta_as_colunas_dos_elegiveis():
    assert colunas_do_dicionario("data/elegiveis_sorteio.csv") == COLUNAS_ELEGIVEIS


# --- consolidar (E/S), comando e integração com `python -m pipeline` ---

CFG = {"window": {"start": "2025-10-01", "end": "2026-09-30"}}


def gravar_saidas(pasta: pathlib.Path, metricas: pd.DataFrame, funil: pd.DataFrame | None = None) -> None:
    """Simula as saídas do orquestrador em `pasta`."""
    metricas.to_csv(pasta / "metricas.csv", index=False)
    (funil_de(len(metricas)) if funil is None else funil).to_csv(pasta / "funil.csv", index=False)


def test_consolidar_grava_dataset_final_e_elegiveis(tmp_path):
    gravar_saidas(tmp_path, dataset(linha(repo="b/b"), linha(repo="a/a", meses_no_teto="2026-01")))
    final = consolidar(tmp_path, CFG)

    salvo = pd.read_csv(tmp_path / "metricas.csv")
    assert list(salvo.columns) == COLUNAS_FINAIS
    assert list(salvo["repo"]) == ["b/b", "a/a"]  # mantém a ordem de coleta
    assert salvo.loc[1, "n_meses_no_teto"] == 1
    assert salvo.loc[0, "prop_censurados"] == pytest.approx(0.25)
    assert list(final.columns) == COLUNAS_FINAIS
    elegiveis = pd.read_csv(tmp_path / "elegiveis_sorteio.csv")
    assert list(elegiveis["repo"]) == ["a/a", "b/b"]


def test_consolidar_duas_vezes_gera_arquivos_identicos(tmp_path):
    gravar_saidas(tmp_path, dataset(linha(), linha(repo="o/x", recovery_median_h=None, score_rec=None,
                                                    dora_overall=None, n_episodes=0, n_censored=0,
                                                    meses_no_teto="2025-12;2026-02", cfr_ci=1 / 3)))
    consolidar(tmp_path, CFG)
    primeira = (tmp_path / "metricas.csv").read_bytes(), (tmp_path / "elegiveis_sorteio.csv").read_bytes()
    consolidar(tmp_path, CFG)
    assert ((tmp_path / "metricas.csv").read_bytes(), (tmp_path / "elegiveis_sorteio.csv").read_bytes()) == primeira


def test_consolidar_mantem_inteiros_sem_casas_decimais(tmp_path):
    gravar_saidas(tmp_path, dataset(linha(), linha(repo="o/x", contributors=None, score_lead=None,
                                                    lead_time_a_days=None, dora_overall=None)))
    consolidar(tmp_path, CFG)
    cabecalho, *linhas = (tmp_path / "metricas.csv").read_text(encoding="utf-8").splitlines()
    for texto in linhas:
        valores = dict(zip(cabecalho.split(","), texto.split(",")))
        for coluna in COLUNAS_INTEIRAS + ["n_meses_no_teto"]:
            assert "." not in valores[coluna], (coluna, valores[coluna])
    assert dict(zip(cabecalho.split(","), linhas[1].split(",")))["contributors"] == ""


def test_consolidar_dataset_invalido_levanta_e_nao_grava(tmp_path):
    gravar_saidas(tmp_path, dataset(linha(), linha()))
    antes = (tmp_path / "metricas.csv").read_bytes()
    with pytest.raises(DatasetInvalido) as erro:
        consolidar(tmp_path, CFG)
    assert any("duplicad" in p for p in erro.value.problemas)
    assert (tmp_path / "metricas.csv").read_bytes() == antes
    assert not (tmp_path / "elegiveis_sorteio.csv").exists()


def test_consolidar_csv_sem_as_variantes_aponta_as_colunas_ausentes(tmp_path):
    gravar_saidas(tmp_path, dataset().drop(columns=["n_tags", "teto_compare_tag"]))
    with pytest.raises(DatasetInvalido, match="n_tags"):
        consolidar(tmp_path, CFG)


def test_consolidar_saida_real_do_orquestrador(tmp_path):
    from tests.test_orquestrador import FakeClient, config, repo
    executar(FakeClient({"o/sem-actions": repo(actions=False), "o/valido": repo()}), config(), tmp_path)
    final = consolidar(tmp_path, config())
    assert list(final["repo"]) == ["o/valido"]
    assert list(pd.read_csv(tmp_path / "elegiveis_sorteio.csv")["repo"]) == ["o/valido"]


def escrever_config(pasta: pathlib.Path) -> pathlib.Path:
    arquivo = pasta / "config.yaml"
    arquivo.write_text('window:\n  start: "2025-10-01"\n  end: "2026-09-30"\n', encoding="utf-8")
    return arquivo


def test_comando_consolidar_devolve_zero_e_resume(tmp_path, capsys):
    gravar_saidas(tmp_path, dataset())
    assert consolidar_main(["--config", str(escrever_config(tmp_path)), "--dados", str(tmp_path)]) == 0
    saida = capsys.readouterr().out
    assert "1 repositórios" in saida and "elegiveis_sorteio.csv" in saida


def test_comando_consolidar_invalido_devolve_dois_e_lista_problemas(tmp_path, capsys):
    gravar_saidas(tmp_path, dataset(linha(cfr_ci=2.0)))
    assert consolidar_main(["--config", str(escrever_config(tmp_path)), "--dados", str(tmp_path)]) == 2
    assert "cfr_ci" in capsys.readouterr().err


def test_comando_consolidar_sem_csv_devolve_um(tmp_path, capsys):
    assert consolidar_main(["--config", str(escrever_config(tmp_path)), "--dados", str(tmp_path)]) == 1
    assert "metricas.csv" in capsys.readouterr().err


def executar_falso(metricas: pd.DataFrame):
    def executar(client, cfg, saida):
        gravar_saidas(pathlib.Path(saida), metricas)
        return metricas, funil_de(len(metricas))
    return executar


def test_pipeline_consolida_ao_final(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "token-falso")
    monkeypatch.setattr(pipeline_main, "SAIDA", tmp_path)
    monkeypatch.setattr(pipeline_main, "executar", executar_falso(dataset()))
    assert pipeline_main.main(["--config", str(escrever_config(tmp_path))]) == 0
    assert list(pd.read_csv(tmp_path / "metricas.csv").columns) == COLUNAS_FINAIS
    assert (tmp_path / "elegiveis_sorteio.csv").exists()


def test_pipeline_com_dataset_invalido_devolve_dois(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_TOKEN", "token-falso")
    monkeypatch.setattr(pipeline_main, "SAIDA", tmp_path)
    monkeypatch.setattr(pipeline_main, "executar", executar_falso(dataset(linha(n_runs_validos=10))))
    assert pipeline_main.main(["--config", str(escrever_config(tmp_path))]) == 2
    assert "n_runs_validos" in capsys.readouterr().err
