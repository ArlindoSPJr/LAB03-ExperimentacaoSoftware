# Documentação do Lab03 (métricas DORA)

Índice por tópico de toda a documentação do projeto. **Nenhum arquivo foi movido**: o `CLAUDE.md`, o agente `.claude/agents/dev-issue.md`, o código (`metricas/`, `pipeline/`, `validacao/`) e os testes citam `docs/ISSUES.md`, `docs/superpowers/plans/...`, `docs/HEURISTICA_VERSOES.md`, `docs/PROTOCOLO_DESEMPATE.md`, `data/DICIONARIO.md` e `artigo/*.md`. Por isso os originais ficam onde estão e esta pasta traz só índices com links relativos (sem cópias, para não haver duas versões divergentes).

Posição em 2026-10-20: S01 e S02 concluídas (Issues #1 a #38 mergeadas); S03 e a entrega final ainda não iniciadas.

| Tópico | O que há | Situação |
|---|---|---|
| [enunciado-e-requisitos](enunciado-e-requisitos/README.md) | Enunciado (fonte de verdade) e `CLAUDE.md` | Completo |
| [backlog-e-processo](backlog-e-processo/README.md) | `docs/ISSUES.md`, planos por Issue, agente `dev-issue`, CI | S01 e S02 concluídas; S03 e final pendentes |
| [metodologia](metodologia/README.md) | Definições operacionais e variantes | Parcial |
| [dados](dados/README.md) | Dicionário de dados, CSVs, funil, README (saídas e consolidação) | Completo para S01/S02 |
| [heuristica](heuristica/README.md) | Versões da heurística de release corretiva (F1) | Concluído (v3, F1 = 0,734) |
| [validacao-manual](validacao-manual/README.md) | Protocolo de desempate, rótulos, kappa, consenso | Concluído |
| [artigo](artigo/README.md) | Hipóteses e metodologia (rascunhos em Markdown) | Parcial |
| [replicacao](replicacao/README.md) | Replicação cruzada | Pendente (nada criado) |

## O que ainda falta (comparando `docs/ISSUES.md`, o enunciado e o repositório)

Documentação:
- `artigo/metodologia.md` (S02-D1 e S02-D3): fonte de dados, janela, funil, protocolo da amostra-ouro, pipeline, cache/retomada, rate limit, censura. Só existe `artigo/metodologia_definicoes.md` (S02-D2, #38). Versões e F1 da heurística ainda não estão no texto da metodologia.
- `artigo/resultados.md`, `artigo/discussao.md` (S03-D1 a D3), `artigo/ameacas.md` (F-D1 e F-D3), `artigo/replicacao.md` (F-D2).
- O artigo oficial deve estar no template SBC (Overleaf), com no máximo 10 páginas; o repositório guarda só rascunhos e não há link do Overleaf.
- Hipóteses de RQ01, RQ02, RQ07 e RQ08 (S01-D3): conferir se `artigo/introducao.md` cobre RQ01 a RQ07.
- Seções Pré-requisitos, Token, Instalação e Comando único do `README.md` (S01-D3; o README ainda traz o comentário de pendência). A tabela de testes do README tem um rascunho a atualizar (S01-D2).
- Notas de passagem (handoff) das ondas vivem em comentários de PR no GitHub, não no repositório.
- A registrar no artigo: F1 da heurística medido na mesma amostra em que foi ajustada (superestima), kappa como achado, as cinco decisões em aberto de `docs/ISSUES.md`.

Trabalho fora de documentação (para contexto):
- S03: `analise/` (estatística, RQ01 a RQ07, RQ08 bônus), `config.subamostra30.yaml`, README testado em ambiente limpo.
- Entrega final: `replicacao/` (script, relatório, comparação), Issues no repositório do outro grupo, tratamento das Issues recebidas, revisão do artigo.
