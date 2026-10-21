# Resultados RQ01 a RQ04 (rascunho)

> Rascunho para montar no Overleaf. Todos os números vêm da tabela de resultados gerada a partir do conjunto final de 300 repositórios. Em tudo usamos mediana e intervalo interquartil (IQR, de Q1 a Q3), nunca média e desvio padrão. As hipóteses citadas são as escritas na Introdução antes de ver os dados.

Seção: Resultados > Visão geral

Os resultados abaixo usam os 300 repositórios da amostra final e a janela de 12 meses definida para a turma. Cada métrica é calculada por repositório. Depois resumimos a distribuição entre os repositórios pela mediana e pelo IQR.

| Métrica | Variante | n | Mediana | Q1 a Q3 | IQR |
|---|---|---|---|---|---|
| Frequência de deploy (releases por semana) | única | 300 | 0,39 | 0,19 a 0,94 | 0,75 |
| Lead time (dias) | (a) por release | 300 | 12,1 | 3,0 a 42,2 | 39,1 |
| Lead time (dias) | (b) por commit | 300 | 11,2 | 3,0 a 46,8 | 43,8 |
| Taxa de falha das mudanças (CFR) | (a) CI | 300 | 4,8% | 2,2% a 11,5% | 9,2 p.p. |
| Taxa de falha das mudanças (CFR) | (b) entrega | 300 | 20,0% | 6,7% a 36,8% | 30,1 p.p. |
| Tempo de recuperação (horas) | por repositório | 277 | 2,3 | 0,9 a 9,3 | 8,5 |

Seção: Resultados > RQ01 Frequência de deploy

**Resultado.** A mediana é de 0,39 releases por semana, ou seja, cerca de uma release a cada duas semanas e meia (aproximadamente 20 releases no ano). O IQR vai de 0,19 a 0,94 releases por semana. A distribuição é assimétrica: 71 repositórios publicam pelo menos uma release por semana, e o mais rápido chega a 12 releases por semana. Por outro lado, 109 repositórios publicam menos de uma release a cada quatro semanas.

**Hipótese.** A Introdução não traz uma hipótese escrita para esta pergunta. Por isso não dá para dizer que o resultado confirmou ou contrariou algo. Se o grupo quiser comparar, é preciso escrever essa hipótese na Introdução e deixar claro que ela foi feita depois de ver os dados.

Seção: Resultados > RQ02 Lead time para mudanças

**Resultado.** As duas variantes dão valores parecidos no centro e diferentes na cauda.
- Variante (a), por release: mediana de 12,1 dias, IQR de 3,0 a 42,2 dias.
- Variante (b), por commit: mediana de 11,2 dias, IQR de 3,0 a 46,8 dias.

O primeiro quartil é praticamente o mesmo (3,0 dias). A diferença aparece na parte alta: o IQR de (b) é maior (43,8 contra 39,1 dias), e o maior valor de (b) chega a cerca de 2.866 dias, contra cerca de 1.568 dias em (a). As duas variantes concordam bastante sobre quem é rápido e quem é lento (correlação de Spearman de 0,76 entre elas), mas não dão o mesmo número. Em 190 repositórios o valor de (b) é menor que o de (a), e em 110 é maior.

**Hipótese.** Assim como na RQ01, a Introdução não tem hipótese escrita para o lead time. A comparação é só descritiva.

**Por que (a) e (b) divergem.** As duas variantes respondem a perguntas diferentes.
- Em (a), cada release conta uma vez, e o valor da release é o do commit mais antigo dela. Ou seja, mede quanto tempo a mudança mais velha esperou. Uma única mudança antiga já puxa o valor daquela release para cima, mesmo que todas as outras tenham sido rápidas.
- Em (b), cada commit conta uma vez. Assim, uma release grande, com muitos commits, pesa muito mais do que uma release pequena. Quando um repositório junta muito trabalho em poucas releases grandes e demoradas, o valor de (b) sobe, porque são muitos commits com espera longa. Quando a maioria dos commits entra em releases rápidas e só há uma mudança velha em cada release, (b) fica menor que (a).
- Por isso, no repositório típico os dois ficam próximos (mediana de 12,1 contra 11,2 dias), mas a cauda de (b) é mais pesada: poucas releases enormes e lentas dominam o resultado por commit.

