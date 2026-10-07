"""Testes do orquestrador e do comando único. Cliente fake: nunca acessam a rede."""
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from pipeline.__main__ import main
from pipeline.http import NotFoundError
from pipeline.orquestrador import COLUNAS, carregar_config, executar, janela_da_config

JANEIRO = "2026-01-01..2026-01-31"


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


def releases_validas(n=5):
    """Uma release antes da janela (base do compare) + n releases mensais na janela."""
    datas = [utc(2025, 9, 1)] + [utc(2025, 11, 1) + timedelta(days=30 * i) for i in range(n)]
    return [{"tag_name": f"v{i}", "published_at": iso(d), "draft": False, "prerelease": False, "body": ""}
            for i, d in enumerate(datas)]


def runs_validos(n=50, falha_a_cada=10):
    """n runs de hora em hora em janeiro; 1 falha a cada `falha_a_cada`, recuperada no run seguinte."""
    runs = []
    for i in range(n):
        inicio = utc(2026, 1, 10) + timedelta(hours=i)
        conclusao = "failure" if falha_a_cada and i % falha_a_cada == 5 else "success"
        runs.append({"workflow_id": 1, "conclusion": conclusao, "run_started_at": iso(inicio),
                     "updated_at": iso(inicio + timedelta(minutes=30)), "created_at": iso(inicio)})
    return runs


def repo(actions=True, disponivel=True, releases=None, runs=None):
    return {"actions": actions, "disponivel": disponivel,
            "releases": releases_validas() if releases is None else releases,
            "runs": runs_validos() if runs is None else runs}


class FakeClient:
    """Roteia os endpoints usados pelo pipeline para repositórios fake."""

    def __init__(self, repos: dict, busca: list[str] | None = None):
        self.repos = repos
        self.busca = busca if busca is not None else list(repos)
        self.calls = []

    @staticmethod
    def _repo(path):
        partes = path.strip("/").split("/")
        return f"{partes[1]}/{partes[2]}", partes[3:]

    def get(self, path, params=None):
        self.calls.append(path)
        nome, resto = self._repo(path)
        r = self.repos[nome]
        if resto == ["actions", "workflows"]:
            return {"total_count": 2 if r["actions"] else 0}, {}
        if not r["disponivel"]:
            raise NotFoundError(404, path, "Not Found")
        if resto == []:
            return {"full_name": nome, "stargazers_count": 1500, "language": "Python",
                    "created_at": "2020-01-01T00:00:00Z", "default_branch": "main"}, {}
        if resto == ["contributors"]:
            return [{"login": "a"}], {}
        raise AssertionError(f"endpoint inesperado: {path}")

    def paginate(self, path, params=None, item_key=None):
        self.calls.append(path)
        if path == "/search/repositories":
            return [{"full_name": nome} for nome in self.busca]
        nome, resto = self._repo(path)
        r = self.repos[nome]
        if resto == ["releases"]:
            return r["releases"]
        if resto[0] == "compare":
            head = resto[1].split("...")[1]
            publicada = next(x["published_at"] for x in r["releases"] if x["tag_name"] == head)
            data = iso(datetime.fromisoformat(publicada.replace("Z", "+00:00")) - timedelta(days=2))
            return [{"sha": head, "commit": {"author": {"date": data}, "message": "feat: x"}}]
        if resto == ["actions", "runs"]:
            return r["runs"] if params["created"] == JANEIRO else []
        raise AssertionError(f"endpoint inesperado: {path}")


def config(**extra):
    cfg = {"window": {"start": "2025-10-01", "end": "2026-09-30"}, "sample_size": 10,
           "star_ranges": [[1000, 2000]], "cache_dir": "cache"}
    cfg.update(extra)
    return cfg


def funil_dict(funil: pd.DataFrame) -> dict:
    return {linha.etapa: (linha.restantes, linha.descartados) for linha in funil.itertuples()}


def test_janela_da_config_vai_do_inicio_do_primeiro_ao_fim_do_ultimo_dia():
    assert janela_da_config(config()) == (utc(2025, 10, 1), utc(2026, 9, 30, 23, 59, 59))


def test_carregar_config_le_yaml(tmp_path):
    arquivo = tmp_path / "config.yaml"
    arquivo.write_text('window:\n  start: "2025-10-01"\n  end: "2026-09-30"\nsample_size: 3\n', encoding="utf-8")
    cfg = carregar_config(arquivo)
    assert cfg["sample_size"] == 3
    assert cfg["window"]["start"] == "2025-10-01"


