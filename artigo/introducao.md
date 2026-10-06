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
