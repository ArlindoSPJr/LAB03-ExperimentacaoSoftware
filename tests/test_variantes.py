"""Testes das funções puras das variantes de unidade de deploy (RQ07)."""
from datetime import datetime, timedelta, timezone

from metricas.variantes import lead_time_b_variante, pares_para_compare, separar_janela

START = datetime(2025, 10, 1, tzinfo=timezone.utc)
END = datetime(2026, 9, 30, 23, 59, 59, tzinfo=timezone.utc)


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


def un(nome, data):
    return {"nome": nome, "data": data}


def nomes(unidades):
    return [u["nome"] for u in unidades]


def test_separar_janela_devolve_a_ultima_anterior_como_base_e_a_janela_ordenada():
    unidades = [un("v3", utc(2026, 2, 1)), un("v0", utc(2025, 8, 1)), un("v1", utc(2025, 9, 1)),
                un("v2", utc(2025, 11, 1)), un("v4", utc(2026, 10, 2))]
    base, na_janela = separar_janela(unidades, START, END)
    assert base["nome"] == "v1"
    assert nomes(na_janela) == ["v2", "v3"]


def test_separar_janela_inclui_os_limites_da_janela():
    base, na_janela = separar_janela([un("a", START), un("b", END)], START, END)
    assert base is None
    assert nomes(na_janela) == ["a", "b"]


def test_separar_janela_sem_unidades():
    assert separar_janela([], START, END) == (None, [])


def test_pares_consecutivos_com_base_anterior_a_janela():
    a, b, c = un("a", utc(2025, 9, 1)), un("b", utc(2025, 11, 1)), un("c", utc(2025, 12, 1))
    assert pares_para_compare(a, [b, c]) == ([(a, b), (b, c)], 0)


def test_sem_base_a_primeira_unidade_da_historia_fica_sem_par():
    b, c = un("b", utc(2025, 11, 1)), un("c", utc(2025, 12, 1))
    assert pares_para_compare(None, [b, c]) == ([(b, c)], 0)
    assert pares_para_compare(None, [b]) == ([], 0)
    assert pares_para_compare(None, []) == ([], 0)


def test_teto_amostra_pares_espalhados_pela_janela_e_conta_os_pulados():
    seq = [un(f"t{i}", utc(2025, 10, 1) + timedelta(days=i)) for i in range(11)]  # 10 pares
    pares, pulados = pares_para_compare(None, seq, max_compares=4)
    assert [atual["nome"] for _, atual in pares] == ["t1", "t3", "t6", "t8"]  # i*10//4 = 0, 2, 5, 7
    assert all(int(atual["nome"][1:]) == int(anterior["nome"][1:]) + 1 for anterior, atual in pares)
    assert pulados == 6


def test_teto_maior_ou_igual_ao_numero_de_pares_nao_amostra():
    seq = [un(f"t{i}", utc(2025, 10, 1) + timedelta(days=i)) for i in range(5)]
    pares, pulados = pares_para_compare(None, seq, max_compares=4)
    assert len(pares) == 4 and pulados == 0


def test_lead_time_b_variante_exemplo_do_enunciado():
    release = utc(2026, 3, 15)
    resultado = lead_time_b_variante([(release, [utc(2026, 3, 2), utc(2026, 3, 10), utc(2026, 3, 14)])])
    assert resultado == {"lead_time_b_days": 5, "compare_404": 0, "n_lead_negativos": 0}


def test_lead_time_b_variante_conta_404_e_negativos_e_aceita_unidade_sem_commits():
    release = utc(2026, 3, 15)
    resultado = lead_time_b_variante([
        (release, None),                                  # compare 404
        (release, []),                                    # unidade sem commits novos
        (release, [utc(2026, 3, 16), utc(2026, 3, 14)]),  # um commit com data posterior
    ])
    assert resultado == {"lead_time_b_days": 1, "compare_404": 1, "n_lead_negativos": 1}


def test_lead_time_b_variante_sem_unidades():
    assert lead_time_b_variante([]) == {"lead_time_b_days": None, "compare_404": 0, "n_lead_negativos": 0}
