"""Comando único: python -m pipeline --config config.yaml (token lido de GITHUB_TOKEN)."""
from __future__ import annotations

import argparse
import logging
import os
import pathlib
import sys

from pipeline.cache import DiskCache
from pipeline.http import GitHubClient
from pipeline.orquestrador import carregar_config, executar

SAIDA = pathlib.Path("data")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m pipeline", description="Mineração de métricas DORA.")
    parser.add_argument("--config", default="config.yaml", help="arquivo de configuração (padrão: config.yaml)")
    args = parser.parse_args(argv)

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("erro: defina a variável de ambiente GITHUB_TOKEN com um token do GitHub.", file=sys.stderr)
        return 1

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = carregar_config(args.config)
    client = GitHubClient(token, DiskCache(pathlib.Path(cfg.get("cache_dir", "cache"))))
    metricas, funil = executar(client, cfg, SAIDA)
    print(funil.to_string(index=False))
    print(f"\n{len(metricas)} repositórios em {SAIDA / 'metricas.csv'}; funil em {SAIDA / 'funil.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
