# Lab03 DORA – Backlog por Ondas (1 onda = 1 integrante)

> **Para IAs e devs:** este arquivo é o backlog oficial. Leia junto com `CLAUDE.md` e `docs/superpowers/plans/2026-10-05-lab03-dora-pipeline.md` (contratos, restrições globais, assinaturas das funções). Em conflito, vale o enunciado em `enunciado/`. As marcações "Dono: A/B/C" no plano antigo ficam **substituídas** pela divisão por ondas deste arquivo.
> **A, B e C** são os três integrantes (trocar pelos usuários do GitHub ao criar as Issues).

## Modelo de trabalho: ondas sequenciais, uma por integrante
- Cada sprint tem **3 ondas**. **Cada onda inteira pertence a um único integrante**, que faz tudo dela de uma vez. A onda seguinte só começa quando a anterior está **fechada** (todos os PRs mergeados, testes verdes no CI e nota de passagem escrita).
- O dono muda de uma sprint para outra (rodízio), para todos passarem pelas fundações e pela integração:

| Sprint | Onda 1 | Onda 2 | Onda 3 |
|---|---|---|---|
| S01 | **A** | **B** | **C** |
| S02 | **C** | **A** | **B** |
| S03 | **B** | **C** | **A** |
| Final | **A** | **B** | **C** |

- Como cada onda tem código, **todos os três commitam código em todas as sprints** (requisito de nota).
- **Nota de passagem (handoff):** ao fechar a onda, o dono comenta no último PR: funções/arquivos entregues (com assinaturas reais), decisões que mudaram contratos, e o que o próximo precisa saber. Se um contrato mudou, atualiza o plano no mesmo PR.
- **Quem espera não fica parado:** enquanto a onda do colega roda, os outros dois fazem (1) as Issues `tipo:docs` marcadas como "livres" (artigo/README, não bloqueiam nada), (2) **revisão cruzada** dos PRs da onda corrente (obrigatória: um PR só é mergeado com aprovação de outro integrante) e (3) fixtures de teste para a onda deles, escritas contra os contratos. Isso não conta como código da própria onda.
- **Exceção declarada:** a rotulagem manual da S02 é feita pelos três ao mesmo tempo, cada um no seu arquivo, dentro da Onda 2 (independência exigida pelo enunciado).

## Convenções
- **ID da Issue:** `S01-O2.3` = sprint 01, onda 2, tarefa 3. Docs livres: `S01-D1`… Portões de conferência: `S01-G1`…. O título da Issue começa com o ID; ao criar no GitHub ela vira `#N`, e **todo commit cita `#N`** (`feat(releases): ... (#N)`).
- **Branch:** `feat/N-slug`; 1 Issue = 1 branch = 1 PR curto. Assignee obrigatório; WIP máx. 1–2 por pessoa.
- **Labels:** `sprint-01…`, `onda-1…3`, `owner-A|B|C`, `tipo:codigo|dados|docs`. **Milestones:** Lab03S01, Lab03S02, Lab03S03, Entrega Final.
- **DoD de toda Issue de código:** testes passando no CI; cobertura de `metricas` ≥ 80%; PR aprovado por outro integrante; sem token, `cache/` ou dados brutos commitados.
- Assinaturas e fórmulas: ver plano `docs/superpowers/plans/2026-10-05-lab03-dora-pipeline.md` (Tasks T0–T9) e `CLAUDE.md`.

---

# LAB03S01 — Pipeline base (100 repos), testes, CI, hipóteses

```
Onda 1 (A)  Fundação: scaffold/CI → cache+HTTP → seleção → metadados+funil → classificação
   ↓
Onda 2 (B)  Coleta de entrega: releases → commits entre releases → lead time → runs mensais → etapa de releases
   ↓
Onda 3 (C)  Métricas de CI e integração: CFR(a) → recuperação → etapa de runs → orquestrador/CSV → cobertura 80% → execução real
   ↓
Portão S01-G  Conferência dos três
```

