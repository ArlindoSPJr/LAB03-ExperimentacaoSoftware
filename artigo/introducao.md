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
