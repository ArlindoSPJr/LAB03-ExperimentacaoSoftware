"""Lead time for changes (RQ02), em dias, nas variantes (a) por release e (b) por commit.

Funções puras: recebem a data da release e as datas (`commit.author.date`) dos
commits incluídos nela, obtidos pelo `compare` com a release anterior.

Decisão 4 de docs/ISSUES.md: commit com data posterior à release (rebase/squash)
daria lead time negativo; o valor é descartado e contado em `n_lead_negativos`.
"""

import statistics
from datetime import datetime

SEGUNDOS_POR_DIA = 86400


def _dias(release_date: datetime, commit_date: datetime) -> float:
    return (release_date - commit_date).total_seconds() / SEGUNDOS_POR_DIA


def lead_time_commits_days(release_date: datetime, commit_dates: list[datetime]) -> list[float]:
    """Variante (b): lead time de cada commit da release, sem os negativos."""
    valores = (_dias(release_date, data) for data in commit_dates)
    return [valor for valor in valores if valor >= 0]


def lead_time_release_days(release_date: datetime, commit_dates: list[datetime]) -> float | None:
    """Variante (a): data da release − commit mais antigo; None sem commits válidos."""
    valores = lead_time_commits_days(release_date, commit_dates)
    return max(valores) if valores else None


def contar_lead_negativos(release_date: datetime, commit_dates: list[datetime]) -> int:
    """Commits descartados por terem data posterior à release."""
    return sum(1 for data in commit_dates if data > release_date)


def repo_lead_time_a(per_release: list[float | None]) -> float | None:
    """Mediana do lead time (a) entre as releases do repositório, ignorando None."""
    valores = [valor for valor in per_release if valor is not None]
    return statistics.median(valores) if valores else None


def repo_lead_time_b(all_commit_values: list[float]) -> float | None:
    """Mediana do lead time (b) de todos os commits de todas as releases."""
    return statistics.median(all_commit_values) if all_commit_values else None
