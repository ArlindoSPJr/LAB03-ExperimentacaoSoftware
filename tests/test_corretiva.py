import pytest

from metricas.corretiva import (HEURISTICA_VERSAO, VERSOES, bump_so_de_patch, eh_corretiva,
                                eh_corretiva_v1, eh_corretiva_v2, eh_corretiva_v3,
                                tag_de_patch, tem_commit_corretivo, versao_semver)


# --- v1: regra literal do enunciado -------------------------------------------------

def test_v1_exemplo_do_enunciado_patch_com_fix_e_corretiva():
    assert eh_corretiva_v1("v2.3.0", "v2.3.1", ["fix: crash ao abrir arquivo"])


def test_v1_exemplo_do_enunciado_minor_sem_correcao_nao_e_corretiva():
    assert not eh_corretiva_v1("v2.4.0", "v2.5.0", ["feat: nova tela"])


def test_v1_so_patch_sem_commit_de_correcao_e_corretiva():
    assert eh_corretiva_v1("1.0.0", "1.0.1", ["docs: atualiza README"])


@pytest.mark.parametrize("mensagem", ["Revert \"feat: x\"", "hotfix: login quebrado", "Fixed crash"])
def test_v1_minor_com_commit_corretivo_e_corretiva(mensagem):
    assert eh_corretiva_v1("v1.2.0", "v1.3.0", ["feat: algo", mensagem])


@pytest.mark.parametrize("mensagem", ["add prefix option", "suffix handling"])
def test_palavra_dentro_de_outra_nao_conta(mensagem):
    assert not tem_commit_corretivo([mensagem])


@pytest.mark.parametrize("anterior, atual", [("ams-v2.16.0", "ams-v2.16.2"),
                                             ("@pkg/x@1.0.0", "@pkg/x@1.0.1")])
def test_patch_reconhecido_em_tags_com_prefixo(anterior, atual):
    assert bump_so_de_patch(anterior, atual)


def test_prefixos_diferentes_nao_sao_bump_de_patch():
    assert not bump_so_de_patch("@a/x@1.0.0", "@b/y@1.0.1")


def test_v1_tag_nao_semver_decide_so_pelos_commits():
    assert versao_semver("release-2026-01-16-342e44b") is None
    assert not eh_corretiva_v1("release-2026-01-15", "release-2026-01-16", ["chore: release"])
    assert eh_corretiva_v1("release-2026-01-15", "release-2026-01-16", ["fix: refs"])


def test_sufixo_de_pre_release_e_ignorado_na_versao():
    assert versao_semver("v5.0.0-M3") == ("", 5, 0, 0)


def test_patch_que_diminui_nao_e_bump():
    assert not bump_so_de_patch("v1.0.3", "v1.0.2")


# --- v2: a própria tag é de patch ---------------------------------------------------

@pytest.mark.parametrize("tag, esperado", [("v2.3.1", True), ("v2.4.0", False), ("1.0", False),
                                          ("release-2026-01-16", False), ("@pkg/x@1.0.2", True)])
def test_tag_de_patch(tag, esperado):
    assert tag_de_patch(tag) is esperado


def test_v2_backport_de_outra_linha_e_corretivo():
    # v8.19.6 publicada depois de v9.2.0: a anterior por data é de outra linha
    assert eh_corretiva_v2("v9.2.0", "v8.19.6", [])
    assert not bump_so_de_patch("v9.2.0", "v8.19.6")


def test_v2_minor_com_fix_nao_e_corretivo():
    assert not eh_corretiva_v2("v1.2.0", "v1.3.0", ["fix: bug"])


# --- v3: tag de patch e commits predominantemente corretivos -------------------------

def test_v3_patch_sem_funcionalidade_e_corretivo():
    assert eh_corretiva_v3("v1.0.0", "v1.0.1", ["docs: README", "chore: release 1.0.1"])


def test_v3_patch_com_funcionalidade_e_poucos_fix_nao_e_corretivo():
    msgs = ["feat: nova tela", "feat(api): filtro", "fix: typo", "refactor: x"]
    assert not eh_corretiva_v3("v1.0.0", "v1.0.1", msgs)


def test_v3_patch_com_funcionalidade_mas_maioria_fix_e_corretivo():
    msgs = ["feat: opção nova", "fix: crash", "fix(core): vazamento", "Revert \"x\""]
    assert eh_corretiva_v3("v1.0.0", "v1.0.1", msgs)


def test_v3_commits_de_ruido_sao_ignorados():
    # "ci: fix build" não conta como correção; sobra só a funcionalidade
    msgs = ["feat: nova tela", "ci: fix build", "chore(deps): bump x", "Merge pull request #1"]
    assert not eh_corretiva_v3("v1.0.0", "v1.0.1", msgs)


def test_v3_usa_so_a_primeira_linha_da_mensagem():
    assert eh_corretiva_v3("v1.0.0", "v1.0.1", ["fix: crash\n\nadd test for it", "feat: x\n\nfix later"]) is True


def test_v3_minor_nunca_e_corretivo():
    assert not eh_corretiva_v3("v1.2.0", "v1.3.0", ["fix: a", "fix: b"])


# --- versão vigente -----------------------------------------------------------------

def test_versao_vigente_e_v3():
    assert HEURISTICA_VERSAO == "v3"
    assert VERSOES["v3"] is eh_corretiva_v3 and set(VERSOES) == {"v1", "v2", "v3"}
    assert eh_corretiva("v2.3.0", "v2.3.1", ["fix: crash ao abrir arquivo"])
    assert not eh_corretiva("v2.4.0", "v2.5.0", ["feat: nova tela"])
