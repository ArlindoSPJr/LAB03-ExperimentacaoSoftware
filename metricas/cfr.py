"""Change failure rate (RQ03), variante (a): proxy de CI por workflow runs.

Tabela de `conclusion` do enunciado (seção 3): `success` é sucesso;
`failure`, `timed_out` e `startup_failure` são falha; qualquer outro valor
(`cancelled`, `skipped`, `neutral`, `action_required`, `stale`, vazio) é ignorado.

Variante (b), `cfr_entrega`: release seguida em até 7 dias por uma release corretiva.
"""
from datetime import datetime, timedelta

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


JANELA_CORRECAO = timedelta(days=7)


def cfr_entrega(releases: list[dict], janela_fim: datetime) -> dict:
    """CFR (b): fração de releases seguidas em até 7 dias por uma release corretiva.

    `releases` tem `published_at` e `corretiva` (bool, da heurística). A release R falhou se
    a próxima release, publicada até 7 dias depois de R, é corretiva. Releases dos últimos
    7 dias da janela ficam fora do denominador e são contadas como censuradas (ainda não se
    sabe se haverá correção). Com `release+pre`, o chamador inclui as pré-releases.
    """
    ordenadas = sorted(releases, key=lambda r: r["published_at"])
    limite = janela_fim - JANELA_CORRECAO
    falhas = avaliadas = censuradas = 0
    for i, release in enumerate(ordenadas):
        if release["published_at"] > limite:
            censuradas += 1
            continue
        avaliadas += 1
        proxima = ordenadas[i + 1] if i + 1 < len(ordenadas) else None
        if (proxima is not None and proxima["corretiva"]
                and proxima["published_at"] - release["published_at"] <= JANELA_CORRECAO):
            falhas += 1
    return {"cfr": falhas / avaliadas if avaliadas else None, "falhas": falhas,
            "avaliadas": avaliadas, "censuradas": censuradas}