Essa explicação vem de como as duas medidas são construídas e do padrão observado (diferença no topo da distribuição, não no centro). Não testamos formalmente essa causa, e isso deve ser dito na versão final.

**Cuidados com os dados.** Commits com data posterior à release (por causa de rebase ou squash) geram lead time negativo e foram descartados: 805 commits no total. Em 8 repositórios, 11 releases foram ignoradas porque a comparação com a release anterior não estava disponível na API (erro 404). A primeira release da história de cada repositório também é ignorada, pois não tem release anterior para comparar.

Seção: Resultados > RQ03 Taxa de falha das mudanças

**Resultado.**
- CFR (a), pelo CI: mediana de 4,8%, IQR de 2,2% a 11,5%. Em 90 repositórios o valor passa de 10%.
- CFR (b), pela entrega (release corretiva em até 7 dias): mediana de 20,0%, IQR de 6,7% a 36,8%. Em 65 repositórios nenhuma release foi seguida por uma corretiva (CFR de 0%), e em 48 repositórios metade ou mais das releases foi seguida por uma.

**Hipótese.** Esperávamos CFR (a) entre 10% e 25% e CFR (b) abaixo de 10%, com (a) bem mais alto que (b).
- Não confirmada para (a): a mediana de 4,8% ficou abaixo da faixa esperada. A cauda chega perto da faixa (o terceiro quartil é 11,5%), mas o repositório típico fica abaixo.
- Não confirmada para (b): a mediana de 20,0% ficou bem acima dos 10% esperados.
- A ordem esperada também se inverteu: (b) ficou mais alto que (a), e não o contrário.

**Como interpretar.** Estas são explicações possíveis, não testadas. Repositórios populares têm muitas execuções de CI bem-sucedidas, o que dilui as falhas em (a). Em (b), o denominador é pequeno (poucas releases por repositório), então uma ou duas releases corretivas já mudam muito a proporção, o que ajuda a explicar o IQR tão largo. Também pode haver o viés que já tínhamos apontado: quem publica muitas releases em sequência tem mais chance de ter uma "corretiva" em até 7 dias, sem que isso seja necessariamente uma falha. O valor de (b) depende da heurística própria que define a release corretiva, que foi avaliada na validação manual. No total, 305 releases dos últimos 7 dias da janela não puderam ser avaliadas e foram registradas como censuradas, não descartadas.

Seção: Resultados > RQ04 Tempo de recuperação

**Resultado.** A mediana por repositório é de 2,3 horas, com IQR de 0,9 a 9,3 horas. Entre os 277 repositórios com recuperação medida, 86 recuperam em menos de 1 hora, 156 entre 1 hora e 1 dia, e 35 levam 1 dia ou mais (5 deles levam uma semana ou mais; o pior caso tem 560 horas, cerca de 23 dias). A distribuição é bem assimétrica: o IQR (8,5 horas) é bem maior que a mediana.

**Hipótese.** Esperávamos mediana entre 1 hora e 1 dia, distribuição assimétrica com cauda longa e menos de 10% de episódios censurados. Confirmada: a mediana de 2,3 horas está dentro da faixa, a assimetria apareceu como previsto e a censura é baixa (ver abaixo). Não verificamos a parte da hipótese que dizia que os episódios longos e os censurados viriam de workflows secundários, pois essa separação não foi feita na análise.

**Censura.** Dos 20.707 episódios de falha observados, 122 não terminaram dentro da janela (falha sem recuperação até o fim), o que dá 0,6% do total. Os episódios censurados estão espalhados em 83 repositórios; na mediana dos repositórios a proporção de censurados é 0%, e o terceiro quartil é 0,5%. A censura ficou bem abaixo dos 10% esperados. Esses episódios foram contados, não descartados, mas não entram no cálculo da mediana de recuperação, o que tende a subestimar um pouco o tempo real de recuperação.

**Repositórios sem recuperação.** Em 23 dos 300 repositórios não foi possível calcular a recuperação, por isso o n desta métrica é 277. Em 20 deles não houve nenhum episódio de falha seguida de recuperação na janela. Nos outros 3, todos os episódios (4 no total) ficaram censurados. Esses 23 repositórios ficaram de fora da mediana, e não foram tratados como "recuperação zero".
