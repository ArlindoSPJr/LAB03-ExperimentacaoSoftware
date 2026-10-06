# Lab03 — Mineração de Métricas DORA

Pipeline que minera métricas DORA (frequência de deploy, lead time, change failure rate e tempo de recuperação) de repositórios open-source do GitHub que usam GitHub Actions.

<!-- Seções Pré-requisitos, Token, Instalação e Comando único: S01-D3. Seção Testes: S01-D2. -->

## Saídas

Ao final da execução, o pipeline grava em `data/`:

| Arquivo | Conteúdo |
|---|---|
| `data/metricas.csv` | Uma linha por repositório da amostra final, com metadados, métricas DORA (RQ01–RQ04), contadores de casos censurados/descartados e a classificação DORA |
| `data/funil.csv` | Funil de seleção: quantos repositórios restaram em cada etapa e o motivo dos descartes |
| `data/DICIONARIO.md` | Dicionário de dados: nome, tipo, unidade e fórmula/origem de cada coluna dos CSVs acima |

Unidades: lead time em **dias**, recuperação em **horas**, CFR como **fração de 0 a 1**, frequência em **releases por semana**. Datas em UTC.

As respostas da API ficam em cache em `cache/` (não versionado). Reexecutar o comando reaproveita o cache e continua de onde parou.
