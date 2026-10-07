# Lab03 — Mineração de Métricas DORA

Pipeline que minera métricas DORA (frequência de deploy, lead time, change failure rate e tempo de recuperação) de repositórios open-source do GitHub que usam GitHub Actions.

<!-- Seções Pré-requisitos, Token, Instalação e Comando único: S01-D3. -->

## Saídas

Ao final da execução, o pipeline grava em `data/`:

| Arquivo | Conteúdo |
|---|---|
| `data/metricas.csv` | Uma linha por repositório da amostra final, com metadados, métricas DORA (RQ01–RQ04), contadores de casos censurados/descartados e a classificação DORA |
| `data/funil.csv` | Funil de seleção: quantos repositórios restaram em cada etapa e o motivo dos descartes |
| `data/DICIONARIO.md` | Dicionário de dados: nome, tipo, unidade e fórmula/origem de cada coluna dos CSVs acima |

Unidades: lead time em **dias**, recuperação em **horas**, CFR como **fração de 0 a 1**, frequência em **releases por semana**. Datas em UTC.

As respostas da API ficam em cache em `cache/` (não versionado). Reexecutar o comando reaproveita o cache e continua de onde parou.

## Testes

Os testes usam [pytest](https://docs.pytest.org/) e ficam em `tests/`. A partir da raiz do repositório, com as dependências de `requirements.txt` instaladas:

```
pytest
```

Para rodar com a cobertura do módulo de métricas (é o comando que o CI usa):

```
pytest --cov=metricas --cov-report=term-missing
```

Para rodar só um arquivo ou um teste:

```
pytest tests/test_lead_time.py -v
pytest tests/test_lead_time.py::test_lead_time_por_release_exemplo_do_enunciado -v
```

Como os testes são escritos:

- **Sem rede e sem token.** As funções de coleta recebem um cliente HTTP com sessão falsa (*fake*) e uma função `sleep` injetada, então nenhum teste acessa a API do GitHub nem espera de verdade. O token real nunca é usado nos testes.
- **Fixtures construídas à mão**, com resultado conhecido no papel. Os exemplos numéricos do enunciado viram testes (ex.: lead time de 13 dias da `v1.1`, recuperação de 1h20, `overall([4,3,3,1]) == "High"`).
- **Casos de borda** exigidos pelo enunciado: release sem commits novos, repositório com uma única release, `compare` com 404, runs `cancelled`/`skipped` ignoradas, falha nunca recuperada (censurada), métrica ausente (`None`).

| Área | Arquivos de teste |
|---|---|
| Cliente HTTP, cache, rate limit e backoff | `tests/test_http.py` |
| Seleção de candidatos, metadados e funil | `tests/test_selecao.py`, `tests/test_metadados.py` |
| Releases, commits entre releases e workflow runs | `tests/test_releases.py`, `tests/test_runs.py`, `tests/test_etapa_releases.py` |
| Métricas: lead time, CFR, recuperação e classificação DORA | `tests/test_lead_time.py`, `tests/test_classificacao.py`; `tests/test_cfr.py` e `tests/test_recuperacao.py` entram com as Issues S01-O3.1 e S01-O3.2 |

**CI:** o workflow `.github/workflows/testes.yml` roda a suíte no GitHub Actions a cada push e pull request. Um PR só é mergeado com os testes verdes. A meta é **cobertura mínima de 80% do módulo `metricas`** (`--cov-fail-under=80`); enquanto as métricas da S01 não estão completas, o limite fica em 0 e sobe para 80 na Issue S01-O3.5.

<!-- Rascunho (S01-D2): atualizar a tabela quando entrarem os testes do orquestrador e das etapas de runs (Onda 3). -->