## Onda 1 — Fundação · dono: **A**
Ordem interna: O1.1 → O1.2 → (O1.3, O1.4, O1.5 em qualquer ordem). **O1.2 é o que mais bloqueia B e C: entregar uma versão mínima (`get`/`paginate`) logo, e o resto depois.**

### S01-O1.1 — Scaffold e CI `tipo:codigo`
- Arquivos: `requirements.txt`, `config.yaml` (janela placeholder até o professor fixar), `.gitignore` (`cache/`, `data/raw/`, `.env`), `.github/workflows/testes.yml`, `pipeline/__init__.py`, `metricas/__init__.py`, `tests/test_smoke.py`.
- Entrega: `pytest` verde no GitHub Actions. CI com `--cov-fail-under=0` até `S01-O3.5` subir para 80.
- Commit: `chore: scaffold e CI (#N)`.
### S01-O1.2 — Cache em disco e cliente HTTP `tipo:codigo`
- Depende de: O1.1. Arquivos: `pipeline/cache.py`, `pipeline/http.py`, `tests/test_http.py`.
- Entrega: `DiskCache`, `GitHubClient.get/paginate`, `NotFoundError`; 5xx com backoff 1,2,4,8s; espera por `X-RateLimit-Remaining/Reset`; paginação por `Link`; cache hit sem rede; testes com sessão fake.
- Commit: `feat(http): cliente com cache, rate limit e backoff (#N)`.
### S01-O1.3 — Seleção de candidatos e filtro de Actions `tipo:codigo`
- Depende de: O1.2. Arquivos: `pipeline/selecao.py`, `tests/test_selecao.py`.
- Entrega: `search_candidates` (faixas de estrelas, sem duplicatas, respeitando 1.000/consulta) e `uses_actions` (`total_count > 0`).
### S01-O1.4 — Metadados e funil de seleção `tipo:codigo`
- Depende de: O1.2. Arquivos: `pipeline/metadados.py`, `pipeline/funil.py`, `tests/test_metadados.py`.
- Entrega: `collect_metadata` (estrelas, linguagem, contributors via `Link` com `per_page=1&anon=true`, `created_at`, `default_branch`); `Funnel.add/to_dataframe` com `etapa,restantes,descartados,motivo`.
### S01-O1.5 — Classificação DORA `tipo:codigo`
- Depende de: O1.1. Arquivos: `metricas/classificacao.py`, `tests/test_classificacao.py`.
- Entrega: `score_deploy_freq`, `score_lead_time`, `score_cfr`, `score_recovery`, `overall`; testes nos limites das faixas; `overall([4,3,3,1])=="High"`.
- **Fechamento da onda:** nota de passagem com a assinatura real de `GitHubClient`.

## Onda 2 — Coleta de entrega · dono: **B** (começa quando a Onda 1 fecha)
Ordem interna: O2.1 → O2.2 → O2.3 → O2.4 → O2.5.

