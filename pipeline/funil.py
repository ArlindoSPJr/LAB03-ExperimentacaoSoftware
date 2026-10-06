"""Funil de seleção: quantos repositórios restam em cada etapa e por que os demais saíram."""
from __future__ import annotations

import pandas as pd

COLUMNS = ["etapa", "restantes", "descartados", "motivo"]


class Funnel:
    def __init__(self):
        self._rows: list[dict] = []

    def add(self, stage: str, remaining: int, reason: str = "") -> None:
        """Registra uma etapa; descartados = restantes da etapa anterior - restantes atuais (0 na primeira)."""
        previous = self._rows[-1]["restantes"] if self._rows else remaining
        self._rows.append({
            "etapa": stage,
            "restantes": remaining,
            "descartados": previous - remaining,
            "motivo": reason,
        })

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self._rows, columns=COLUMNS)
