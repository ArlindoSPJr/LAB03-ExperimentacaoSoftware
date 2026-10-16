import pytest

from metricas.corretiva import (HEURISTICA_VERSAO, bump_so_de_patch, eh_corretiva,
                                tem_commit_corretivo, versao_semver)


def test_exemplo_do_enunciado_patch_com_fix_e_corretiva():
    assert eh_corretiva("v2.3.0", "v2.3.1", ["fix: crash ao abrir arquivo"])


def test_exemplo_do_enunciado_minor_sem_correcao_nao_e_corretiva():
    assert not eh_corretiva("v2.4.0", "v2.5.0", ["feat: nova tela"])


def test_so_patch_sem_commit_de_correcao_e_corretiva():
    assert eh_corretiva("1.0.0", "1.0.1", ["docs: atualiza README"])


@pytest.mark.parametrize("mensagem", ["Revert \"feat: x\"", "hotfix: login quebrado", "Fixed crash"])
def test_minor_com_commit_corretivo_e_corretiva(mensagem):
    assert eh_corretiva("v1.2.0", "v1.3.0", ["feat: algo", mensagem])


@pytest.mark.parametrize("mensagem", ["add prefix option", "suffix handling"])
def test_palavra_dentro_de_outra_nao_conta(mensagem):
    assert not tem_commit_corretivo([mensagem])


@pytest.mark.parametrize("anterior, atual", [("ams-v2.16.0", "ams-v2.16.2"),
                                             ("@pkg/x@1.0.0", "@pkg/x@1.0.1")])
def test_patch_reconhecido_em_tags_com_prefixo(anterior, atual):
    assert bump_so_de_patch(anterior, atual)


def test_prefixos_diferentes_nao_sao_bump_de_patch():
    assert not bump_so_de_patch("@a/x@1.0.0", "@b/y@1.0.1")


def test_tag_nao_semver_decide_so_pelos_commits():
    assert versao_semver("release-2026-01-16-342e44b") is None
    assert not eh_corretiva("release-2026-01-15", "release-2026-01-16", ["chore: release"])
    assert eh_corretiva("release-2026-01-15", "release-2026-01-16", ["fix: refs"])


def test_sufixo_de_pre_release_e_ignorado_na_versao():
    assert versao_semver("v5.0.0-M3") == ("", 5, 0, 0)


def test_patch_que_diminui_nao_e_bump():
    assert not bump_so_de_patch("v1.0.3", "v1.0.2")


def test_versao_da_heuristica():
    assert HEURISTICA_VERSAO == "v1"
