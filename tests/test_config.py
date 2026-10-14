"""Conferência do config.yaml versionado (o que a coleta da S02 usa)."""
import pathlib
from datetime import datetime, timezone

from pipeline.orquestrador import carregar_config, janela_da_config

CONFIG = pathlib.Path(__file__).resolve().parent.parent / "config.yaml"


def test_config_pede_pelo_menos_300_repositorios():
    assert carregar_config(CONFIG)["sample_size"] >= 300


def test_janela_tem_12_meses_e_ja_terminou():
    inicio, fim = janela_da_config(carregar_config(CONFIG))
    assert 364 <= (fim - inicio).days <= 366
    assert fim < datetime.now(timezone.utc)


def test_faixas_de_estrelas_validas():
    for lo, hi in carregar_config(CONFIG)["star_ranges"]:
        assert 0 <= lo <= hi
