### 3.x Definições operacionais e variantes

**Janela e escopo.** Todas as medidas usam uma janela de 12 meses, de 01/10/2025 a 30/09/2026 (UTC; 365 dias ≈ 52,14 semanas). Só entram releases publicadas e workflow runs criados dentro da janela, e apenas o *default branch* de cada repositório (campo `default_branch` da API). A data de um commit é sempre `commit.author.date`.

**Unidade de deploy.** Na definição principal, um deploy é uma *release* publicada (`draft = false`, `prerelease = false`). Na análise de sensibilidade (RQ07) usamos duas variantes: *release + pré-release*, que inclui as releases com `prerelease = true`, e *tag*, que considera as tags cujo commit apontado está no default branch e tem data dentro da janela; como tags não têm data, usamos a do commit apontado. A frequência de deploy (RQ01) é o número de unidades na janela dividido por 52,14 semanas.

**Release anterior e commits de uma release.** Os commits de uma unidade R são obtidos por `compare/{anterior}...{R}`, com paginação completa. A unidade anterior é a imediatamente anterior do mesmo tipo, mesmo fora da janela; na definição principal, só releases não-pré-release servem de base. A primeira unidade da história não tem base e é ignorada no lead time. Quando o `compare` retorna 404 (tag apagada ou reescrita), a release é ignorada e contada (`compare_404`). Nas variantes, repositórios com muitas unidades têm os compares limitados a 100 por variante, com amostra sistemática espalhada pela janela; a frequência continua exata e as unidades puladas são contadas.

**Lead time (RQ02).** Na variante (a), o lead time de R é `published_at(R)` menos a data do commit mais antigo de R, e o valor do repositório é a mediana entre as releases. Na variante (b), cada commit de R contribui com `published_at(R)` menos a sua data, e o valor do repositório é a mediana de todos os commits. Commits com data posterior à release, causados por rebase ou squash, geram lead time negativo; esses valores são descartados e contados.

**CI e CFR por pipeline (RQ03 a).** Consideramos só workflow runs do default branch com `event = push`. Pelo campo `conclusion`, `success` é sucesso; `failure`, `timed_out` e `startup_failure` são falha; os demais valores são ignorados. O CFR (a) é falhas ÷ (falhas + sucessos), somando todos os workflows. Como a listagem filtrada devolve no máximo 1.000 resultados, a janela é dividida por mês, e os meses que atingem o teto são registrados.

**Tempo de recuperação (RQ04).** Calculado dentro de cada workflow: um episódio começa na primeira falha após um sucesso e termina no próximo sucesso do mesmo workflow; a duração é `updated_at` do sucesso menos `run_started_at` da primeira falha. O valor do repositório é a mediana dos episódios de todos os workflows. Falhas antes do primeiro sucesso da janela não abrem episódio. Episódios sem sucesso até o fim da janela são **censurados**: entram na contagem de episódios e na proporção de censurados, mas não na mediana.

**CFR por entrega (RQ03 b).** Uma release falha se a próxima release, publicada em até 7 dias, é corretiva. O CFR (b) é releases que falharam ÷ releases avaliadas. Releases publicadas nos últimos 7 dias da janela não podem ser avaliadas e ficam fora do denominador, contadas como censuradas. A variante *release + pré-release* (entrada da combinação C2) aplica a mesma regra a releases e pré-releases.

**Heurística de release corretiva.** Testamos três versões contra o consenso da amostra-ouro (300 releases, classe positiva "corretiva"):

| Versão | Regra | Precisão | Recall | F1 |
|---|---|---:|---:|---:|
| v1 | bump só de patch **ou** algum commit com `revert`, `hotfix` ou `fix` | 0,402 | 1,000 | 0,574 |
| v2 | a própria tag é de patch (`x.y.z`, `z > 0`) | 0,544 | 0,974 | 0,698 |
| v3 | tag de patch **e** (nenhum commit de funcionalidade **ou** ao menos metade dos commits corretivos), ignorando commits de CI, documentação, manutenção, dependências e merges | 0,684 | 0,791 | 0,734 |

A v1 segue literalmente o enunciado e marca corretivas demais, porque quase toda release tem algum commit com "fix". A v2 resolve os *backports*: projetos que publicam patches de várias linhas, como `v8.19.6` depois de `v9.2.0`, não podem ser comparados com a release anterior por data. A v3, adotada no dataset, separa os patches que trazem funcionalidades. As regras usam só versionamento semântico e convenções de mensagem de commit, sem casos específicos de repositório. Como foram ajustadas e avaliadas na mesma amostra, o F1 tende a ser otimista (ver Ameaças à validade).

**Rework rate (RQ08).** Proporção de releases corretivas (heurística v3) sobre o total de releases da janela, sem censura.

**Classificação DORA e combinações da RQ07.** Cada métrica recebe uma nota de 1 a 4 pelos cortes fixos do enunciado, e a categoria geral é a mediana das quatro notas, arredondada para baixo. Repositórios com alguma das quatro métricas ausente não são classificados. As combinações são C1 (release, lead time (a), CFR (a)), C2 (release + pré-release, lead time (b), CFR (b)) e C3 (tag, lead time (b), CFR (a)).

**Estatística.** Em todas as RQs reportamos mediana e intervalo interquartil (IQR).
