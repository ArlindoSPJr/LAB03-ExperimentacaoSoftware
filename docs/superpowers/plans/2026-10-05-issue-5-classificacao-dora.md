# Issue #5 (S01-O1.5) — Classificação DORA: plano de implementação

> **Para agentes:** execução inline com `superpowers:executing-plans` + `superpowers:test-driven-development`. Passos em checkbox (`- [ ]`).

**Goal:** Converter as 4 métricas DORA de um repositório (variantes de referência C1) em notas 4/3/2/1 e na categoria geral Elite/High/Medium/Low, pelos cortes fixos do enunciado.

**Architecture:** Um único módulo puro, `metricas/classificacao.py` (sem rede, sem arquivo). Quatro funções de nota por métrica, `overall` (mediana arredondada para baixo) e `classificar_repositorio`, que o orquestrador (`S01-O3.4`) chama uma vez por repositório.

**Tech Stack:** Python 3.12 (stdlib: `math`, `statistics`), pytest, pytest-cov.

**Spec:** Issue #5; `docs/ISSUES.md` (S01-O1.5 e Decisão 1); `docs/superpowers/plans/2026-10-05-lab03-dora-pipeline.md` (Task 4); `enunciado/03 - Mineração de Métricas DORA.md`, seção RQ 07 (tabela de referência).

**Modo do plano:** completo, porque a Issue toca a "Decisão a confirmar com o grupo" nº 1 (métrica ausente). A regra já está especificada na Issue (qualquer métrica `None` → as 5 chaves `None`) e é implementada como está; continua pendente de confirmação do grupo (registrar no PR).

## Global Constraints
- Arquivos: só `metricas/classificacao.py` e `tests/test_classificacao.py`.
- Unidades: frequência em releases **por semana**; lead time em **dias**; CFR em **fração 0–1**; recuperação em **horas**.
- Cortes (enunciado, RQ 07):
  - Frequência: Elite ≥ 7/sem; High ≥ 1 e < 7; Medium ≥ 1 por mês e < 1/sem; Low < 1 por mês. "1 por mês" = `1/4.345` por semana (52,14 sem ÷ 12).
  - Lead time: Elite < 1 dia; High 1 a < 7; Medium 7 a < 30; Low ≥ 30.
  - CFR: Elite ≤ 0,15; High > 0,15 e ≤ 0,30; Medium > 0,30 e ≤ 0,45; Low > 0,45.
  - Recuperação: Elite < 1 h; High 1 h a < 24 h; Medium 24 h a < 168 h; Low ≥ 168 h.
- Geral: 4/3/2/1 pontos; mediana das 4 notas **arredondada para baixo**; 4 Elite, 3 High, 2 Medium, 1 Low.
- `classificar_repositorio` não lê nem grava arquivo.

## Contrato (nomes públicos exatos)
```python
def score_deploy_freq(per_week: float) -> int
def score_lead_time(days: float) -> int
def score_cfr(rate: float) -> int
def score_recovery(hours: float) -> int
def overall(scores: list[int]) -> str          # "Elite" | "High" | "Medium" | "Low"
def classificar_repositorio(deploy_freq_week, lead_time_a_days, cfr_ci, recovery_median_h) -> dict
    # {"score_freq", "score_lead", "score_cfr", "score_rec", "dora_overall"}; qualquer métrica None -> as 5 None
```

## Review Focus
1. Valor exatamente no corte (7/sem, 1 dia, 0,15, 24 h…) → cai na faixa que o enunciado indica (≥ ou ≤ inclusivo conforme a tabela); testar os dois lados de cada corte.
2. "1 por mês" com a frequência da RQ01 (releases ÷ 52,1 sem): 12 releases na janela → Medium; 11 → Low.
3. Mediana de número par de notas com empate no meio (`[4,4,1,1]` = 2,5) → arredonda para baixo (Medium), nunca para cima.
4. Métrica `NaN` (vinda de pandas no orquestrador) → tratada como ausente em `classificar_repositorio` (as 5 chaves `None`), em vez de cair silenciosamente em Low porque toda comparação com NaN é falsa. As funções `score_*` levantam `ValueError` com NaN.
5. Valor zero (0 releases/sem, CFR 0, lead time 0) → classificado normalmente (Low, Elite, Elite), sem ser confundido com ausente.

---

### Task 1: `score_deploy_freq`
**Files:** Create `metricas/classificacao.py`; Test `tests/test_classificacao.py`
**Produces:** `score_deploy_freq(per_week: float) -> int`, constante `UMA_POR_MES_POR_SEMANA = 1 / 4.345`.

- [ ] Teste (falha com ImportError):
```python
import math
import pytest
from metricas.classificacao import UMA_POR_MES_POR_SEMANA, score_deploy_freq

@pytest.mark.parametrize("per_week, esperado", [
    (7, 4), (30, 4), (6.99, 3), (1, 3), (0.99, 2),
    (UMA_POR_MES_POR_SEMANA, 2), (UMA_POR_MES_POR_SEMANA - 1e-9, 1), (0, 1),
])
def test_score_deploy_freq_limites(per_week, esperado):
    assert score_deploy_freq(per_week) == esperado

def test_score_deploy_freq_um_por_mes_na_janela_da_rq01():
    assert score_deploy_freq(12 / 52.1) == 2
    assert score_deploy_freq(11 / 52.1) == 1
```
- [ ] Rodar `pytest tests/test_classificacao.py -v` → FAIL (módulo não existe).
- [ ] Implementar:
```python
UMA_POR_MES_POR_SEMANA = 1 / 4.345

def score_deploy_freq(per_week: float) -> int:
    if per_week >= 7:
        return 4
    if per_week >= 1:
        return 3
    if per_week >= UMA_POR_MES_POR_SEMANA:
        return 2
    return 1
```
- [ ] Rodar → PASS. Commit: `feat(metricas): nota de deployment frequency (#5)`.

