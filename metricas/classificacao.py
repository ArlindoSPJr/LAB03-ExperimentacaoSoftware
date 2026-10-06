"""Classificação DORA de um repositório pelos cortes fixos do enunciado (seção RQ 07).

Funções puras: recebem as métricas já calculadas e devolvem notas
(4 Elite, 3 High, 2 Medium, 1 Low). Não leem nem gravam arquivo.

Unidades: frequência em releases por semana; lead time em dias;
CFR em fração de 0 a 1; tempo de recuperação em horas.
"""

import math
import statistics

# "1 por mês" expresso em releases por semana (52,14 semanas / 12 meses ≈ 4,345).
UMA_POR_MES_POR_SEMANA = 1 / 4.345

CATEGORIAS = {4: "Elite", 3: "High", 2: "Medium", 1: "Low"}

CHAVES = ("score_freq", "score_lead", "score_cfr", "score_rec", "dora_overall")


def _eh_nan(valor) -> bool:
    return isinstance(valor, float) and math.isnan(valor)


def _exigir_numero(valor) -> None:
    # Toda comparação com NaN é falsa: sem esta guarda, NaN cairia em Low.
    if _eh_nan(valor):
        raise ValueError("métrica NaN não pode ser classificada")


def score_deploy_freq(per_week: float) -> int:
    """Elite >= 7/sem; High >= 1/sem; Medium >= 1/mês; Low < 1/mês."""
    _exigir_numero(per_week)
    if per_week >= 7:
        return 4
    if per_week >= 1:
        return 3
    if per_week >= UMA_POR_MES_POR_SEMANA:
        return 2
    return 1


def score_lead_time(days: float) -> int:
    """Elite < 1 dia; High < 7 dias; Medium < 30 dias; Low >= 30 dias."""
    _exigir_numero(days)
    if days < 1:
        return 4
    if days < 7:
        return 3
    if days < 30:
        return 2
    return 1


def score_cfr(rate: float) -> int:
    """Elite <= 15%; High <= 30%; Medium <= 45%; Low > 45% (rate em fração 0-1)."""
    _exigir_numero(rate)
    if rate <= 0.15:
        return 4
    if rate <= 0.30:
        return 3
    if rate <= 0.45:
        return 2
    return 1


def score_recovery(hours: float) -> int:
    """Elite < 1 h; High < 24 h; Medium < 168 h (1 semana); Low >= 168 h."""
    _exigir_numero(hours)
    if hours < 1:
        return 4
    if hours < 24:
        return 3
    if hours < 168:
        return 2
    return 1


def overall(scores: list[int]) -> str:
    """Categoria geral: mediana das notas arredondada para baixo (enunciado, RQ 07)."""
    return CATEGORIAS[math.floor(statistics.median(scores))]


def classificar_repositorio(deploy_freq_week, lead_time_a_days, cfr_ci, recovery_median_h) -> dict:
    """Notas por métrica e categoria geral de um repositório (variantes C1).

    Regra de métrica ausente (decisão 1 de docs/ISSUES.md, a confirmar com o grupo):
    se qualquer métrica for None (ou NaN), o repositório não é classificado e as
    5 chaves voltam None.
    """
    metricas = (deploy_freq_week, lead_time_a_days, cfr_ci, recovery_median_h)
    if any(m is None or _eh_nan(m) for m in metricas):
        return dict.fromkeys(CHAVES)
    notas = {
        "score_freq": score_deploy_freq(deploy_freq_week),
        "score_lead": score_lead_time(lead_time_a_days),
        "score_cfr": score_cfr(cfr_ci),
        "score_rec": score_recovery(recovery_median_h),
    }
    notas["dora_overall"] = overall(list(notas.values()))
    return notas
