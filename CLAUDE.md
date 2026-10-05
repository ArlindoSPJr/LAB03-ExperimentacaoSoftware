# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Estado atual do repositório

Ainda **não há código**: o repositório contém apenas o enunciado em `enunciado/03 - Mineração de Métricas DORA.md` (em português, fonte de verdade — releia-o antes de decidir qualquer definição). Não existem comandos de build/lint/teste ainda; os comandos abaixo são os exigidos pelo enunciado e devem ser criados.

Projeto: Lab03 de Laboratório de Experimentação de Software (Engenharia de Software). Pipeline que **minera métricas DORA** de repositórios open-source do GitHub (que usam GitHub Actions) e gera um artigo (template SBC, ≤ 10 páginas). Trabalho em trio, dividido em sprints S01 (100 repos), S02 (≥ 300 repos + validação manual), S03 (análise estatística RQ01–07) e entrega final (replicação cruzada).

**Antes de implementar qualquer tarefa, leia:**
- `docs/ISSUES.md`: fonte de verdade de **donos (A/B/C), ondas, dependências, escopo das Issues e decisões em aberto**. Siga o ID e o "Depende de" da Issue correspondente.
- `docs/superpowers/plans/2026-10-05-lab03-dora-pipeline.md`: contratos entre módulos, restrições globais, regras de colaboração e detalhes técnicos das tarefas da S01.

## Restrições obrigatórias

- **Proibido** usar bibliotecas prontas de acesso à API do GitHub (ex.: PyGithub). Coleta via script próprio com REST e/ou GraphQL (`requests`/`httpx` direto). Pandas, SciPy, statsmodels, scikit-learn, pymannkendall são permitidos.
- Execução com **um único comando** (ex.: `python -m pipeline --config config.yaml`); token lido de `GITHUB_TOKEN`, nunca commitado.
- **Cache em disco + retomada**: cada resposta da API é persistida (JSON por repo/endpoint ou SQLite); reexecutar continua de onde parou sem repetir chamadas.
- Rate limit: ler `X-RateLimit-Remaining`/`X-RateLimit-Reset` e pausar sozinho; 5xx com backoff exponencial (1s, 2s, 4s, 8s…, com limite). Paginação via cabeçalho `Link rel="next"`.
- Testes com pytest + fixtures artesanais (usar os exemplos numéricos do enunciado), incluindo casos de borda: release sem commits novos, falha nunca recuperada (censurada), repo com uma única release, runs `cancelled` ignoradas. Cobertura ≥ 80% do módulo de métricas:
  - `pytest --cov=metricas --cov-report=term-missing`
  - um teste só: `pytest tests/test_x.py::test_nome`
  - o módulo de métricas deve se chamar `metricas` (o CI do enunciado usa `--cov=metricas --cov-fail-under=80`).
- CI do próprio grupo em `.github/workflows/testes.yml` (Python 3.12, `pip install -r requirements.txt`, pytest com cobertura).
- Saídas obrigatórias: **funil de seleção** gerado automaticamente (candidatos → com Actions → ≥5 releases e ≥50 runs → amostra final) e **dicionário de dados** (nome, tipo, unidade, fórmula/origem) para cada coluna dos CSVs finais.
- Commits devem **referenciar o número da Issue** correspondente (a correção é feita via GitHub Projects; commits sem Issue não contam). Cada integrante precisa de commits de código em cada sprint.

## Definições operacionais (iguais para toda a turma)

- Janela de 12 meses (datas fixadas pelo professor); só releases/runs criados dentro dela.
- Apenas o **default branch** (`default_branch` da API).
- **Deploy** = release publicada (`draft=false`); `prerelease` e tags sem release só como variantes na RQ07.
- Data do commit = `commit.author.date`.
- CI: só runs do default branch com `event=push`. `conclusion`: `success` = sucesso; `failure|timed_out|startup_failure` = falha; `cancelled|skipped|neutral|action_required|stale|vazio` = **ignorar**.
- Inclusão mínima: ≥ 5 releases e ≥ 50 workflow runs válidos na janela; descartes entram no funil.
- **Censura**: eventos que não terminam na janela (falha não recuperada; releases nos últimos 7 dias para CFR b) são registrados como censurados e contados, **nunca descartados silenciosamente**.
- Em todas as RQs reportar **mediana e IQR**, não média/desvio.

