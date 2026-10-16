"""Kappa de Fleiss por dimensão, consenso e decisões de reunião (S02-O2.4)."""
import pandas as pd
import pytest

from validacao.consolidar import (
    COLUNAS_CONSENSO, COLUNAS_KAPPA, RotulosInvalidos, carregar_rotulos, consolidar, montar_consenso,
    tabela_kappa,
)
from validacao.consolidar import main as consolidar_main
from validacao.gerar_planilhas import COLUNAS_PLANILHA


def planilha(tipos, entregas, corretivas):
    """Dois repos (r1 com 2 releases, r2 com 1 release) já rotulados."""
    linhas = [
        ("repo", "o/r1", "", tipos[0], entregas[0], ""),
        ("release", "o/r1", "v1.0.1", "", "", corretivas[0]),
        ("release", "o/r1", "v1.1.0", "", "", corretivas[1]),
        ("repo", "o/r2", "", tipos[1], entregas[1], ""),
        ("release", "o/r2", "v2.0.1", "", "", corretivas[2]),
    ]
    df = pd.DataFrame([dict.fromkeys(COLUNAS_PLANILHA, "") | {
        "nivel": n, "repo": r, "tag": t, "tipo_projeto": tp, "entregas_reais": e, "corretiva": c,
        "url": f"https://github.com/{r}" + (f"/releases/tag/{t}" if t else "")}
        for n, r, t, tp, e, c in linhas])
    return df[COLUNAS_PLANILHA]


def gravar(pasta, **planilhas):
    pasta.mkdir(exist_ok=True)
    for avaliador, df in planilhas.items():
        df.to_csv(pasta / f"{avaliador}.csv", index=False)
    return pasta


A = planilha(["biblioteca/framework", "outro"], ["sim", "sim"], ["sim", "nao", "sim"])
B = planilha(["biblioteca/framework", "aplicacao/servico"], ["sim", "nao"], ["sim", "nao", "nao"])
C = planilha(["biblioteca/framework", "ferramenta CLI"], ["sim", "nao"], ["sim", "sim", "sim"])


def test_carrega_as_tres_planilhas(tmp_path):
    rotulos = carregar_rotulos(gravar(tmp_path / "rotulos", A=A, B=B, C=C))
    assert list(rotulos) == ["A", "B", "C"]


def test_planilha_faltando_levanta_erro(tmp_path):
    with pytest.raises(FileNotFoundError):
        carregar_rotulos(gravar(tmp_path / "rotulos", A=A, B=B))


def test_itens_diferentes_entre_avaliadores_levanta_erro(tmp_path):
    outra = B.copy()
    outra.loc[1, "tag"] = "v9.9.9"
    with pytest.raises(RotulosInvalidos, match="B"):
        carregar_rotulos(gravar(tmp_path / "rotulos", A=A, B=outra, C=C))


def test_rotulo_vazio_ou_fora_do_vocabulario_levanta_erro(tmp_path):
    vazio = C.copy()
    vazio.loc[0, "tipo_projeto"] = ""
    with pytest.raises(RotulosInvalidos, match="C.*tipo_projeto"):
        carregar_rotulos(gravar(tmp_path / "rotulos", A=A, B=B, C=vazio))
    errado = C.copy()
    errado.loc[1, "corretiva"] = "talvez"
    with pytest.raises(RotulosInvalidos, match="talvez"):
        carregar_rotulos(gravar(tmp_path / "rotulos", A=A, B=B, C=errado))


def test_tabela_kappa_tem_as_tres_dimensoes(tmp_path):
    kappa = tabela_kappa(carregar_rotulos(gravar(tmp_path / "rotulos", A=A, B=B, C=C)))
    assert list(kappa.columns) == COLUNAS_KAPPA
    assert kappa["dimensao"].tolist() == ["tipo_projeto", "entregas_reais", "corretiva"]
    assert kappa["n_itens"].tolist() == [2, 2, 3]
    assert kappa["n_unanimes"].tolist() == [1, 1, 1]
    assert kappa["n_reuniao"].tolist() == [1, 0, 0]


