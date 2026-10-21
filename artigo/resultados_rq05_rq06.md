# Resultados RQ05 e RQ06 (rascunho)

> Rascunho para montar no Overleaf, continuação de `resultados.md` (RQ01 a RQ04). Os números vêm de `analise/saida/tabela_rq05.csv`, `tabela_rq06.csv` e `rq06_grupos.csv`, gerados por `analise/rq05.py` e `analise/rq06.py` a partir de `data/metricas.csv` (300 repositórios). As hipóteses citadas são as da Introdução, escritas antes de ver os dados. Os números marcados como "apoio" foram calculados à parte, sobre o mesmo CSV, só para a interpretação.

Seção: Resultados > RQ05 Frequência de deploy × taxa de falha

**Resultado.** Calculamos a correlação de Spearman entre a frequência de deploy (RQ01) e cada variante do CFR (RQ03), com os 300 repositórios.

| Variante do CFR | n | ρ de Spearman | p-valor |
|---|---:|---:|---:|
| (a) CI | 300 | 0,13 | 0,019 |
| (b) entrega | 300 | 0,58 | < 0,001 (1,4 × 10⁻²⁸) |

As duas correlações são **positivas**: quem publica mais releases tende a ter CFR maior. Mas a força é muito diferente.
- Com o CFR (a), a correlação é fraca (ρ = 0,13). É estatisticamente significativa ao nível de 5%, mas a frequência explica muito pouco da ordem dos repositórios no CFR de CI. Na prática, os três quartis mais lentos de frequência têm CFR (a) mediano quase igual (4,2%, 4,7% e 4,5%); só o quartil mais rápido sobe, para 8,0% (apoio).
- Com o CFR (b), a correlação é moderada a forte (ρ = 0,58). O CFR (b) mediano cresce a cada quartil de frequência: 10,0%, 14,3%, 25,8% e 43,8% (apoio).

As Figuras `rq05a_freq_cfr_ci.png` e `rq05b_freq_cfr_entrega.png` mostram a dispersão, com a frequência em escala logarítmica, porque ela varia de menos de 0,1 a 12 releases por semana.

**Hipótese.** Esperávamos correlação fraca (|ρ| < 0,3) nas duas variantes e, se houvesse sinal no CFR (b), levemente negativo.
- **Confirmada para (a):** ρ = 0,13 está dentro da faixa de correlação fraca. O sinal positivo também era uma das possibilidades que levantamos: repositórios mais ativos rodam mais workflows e ficam mais expostos a testes instáveis.
- **Não confirmada para (b):** a correlação é forte e positiva, e não fraca e negativa.

**Por que o CFR (b) correlaciona tanto com a frequência.** Na Introdução já tínhamos apontado um viés mecânico, e os dados são coerentes com ele. O CFR (b) marca uma release como falha quando a **próxima** release, em até 7 dias, é corretiva. Quem publica uma release por semana ou mais quase sempre tem uma próxima release dentro de 7 dias; quem publica uma vez por mês quase nunca tem. Além disso, projetos com cadência alta costumam publicar muitas versões de *patch*, que a heurística tende a marcar como corretivas. Um indício a favor dessa explicação: a *rework rate* (proporção de releases corretivas, que não depende da janela de 7 dias) tem correlação bem menor com a frequência (ρ = 0,19, apoio). Ou seja, boa parte do ρ = 0,58 parece vir da própria definição do CFR (b), e não de projetos rápidos entregarem mudanças piores. Essa explicação não foi testada formalmente.

**Velocidade × estabilidade e o DORA.** O DORA afirma que velocidade e estabilidade não são um *trade-off*: as equipes de alto desempenho vão bem nas duas. Nossos dados não confirmam isso de forma clara, mas também não mostram um *trade-off* forte:
- pelo CI, a relação é fraca, e só os repositórios mais rápidos têm um CFR um pouco maior;
- pela entrega, aparece um aparente *trade-off*, mas ele é em grande parte explicado pela forma como a métrica é construída.

Em nenhum dos casos o resultado mostra que ser rápido **causa** mais falhas. Spearman mede associação, não causalidade. Há fatores que podem influenciar as duas métricas ao mesmo tempo, como o tamanho e a atividade do projeto, a idade do repositório e o hábito de publicar *patches* com frequência. Também não estamos medindo equipes, como nas pesquisas do DORA, e sim repositórios open-source, com releases como aproximação de deploy.

Seção: Resultados > RQ06 Características associadas ao desempenho DORA

**Desenho.** Comparamos as quatro métricas DORA (frequência, lead time (a), CFR (a) e recuperação) entre os grupos de cinco fatores:
- **linguagem principal**: 7 linguagens com pelo menos 10 repositórios, e as demais em "Outras" (8 grupos);
- **estrelas**, **contribuidores** e **idade**: quartis (Q1 = menores valores). Os cortes de contribuidores são 83, 193 e 491; os de idade, 2,9, 6,7 e 10,5 anos;
- **tipo do projeto**: rotulado na amostra-ouro, então só existe para os 60 repositórios sorteados (27 aplicação/serviço, 22 biblioteca/framework, 9 ferramenta CLI e 2 outro).