### S01-O2.1 — Coleta de releases `tipo:codigo`
- Arquivos: `pipeline/releases.py` (`fetch_releases`), `tests/test_releases.py`.
- Entrega: `draft=false`, ordenadas; pré-releases mantidas (`prerelease=True`, usadas na RQ07); inclui a release imediatamente anterior à janela; paginação.
### S01-O2.2 — Commits entre releases `tipo:codigo`
- Arquivos: `pipeline/releases.py` (`fetch_commit_dates`), testes.
- Entrega: `compare/{base}...{head}` paginado (`per_page/page`), datas `author.date`; 404 → `None` com registro/contagem; primeira release da história ignorada.
### S01-O2.3 — Lead time (a) e (b) `tipo:codigo`
- Arquivos: `metricas/lead_time.py`, `tests/test_lead_time.py`.
- Entrega: `lead_time_release_days`, `lead_time_commits_days`, `repo_lead_time_a`, `repo_lead_time_b`; teste do enunciado (v1.1 → 13 dias; [13,5,1]); lista vazia → `None`; release sem commits novos.
### S01-O2.4 — Coleta mensal de workflow runs `tipo:codigo`
- Arquivos: `pipeline/runs.py` (`fetch_runs`), `tests/test_runs.py`.
- Entrega: 12 consultas `branch=<default>&event=push&created=AAAA-MM-DD..AAAA-MM-DD`; meses com 1.000 resultados sinalizados; mapeamento para `Run`.
### S01-O2.5 — Etapa de releases para o orquestrador `tipo:codigo`
- Arquivos: `pipeline/etapa_releases.py` (`coletar_releases_e_lead_time(client, meta, janela)` → `n_releases`, `deploy_freq_week`, `lead_time_a_days`, `lead_time_b_days`, `compare_404`), teste com cliente fake.
- **Fechamento da onda:** nota de passagem com o formato real do retorno das etapas e dos `Run`.

## Onda 3 — Métricas de CI, integração e execução · dono: **C** (começa quando a Onda 2 fecha)
Ordem interna: O3.1 → O3.2 → O3.3 → O3.4 → O3.5 → O3.6.

### S01-O3.1 — CFR(a) por runs de CI `tipo:codigo`
- Arquivos: `metricas/cfr.py`, `tests/test_cfr.py`. Entrega: `classify_conclusion`, `cfr_ci`; 3 sucessos + 1 falha = 0,25; `cancelled/skipped/None` ignorados; sem runs válidos → `None`.
### S01-O3.2 — Tempo de recuperação com censura `tipo:codigo`
- Arquivos: `metricas/recuperacao.py`, `tests/test_recuperacao.py`. Entrega: `recovery_episodes`, `repo_recovery` (por workflow, depois mediana); tabela do enunciado → 1h20; falha nunca recuperada → censurada e contada; `cancelled` no meio não afeta.
### S01-O3.3 — Etapa de runs para o orquestrador `tipo:codigo`
- Arquivos: `pipeline/etapa_runs.py` (`coletar_runs_e_metricas(client, meta, janela)` → `n_runs_validos`, `cfr_ci`, `recovery_median_h`, `n_episodes`, `n_censored`, `meses_no_teto`), teste com cliente fake.
### S01-O3.4 — Orquestrador, funil e CSV `tipo:codigo`
- Arquivos: `pipeline/__main__.py`, `pipeline/orquestrador.py`, `tests/test_orquestrador.py`.
- Entrega: lê `config.yaml` → seleção → Actions → metadados → etapa de releases → etapa de runs → critério (≥5 releases e ≥50 runs válidos) → classificação → `data/funil.csv` e `data/metricas.csv` (colunas do plano T8). Teste com 3 repos fake (sem Actions / poucas releases / válido). `python -m pipeline --config config.yaml` roda do começo ao fim.
### S01-O3.5 — Restaurar cobertura 80% no CI `tipo:codigo`
- Arquivo: `.github/workflows/testes.yml` (`--cov-fail-under=80`); completar testes de `metricas/` se faltar cobertura.
### S01-O3.6 — Execução real (5 → 100 repos) `tipo:dados`
- Rodar com token real em 5 repos, depois nos 100; segunda execução deve usar cache. Anexar `data/funil.csv`. Problemas viram novas Issues (cada uma com dono e onda).

## Docs livres da S01 (não bloqueiam; feitas por quem está esperando)
- **S01-D1 (B, durante a Onda 1):** hipóteses informais de RQ03 e RQ05 em `artigo/introducao.md`, **antes de ver dados**; `README.md` seção Saídas + `data/DICIONARIO.md` (versão inicial das colunas do plano T8).
- **S01-D2 (C, durante a Onda 1):** hipóteses de RQ04 e RQ06 em `artigo/introducao.md`; seção Testes do `README.md` (rascunho).
- **S01-D3 (A, durante a Onda 2):** hipóteses de RQ01, RQ02 e RQ07; seções Pré-requisitos, Token, Instalação e Comando único do `README.md`.
- Revisão cruzada obrigatória de PRs também conta como tarefa de espera.

