"""Change failure rate (RQ03), variante (a): proxy de CI por workflow runs.

Tabela de `conclusion` do enunciado (seção 3): `success` é sucesso;
`failure`, `timed_out` e `startup_failure` são falha; qualquer outro valor
(`cancelled`, `skipped`, `neutral`, `action_required`, `stale`, vazio) é ignorado.
"""

SUCESSOS = {"success"}
FALHAS = {"failure", "timed_out", "startup_failure"}


def classify_conclusion(c: str | None) -> str | None:
    """'success', 'failure' ou None (run ignorada no CFR e na recuperação)."""
    if c in SUCESSOS:
        return "success"
    if c in FALHAS:
        return "failure"
    return None


def cfr_ci(runs: list[dict]) -> float | None:
    """falhas / (falhas + sucessos) sobre todos os runs; None sem runs válidos."""
    classes = [classify_conclusion(run["conclusion"]) for run in runs]
    falhas = classes.count("failure")
    validos = falhas + classes.count("success")
    return falhas / validos if validos else None
