"""Concordância entre avaliadores e consenso (S02-O2.1)."""
import math

import pandas as pd
import pytest

from validacao.concordancia import DIMENSOES, consenso, fleiss_kappa_dimensao

CORRETIVA = DIMENSOES["corretiva"]


def tabela(*linhas) -> pd.DataFrame:
    """Uma linha por item, uma coluna por avaliador (A, B, C)."""
    return pd.DataFrame(list(linhas), columns=["A", "B", "C"])


def test_dimensoes_seguem_o_enunciado():
    assert DIMENSOES["tipo_projeto"] == ["biblioteca/framework", "aplicacao/servico", "ferramenta CLI", "outro"]
    assert DIMENSOES["entregas_reais"] == ["sim", "nao", "incerto"]
    assert DIMENSOES["corretiva"] == ["sim", "nao"]


def test_concordancia_perfeita_da_kappa_1():
    rotulos = tabela(["sim"] * 3, ["nao"] * 3, ["sim"] * 3, ["nao"] * 3)
    assert fleiss_kappa_dimensao(rotulos, CORRETIVA) == pytest.approx(1.0)


def test_kappa_conhecido_a_mao():
    # 4 itens, 3 avaliadores: p_sim = 6/12 = 0,5 -> Pe = 0,5
    # P_i: 3-0 -> 1; 2-1 -> 1/3; 3-0 -> 1; 1-2 -> 1/3 -> P_barra = 2/3
    # kappa = (2/3 - 1/2) / (1 - 1/2) = 1/3
    rotulos = tabela(["sim"] * 3, ["sim", "sim", "nao"], ["nao"] * 3, ["sim", "nao", "nao"])
    assert fleiss_kappa_dimensao(rotulos, CORRETIVA) == pytest.approx(1 / 3)


def test_discordancia_sistematica_da_kappa_negativo():
    rotulos = tabela(["sim", "sim", "nao"], ["nao", "nao", "sim"], ["sim", "nao", "nao"], ["nao", "sim", "sim"])
    assert fleiss_kappa_dimensao(rotulos, CORRETIVA) < 0


def test_rotulos_sao_normalizados():
    rotulos = tabela([" Sim", "SIM", "sim "], ["nao", "Nao", "NAO"])
    assert fleiss_kappa_dimensao(rotulos, CORRETIVA) == pytest.approx(1.0)


def test_categoria_ausente_nos_dados_nao_muda_o_kappa():
    rotulos = tabela(["sim"] * 3, ["sim", "sim", "nao"], ["nao"] * 3, ["sim", "nao", "nao"])
    com_extra = fleiss_kappa_dimensao(rotulos, ["sim", "nao", "talvez"])
    assert com_extra == pytest.approx(1 / 3)


def test_rotulo_fora_das_categorias_levanta_erro():
    with pytest.raises(ValueError, match="talvez"):
        fleiss_kappa_dimensao(tabela(["sim", "talvez", "sim"]), CORRETIVA)


def test_rotulo_vazio_levanta_erro():
    with pytest.raises(ValueError, match="vazio"):
        fleiss_kappa_dimensao(tabela(["sim", None, "sim"]), CORRETIVA)


def test_todos_iguais_numa_so_categoria_nao_tem_kappa_definido():
    # Pe = 1: o kappa é 0/0. Devolve NaN em vez de um número enganoso.
    assert math.isnan(fleiss_kappa_dimensao(tabela(["sim"] * 3, ["sim"] * 3), CORRETIVA))


def test_consenso_por_maioria_simples():
    rotulos = tabela(["sim"] * 3, ["sim", "nao", "sim"], ["nao", "nao", "sim"])
    resultado = consenso(rotulos)
    assert resultado["consenso"].tolist() == ["sim", "sim", "nao"]
    assert resultado["reuniao"].tolist() == [False, False, False]


def test_empate_1_1_1_vai_para_reuniao():
    rotulos = tabela(["biblioteca/framework", "aplicacao/servico", "outro"], ["outro"] * 3)
    resultado = consenso(rotulos)
    assert resultado.loc[0, "reuniao"]
    assert pd.isna(resultado.loc[0, "consenso"])
    assert resultado.loc[1, "consenso"] == "outro"
    assert not resultado.loc[1, "reuniao"]


def test_consenso_normaliza_e_preserva_o_indice():
    rotulos = tabela(["Sim", "sim ", "nao"]).set_axis(["octo/hello#v1.0.1"])
    resultado = consenso(rotulos)
    assert resultado.index.tolist() == ["octo/hello#v1.0.1"]
    assert resultado.loc["octo/hello#v1.0.1", "consenso"] == "sim"


def test_consenso_registra_os_votos():
    resultado = consenso(tabela(["sim", "nao", "sim"]))
    assert resultado.loc[0, "votos"] == "A=sim; B=nao; C=sim"
