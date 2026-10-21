Rascunho (não é a versão final). Para montar no Overleaf.

## Seção: Metodologia > Pipeline de coleta e processamento

Toda a coleta foi feita por um programa próprio, sem nenhuma biblioteca pronta de acesso à API do GitHub. O programa conversa direto com a API REST usando apenas requisições HTTP. Ele roda com um único comando, a partir de um arquivo de configuração. Esse arquivo guarda a janela de 12 meses, o tamanho da amostra, as faixas de estrelas da busca e o limite de comparações das variantes. O token de acesso é lido de uma variável de ambiente e nunca é gravado no repositório de código.

O pipeline segue sempre a mesma ordem:

1. **Busca de candidatos.** Pesquisamos repositórios por faixas de estrelas, excluindo forks e repositórios arquivados. A busca do GitHub devolve no máximo 1.000 resultados por consulta, então dividimos em quatro faixas de estrelas. Os nomes encontrados são ordenados e depois embaralhados com uma semente fixa, para que a amostra seja reproduzível e não fique viciada nos projetos mais populares.
2. **Filtro de GitHub Actions.** Antes de gastar mais chamadas, verificamos se o repositório tem pelo menos um workflow. Quem não tem é descartado já nessa etapa.
3. **Metadados.** Coletamos estrelas, linguagem principal, data de criação, branch principal e número de contribuidores. Para contar os contribuidores, pedimos uma lista com um item por página, incluindo anônimos, e lemos o número da última página. Quando a API recusa a lista por ser grande demais, o valor fica vazio.
4. **Releases e lead time.** Coletamos as releases publicadas na janela e, para cada uma, os commits que entraram nela em relação à release anterior, seguindo todas as páginas de resultado.
5. **Workflow runs e métricas de CI.** Coletamos as execuções de workflow do branch principal disparadas por push. Como a API limita cada consulta filtrada a 1.000 resultados, a janela é dividida em meses, uma consulta por mês. Se algum mês atinge esse teto, ele é registrado no dado final.
6. **Critério de inclusão.** O repositório só entra na amostra com pelo menos 5 releases e 50 execuções válidas na janela. Os repositórios que não atingem esse mínimo saem e são contados no funil.
7. **Variantes e classificação.** Só para os repositórios que passaram, coletamos as variantes usadas na análise de sensibilidade (releases com pré-releases e tags) e o CFR por entrega. Depois calculamos as notas e a categoria DORA de cada repositório.
8. **Consolidação.** No fim, o programa valida o conjunto de dados antes de liberá-lo e acrescenta as colunas derivadas. Essa etapa não faz novas chamadas à API.

Os repositórios são processados um por vez, na ordem do embaralhamento, até a amostra chegar ao tamanho pedido (300 repositórios válidos). Por isso nem todos os candidatos precisam ser processados: dos 4.000 encontrados na busca, 1.328 foram processados para chegar à amostra final.

## Seção: Metodologia > Cache em disco e retomada

Cada resposta bem-sucedida da API é gravada em disco, em um arquivo próprio, identificado pelo endereço da requisição e seus parâmetros. Antes de qualquer chamada, o programa olha se aquela resposta já existe. Se existir, ela é reaproveitada e nenhuma chamada é feita. Isso vale também para cada página de uma consulta paginada.

Essa estratégia dá a retomada de graça. Se a execução for interrompida (queda de rede, fim da cota, o usuário fechar o programa), basta rodar o mesmo comando de novo: tudo o que já foi baixado vem do disco e o programa continua do ponto onde parou, sem repetir chamadas. Alguns cuidados tornam isso seguro:

- a gravação é feita em um arquivo temporário que depois substitui o definitivo, então uma interrupção no meio da escrita não deixa um arquivo pela metade;
- se mesmo assim um arquivo estiver corrompido ou truncado, ele é tratado como se não existisse e a resposta é baixada de novo;
- só respostas de sucesso são guardadas. Erros (por exemplo, recurso inexistente ou falha do servidor) não entram no cache e serão tentados de novo na próxima execução.

Há um cuidado com a janela de observação: ela precisa estar totalmente no passado. Se a janela ainda estivesse em andamento, o cache guardaria respostas incompletas (sem as releases e execuções futuras), e a retomada reaproveitaria esses dados errados. No nosso caso, a janela (de 01/10/2025 a 30/09/2026) já tinha terminado quando coletamos os dados. O cache não é versionado junto com o código.

## Seção: Metodologia > Limite de requisições e erros da API

O programa respeita o limite de uso da API sozinho, sem intervenção humana:

- **Limite primário.** Em toda resposta, lemos quantas requisições ainda restam e quando a cota renova. Quando restam zero, o programa dorme até o horário de renovação antes de fazer a próxima chamada.
- **Limite secundário e respostas 403/429.** Se a API recusa a chamada por excesso de uso, o programa espera o tempo indicado pelo próprio GitHub. Quando não há indicação, espera 60 segundos. Um 403 que não é de limite (por exemplo, falta de permissão) não é repetido: vira erro.
- **Erros do servidor e de rede.** Falhas 5xx, quedas de conexão, respostas cortadas e estouro de tempo são repetidos com espera exponencial: 1, 2, 4, 8 e 16 segundos. São no máximo 5 novas tentativas por requisição; se todas falharem, o erro é levantado.
- **Recurso inexistente (404).** Não é repetido. É tratado como um caso conhecido: um repositório apagado ou renomeado é descartado e registrado no funil, e uma comparação entre releases que dá 404 (tag apagada ou reescrita) faz a release ser ignorada e contada.
- **Paginação.** Seguimos o cabeçalho que indica a próxima página até ele deixar de existir, juntando todas as páginas.

