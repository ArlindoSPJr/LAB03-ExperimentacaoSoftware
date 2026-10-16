# Versões da heurística de release corretiva

Avaliação contra `rotulos/consenso.csv` (300 releases da amostra-ouro; classe positiva `sim`),
gerada por `python -m validacao.avaliar_heuristica --versao <v>`. O consenso não é alterado
entre versões. A versão vigente é a de `HEURISTICA_VERSAO` em `metricas/corretiva.py`.

| Versão | Regra | n | Precisão | Recall | F1 | Data |
|---|---|---:|---:|---:|---:|---|
| v1 | bump só de patch semver **ou** commit com `revert`/`hotfix`/`fix` desde a release anterior | 300 | 0,402 | 1,000 | 0,574 | 2026-10-16 |
| v2 | a própria tag é de patch (`x.y.z` com `z > 0`), sem comparar com a release anterior | 300 | 0,544 | 0,974 | 0,698 | 2026-10-16 |
| **v3** (vigente) | tag de patch **e** (nenhum commit de funcionalidade **ou** ao menos metade dos commits com `revert`/`hotfix`/`fix`), ignorando commits de CI, docs, manutenção, dependências e merges | 300 | 0,684 | 0,791 | **0,734** | 2026-10-16 |

## Notas por versão

- **v1:** regra literal do enunciado. Quase toda release tem algum commit com "fix", então a
  heurística marca corretiva demais (precisão baixa, recall total).
- **v2:** comparar com a release anterior por data falha em projetos que publicam patches de
  várias linhas ao mesmo tempo (backports): `v8.19.6` publicada depois de `v9.2.0` parece um
  bump de major. Olhar só a própria tag resolve esses casos.
- **v3:** entre as tags de patch, separa as que trazem funcionalidades novas. Considera só a
  primeira linha de cada commit; commits `ci:`, `docs:`, `chore:`, `test:`, `build:`, `style:`,
  bumps de dependência e merges são ignorados. Funcionalidade é `feat:`/`feat(...)` ou título
  iniciado por "add", "added", "implement", "new" ou "support". Atinge a meta (F1 ≥ 0,70).

As regras usam só versionamento semântico e convenções de mensagem de commit, sem casos
específicos de repositório. Ainda assim, foram ajustadas e avaliadas na mesma amostra de 300
releases, o que tende a superestimar o F1 (ameaça à validade a registrar no artigo).
