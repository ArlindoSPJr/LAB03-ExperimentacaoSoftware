Rascunho (não é a versão final). Para montar no Overleaf.

> **Nota para quem montar o Overleaf:** a ordem sugerida da Metodologia é (1) fonte de dados e janela, (2) seleção da amostra e funil (este arquivo), (3) definições operacionais e variantes (`metodologia_definicoes.md`), (4) pipeline, cache, rate limit e censura (`metodologia_pipeline.md`) e (5) protocolo da validação manual (este arquivo). A tabela do funil aparece também em `metodologia_pipeline.md`; no artigo ela deve entrar **uma vez só**, de preferência aqui.

## Seção: Metodologia > Fonte de dados

Os dados vêm exclusivamente da API REST do GitHub (versão de 2022-11-28), consultada por um programa próprio, sem bibliotecas prontas de acesso à API. Usamos cinco grupos de recursos:

- **Busca de repositórios** (`search/repositories`), para montar a lista de candidatos;
- **Metadados do repositório** (estrelas, linguagem principal, data de criação, *default branch*) e **contribuidores**;
- **Releases** e **comparação entre releases** (`compare/{anterior}...{R}`), para a frequência de deploy, o lead time e o CFR por entrega;
- **Workflows e workflow runs** do GitHub Actions, para o CFR por pipeline e o tempo de recuperação;
- **Tags**, só para a variante "tag" da análise de sensibilidade (RQ07).

Escolhemos repositórios open-source populares que usam GitHub Actions porque são a única população em que as quatro métricas DORA podem ser aproximadas com dados públicos: releases fazem o papel de deploys, e as execuções de CI fazem o papel dos sinais de falha e de recuperação. Como discutimos nas ameaças à validade, essas são **aproximações**: uma release publicada não é necessariamente um deploy em produção, e um workflow que falha não é necessariamente uma falha percebida pelo usuário.

## Seção: Metodologia > Janela de observação

Todas as medidas usam a mesma janela de **12 meses, de 01/10/2025 a 30/09/2026** (UTC, 365 dias ≈ 52,14 semanas). Entram nos cálculos só as releases **publicadas** e os workflow runs **criados** dentro dela, e só no *default branch* de cada repositório. A única exceção é a base de comparação do lead time: a primeira release da janela é comparada com a última release anterior a ela, mesmo que essa esteja fora da janela.

A janela foi escolhida para terminar antes da coleta. Isso evita duas distorções: eventos ainda em andamento (falhas sem correção, releases recentes) seriam tratados como censurados em excesso, e o cache em disco guardaria respostas incompletas que a retomada reaproveitaria. Mesmo assim, há eventos que começam no fim da janela e não terminam dentro dela; eles são tratados como **censurados** (falhas de CI sem recuperação; releases dos últimos 7 dias no CFR por entrega), contados e reportados, nunca descartados em silêncio.

## Seção: Metodologia > Seleção da amostra e funil

**Candidatos.** A busca do GitHub devolve no máximo 1.000 resultados por consulta. Por isso dividimos a busca em quatro faixas de estrelas (1.000–2.000, 2.000–5.000, 5.000–20.000 e acima de 20.000), excluindo *forks* e repositórios arquivados. As quatro faixas atingiram o teto, o que deu 4.000 candidatos únicos. O piso de 1.000 estrelas restringe a amostra a projetos com comunidade ativa, onde releases e CI são mais prováveis.

**Ordem de processamento.** A busca ordena por relevância, o que favoreceria os projetos mais conhecidos de cada faixa. Para evitar isso, a lista de candidatos é ordenada alfabeticamente e depois **embaralhada com semente fixa** (`random_state = 42`). Os repositórios são processados nessa ordem, um a um, até a amostra atingir 300 repositórios válidos. Com a mesma configuração, a amostra é sempre a mesma.

**Critérios de inclusão.** Um candidato entra na amostra se:
1. tem ao menos um workflow do GitHub Actions (os que não têm são descartados antes de qualquer chamada cara);
2. tem **pelo menos 5 releases** publicadas (não rascunho, não pré-release) na janela;
3. tem **pelo menos 50 workflow runs válidos** na janela, ou seja, runs do *default branch*, disparados por `push`, com conclusão de sucesso ou de falha.

**Funil.** O programa gera o funil automaticamente a cada execução (`data/funil.csv`):

| Etapa | Restantes | Descartados | Motivo do descarte |
|---|---:|---:|---|
| Candidatos da busca | 4.000 | – | – |
| Processados | 1.328 | 2.672 | não processados: a amostra fechou antes |
| Com GitHub Actions | 939 | 389 | sem workflows |
| Metadados coletados | 939 | 0 | – |
| ≥ 5 releases na janela | 373 | 566 | menos de 5 releases não-pré-release |
| ≥ 50 runs válidos na janela | 300 | 73 | menos de 50 runs válidos |
| **Amostra final** | **300** | – | – |

