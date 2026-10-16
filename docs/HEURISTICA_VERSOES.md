# Versões da heurística de release corretiva

Avaliação contra `rotulos/consenso.csv` (300 releases da amostra-ouro; classe positiva `sim`),
gerada por `python -m validacao.avaliar_heuristica`. O consenso não é alterado entre versões.

| Versão | Regra | n | Precisão | Recall | F1 | Data |
|---|---|---:|---:|---:|---:|---|
| v1 | bump só de patch semver **ou** commit com `revert`/`hotfix`/`fix` desde a release anterior | 300 | 0,402 | 1,000 | 0,574 | 2026-10-16 |

A v1 é a regra literal do enunciado. Quase toda release tem algum commit com "fix", então a
heurística marca corretiva demais (precisão baixa, recall total). Meta: F1 ≥ 0,70 (S02-O3.3).
