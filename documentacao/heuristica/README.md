# Heurística de release corretiva (CFR b)

| Documento | Conteúdo |
|---|---|
| [docs/HEURISTICA_VERSOES.md](../../docs/HEURISTICA_VERSOES.md) | Cada versão testada (v1, v2, v3), regra, precisão, recall, F1 e notas |
| [metricas/corretiva.py](../../metricas/corretiva.py) | Implementação (`HEURISTICA_VERSAO`) |
| [validacao/avaliar_heuristica.py](../../validacao/avaliar_heuristica.py) | Avaliação contra o consenso |
| [data/heuristica_avaliacao.csv](../../data/heuristica_avaliacao.csv) | Resultados |

Situação: concluído. A v3 (vigente) tem F1 = 0,734 (meta >= 0,70). Ameaça a registrar no artigo: regras ajustadas e avaliadas na mesma amostra de 300 releases, o que tende a superestimar o F1.
