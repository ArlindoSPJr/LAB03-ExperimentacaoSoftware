# Introdução — hipóteses informais (rascunho)

> Rascunho das hipóteses de cada RQ, escritas **antes de ver os dados** (enunciado, seção 8). A versão final vai para a Introdução no template SBC (Overleaf). Cada integrante preenche as RQs da sua Issue de docs (ver `docs/ISSUES.md`, S01-D1 a S01-D3).

## RQ03 — Taxa de falha das mudanças entregues (S01-D1)

**Hipótese:** o CFR pelo proxy de CI (a) será bem mais alto que o CFR pelo proxy de entrega (b). Esperamos uma mediana de CFR (a) entre 10% e 25% e uma mediana de CFR (b) abaixo de 10%.

**Por quê:**
- Um workflow que falha no default branch nem sempre é um defeito entregue ao usuário. Testes instáveis (*flaky*), falhas de infraestrutura do runner, lint e jobs de documentação também contam como falha em (a).
- Em (b), só conta como falha uma release seguida, em até 7 dias, por uma release corretiva. Projetos populares costumam ter revisão de código e CI antes da release, o que filtra boa parte dos defeitos.
- Esperamos também que (a) e (b) tenham **correlação fraca** entre si, porque medem coisas diferentes: estabilidade do pipeline × estabilidade do que é entregue.

## RQ05 — Frequência de deploy × taxa de falha (S01-D1)

**Hipótese:** não haverá *trade-off* entre velocidade e estabilidade. A correlação de Spearman entre frequência de deploy e CFR será **fraca** (|ρ| < 0,3) nas duas variantes. Se houver sinal, esperamos ρ levemente **negativo** para o CFR (b): quem publica com mais frequência publica releases menores e falha menos.

**Por quê:**
- O DORA afirma que equipes de alto desempenho são rápidas e estáveis ao mesmo tempo; esperamos que os dados open-source não contradigam isso de forma forte.
- No CFR (a), um efeito oposto pode aparecer: repositórios mais ativos rodam mais workflows e ficam mais expostos a testes instáveis, o que puxaria ρ para perto de zero ou levemente positivo.
- No CFR (b), há um viés mecânico a considerar: quem publica muitas releases tem mais chances de ter uma release "corretiva" em até 7 dias da anterior, o que pode criar correlação positiva artificial. Isso será discutido junto com a validação da heurística.

## RQ04 — Tempo de recuperação após falha de CI (S01-D2)

**Hipótese:** a recuperação será rápida na maioria dos repositórios. Esperamos uma mediana por repositório entre **1 hora e 1 dia** (faixa *High* do DORA), com distribuição muito assimétrica: muitos episódios de poucos minutos e uma cauda longa de episódios de vários dias. A proporção de episódios censurados deve ser baixa, abaixo de 10% na mediana dos repositórios.

**Por quê:**
- Em projetos populares e ativos, um default branch "vermelho" bloqueia o trabalho de todos os contribuidores, então há pressão para corrigir logo, com um *revert* ou com um novo commit.
- Boa parte das falhas de CI vem de testes instáveis (*flaky*) ou de problemas de infraestrutura do runner. Nesses casos, o próximo push costuma passar sem nenhuma correção, o que gera episódios curtos e puxa a mediana para baixo.
- A cauda longa deve vir de workflows secundários (documentação, publicação, jobs com dependências externas), que ficam quebrados por dias sem bloquear ninguém, e de falhas perto de fins de semana ou feriados.
- Episódios censurados devem se concentrar nesses workflows secundários e nas falhas ocorridas perto do fim da janela.

## RQ06 — Características associadas a melhor desempenho DORA (S01-D2)

**Hipótese:** o **número de contribuidores** será o fator mais associado ao desempenho nas métricas de velocidade. Repositórios com mais contribuidores devem ter frequência de deploy maior, lead time menor e recuperação mais rápida, mas **não** CFR (a) menor. O **tipo do projeto** também deve pesar: aplicações e serviços publicam com mais frequência que bibliotecas e frameworks. Popularidade (estrelas) e idade devem ter efeito pequeno. Esperamos, no geral, tamanhos de efeito **pequenos** (ε² < 0,06 ou |δ| < 0,33), com poucas diferenças significativas depois da correção de Holm.

