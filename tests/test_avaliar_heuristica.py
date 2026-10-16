import pandas as pd
import pytest

from metricas.corretiva import HEURISTICA_VERSAO
from validacao.avaliar_heuristica import avaliar, metricas, tags_do_compare


def test_tags_do_compare_url_normal():
    assert tags_do_compare("https://github.com/o/r/compare/v1.0.0...v1.0.1") == ("v1.0.0", "v1.0.1")


def test_tags_do_compare_decodifica_tag():
    url = "https://github.com/o/r/compare/%40pkg%2Fx%401.0.0...%40pkg%2Fx%401.0.1"
    assert tags_do_compare(url) == ("@pkg/x@1.0.0", "@pkg/x@1.0.1")


def test_tags_do_compare_primeira_release_sem_compare():
    assert tags_do_compare("https://github.com/o/r/commits/v0.1.0") is None
    assert tags_do_compare("") is None


def test_metricas_acerto_perfeito():
    m = metricas(["sim", "nao", "sim"], ["sim", "nao", "sim"])
    assert m == {"n": 3, "precisao": 1.0, "recall": 1.0, "f1": 1.0}


def test_metricas_calculadas_a_mao():
    # VP=1, FP=1, FN=1 -> precisão 0,5; recall 0,5; F1 0,5
    m = metricas(["sim", "nao", "sim", "nao"], ["sim", "sim", "nao", "nao"])
    assert (m["precisao"], m["recall"], m["f1"]) == (0.5, 0.5, 0.5)


def test_metricas_sem_positivos_previstos_nao_quebra():
    assert metricas(["sim", "nao"], ["nao", "nao"])["f1"] == 0.0


def test_avaliar_casos_de_borda():
    itens = pd.DataFrame([
        {"repo": "o/r", "tag": "v1.0.0", "url_commits": "https://github.com/o/r/commits/v1.0.0", "corretiva": "nao"},
        {"repo": "o/r", "tag": "v1.1.0", "url_commits": "https://github.com/o/r/compare/v1.0.0...v1.1.0", "corretiva": "sim"},
        {"repo": "o/r", "tag": "v1.2.0", "url_commits": "https://github.com/o/r/compare/v1.1.0...v1.2.0", "corretiva": "nao"},
        {"repo": "o/r", "tag": "v1.2.1", "url_commits": "https://github.com/o/r/compare/v1.2.0...v1.2.1", "corretiva": "sim"},
    ])
    respostas = {"v1.1.0": ["fix: bug"], "v1.2.0": None, "v1.2.1": ["docs"]}
    chamadas = []

    def mensagens(repo, base, head):
        chamadas.append((repo, base, head))
        return respostas[head]

    out = avaliar(itens, mensagens)
    assert out["predicao"].tolist() == ["nao", "sim", "nao", "sim"]
    assert out["com_commits"].tolist() == [False, True, False, True]
    assert (out["versao"] == HEURISTICA_VERSAO).all()
    assert out["consenso"].tolist() == itens["corretiva"].tolist()
    assert ("o/r", "v1.0.0", "v1.1.0") in chamadas and len(chamadas) == 3