### Task 2: `score_lead_time`
- [ ] Teste:
```python
@pytest.mark.parametrize("days, esperado", [
    (0, 4), (0.99, 4), (1, 3), (6.99, 3), (7, 2), (29.99, 2), (30, 1), (400, 1),
])
def test_score_lead_time_limites(days, esperado):
    assert score_lead_time(days) == esperado
```
- [ ] FAIL (ImportError) → implementar `<1:4, <7:3, <30:2, senão 1` → PASS. Commit: `feat(metricas): nota de lead time (#5)`.

### Task 3: `score_cfr`
- [ ] Teste:
```python
@pytest.mark.parametrize("rate, esperado", [
    (0, 4), (0.15, 4), (0.1501, 3), (0.30, 3), (0.3001, 2), (0.45, 2), (0.4501, 1), (1, 1),
])
def test_score_cfr_limites(rate, esperado):
    assert score_cfr(rate) == esperado
```
- [ ] FAIL → implementar `<=.15:4, <=.30:3, <=.45:2, senão 1` → PASS. Commit: `feat(metricas): nota de change failure rate (#5)`.

### Task 4: `score_recovery`
- [ ] Teste:
```python
@pytest.mark.parametrize("hours, esperado", [
    (0, 4), (0.99, 4), (1, 3), (23.99, 3), (24, 2), (167.99, 2), (168, 1), (1000, 1),
])
def test_score_recovery_limites(hours, esperado):
    assert score_recovery(hours) == esperado
```
- [ ] FAIL → implementar `<1:4, <24:3, <168:2, senão 1` → PASS. Commit: `feat(metricas): nota de tempo de recuperação (#5)`.

### Task 5: `overall`
- [ ] Teste:
```python
@pytest.mark.parametrize("scores, esperado", [
    ([4, 3, 3, 1], "High"),      # exemplo do enunciado
    ([4, 4, 1, 1], "Medium"),    # mediana 2,5 -> 2
    ([4, 4, 4, 4], "Elite"), ([1, 1, 1, 1], "Low"),
    ([4, 4, 3, 1], "High"),      # mediana 3,5 -> 3
    ([2, 1, 1, 4], "Low"),       # mediana 1,5 -> 1 (ordem não importa)
])
def test_overall(scores, esperado):
    assert overall(scores) == esperado
```
- [ ] FAIL → implementar:
```python
CATEGORIAS = {4: "Elite", 3: "High", 2: "Medium", 1: "Low"}

def overall(scores: list[int]) -> str:
    return CATEGORIAS[math.floor(statistics.median(scores))]
```
- [ ] PASS. Commit: `feat(metricas): categoria geral pela mediana arredondada para baixo (#5)`.

### Task 6: `classificar_repositorio` e métrica ausente
- [ ] Testes:
```python
def test_classificar_repositorio_completo():
    assert classificar_repositorio(2.0, 3.0, 0.20, 30.0) == {
        "score_freq": 3, "score_lead": 3, "score_cfr": 3, "score_rec": 2, "dora_overall": "High",
    }

def test_classificar_repositorio_exemplo_mediana_par():
    r = classificar_repositorio(10.0, 0.5, 0.5, 200.0)   # 4, 4, 1, 1
    assert r["dora_overall"] == "Medium"

NENHUMA = {"score_freq": None, "score_lead": None, "score_cfr": None, "score_rec": None, "dora_overall": None}

@pytest.mark.parametrize("args", [
    (None, 3.0, 0.2, 30.0), (2.0, None, 0.2, 30.0), (2.0, 3.0, None, 30.0),
    (2.0, 3.0, 0.2, None), (None, None, None, None),
    (2.0, 3.0, float("nan"), 30.0),
])
def test_classificar_repositorio_metrica_ausente(args):
    assert classificar_repositorio(*args) == NENHUMA

def test_classificar_repositorio_zeros_nao_sao_ausentes():
    assert classificar_repositorio(0.0, 0.0, 0.0, 0.0)["score_freq"] == 1

@pytest.mark.parametrize("func", [score_deploy_freq, score_lead_time, score_cfr, score_recovery])
def test_score_rejeita_nan(func):
    with pytest.raises(ValueError):
        func(float("nan"))
```
- [ ] FAIL → implementar (e chamar `_exigir_numero(valor)` no início de cada `score_*`):
```python
CHAVES = ("score_freq", "score_lead", "score_cfr", "score_rec", "dora_overall")

def _eh_nan(valor) -> bool:
    return isinstance(valor, float) and math.isnan(valor)

def _exigir_numero(valor) -> None:
    if _eh_nan(valor):
        raise ValueError("métrica NaN não pode ser classificada")

def classificar_repositorio(deploy_freq_week, lead_time_a_days, cfr_ci, recovery_median_h) -> dict:
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
```
- [ ] PASS. Commit: `feat(metricas): classificar_repositorio com regra de métrica ausente (#5)`.

### Fechamento
- [ ] `pytest --cov=metricas --cov-report=term-missing` → tudo verde, `metricas/classificacao.py` 100%.
- [ ] Conferir `git status` sem `__pycache__`/`.pyc`.