Os 2.672 candidatos não processados não foram rejeitados por nenhum critério: a amostra de 300 fechou antes de chegar a eles. Entre os 1.328 processados, 1.028 saíram por critério, e o filtro mais forte foi o de releases: só 40% dos repositórios com Actions publicaram 5 releases na janela. Isso já indica um viés da amostra a ser discutido: ela representa projetos que **usam releases do GitHub como mecanismo de entrega**, não todos os projetos populares.

## Seção: Metodologia > Protocolo de validação manual (amostra-ouro)

A heurística de release corretiva (CFR por entrega, RQ03 b) e o tipo do projeto (RQ06) precisam de julgamento humano. Para isso montamos uma amostra-ouro rotulada pelos três integrantes do grupo.

**Sorteio.** Sorteamos 60 dos 300 repositórios da amostra final com `df.sample(n = 60, random_state = 42)`, sobre a lista de elegíveis em ordem alfabética (para que o sorteio não dependa da ordem de coleta). Em cada repositório sorteamos, com a mesma semente, 5 releases da janela. Isso dá 60 itens por repositório e 300 itens por release.

**Planilhas.** Um script gera três planilhas idênticas, uma por avaliador, com links diretos para a página do repositório, de cada release e da lista de commits da release. As planilhas **não** trazem nenhuma saída da heurística, que ainda não existia quando a rotulagem foi feita.

**Rotulagem independente.** Cada avaliador preencheu sozinho, sem consultar os demais:
1. o **tipo do projeto**: biblioteca/framework, aplicação/serviço, ferramenta CLI ou outro;
2. se as releases do repositório são **entregas reais ao usuário**: sim, não ou incerto;
3. para cada uma das 5 releases, se ela é **corretiva** (sim/não), lendo as notas da release e os commits.

Cada avaliador fez commit do próprio arquivo de rótulos no repositório.

**Concordância.** Calculamos o kappa de Fleiss (statsmodels, `aggregate_raters` + `fleiss_kappa`) em cada dimensão, interpretado pela escala de Landis e Koch (1977). Como o kappa é sensível a classes muito desbalanceadas, reportamos também a concordância observada.

**Consenso e desempate.** O rótulo de consenso é o da maioria: unânime (3-0) ou maioria simples (2-1). Empates 1-1-1 (possíveis só nas dimensões com três ou mais categorias) seriam decididos em reunião, com a decisão e a justificativa registradas no repositório; a reunião não pode reverter uma maioria. O consenso foi fechado **antes** de avaliar a heurística e não foi alterado depois. O protocolo completo está em `docs/PROTOCOLO_DESEMPATE.md`.

| Dimensão | Itens | Kappa de Fleiss | Concordância observada | Unânimes | Maioria (2-1) |
|---|---:|---:|---:|---:|---:|
| Tipo do projeto | 60 | 0,91 | 0,94 | 55 | 5 |
| Entregas reais | 60 | 0,38 | 0,97 | 57 | 3 |
| Release corretiva | 300 | 0,86 | 0,93 | 270 | 30 |

Não houve nenhum empate 1-1-1, então nenhuma decisão de reunião foi necessária. O tipo do projeto e a release corretiva tiveram concordância quase perfeita. O kappa baixo de "entregas reais" é um efeito do desbalanceamento (quase todos os rótulos são "sim", e 57 dos 60 repositórios foram unânimes), mas as três divergências apontam um critério de fato ambíguo: releases sem notas, com notas provisórias ou só versões *alpha*. O consenso deu 58 repositórios com entregas reais e 2 incertos; 115 das 300 releases foram consideradas corretivas.

**Avaliação da heurística.** A saída da heurística foi comparada com o consenso das 300 releases por precisão, recall e F1 (classe positiva: corretiva). Seguindo o enunciado, a heurística seria refinada enquanto o F1 ficasse abaixo de 0,70. Foram três versões, todas documentadas com o seu F1 (ver Definições operacionais); a versão adotada chegou a F1 = 0,73.

**Uso de ferramentas pelos avaliadores.** Um avaliador rotulou com auxílio de um modelo de linguagem, e outro revisou sugestões de um script de pré-rotulagem por palavras-chave. Isso deve ser declarado no artigo e discutido nas ameaças à validade: ferramentas que leem o mesmo texto tendem a errar nos mesmos casos, o que pode inflar o kappa, e a pré-rotulagem por palavras-chave se parece com a heurística avaliada, o que pode favorecer o F1.
