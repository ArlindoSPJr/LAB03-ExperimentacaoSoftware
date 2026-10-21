# Discussão (rascunho)

> Rascunho para montar no Overleaf. Retoma os resultados das RQ01 a RQ08 e a pergunta da RQ07: as conclusões são robustas à definição adotada?

Seção: Discussão > O que surpreendeu

- **A ordem dos CFRs se inverteu.** Esperávamos o CFR de CI (a) bem acima do CFR de entrega (b), e aconteceu o contrário: 4,8% contra 20,0% de mediana. Repositórios populares têm muitas execuções de CI bem-sucedidas, que diluem as falhas. Já o CFR (b) depende de uma heurística e de poucas releases por repositório.
- **O CFR (b) está ligado à frequência pela própria definição.** A correlação forte entre frequência e CFR (b) (ρ = 0,58) parece vir em boa parte da janela de 7 dias: quem publica toda semana quase sempre tem uma próxima release dentro da janela. A rework rate, que não usa essa janela, correlaciona pouco com a frequência.
- **A idade pesa mais que o número de contribuidores.** Projetos novos são os mais rápidos em frequência, lead time e recuperação. Mais contribuidores vieram com lead time **maior**, ao contrário do esperado, provavelmente porque contribuidores e idade andam juntos.
- **A estabilidade de CI não difere entre grupos.** Nenhum fator da RQ06 está associado ao CFR (a).

Seção: Discussão > As conclusões são robustas à definição?

Só em parte. A RQ07 mostra que um quarto a um terço dos repositórios muda de categoria DORA quando trocamos a definição, com concordância apenas moderada a substancial. A escolha que mais pesa é a variante do CFR: trocar o proxy de CI pelo de entrega rebaixa muitos repositórios. A unidade de deploy (release, release + pré-release ou tag) pesa pouco.

Consequências para as outras RQs:
- Os resultados descritivos das RQ01 a RQ04 valem **para a definição adotada** (C1). A posição relativa dos repositórios muda pouco: as mudanças são de um degrau e o kappa nunca fica abaixo de 0,50. Mas a proporção em cada faixa DORA muda bastante. Em C2, por exemplo, só 4 repositórios são Elite.
- As conclusões da RQ05 já dependiam da variante do CFR (correlação fraca em (a) e forte em (b)), e a RQ07 reforça que o CFR (b) leva a outro retrato do desempenho.
- A RQ06 usou só as métricas da C1. Não verificamos se os mesmos fatores apareceriam em C2 ou C3.

Seção: Discussão > Ameaças à validade

- **Hipóteses de RQ01 e RQ02 escritas depois da coleta.** Como avisado na Introdução, essas duas hipóteses não são previsões feitas antes dos dados e não devem ser lidas como confirmação.
- **Heurística de release corretiva.** O CFR (b) e a rework rate dependem dela. A versão adotada (v3) tem F1 de 0,734 contra o consenso da amostra-ouro, mas foi ajustada e avaliada na mesma amostra de 300 releases, o que tende a superestimar o F1.
- **Proxies.** Release não é deploy em produção, e falha de CI não é falha em produção. Bibliotecas não "deployam"; quem faz isso são os usuários.
- **Datas de commit.** O lead time usa `commit.author.date`, distorcida por rebase e squash. Os valores negativos foram descartados e contados.
- **Dados incompletos.** 23 repositórios não têm recuperação, e 26 não têm lead time por tag. Nas variantes, repositórios com muitas unidades tiveram os compares limitados a 100.
- **Tipo do projeto com n = 60.** Pouco poder estatístico, e dois grupos têm 9 e 2 repositórios.