def test_tres_repos_sem_actions_poucas_releases_e_valido(tmp_path):
    client = FakeClient({
        "o/sem-actions": repo(actions=False),
        "o/poucas-releases": repo(releases=releases_validas(3)),
        "o/valido": repo(),
    })
    metricas, funil = executar(client, config(), tmp_path)

    assert list(metricas["repo"]) == ["o/valido"]
    assert funil_dict(funil) == {
        "candidatos da busca": (3, 0),
        "processados": (3, 0),
        "com GitHub Actions": (2, 1),
        "metadados coletados": (2, 0),
        ">= 5 releases na janela": (1, 1),
        ">= 50 runs válidos na janela": (1, 0),
        "amostra final": (1, 0),
    }
    # sem Actions e com poucas releases: a etapa de runs nem é chamada
    assert not any("o/poucas-releases/actions/runs" in c for c in client.calls)


def test_linha_do_repositorio_valido(tmp_path):
    metricas, _ = executar(FakeClient({"o/valido": repo()}), config(), tmp_path)
    linha = metricas.iloc[0]
    assert linha["stars"] == 1500
    assert linha["language"] == "Python"
    assert linha["contributors"] == 1
    assert linha["age_days"] == (utc(2026, 9, 30).date() - utc(2020, 1, 1).date()).days
    assert linha["n_releases"] == 5
    assert linha["n_runs_validos"] == 50
    assert linha["lead_time_a_days"] == pytest.approx(2)
    assert linha["cfr_ci"] == pytest.approx(0.1)
    assert linha["recovery_median_h"] == pytest.approx(1.5)
    assert linha["n_episodes"] == 5
    assert linha["score_cfr"] == 4
    assert linha["dora_overall"] in {"Elite", "High", "Medium", "Low"}


def test_lista_fornecida_pula_a_busca(tmp_path):
    client = FakeClient({"o/a": repo(), "o/b": repo()}, busca=[])
    metricas, funil = executar(client, config(repos=["o/b", "o/a"]), tmp_path)
    assert "/search/repositories" not in client.calls
    assert list(metricas["repo"]) == ["o/b", "o/a"]
    assert funil.iloc[0]["etapa"] == "lista fornecida"
    assert funil.iloc[0]["restantes"] == 2


def test_para_ao_atingir_sample_size(tmp_path):
    client = FakeClient({"o/a": repo(), "o/b": repo(), "o/c": repo()})
    metricas, funil = executar(client, config(repos=["o/a", "o/b", "o/c"], sample_size=1), tmp_path)
    assert list(metricas["repo"]) == ["o/a"]
    assert not any(c.startswith("/repos/o/b") for c in client.calls)
    linha = funil[funil["etapa"] == "processados"].iloc[0]
    assert (linha["restantes"], linha["descartados"]) == (1, 2)
    assert "sample_size" in linha["motivo"]


def test_poucos_runs_validos_descarta(tmp_path):
    poucos = runs_validos(60)
    for r in poucos[:20]:
        r["conclusion"] = "cancelled"
    metricas, funil = executar(FakeClient({"o/a": repo(runs=poucos)}), config(), tmp_path)
    assert metricas.empty
    assert funil_dict(funil)[">= 50 runs válidos na janela"] == (0, 1)


def test_repositorio_indisponivel_e_descartado(tmp_path):
    client = FakeClient({"o/sumiu": repo(disponivel=False), "o/a": repo()})
    metricas, funil = executar(client, config(), tmp_path)
    assert list(metricas["repo"]) == ["o/a"]
    assert funil_dict(funil)["metadados coletados"] == (1, 1)


def test_metrica_ausente_deixa_notas_e_dora_overall_vazios(tmp_path):
    sem_falhas = runs_validos(50, falha_a_cada=0)  # sem episódios -> recuperação None
    metricas, _ = executar(FakeClient({"o/a": repo(runs=sem_falhas)}), config(), tmp_path)
    linha = metricas.iloc[0]
    assert linha["cfr_ci"] == 0
    assert pd.isna(linha["recovery_median_h"])
    for coluna in ["score_freq", "score_lead", "score_cfr", "score_rec", "dora_overall"]:
        assert pd.isna(linha[coluna])


def test_grava_os_dois_csvs_com_as_colunas_na_ordem(tmp_path):
    executar(FakeClient({"o/a": repo(), "o/b": repo(actions=False)}), config(), tmp_path)
    metricas = pd.read_csv(tmp_path / "metricas.csv")
    funil = pd.read_csv(tmp_path / "funil.csv")
    assert list(metricas.columns) == COLUNAS
    assert len(metricas) == 1
    assert list(funil.columns) == ["etapa", "restantes", "descartados", "motivo"]


def test_csv_vazio_tem_cabecalho(tmp_path):
    executar(FakeClient({"o/a": repo(actions=False)}), config(), tmp_path)
    assert list(pd.read_csv(tmp_path / "metricas.csv").columns) == COLUNAS


def test_main_sem_token_falha_com_mensagem(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    arquivo = tmp_path / "config.yaml"
    arquivo.write_text('window:\n  start: "2025-10-01"\n  end: "2026-09-30"\n', encoding="utf-8")
    assert main(["--config", str(arquivo)]) != 0
    assert "GITHUB_TOKEN" in capsys.readouterr().err
