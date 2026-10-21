import pandas as pd

from analise.classificacao_c1 import classificar


def _df():
    return pd.DataFrame({
        "repo": ["a/a", "b/b", "c/c"],
        "score_freq": [4, 3, None],
        "score_lead": [3, 2, None],
        "score_cfr": [3, 4, None],
        "score_rec": [1, 4, None],
        "dora_overall": ["High", "High", None],
        "outra_coluna": [9, 9, 9],
    })


def test_classificar_traduz_notas_em_categorias_sem_reclassificar():
    r = classificar(_df())
    a = r.iloc[0]
    assert (a["cat_freq"], a["cat_lead"], a["cat_cfr"], a["cat_rec"]) == ("Elite", "High", "High", "Low")
    assert a["dora_overall"] == "High"  # copiado do CSV, nao recalculado
    assert a["score_freq"] == 4 and bool(a["classificado"]) is True


def test_classificar_repo_sem_classificacao_fica_nao_classificado():
    c = classificar(_df()).iloc[2]
    assert bool(c["classificado"]) is False
    assert c["cat_freq"] is None and c["dora_overall"] is None


def test_classificar_mantem_so_colunas_de_saida_na_ordem():
    r = classificar(_df())
    assert list(r.columns) == [
        "repo", "score_freq", "score_lead", "score_cfr", "score_rec",
        "cat_freq", "cat_lead", "cat_cfr", "cat_rec", "dora_overall", "classificado",
    ]
    assert list(r["repo"]) == ["a/a", "b/b", "c/c"]


def test_classificar_csv_sem_colunas_de_score_nao_classifica_ninguem():
    r = classificar(pd.DataFrame({"repo": ["a/a"]}))
    assert bool(r.iloc[0]["classificado"]) is False


from analise.classificacao_c1 import distribuicao


def test_distribuicao_conta_categorias_a_mao():
    d = distribuicao(classificar(_df()))
    g = d[(d["dimensao"] == "geral")].set_index("categoria")
    assert g.loc["High", "n"] == 2 and g.loc["Elite", "n"] == 0
    assert g.loc["Nao classificado", "n"] == 1
    assert abs(g.loc["High", "prop"] - 2 / 3) < 1e-9
    f = d[d["dimensao"] == "freq"].set_index("categoria")
    assert (f.loc["Elite", "n"], f.loc["High", "n"], f.loc["Nao classificado", "n"]) == (1, 1, 1)


def test_distribuicao_ordem_das_categorias_e_dimensoes():
    d = distribuicao(classificar(_df()))
    assert list(d["dimensao"].drop_duplicates()) == ["freq", "lead", "cfr", "rec", "geral"]
    assert list(d[d["dimensao"] == "geral"]["categoria"]) == [
        "Elite", "High", "Medium", "Low", "Nao classificado"]


def test_distribuicao_vazia_tem_prop_none():
    d = distribuicao(classificar(pd.DataFrame({"repo": []})))
    assert d["n"].sum() == 0 and d["prop"].isna().all()


from analise.classificacao_c1 import executar


def test_executar_grava_classificacao_e_distribuicao(tmp_path):
    entrada = tmp_path / "m.csv"
    _df().to_csv(entrada, index=False)
    res = executar(entrada, tmp_path / "saida")
    lido = pd.read_csv(tmp_path / "saida" / "classificacao_c1.csv")
    assert list(lido["repo"]) == ["a/a", "b/b", "c/c"]
    assert (tmp_path / "saida" / "distribuicao_c1.csv").exists()
    assert len(res["classificacao"]) == 3