## Portão S01-G — Conferência (os três, curta, após a Onda 3)
- **S01-G1 (A):** confere metadados e funil de 2 repos contra a página do GitHub.
- **S01-G2 (B):** confere nº de releases e 1 lead time de 2 repos.
- **S01-G3 (C):** confere CFR e 1 episódio de recuperação de 2 repos no Actions.
- Divergências viram Issues com dono.

## Checklist de entrega S01
- [ ] Pipeline roda em 100 repos com um comando; funil gerado.
- [ ] Testes e CI verdes; cobertura de `metricas` ≥ 80%.
- [ ] A (Onda 1), B (Onda 2) e C (Onda 3) com commits de código atribuídos a Issues.
- [ ] Hipóteses RQ01–RQ07 em `artigo/introducao.md`; README executável.

---

# LAB03S02 — Amostra ≥ 300, métricas completas, validação manual, metodologia

```
Onda 1 (C)  Dados: coleta ≥300 → variantes (tags/pré-releases) → dataset + dicionário
   ↓
Onda 2 (A)  Validação humana: funções de concordância → planilhas → rotulagem dos 3 (paralela) → kappa e consenso
   ↓
Onda 3 (B)  Heurística e CFR(b): heurística v1 → avaliação F1 → refino ≥ 0,70 → CFR(b) → dataset final
```

## Onda 1 — Dados · dono: **C**
### S02-O1.1 — Coleta completa ≥ 300 repos `tipo:codigo`
- **Iniciar primeiro; roda em segundo plano horas.** Ajustes no pipeline (config para ≥ 300 válidos, `star_ranges` ampliadas), teste de retomada com `Ctrl+C`, `data/funil.csv` e `data/metricas.csv` com ≥ 300 repos. Correções em arquivos de A e B vão em PR pequeno avisando o autor original.
### S02-O1.2 — Variantes de deploy: tags e pré-releases `tipo:codigo`
- Arquivos: `pipeline/tags.py` (`fetch_tags`, data = commit apontado), `metricas/variantes.py` (`deploy_freq(unidade)` com `release | release+pre | tag`), testes.
### S02-O1.3 — Consolidação do dataset e dicionário `tipo:codigo`
- Arquivos: `pipeline/consolidar.py`, `data/DICIONARIO.md` (toda coluna: nome, tipo, unidade, fórmula/origem na API). `data/metricas.csv` com lead time a/b, CFR(a), recuperação, frequência por unidade.
- **Fechamento:** nota de passagem com o caminho do dataset e a lista de repositórios elegíveis para o sorteio.

## Onda 2 — Validação humana · dono: **A**
### S02-O2.1 — Funções de concordância e consenso `tipo:codigo`
- Arquivos: `validacao/concordancia.py`, `tests/test_concordancia.py`. `fleiss_kappa_dimensao` (`aggregate_raters` + `fleiss_kappa`), `consenso` por maioria simples, 1-1-1 marcado para reunião; fixtures sintéticas (concordância perfeita → 1,0).
### S02-O2.2 — Gerador das planilhas de rotulagem `tipo:codigo`
- Arquivo: `validacao/gerar_planilhas.py`. Sorteio de 60 repos com `df.sample(n=60, random_state=42)`, 5 releases sorteadas por repo, colunas: link direto da release, tipo do projeto, entregas reais (sim/não/incerto), corretiva (sim/não). **Sem** a saída da heurística. Gera 3 arquivos em branco.
### S02-O2.3 — Rotulagem independente (os três em paralelo) `tipo:dados`
- **A:** `rotulos/A.csv` · **B:** `rotulos/B.csv` · **C:** `rotulos/C.csv`. Cada um na sua Issue, sem consultar os outros e sem ver a heurística. Os três commits ficam atribuídos às suas Issues.
### S02-O2.4 — Kappa de Fleiss, consenso e protocolo `tipo:codigo`
- Arquivo: `validacao/consolidar.py`; saídas: kappa nas 3 dimensões, `rotulos/consenso.csv`, `docs/PROTOCOLO_DESEMPATE.md` (maioria simples; 1-1-1 decidido em reunião). Kappa baixo é achado para o artigo.
- **Fechamento:** nota de passagem com `rotulos/consenso.csv` pronto para B.

