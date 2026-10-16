"""Gerador das planilhas de rotulagem da amostra-ouro (S02-O2.2). Nunca acessa a rede."""
from datetime import datetime, timezone

import pandas as pd
import pytest

import validacao.gerar_planilhas as gp
from validacao.gerar_planilhas import (
    COLUNAS_PLANILHA, SEMENTE, gravar_planilhas, montar_planilha, sortear_releases, sortear_repos,
)

START = datetime(2025, 10, 1, tzinfo=timezone.utc)
END = datetime(2026, 9, 30, 23, 59, 59, tzinfo=timezone.utc)


class FakeClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def paginate(self, path, params=None, item_key=None):
        self.calls.append(path)
        return self.responses[path]


def rel(tag, published_at, prerelease=False, draft=False):
    return {"tag_name": tag, "published_at": published_at, "prerelease": prerelease,
            "draft": draft, "body": "notas"}


def releases_api(n=7, prefixo="v1."):
    """Uma release antes da janela (base) + `n` na janela, uma por mês."""
    itens = [rel("v0.9", "2025-09-15T00:00:00Z")]
    itens += [rel(f"{prefixo}{i}", f"2025-{10 + i:02d}-05T12:00:00Z" if i < 3 else f"2026-{i - 2:02d}-05T12:00:00Z")
              for i in range(n)]
    return itens


def elegiveis(n):
    repos = [f"org/r{i:03d}" for i in range(n)]
    return pd.DataFrame({"repo": repos, "url_releases": [f"https://github.com/{r}/releases" for r in repos],
                         "n_releases": 7})


def test_semente_documentada():
    assert SEMENTE == 42


def test_sorteio_de_60_repos_reproduz_df_sample():
    df = elegiveis(300)
    esperado = set(df.sample(n=60, random_state=42)["repo"])
    sorteados = sortear_repos(df)
    assert len(sorteados) == 60
    assert set(sorteados["repo"]) == esperado
    assert sorteados["repo"].is_monotonic_increasing


def test_sorteio_com_menos_de_60_elegiveis_levanta_erro():
    with pytest.raises(ValueError, match="60"):
        sortear_repos(elegiveis(59))


def test_sorteia_5_releases_da_janela_sem_pre_release_com_base_anterior():
    from pipeline.releases import fetch_releases
    api = releases_api(7) + [rel("v2.0-rc1", "2026-02-01T00:00:00Z", prerelease=True)]
    releases = fetch_releases(FakeClient({"/repos/o/r/releases": api}), "o/r", START, END)
    pares = sortear_releases(releases, START, END)
    assert len(pares) == 5
    tags = [r["tag_name"] for _, r in pares]
    assert "v2.0-rc1" not in tags and "v0.9" not in tags
    datas = [r["published_at"] for _, r in pares]
    assert datas == sorted(datas)
    # base = release não-pré-release imediatamente anterior (para o link dos commits)
    ordem = ["v0.9"] + [f"v1.{i}" for i in range(7)]
    for base, r in pares:
        assert base == ordem[ordem.index(r["tag_name"]) - 1]


def test_sorteio_de_releases_e_reprodutivel():
    from pipeline.releases import fetch_releases
    releases = fetch_releases(FakeClient({"/repos/o/r/releases": releases_api(12)}), "o/r", START, END)
    primeiro = [r["tag_name"] for _, r in sortear_releases(releases, START, END)]
    segundo = [r["tag_name"] for _, r in sortear_releases(list(reversed(releases)), START, END)]
    assert primeiro == segundo


def test_repo_com_menos_de_5_releases_usa_todas():
    from pipeline.releases import fetch_releases
    releases = fetch_releases(FakeClient({"/repos/o/r/releases": releases_api(3)}), "o/r", START, END)
    pares = sortear_releases(releases, START, END)
    assert [r["tag_name"] for _, r in pares] == ["v1.0", "v1.1", "v1.2"]


def planilha_de_um_repo(api):
    client = FakeClient({"/repos/o/r/releases": api})
    df = pd.DataFrame({"repo": ["o/r"], "url_releases": ["https://github.com/o/r/releases"], "n_releases": [7]})
    return montar_planilha(client, df, (START, END), n_repos=1)


def test_planilha_tem_linha_do_repo_e_das_releases_com_links():
    planilha = planilha_de_um_repo(releases_api(7))
    assert list(planilha.columns) == COLUNAS_PLANILHA
    assert planilha["nivel"].tolist() == ["repo"] + ["release"] * 5
    linha_repo = planilha.iloc[0]
    assert linha_repo["url"] == "https://github.com/o/r"
    assert linha_repo["tag"] == ""
    release = planilha.iloc[1]
    assert release["url"] == f"https://github.com/o/r/releases/tag/{release['tag']}"
    assert release["url_commits"].startswith("https://github.com/o/r/compare/")
    assert release["url_commits"].endswith(f"...{release['tag']}")
    assert release["published_at"].endswith("Z")


def test_tags_com_caracteres_especiais_sao_codificadas_no_link():
    api = [rel("pkg@0.9", "2025-09-15T00:00:00Z")] + [
        rel(f"pkg@1.{i}", f"2026-0{i + 1}-05T00:00:00Z") for i in range(5)]
    planilha = planilha_de_um_repo(api)
    urls = planilha.loc[planilha["nivel"] == "release", "url"].tolist()
    assert "https://github.com/o/r/releases/tag/pkg%401.0" in urls


def test_colunas_de_rotulo_em_branco_e_sem_heuristica():
    planilha = planilha_de_um_repo(releases_api(7))
    for coluna in ["tipo_projeto", "entregas_reais", "corretiva", "observacao"]:
        assert (planilha[coluna] == "").all()
    assert not any("heur" in c or "patch" in c or "cfr" in c for c in planilha.columns)


def test_gravar_gera_tres_arquivos_identicos(tmp_path):
    planilha = planilha_de_um_repo(releases_api(7))
    caminhos = gravar_planilhas(planilha, tmp_path / "rotulos")
    assert [c.name for c in caminhos] == ["A.csv", "B.csv", "C.csv"]
    conteudos = {c.read_text(encoding="utf-8") for c in caminhos}
    assert len(conteudos) == 1
    lido = pd.read_csv(caminhos[0], keep_default_na=False)
    assert list(lido.columns) == COLUNAS_PLANILHA and len(lido) == 6


def test_gravar_nunca_sobrescreve_rotulos_existentes(tmp_path):
    pasta = tmp_path / "rotulos"
    pasta.mkdir()
    (pasta / "B.csv").write_text("já rotulado", encoding="utf-8")
    with pytest.raises(FileExistsError, match="B.csv"):
        gravar_planilhas(planilha_de_um_repo(releases_api(7)), pasta)
    assert (pasta / "B.csv").read_text(encoding="utf-8") == "já rotulado"
    assert not (pasta / "A.csv").exists()


def test_main_sem_token_falha(monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    assert gp.main(["--config", "config.yaml"]) == 1
    assert "GITHUB_TOKEN" in capsys.readouterr().err