A consulta do próprio limite de uso não consome cota, e é usada só para acompanhamento. Nos testes automatizados, nenhuma chamada real é feita: usamos uma sessão HTTP falsa e uma função de espera simulada, o que permite verificar o backoff e a espera pela renovação da cota sem esperar de verdade.

## Seção: Metodologia > Funil de seleção e dicionário de dados

**Funil.** A cada execução o programa gera automaticamente o funil de seleção, com o número de repositórios que restam em cada etapa, quantos saíram e o motivo. Nesta coleta o funil foi:

| Etapa | Restantes | Descartados |
|---|---:|---:|
| Candidatos da busca | 4.000 | – |
| Processados (os demais não foram necessários, pois a amostra fechou) | 1.328 | 2.672 |
| Com GitHub Actions | 939 | 389 |
| Metadados coletados | 939 | 0 |
| Pelo menos 5 releases na janela | 373 | 566 |
| Pelo menos 50 execuções válidas na janela | 300 | 73 |
| Amostra final | 300 | – |

Os 2.672 "descartados" da segunda linha não foram rejeitados por critério: simplesmente não precisaram ser processados, porque a amostra de 300 já estava completa. Os descartes por critério (sem Actions, poucas releases, poucas execuções) somam 1.028 repositórios.

**Dicionário de dados.** Para cada coluna dos arquivos finais mantemos um dicionário com nome, tipo, unidade e fórmula ou origem do valor. O conjunto de dados principal tem 45 colunas, uma linha por repositório da amostra final, e o funil e a lista de repositórios elegíveis ao sorteio da validação manual também são descritos. Há um teste automatizado que confere que as colunas listadas no dicionário são exatamente as do conjunto de dados, na mesma ordem, de modo que o dicionário não fica desatualizado quando uma coluna nova é criada. Convenções gerais: datas em UTC, só o branch principal, lead time em dias, tempo de recuperação em horas, CFR como fração entre 0 e 1, e célula vazia quando o valor não pôde ser calculado.

**Validação do conjunto de dados.** Antes de liberar o resultado, o programa confere a integridade e interrompe com uma lista de problemas se algo estiver errado. Entre as verificações estão: nomes de repositório vazios ou duplicados; critério de inclusão respeitado (mínimo de releases e de execuções); CFR e rework dentro de 0 a 1; métricas sem valores negativos; notas entre 1 e 4; frequência de deploy coerente com a contagem de releases dividida pelas semanas da janela; categoria DORA preenchida se e somente se as quatro métricas existem; e funil consistente (restantes nunca crescem e a última etapa tem o mesmo número de linhas do conjunto de dados).

## Seção: Metodologia > Tratamento de censura e dados descartados

Nenhum evento incompleto é jogado fora em silêncio. Quando um evento não termina dentro da janela, ou um dado não pode ser usado, ele é registrado e contado, e a contagem fica no conjunto de dados:

- **Falhas de CI não recuperadas.** Um episódio de falha que não tem sucesso depois dentro da janela é censurado. Ele entra na contagem de episódios e na proporção de censurados do repositório, mas não entra na mediana do tempo de recuperação. Nesta amostra, dos 20.707 episódios de falha, 122 ficaram censurados, distribuídos em 83 repositórios. Falhas anteriores ao primeiro sucesso do workflow não abrem episódio e também são contadas à parte.
- **Releases dos últimos 7 dias.** No CFR por entrega, a release precisa de 7 dias para saber se foi seguida de uma correção. As releases publicadas nos últimos 7 dias da janela não podem ser avaliadas: saem do denominador e são contadas como censuradas. Na amostra, são 305 releases nessa situação.
- **Comparações que dão 404.** Releases cuja comparação com a anterior falha são ignoradas no lead time e contadas (11 releases no total da amostra).
- **Lead time negativo.** Commits com data posterior à release (efeito de rebase ou squash) são descartados do lead time e contados.
- **Meses no teto da API.** Os meses em que a consulta de execuções bateu no teto de 1.000 resultados são listados por repositório, porque os dados daquele mês podem estar incompletos.
- **Limite de comparações nas variantes.** Em repositórios com muitas releases ou tags, as variantes limitam o número de comparações a 100 e usam uma amostra espalhada pela janela. A frequência continua exata, e as unidades que ficaram sem comparação também são contadas.
- **Repositórios descartados.** Os que não cumprem o critério de inclusão não somem: aparecem no funil, com a etapa e o motivo.

Em todas as análises seguintes, esses contadores permitem informar quanto dos dados é censurado ou ignorado, em vez de deixar o leitor supor que todos os eventos foram observados por completo.