## Onda 3 — Heurística e CFR(b) · dono: **B**
### S02-O3.1 — Heurística de release corretiva v1 `tipo:codigo`
- Arquivos: `metricas/corretiva.py`, `tests/test_corretiva.py`. `eh_corretiva(...)` (bump só de patch semver e/ou commits `revert|hotfix|fix`); `HEURISTICA_VERSAO`; `2.3.0→2.3.1` com `fix:` → sim; `2.4.0→2.5.0` → não.
### S02-O3.2 — Avaliação contra o consenso `tipo:codigo`
- Arquivo: `validacao/avaliar_heuristica.py`. Precisão, recall e F1 (`precision_recall_fscore_support`) por versão; tabela `docs/HEURISTICA_VERSOES.md` com cada versão e o F1.
### S02-O3.3 — Refino até F1 ≥ 0,70 `tipo:codigo`
- Versões v2, v3… em `metricas/corretiva.py`, cada uma documentada. **Proibido** alterar o consenso para melhorar o F1.
### S02-O3.4 — CFR(b) `tipo:codigo`
- Arquivo: `metricas/cfr.py` (`cfr_entrega(releases, janela_fim)`): release falha se seguida em ≤ 7 dias por corretiva; releases dos últimos 7 dias da janela ficam fora do denominador e contam como censuradas; testes de borda.
### S02-O3.5 — Dataset final `tipo:codigo`
- Em `pipeline/consolidar.py` (PR avisando C): coluna `cfr_entrega`, `rework_rate` (para RQ08), `tipo_projeto` (do consenso, só nos 60 rotulados), regenerar `data/metricas.csv` e atualizar `data/DICIONARIO.md`.

## Docs livres da S02
- **S02-D1 (A, durante a Onda 1):** metodologia — fonte de dados, janela, funil, protocolo da amostra-ouro (`artigo/metodologia.md`).
- **S02-D2 (B, durante a Onda 1 e 2):** metodologia — definições operacionais e variantes; heurística (versões e F1 entram após a Onda 3).
- **S02-D3 (C, durante a Onda 3):** metodologia — pipeline, cache/retomada, rate limit, dicionário, censura; revisão final da seção.
- Revisão cruzada de PRs da onda corrente.

## Checklist de entrega S02
- [ ] ≥ 300 repos com todas as métricas e variantes; CSV + `DICIONARIO.md`.
- [ ] 3 arquivos de rótulos; kappa de Fleiss por dimensão; consenso e protocolo registrados.
- [ ] Heurística com F1 ≥ 0,70 (ou justificativa) e histórico de versões.
- [ ] Metodologia completa; C, A e B com commits de código atribuídos.

---

# LAB03S03 — Análise RQ01–RQ07 (RQ08 opcional)

Todas as análises leem **apenas** `data/metricas.csv`; um script reexecutável por análise em `analise/`.
```
Onda 1 (B)  Base descritiva: utilitários estatísticos → RQ01–RQ04 → classificação C1
   ↓
Onda 2 (C)  Relações: RQ05 (Spearman) → RQ06 (fatores, testes, Holm, tamanho de efeito)
   ↓
Onda 3 (A)  Robustez: RQ07 (sensibilidade) → RQ08 opcional → preparar repo para replicação
```

