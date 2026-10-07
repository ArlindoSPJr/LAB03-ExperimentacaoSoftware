"""Tempo de recuperação após falha de CI (RQ04), em horas.

Por workflow, com os runs em ordem de `run_started_at` e ignorando os que
`classify_conclusion` descarta: um episódio começa na primeira falha **após um
sucesso** e termina no próximo sucesso do mesmo workflow; dura
`updated_at` do sucesso − `run_started_at` da primeira falha.

Decisão 3 de docs/ISSUES.md: falhas antes do primeiro sucesso não abrem episódio
(contadas por `contar_falhas_iniciais`); episódio sem sucesso até o fim da janela
é censurado, contado e não descartado.
"""

import statistics
from collections import defaultdict

from metricas.cfr import classify_conclusion

SEGUNDOS_POR_HORA = 3600


def _validos(runs: list[dict]) -> list[tuple[str, dict]]:
    ordenados = sorted(runs, key=lambda r: r["run_started_at"])
    classes = ((classify_conclusion(r["conclusion"]), r) for r in ordenados)
    return [(classe, r) for classe, r in classes if classe is not None]


def _por_workflow(runs: list[dict]) -> dict[int, list[dict]]:
    grupos: dict[int, list[dict]] = defaultdict(list)
    for r in runs:
        grupos[r["workflow_id"]].append(r)
    return grupos


def recovery_episodes(runs: list[dict]) -> tuple[list[float], int]:
    """(horas de cada episódio recuperado, nº de censurados) para UM workflow."""
    horas: list[float] = []
    teve_sucesso = False
    inicio_falha = None
    for classe, r in _validos(runs):
        if classe == "failure":
            if teve_sucesso and inicio_falha is None:
                inicio_falha = r["run_started_at"]
        else:
            if inicio_falha is not None:
                horas.append((r["updated_at"] - inicio_falha).total_seconds() / SEGUNDOS_POR_HORA)
                inicio_falha = None
            teve_sucesso = True
    return horas, int(inicio_falha is not None)


def contar_falhas_iniciais(runs: list[dict]) -> int:
    """Falhas anteriores ao primeiro sucesso de cada workflow (não abrem episódio)."""
    total = 0
    for runs_wf in _por_workflow(runs).values():
        for classe, _ in _validos(runs_wf):
            if classe == "success":
                break
            total += 1
    return total


def repo_recovery(runs: list[dict]) -> tuple[float | None, int, int]:
    """(mediana em horas, nº de episódios, nº de censurados) agrupando por `workflow_id`.

    `n_episodes` inclui os censurados; a mediana usa só os recuperados e é None sem eles.
    """
    horas: list[float] = []
    censurados = 0
    for runs_wf in _por_workflow(runs).values():
        horas_wf, censurados_wf = recovery_episodes(runs_wf)
        horas.extend(horas_wf)
        censurados += censurados_wf
    mediana = statistics.median(horas) if horas else None
    return mediana, len(horas) + censurados, censurados