def test_concordancia_perfeita_da_kappa_1_e_observada_1(tmp_path):
    kappa = tabela_kappa(carregar_rotulos(gravar(tmp_path / "rotulos", A=A, B=A, C=A)))
    corretiva = kappa.set_index("dimensao").loc["corretiva"]
    assert corretiva["kappa"] == pytest.approx(1.0)
    assert corretiva["concordancia_observada"] == pytest.approx(1.0)


def test_concordancia_observada_media_dos_pares(tmp_path):
    # corretiva: 3-0 -> 1; 2-1 -> 1/3; 2-1 -> 1/3  => média 5/9
    kappa = tabela_kappa(carregar_rotulos(gravar(tmp_path / "rotulos", A=A, B=B, C=C)))
    assert kappa.set_index("dimensao").loc["corretiva", "concordancia_observada"] == pytest.approx(5 / 9)


def test_consenso_por_maioria_e_empate_pendente(tmp_path):
    consenso = montar_consenso(carregar_rotulos(gravar(tmp_path / "rotulos", A=A, B=B, C=C)))
    assert list(consenso.columns) == COLUNAS_CONSENSO
    repo2 = consenso[(consenso["nivel"] == "repo") & (consenso["repo"] == "o/r2")].iloc[0]
    assert repo2["entregas_reais"] == "nao"
    assert repo2["tipo_projeto"] == ""
    assert repo2["origem_tipo_projeto"] == "pendente"
    assert repo2["votos_tipo_projeto"] == "A=outro; B=aplicacao/servico; C=ferramenta CLI"
    releases = consenso[consenso["nivel"] == "release"]
    assert releases["corretiva"].tolist() == ["sim", "nao", "sim"]
    assert set(releases["origem_corretiva"]) == {"unanime", "maioria"}


def test_decisao_de_reuniao_resolve_o_empate(tmp_path):
    rotulos = carregar_rotulos(gravar(tmp_path / "rotulos", A=A, B=B, C=C))
    decisoes = pd.DataFrame([{"nivel": "repo", "repo": "o/r2", "tag": "", "dimensao": "tipo_projeto",
                              "rotulo": "ferramenta CLI", "justificativa": "binário de linha de comando"}])
    consenso = montar_consenso(rotulos, decisoes)
    repo2 = consenso[(consenso["nivel"] == "repo") & (consenso["repo"] == "o/r2")].iloc[0]
    assert repo2["tipo_projeto"] == "ferramenta CLI"
    assert repo2["origem_tipo_projeto"] == "reuniao"


def test_decisao_so_vale_para_empate(tmp_path):
    rotulos = carregar_rotulos(gravar(tmp_path / "rotulos", A=A, B=B, C=C))
    decisoes = pd.DataFrame([{"nivel": "repo", "repo": "o/r1", "tag": "", "dimensao": "tipo_projeto",
                              "rotulo": "outro", "justificativa": "x"}])
    with pytest.raises(RotulosInvalidos, match="o/r1"):
        montar_consenso(rotulos, decisoes)


def test_consolidar_grava_saidas_e_conta_pendentes(tmp_path):
    pasta = gravar(tmp_path / "rotulos", A=A, B=B, C=C)
    kappa, consenso, pendentes = consolidar(pasta)
    assert pendentes == 1
    assert pd.read_csv(pasta / "kappa.csv").shape[0] == 3
    lido = pd.read_csv(pasta / "consenso.csv", keep_default_na=False)
    assert list(lido.columns) == COLUNAS_CONSENSO and len(lido) == 5


def test_main_codigos_de_saida(tmp_path, capsys):
    pasta = gravar(tmp_path / "rotulos", A=A, B=A, C=B)
    assert consolidar_main(["--rotulos", str(pasta)]) == 0
    assert "kappa" in capsys.readouterr().out
    empate = gravar(tmp_path / "empate", A=A, B=B, C=C)
    assert consolidar_main(["--rotulos", str(empate)]) == 2
    assert consolidar_main(["--rotulos", str(tmp_path / "nada")]) == 1
