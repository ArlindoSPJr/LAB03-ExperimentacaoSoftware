"""Classificação DORA de um repositório pelos cortes fixos do enunciado (seção RQ 07).

Funções puras: recebem as métricas já calculadas e devolvem notas
(4 Elite, 3 High, 2 Medium, 1 Low). Não leem nem gravam arquivo.

Unidades: frequência em releases por semana; lead time em dias;
CFR em fração de 0 a 1; tempo de recuperação em horas.
"""

# "1 por mês" expresso em releases por semana (52,14 semanas / 12 meses ≈ 4,345).
UMA_POR_MES_POR_SEMANA = 1 / 4.345


def score_deploy_freq(per_week: float) -> int:
    """Elite >= 7/sem; High >= 1/sem; Medium >= 1/mês; Low < 1/mês."""
    if per_week >= 7:
        return 4
    if per_week >= 1:
        return 3
    if per_week >= UMA_POR_MES_POR_SEMANA:
        return 2
    return 1


def score_lead_time(days: float) -> int:
    """Elite < 1 dia; High < 7 dias; Medium < 30 dias; Low >= 30 dias."""
    if days < 1:
        return 4
    if days < 7:
        return 3
    if days < 30:
        return 2
    return 1
