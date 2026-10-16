"""Testes da etapa de CFR de entrega e rework rate. Nunca acessam a rede."""
from datetime import datetime, timezone

import pytest

from pipeline.etapa_entrega import classificar_unidades, coletar_cfr_entrega
from pipeline.http import NotFoundError

START = datetime(2025, 10, 1, tzinfo=timezone.utc)
END = datetime(2026, 9, 30, 23, 59, 59, tzinfo=timezone.utc)
JANELA = (START, END)
META = {"full_name": "octo/hello", "default_branch": "main"}
R = "/repos/octo/hello"


class FakeClient:
    """path -> resposta ou exceção. Compare sem resposta definida devolve []."""

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def paginate(self, path, params=None, item_key=None):
        self.calls.append(path)
        resp = self.responses.get(path, [])
        if isinstance(resp, Exception):
            raise resp
        return resp


def rel(tag, published_at, prerelease=False):
    return {"tag_name": tag, "published_at": published_at, "draft": False, "prerelease": prerelease, "body": ""}


def commits(*mensagens):
    return [{"sha": f"s{i}", "commit": {"author": {"date": "2026-01-01T00:00:00Z"}, "message": m}}
            for i, m in enumerate(mensagens)]


def compare(base, head):
    return f"{R}/compare/{base}...{head}"


def compares(client):
    return [c for c in client.calls if "/compare/" in c]


def unidade(nome, data):
    return {"nome": nome, "data": datetime.fromisoformat(data.replace("Z", "+00:00"))}


def test_release_seguida_por_patch_corretivo_falha():
    releases = [rel("v1.0.0", "2025-09-01T00:00:00Z"), rel("v1.1.0", "2026-03-01T00:00:00Z"),
                rel("v1.1.1", "2026-03-03T00:00:00Z"), rel("v1.2.0", "2026-05-01T00:00:00Z")]
    client = FakeClient({
        f"{R}/releases": releases,
        compare("v1.0.0", "v1.1.0"): commits("feat: nova tela"),
        compare("v1.1.0", "v1.1.1"): commits("fix: crash ao abrir"),
        compare("v1.1.1", "v1.2.0"): commits("feat: filtro"),
    })
    r = coletar_cfr_entrega(client, META, JANELA)
    assert r["cfr_entrega"] == pytest.approx(1 / 3)
    assert (r["n_falhas_entrega"], r["n_censuradas_entrega"]) == (1, 0)
    assert r["rework_rate"] == pytest.approx(1 / 3)
    assert r["cfr_entrega_pre"] == pytest.approx(1 / 3)


def test_release_dos_ultimos_7_dias_e_censurada():
    releases = [rel("v1.0.0", "2026-03-01T00:00:00Z"), rel("v1.0.1", "2026-09-28T00:00:00Z")]
    client = FakeClient({f"{R}/releases": releases,
                         compare("v1.0.0", "v1.0.1"): commits("fix: x")})
    r = coletar_cfr_entrega(client, META, JANELA)
    assert (r["cfr_entrega"], r["n_falhas_entrega"], r["n_censuradas_entrega"]) == (0, 0, 1)
    assert r["rework_rate"] == pytest.approx(0.5)


def test_pre_release_entra_so_na_variante_pre():
    releases = [rel("v1.0.0", "2026-03-01T00:00:00Z"),
                rel("v1.0.1-rc.1", "2026-03-02T00:00:00Z", prerelease=True),
                rel("v1.1.0", "2026-05-01T00:00:00Z")]
    client = FakeClient({f"{R}/releases": releases,
                         compare("v1.0.0", "v1.0.1-rc.1"): commits("fix: bug"),
                         compare("v1.0.0", "v1.1.0"): commits("feat: x"),
                         compare("v1.0.1-rc.1", "v1.1.0"): commits("feat: x")})
    r = coletar_cfr_entrega(client, META, JANELA)
    assert r["cfr_entrega"] == 0
    assert r["cfr_entrega_pre"] == pytest.approx(1 / 3)


def test_primeira_release_sem_compare_e_classificada_pela_tag():
    client = FakeClient({})
    unidades = [unidade("v2.0.1", "2026-02-01T00:00:00Z"), unidade("v2.1.0", "2026-03-01T00:00:00Z")]
    out = classificar_unidades(client, "octo/hello", unidades, JANELA)
    assert [u["corretiva"] for u in out] == [True, False]
    assert compares(client) == [compare("v2.0.1", "v2.1.0")]


def test_compare_404_e_classificada_pela_tag():
    client = FakeClient({compare("v1.0.0", "v1.0.1"): NotFoundError(404, "x", "Not Found")})
    unidades = [unidade("v1.0.0", "2025-09-01T00:00:00Z"), unidade("v1.0.1", "2026-02-01T00:00:00Z")]
    out = classificar_unidades(client, "octo/hello", unidades, JANELA)
    assert [u["corretiva"] for u in out] == [True]


def test_teto_de_compares_limita_chamadas_e_classifica_o_resto_pela_tag():
    unidades = [unidade(f"v1.0.{i}", f"2026-01-{i + 1:02d}T00:00:00Z") for i in range(6)]
    client = FakeClient({})
    out = classificar_unidades(client, "octo/hello", unidades, JANELA, max_compares=2)
    assert len(compares(client)) == 2
    assert len(out) == 6
    assert out[0]["corretiva"] is False  # v1.0.0: tag sem patch e sem compare


def test_sem_releases_na_janela_tudo_vazio():
    client = FakeClient({f"{R}/releases": [rel("v1.0.0", "2025-09-01T00:00:00Z")]})
    r = coletar_cfr_entrega(client, META, JANELA)
    assert r == {"cfr_entrega": None, "n_falhas_entrega": 0, "n_censuradas_entrega": 0,
                 "rework_rate": None, "cfr_entrega_pre": None}
