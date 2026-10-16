import pandas as pd

from validacao.pre_rotular import (classificar_corretiva, classificar_entregas, classificar_tipo,
                                   pre_rotular)


def test_corretiva_so_correcoes_vira_sim():
    rotulo, _, _ = classificar_corretiva("### Bug Fixes\n* crash ao abrir arquivo\n* fix leak",
                                         "2 commits:\n- fix: null pointer\n- fix: typo", "v1.2.3")
    assert rotulo == "sim"


def test_corretiva_so_funcionalidades_vira_nao():
    rotulo, _, _ = classificar_corretiva("### Features\n* Added user mentions\n* New theme",
                                         "1 commits:\n- feat: mentions", "v1.3.0")
    assert rotulo == "nao"


def test_corretiva_mista_fica_para_revisao():
    rotulo, sugestao, motivo = classificar_corretiva("", "2 commits:\n- fix: bug\n- feat: nova tela")
    assert rotulo is None and sugestao in ("sim", "nao") and motivo.startswith("misto")


def test_corretiva_sem_evidencia_fica_para_revisao():
    assert classificar_corretiva("(notas vazias)", "1 commits:\n- Bump version to 1.2.3")[0] is None


def test_corretiva_com_bump_minor_fica_para_revisao():
    rotulo, sugestao, _ = classificar_corretiva("", "3 commits:\n- fix: a\n- fix: b\n- fix: c", "v2.4.0")
    assert rotulo is None and sugestao == "sim"


def test_commit_de_ci_nao_conta_como_correcao():
    assert classificar_corretiva("", "1 commits:\n- ci: fix Linux builds")[0] is None


def test_tipo_cli_claro():
    rotulo, _, _ = classificar_tipo("A command-line tool for X\nTópicos: cli", "brew install x")
    assert rotulo == "ferramenta CLI"


def test_tipo_biblioteca_com_server_na_descricao():
    rotulo, _, _ = classificar_tipo("Asynchronous HTTP client/server framework\nTópicos: http-server", "")
    assert rotulo in (None, "biblioteca/framework")


def test_tipo_sem_sinal_fica_para_revisao():
    assert classificar_tipo("Coisas", "")[0] is None


def test_entregas_nightly_fica_para_revisao():
    rotulo, sugestao, _ = classificar_entregas(["nightly-1", "nightly-2", "nightly-3"], ["x"] * 3)
    assert rotulo is None and sugestao == "nao"


def test_nao_sobrescreve_rotulo_manual():
    df = pd.DataFrame([
        {"nivel": "repo", "repo": "o/r", "tag": "", "descricao_repo": "Coisas", "readme": "",
         "notas_release": "", "commits_release": "", "tipo_projeto": "outro", "entregas_reais": "", "corretiva": ""},
        {"nivel": "release", "repo": "o/r", "tag": "v1", "descricao_repo": "", "readme": "",
         "notas_release": "", "commits_release": "1 commits:\n- fix: x", "tipo_projeto": "", "entregas_reais": "",
         "corretiva": "nao"},
    ])
    out = pre_rotular(df)
    assert out.loc[0, "tipo_projeto"] == "outro" and out.loc[0, "origem_rotulo"].startswith("manual")
    assert out.loc[1, "corretiva"] == "nao" and out.loc[1, "origem_rotulo"] == "manual"
