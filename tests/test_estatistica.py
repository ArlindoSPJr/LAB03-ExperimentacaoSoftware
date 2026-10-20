import math

import pytest

from analise.estatistica import (
    cliffs_delta,
    epsilon_quadrado,
    mediana_iqr,
    quartis_grupos,
)


def test_mediana_iqr_valores_a_mao():
    # 1..8: mediana 4,5; Q1 = 2,75; Q3 = 6,25 (interpolacao linear)
    r = mediana_iqr([1, 2, 3, 4, 5, 6, 7, 8])
    assert r["mediana"] == pytest.approx(4.5)
    assert r["q1"] == pytest.approx(2.75)
    assert r["q3"] == pytest.approx(6.25)
    assert r["iqr"] == pytest.approx(3.5)
    assert r["n"] == 8


def test_mediana_iqr_resistente_a_outlier():
    r = mediana_iqr([1, 2, 3, 4, 1000])
    assert r["mediana"] == 3
    assert r["q1"] == 2
    assert r["q3"] == 4
    assert r["iqr"] == 2


def test_mediana_iqr_ignora_none_e_nan():
    r = mediana_iqr([1, None, 3, float("nan"), 5])
    assert r["n"] == 3
    assert r["mediana"] == 3


def test_mediana_iqr_vazio_devolve_none():
    r = mediana_iqr([None, float("nan")])
    assert r == {"mediana": None, "q1": None, "q3": None, "iqr": None, "n": 0}
    assert mediana_iqr([])["n"] == 0


def test_mediana_iqr_um_valor():
    r = mediana_iqr([7])
    assert (r["mediana"], r["q1"], r["q3"], r["iqr"], r["n"]) == (7, 7, 7, 0, 1)


def test_cliffs_delta_formula():
    # n1=n2=10, U=75 -> 2*75/100 - 1 = 0,5
    assert cliffs_delta(75, 10, 10) == pytest.approx(0.5)


def test_cliffs_delta_extremos_e_nulo():
    assert cliffs_delta(100, 10, 10) == pytest.approx(1.0)
    assert cliffs_delta(0, 10, 10) == pytest.approx(-1.0)
    assert cliffs_delta(50, 10, 10) == pytest.approx(0.0)


def test_cliffs_delta_tamanhos_diferentes():
    # U=6, n1=3, n2=4 -> 12/12 - 1 = 0
    assert cliffs_delta(6, 3, 4) == pytest.approx(0.0)


def test_cliffs_delta_grupo_vazio_erro():
    with pytest.raises(ValueError):
        cliffs_delta(0, 0, 5)


def test_epsilon_quadrado_formula():
    # H=12,5, n=26 -> 12,5/25 = 0,5
    assert epsilon_quadrado(12.5, 26) == pytest.approx(0.5)


def test_epsilon_quadrado_n_pequeno_erro():
    with pytest.raises(ValueError):
        epsilon_quadrado(1.0, 1)


def test_quartis_grupos_a_mao():
    # cortes 2,75 / 4,5 / 6,25
    g = quartis_grupos([1, 2, 3, 4, 5, 6, 7, 8])
    assert g == ["Q1", "Q1", "Q2", "Q2", "Q3", "Q3", "Q4", "Q4"]


def test_quartis_grupos_preserva_ordem_e_ausentes():
    g = quartis_grupos([8, None, 1, float("nan"), 4, 5])
    # validos 1,4,5,8: cortes 3,25 / 4,5 / 5,75
    assert g == ["Q4", None, "Q1", None, "Q2", "Q3"]


def test_quartis_grupos_valor_no_corte_vai_para_grupo_inferior():
    # 1,2,3,4,5: cortes 2 / 3 / 4
    assert quartis_grupos([1, 2, 3, 4, 5]) == ["Q1", "Q1", "Q2", "Q3", "Q4"]


def test_quartis_grupos_vazio():
    assert quartis_grupos([]) == []
    assert quartis_grupos([None]) == [None]