**Por quê:**
- Mais contribuidores significam mais mudanças chegando ao default branch e mais gente disponível para corrigir um build quebrado. Isso favorece frequência, lead time e recuperação. Também significa mais pushes e mais execuções de CI, o que expõe o repositório a mais falhas instáveis e pode deixar o CFR (a) igual ou maior.
- Bibliotecas e frameworks tendem a agrupar mudanças em releases maiores e menos frequentes, para não quebrar quem depende delas (compatibilidade, versionamento semântico). Aplicações e ferramentas podem publicar a cada mudança. Como o tipo só será rotulado para 60 repositórios, a comparação terá pouco poder estatístico.
- Estrelas medem atenção, não processo de entrega: muitos repositórios populares são estáveis e publicam pouco. Por isso esperamos efeito fraco da popularidade.
- A idade pode puxar em dois sentidos: projetos antigos têm processos de release mais maduros e automatizados, mas também mais cautela com compatibilidade. Esperamos que os dois efeitos se compensem.
- Na linguagem, esperamos diferenças pequenas ligadas ao ecossistema (por exemplo, ecossistemas com publicação automatizada em registros de pacotes publicando com mais frequência). As linguagens com poucos repositórios serão agrupadas em "Outras".

## RQ01, RQ02 e RQ07 — hipóteses do integrante A

> **Aviso de transparência (leia antes das hipóteses).** O enunciado pede hipóteses escritas **antes** de ver os dados. Pelo plano do projeto, as hipóteses de RQ03, RQ05, RQ04 e RQ06 acima foram escritas na primeira etapa, antes dos dados. **Isso não vale para RQ01 e RQ02**: o texto destas duas foi escrito **depois da coleta**, quando os resultados dessas questões já existiam. Elas se apoiam no conhecimento geral sobre as métricas DORA e sobre o ritmo de publicação de projetos open-source, e **não foram ajustadas para combinar com o que foi encontrado**. Mesmo assim, não devem ser lidas como previsões feitas antes dos dados, e a Discussão precisa dizer isso. A hipótese de RQ07 também foi escrita sem consultar nenhum resultado de RQ07, porque essa análise ainda não tinha sido feita quando o texto foi escrito. RQ08 (bônus) fica de fora deste rascunho, porque o grupo ainda não decidiu se vai fazê-la.

### Seção: Introdução > Hipótese RQ01 (escrita depois da coleta)

**Hipótese:** a maioria dos repositórios populares publica poucas versões por semana. Esperamos uma mediana de deploys por semana **bem abaixo de 1**, na faixa de uma publicação a cada um ou dois meses (algo entre 0,1 e 0,3 por semana). A distribuição deve ser muito assimétrica: uma maioria que publica de vez em quando e uma cauda pequena de projetos que publicam várias vezes por semana. Pelos cortes de referência do enunciado, esperamos que poucos repositórios cheguem à faixa Elite nessa métrica (7 ou mais por semana), e que a maior parte fique em Médio ou Baixo.

**Por quê:**
- Projetos de código aberto costumam agrupar mudanças em versões numeradas, que exigem decidir o número da versão, escrever notas e, muitas vezes, avisar quem depende do projeto. Isso desestimula publicar a cada mudança.
- Bibliotecas e frameworks, que são comuns entre os projetos populares, têm um motivo extra para publicar menos: cada versão nova impõe custo a quem usa.
- Uma minoria de projetos automatiza a publicação (por exemplo, uma versão a cada mudança aceita ou a cada noite). Esses projetos puxam a cauda para cima, mas não a mediana.
- Usar a versão publicada como unidade de deploy é uma escolha conservadora: ela deixa de fora projetos que entregam continuamente sem marcar versões. Por isso, a métrica provavelmente subestima a frequência real desses projetos.

### Seção: Introdução > Hipótese RQ02 (escrita depois da coleta)

