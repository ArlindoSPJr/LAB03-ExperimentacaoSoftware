def test_imports():
    import metricas  # noqa: F401
    import pipeline  # noqa: F401


def _carregar_config():
    from pathlib import Path

    import yaml

    raiz = Path(__file__).resolve().parent.parent
    with open(raiz / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_config_window_end_no_passado():
    from datetime import date

    cfg = _carregar_config()
    inicio = date.fromisoformat(str(cfg["window"]["start"]))
    fim = date.fromisoformat(str(cfg["window"]["end"]))
    assert inicio < fim < date.today()