## Onda 1 — Base descritiva · dono: **B**
### S03-O1.1 — Utilitários estatísticos `tipo:codigo`
- Arquivos: `analise/estatistica.py`, `tests/test_estatistica.py`. `mediana_iqr`, `cliffs_delta(U, n1, n2)`, `epsilon_quadrado(H, n)`, `quartis_grupos`; valores calculados à mão.
### S03-O1.2 — RQ01 a RQ04 `tipo:codigo`
- Arquivo: `analise/rq01_rq04.py`. Mediana e IQR de frequência, lead time (a/b), CFR (a/b) e recuperação; proporção de censurados; tabelas e gráficos em `analise/saida/`.
### S03-O1.3 — Classificação DORA de referência (C1) `tipo:codigo`
- Arquivo: `analise/classificacao_c1.py` (usa `metricas/classificacao.py`): categoria por métrica e geral; distribuição Elite/High/Medium/Low. C1 = release / lead time (a) / CFR (a); grava `analise/saida/classificacao_c1.csv` para a RQ07.
- **Fechamento:** nota de passagem com os nomes das colunas e dos utilitários.

## Onda 2 — Relações · dono: **C**
### S03-O2.1 — RQ05: Spearman `tipo:codigo`
- Arquivo: `analise/rq05.py`. `spearmanr` entre frequência e CFR (a) e (b): ρ, p, n; dispersão com eixo log quando preciso.
### S03-O2.2 — RQ06: fatores, testes, Holm e tamanho de efeito `tipo:codigo`
- Arquivo: `analise/rq06.py`. ≥ 3 fatores (linguagem, estrelas, contribuidores, idade em quartis; tipo de projeto); Kruskal-Wallis (ε² = H/(n−1)) ou Mann-Whitney (Cliff's δ = 2·U₁/(n₁·n₂) − 1); `multipletests(method='holm')`; tabela com p ajustado e efeito.
- **Fechamento:** nota de passagem.

## Onda 3 — Robustez · dono: **A**
### S03-O3.1 — RQ07: sensibilidade `tipo:codigo`
- Arquivo: `analise/rq07.py`. ≥ 3 combinações (C1 release/a/a; C2 release+pré/b/b; C3 tag/b/a), classificação por repo, % que mudou de categoria e `cohen_kappa_score(weights='linear')` para C1×C2, C1×C3, C2×C3. Usa `metricas/variantes.py` (S02) e `classificacao_c1.csv`.
### S03-O3.2 — RQ08 bônus (opcional, +1 ponto) `tipo:codigo`
- Rework rate **ou** Mann-Kendall trimestral (`pymannkendall`). Arquivo: `analise/rq08.py`.
### S03-O3.3 — Preparar o repositório para replicação (pré-requisito da Entrega Final) `tipo:codigo`
- `config.subamostra30.yaml` (30 repos do dataset), versões fixadas em `requirements.txt`, README testado em ambiente limpo, dataset publicado em `data/`.

## Docs livres da S03
- **S03-D1 (B, durante a Onda 2):** Resultados RQ01–RQ04 (compara hipótese × resultado; explica a divergência lead time (a) vs (b)) em `artigo/resultados.md`.
- **S03-D2 (C, durante a Onda 3):** Resultados RQ05 e RQ06 (velocidade × estabilidade vs. DORA; correlação ≠ causalidade).
- **S03-D3 (A, após a Onda 3):** Resultados RQ07 e `artigo/discussao.md` (o que surpreendeu; as conclusões são robustas à definição?).

## Checklist de entrega S03
- [ ] RQ01–RQ07 reexecutáveis a partir do CSV; mediana e IQR em tudo.
- [ ] Holm e tamanhos de efeito (RQ06); kappa ponderado (RQ07).
- [ ] Resultados e Discussão no artigo; B, C e A com commits de código.

---

# ENTREGA FINAL — Replicação cruzada e artigo completo

```
Onda 1 (A)  Executar o pipeline do outro grupo (só README, 30 repos)
   ↓
Onda 2 (B)  Comparar com o CSV original e abrir Issues no repo do outro grupo
   ↓
Onda 3 (C)  Tratar Issues recebidas e fechar o artigo
```
Pré-requisito: `S03-O3.3` concluída antes de outro grupo nos replicar.

## Onda 1 — Executar · dono: **A**
### F-O1.1 — Script e execução da replicação `tipo:codigo`
- `replicacao/rodar_subamostra.sh` (ou `.ps1`) e execução em 30 repos usando **apenas** o README do outro grupo; sem pedir ajuda ao grupo autor.
### F-O1.2 — Relatório de execução `tipo:docs`
- `replicacao/executar.md`: cada tropeço com comando, erro e versão. Se travar, isso é resultado.

## Onda 2 — Comparar · dono: **B**
### F-O2.1 — Script de comparação `tipo:codigo`
- `replicacao/comparar.py`, `tests/test_comparar.py`: diferença relativa por métrica e % de repositórios com a mesma classificação DORA.
### F-O2.2 — Issues no repositório do grupo autor `tipo:docs`
- Uma Issue por problema (execução, documentação faltante, divergência) com comando, erro, esperado × obtido.

## Onda 3 — Responder e fechar · dono: **C**
### F-O3.1 — Tratar Issues recebidas `tipo:codigo`
- Para cada Issue do grupo replicador: corrigir o pipeline (commits citando a Issue) ou justificar por escrito; adicionar todas ao GitHub Projects.
### F-O3.2 — Revisão final do artigo `tipo:docs`
- Consolidar no template SBC (≤ 10 páginas), com link do repositório/Projects.

## Docs livres da Entrega Final
- **F-D1 (A, durante a Onda 2):** Ameaças à validade — construto e interna, apoiadas em kappa, F1 e RQ07 (`artigo/ameacas.md`).
- **F-D2 (B, após a Onda 2):** `artigo/replicacao.md`.
- **F-D3 (C, durante a Onda 3):** Ameaças — externa e de conclusão.

## Checklist de entrega final
- [ ] Replicação executada e comparada; Issues abertas com evidências.
- [ ] Issues recebidas respondidas até o prazo.
- [ ] Artigo completo (ameaças + replicação), ≤ 10 páginas, com link do GitHub Projects.

---

## Conferência: código por integrante em cada sprint
| Sprint | A | B | C |
|---|---|---|---|
| S01 | Onda 1 (O1.1–O1.5) | Onda 2 (O2.1–O2.5) | Onda 3 (O3.1–O3.5) |
| S02 | Onda 2 (O2.1, O2.2, O2.4) | Onda 3 (O3.1–O3.5) | Onda 1 (O1.1–O1.3) |
| S03 | Onda 3 (O3.1–O3.3) | Onda 1 (O1.1–O1.3) | Onda 2 (O2.1, O2.2) |
| Final | Onda 1 (F-O1.1) | Onda 2 (F-O2.1) | Onda 3 (F-O3.1) |

## Riscos do modelo "uma onda por integrante"
- **Tempo ocioso:** quem espera tem docs livres, revisão e fixtures. Não deixar a Onda 1 de cada sprint atrasar: ela libera os outros dois.
- **Gargalo na S01-O1.2 (HTTP):** entregar a versão mínima primeiro; B e C podem começar fixtures e testes dos módulos puros (`lead_time`, `cfr`, `recuperacao`) em seus branches antes da vez, **mas só mergeiam na sua onda**.
- **Reentrada:** se uma onda estourar, as seguintes escorregam; priorizar pedir ajuda em PR pequeno em vez de acumular.
- **Prazos reais:** as ondas são sequenciais; dividir os dias da sprint em três blocos aproximadamente iguais (A, B, C) e reservar o último bloco para o portão de conferência.