**Hipótese:** o tempo entre a mudança e a publicação será de **semanas**, e não de dias, na maioria dos repositórios. Esperamos que a variante por versão (que olha para o commit mais antigo de cada versão) dê valores **claramente maiores** que a variante por commit (que olha para todos os commits). Como ordem de grandeza, esperamos uma mediana da variante por versão entre duas semanas e dois meses, e uma mediana da variante por commit entre alguns dias e três semanas. Em termos de faixa DORA, esperamos que a variante por versão coloque a maioria dos repositórios em Médio ou Baixo, e que a variante por commit os coloque em Alto ou Médio; poucos em Elite nas duas.

**Por quê:**
- A diferença entre as duas variantes é quase mecânica. Na variante por versão, cada versão é representada pelo seu commit **mais antigo**, que é o pior caso daquela versão. Na variante por commit, esse commit antigo é só um entre muitos, e a maioria dos commits entra perto da data da publicação. Por isso, a variante por versão tende a ser maior.
- Quanto menos frequente a publicação, mais tempo o commit espera pela próxima versão. Então esperamos que lead time e frequência de deploy andem juntos: repositórios que publicam pouco terão lead time maior.
- Esse tempo é espera pela próxima versão, não tempo de desenvolvimento. Num projeto que publica a cada dois meses, um commit pode ficar até dois meses parado depois de aceito, sem que ninguém esteja trabalhando nele.
- Existe um limite para a nossa medida: usamos a data de autoria do commit. Mudanças que ficaram muito tempo em revisão antes de serem aceitas, ou commits reaplicados em outro ramo, podem aumentar o tempo medido. Esperamos uma cauda longa à direita.

### Seção: Introdução > Hipótese RQ07 (escrita antes de qualquer resultado)

**Hipótese:** a classificação DORA de um repositório **depende de forma relevante** da definição escolhida. Esperamos que entre **um quarto e metade** dos repositórios mude de categoria quando comparamos pelo menos um par de combinações de definições, e que a concordância ponderada entre as classificações seja apenas **moderada** (kappa entre 0,4 e 0,6), longe de uma concordância quase perfeita. Esperamos que a mudança de categoria seja quase sempre de **um degrau** (por exemplo, de Alto para Médio), e que trocas de três degraus (de Elite para Baixo) sejam raras.

**Por quê:**
- A escolha entre as duas variantes de lead time deve ser a que mais mexe na classificação. Como os valores da variante por versão tendem a ser bem maiores que os da variante por commit, trocar uma pela outra deve empurrar muitos repositórios para outra faixa nessa métrica.
- A escolha entre as duas variantes de taxa de falha também pesa. Esperamos que a variante pela entrega dê taxas menores que a variante pelo CI (ver a hipótese de RQ03), o que melhora a nota de estabilidade de vários repositórios.
- Contar pré-releases como deploy aumenta a frequência só nos repositórios que usam esse recurso, que são minoria. Esperamos pouca mudança vinda só dessa escolha.
- Contar tags no lugar de versões publicadas deve mudar bastante a frequência nos projetos que criam uma tag por mudança ou por build, e pouco nos demais. Também esperamos que alguns repositórios tenham tags demais para serem medidos por completo.
- Como a classificação geral usa a mediana das quatro notas (arredondada para baixo), uma mudança em uma só métrica nem sempre muda a categoria final. Isso deve **amortecer** o efeito, e é por isso que esperamos mudanças de um degrau, e não de vários.
- Entre os três pares de combinações, esperamos a **menor concordância** no par formado pela combinação de referência (versões publicadas, lead time por versão, taxa de falha pelo CI) e pela combinação com versões mais pré-releases, lead time por commit e taxa de falha pela entrega, porque esse par difere nas três escolhas ao mesmo tempo. Os outros dois pares diferem em duas escolhas cada e devem concordar mais.
- Consequência para o resto do artigo: se esta hipótese se confirmar, as conclusões sobre RQ01 a RQ06 valem **para a definição adotada**, e não de forma geral. Cabe dizer isso com clareza na Discussão.