Todos os fatores têm mais de dois grupos, por isso usamos Kruskal-Wallis nos 20 testes (5 fatores × 4 métricas), com tamanho de efeito ε² = H/(n − 1). Os 20 p-valores foram corrigidos juntos pelo método de Holm. Para o ε², usamos as faixas 0,01 (pequeno), 0,08 (médio) e 0,26 (grande). Na recuperação, n é 277 (58 no tipo do projeto), porque 23 repositórios não têm nenhum episódio de recuperação completo.

**Resultado.** 6 dos 20 testes continuam significativos depois da correção de Holm:

| Fator | Métrica | n | H | ε² | Efeito | p (Holm) |
|---|---|---:|---:|---:|---|---:|
| Idade | Lead time (a) | 300 | 67,6 | 0,23 | médio | < 0,001 |
| Idade | Frequência | 300 | 40,2 | 0,13 | médio | < 0,001 |
| Linguagem | Lead time (a) | 300 | 39,8 | 0,13 | médio | < 0,001 |
| Contribuidores | Lead time (a) | 300 | 31,2 | 0,10 | médio | < 0,001 |
| Linguagem | Frequência | 300 | 24,8 | 0,08 | médio | 0,012 |
| Idade | Recuperação | 277 | 17,4 | 0,06 | pequeno | 0,009 |

Os outros 14 testes não são significativos (p de Holm ≥ 0,93). Em especial:
- **nenhum fator** está associado ao CFR (a) (ε² entre 0,001 e 0,040);
- **estrelas** não estão associadas a nenhuma métrica (ε² ≤ 0,024);
- **tipo do projeto** não está associado a nenhuma métrica (ε² ≤ 0,058; p de Holm = 1,0).

**Direção das diferenças** (medianas por grupo, `rq06_grupos.csv`):
- **Idade.** Os repositórios mais novos (Q1, até 2,9 anos) são os mais rápidos: publicam 0,82 releases por semana, contra 0,27 a 0,31 nos dois quartis mais antigos. O lead time mediano é de 1,9 dia no Q1, 11,3 dias no Q2 e cerca de 31 dias no Q3 e no Q4. A recuperação também é mais rápida no Q1 (1,4 hora, contra 6,5 horas no Q3 e 3,3 horas no Q4).
- **Linguagem.** TypeScript e JavaScript têm os menores lead times (5,3 e 5,8 dias) e TypeScript a maior frequência (0,73 por semana). C++ está no extremo oposto: 60,9 dias de lead time e 0,22 release por semana. Java também é lento no lead time (36,1 dias).
- **Contribuidores.** O lead time **cresce** com o número de contribuidores: 4,0 dias no Q1 (até 83), 7,7 no Q2, 18,9 no Q3 e 24,8 no Q4 (mais de 491). A frequência não muda entre os quartis.

**Hipótese.** Esperávamos que o número de contribuidores fosse o fator mais associado às métricas de velocidade, que o tipo do projeto também pesasse, que estrelas e idade tivessem efeito pequeno e que, no geral, os efeitos fossem pequenos e poucos significativos.
- **Contribuidores — não confirmada.** O fator só está associado ao lead time, e na direção **oposta** à esperada: mais contribuidores, lead time maior.
- **Idade — não confirmada.** Esperávamos que os efeitos se compensassem, mas a idade é o fator mais forte: está associada a três das quatro métricas, sempre com os projetos novos mais rápidos.
- **Tipo do projeto — não confirmada**, mas com pouco poder estatístico: são só 60 repositórios, e dois grupos têm 9 e 2 repositórios. A ausência de significância aqui não mostra que o tipo não importa.
- **Estrelas — confirmada:** nenhum efeito relevante.
- **Linguagem — parcialmente confirmada:** havia diferenças ligadas ao ecossistema, como previsto, mas com efeito médio, e não pequeno.
- **CFR (a) igual entre grupos — confirmada:** nenhum fator está associado ao CFR de CI.
- **Efeitos pequenos e poucos significativos — parcialmente:** 14 dos 20 testes não são significativos, mas os 6 que são têm efeito médio em 5 casos.

**Cuidados na interpretação.**
- **Associação não é causa.** Kruskal-Wallis diz que as distribuições diferem entre os grupos, não por quê. Não fizemos comparações par a par entre grupos, então as direções acima são descritivas (medianas por grupo).
- **Os fatores não são independentes.** Idade e número de contribuidores estão correlacionados (ρ = 0,42, apoio): projetos antigos acumulam contribuidores. O efeito dos contribuidores no lead time pode ser, em parte, o efeito da idade. Projetos antigos também publicam menos releases na janela (ρ = −0,33 entre idade e nº de releases, apoio), e releases mais espaçadas acumulam commits mais antigos, o que aumenta o lead time (a) por construção.
- **Linguagem e idade também se misturam.** A idade mediana dos repositórios TypeScript é de 4,8 anos, contra 11,1 anos dos de C++ (apoio). Parte da diferença entre linguagens pode ser efeito da idade. Por outro lado, JavaScript tem lead time baixo mesmo com repositórios antigos (9,9 anos de mediana), o que sugere que a linguagem não é só um reflexo da idade. Separar os dois efeitos exigiria um modelo multivariado, que está fora do escopo do enunciado.