## Métricas (resumo; detalhes no enunciado §5)

- RQ01 deployment frequency = releases na janela ÷ ≈52,1 semanas.
- RQ02 lead time, duas variantes: (a) por release (data R − commit mais antigo; mediana por repo); (b) por commit (mediana de todos os commits de todas as releases). Commits via `compare/{anterior}...{R}` com paginação (teto 250 sem paginar); primeira release da história é ignorada; `compare` 404 → registrar e ignorar a release, contando quantas.
- RQ03 CFR: (a) falhas ÷ (falhas+sucessos) de workflow runs, todos os workflows juntos; (b) release falha se seguida em ≤ 7 dias por release corretiva (heurística própria: bump só de patch semver e/ou commits com revert/hotfix/fix) — heurística deve ser validada (F1 ≥ 0,70, documentar cada versão testada).
- RQ04 recuperação: calculada **dentro de cada workflow** (episódio = primeira falha após sucesso até próximo sucesso; `updated_at` do sucesso − `run_started_at` da primeira falha), depois mediana agregada por repo; reportar proporção de episódios censurados.
- RQ05 Spearman (ρ, p, n) entre RQ01 e CFR (a) e (b); dispersão em escala log se necessário.
- RQ06 ≥ 3 fatores (linguagem, estrelas, contribuidores, idade em quartis; tipo de projeto rotulado manualmente) × 4 métricas; Kruskal-Wallis (ε² = H/(n−1)) ou Mann-Whitney (Cliff's δ = 2·U₁/(n₁n₂)−1); **correção de Holm** (`multipletests(method='holm')`).
- RQ07 sensibilidade: ≥ 3 combinações de definições (ex.: C1 release/(a)/(a), C2 release+pré-release/(b)/(b), C3 tag/(b)/(a)); % que mudou de categoria + `cohen_kappa_score(weights='linear')`. Classificação Elite/High/Medium/Low pelos cortes fixos do enunciado (4/3/2/1 pontos por métrica, mediana arredondada para baixo).
- RQ08 (bônus): rework rate ou tendência temporal (Mann-Kendall).

## Armadilhas da API do GitHub

- Search: máx. 1.000 resultados/consulta → fatiar por faixas de estrelas ou linguagem.
- `actions/workflows` com `total_count = 0` → descartar o repo antes de gastar chamadas.
- `actions/runs` com filtros: teto de 1.000 resultados/consulta → dividir a janela por mês e verificar se algum mês atingiu o teto.
- Tags não têm data: usar a data do commit apontado.
- Nº de contribuidores: `GET /repos/{o}/{r}/contributors?per_page=1&anon=true` e ler a última página no `Link`.
- `GET /rate_limit` não consome cota.

## Validação manual (S02)

Sortear 60 repos com semente fixa (`df.sample(n=60, random_state=42)`); 3 avaliadores rotulam **independentemente** (tipo do projeto; releases são entregas reais?; 5 releases sorteadas por repo: corretiva sim/não) sem ver a saída da heurística; kappa de Fleiss (`aggregate_raters` + `fleiss_kappa`) por dimensão; consenso com protocolo de desempate registrado no repo; precisão/recall/F1 da heurística vs. consenso. Cada avaliador commita seu próprio arquivo de rótulos.

## Replicação cruzada (entrega final)

Outro grupo executará o pipeline **usando só o README** sobre 30 repos; o README deve ser completo e autossuficiente. Issues recebidas devem ser respondidas e adicionadas ao GitHub Projects.
