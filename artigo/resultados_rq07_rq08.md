# Resultados RQ07 e RQ08 (rascunho)

> Rascunho para montar no Overleaf, continuação de `resultados_rq05_rq06.md`. Os números vêm de `analise/saida/rq07_*.csv`, `tabela_rq08.csv` e `tabela_rq08_comparacao.csv`, gerados por `analise/rq07.py` e `analise/rq08.py` a partir de `data/metricas.csv` (300 repositórios). Os números marcados como "apoio" foram calculados à parte, sobre os mesmos arquivos, só para a interpretação.

Seção: Resultados > RQ07 Sensibilidade à definição operacional

**Desenho.** Classificamos cada repositório em Elite, High, Medium ou Low em três combinações de definições. O tempo de recuperação é o mesmo nas três.

| Combinação | Unidade de deploy | Lead time | CFR |
|---|---|---|---|
| C1 (referência) | release | (a) por release | (a) CI |
| C2 | release + pré-release | (b) por commit | (b) entrega |
| C3 | tag | (b) por commit | (a) CI |

Repositórios com alguma métrica ausente ficam sem classificação na combinação. São 23 em C1 e C2 (sem recuperação) e 47 em C3 (sem recuperação ou sem lead time por tag). Cada par é comparado só nos repositórios classificados nas duas combinações.

**Resultado.**

| Par | n | Mudaram de categoria | % | Kappa de Cohen (linear) |
|---|---:|---:|---:|---:|
| C1 × C2 | 277 | 90 | 32,5% | 0,50 |
| C1 × C3 | 253 | 61 | 24,1% | 0,66 |
| C2 × C3 | 253 | 85 | 33,6% | 0,50 |

Distribuição das categorias:

| Categoria | C1 | C2 | C3 |
|---|---:|---:|---:|
| Elite | 21 | 4 | 23 |
| High | 117 | 111 | 135 |
| Medium | 121 | 145 | 87 |
| Low | 18 | 17 | 8 |
| Sem classificação | 23 | 23 | 47 |

- Entre um quarto e um terço dos repositórios muda de categoria conforme a combinação. A concordância vai de moderada (0,50) a substancial (0,66).
- As mudanças são quase sempre de **um degrau**. Saltos de dois degraus são raros: 7 em C1 × C2, 3 em C1 × C3 e 4 em C2 × C3. Nenhum repositório passa de Elite para Low ou o contrário.
- **C2 rebaixa.** De C1 para C2, 62 repositórios descem e 28 sobem; Elite cai de 21 para 4.
- **C3 eleva.** De C1 para C3, 46 sobem e 15 descem.

**Qual escolha mais mexe na classificação** (apoio: notas por métrica que mudam em cada par):
- **CFR:** é a maior fonte de mudança quando as duas combinações usam CFRs diferentes. A nota de CFR muda em 176 repositórios em C1 × C2 e em 166 em C2 × C3. O CFR (b) é bem maior que o (a): medianas de 20,0% e 4,8%. Por isso, a C2 tira muitos repositórios das faixas Elite e High de estabilidade.
- **Lead time:** a nota muda em 121 repositórios em C1 × C2 e em 118 em C1 × C3. O lead time por commit fica menor quando a unidade inclui pré-releases ou tags (medianas de 9,9 e 6,7 dias, contra 12,1 dias em C1), o que melhora a nota.
- **Unidade de deploy:** é a que menos pesa. A nota de frequência muda em 34 repositórios (C1 × C2) e em 60 (C1 × C3). Só 120 repositórios têm pré-releases na janela e 126 têm mais tags que releases.
- Como a categoria geral é a mediana das quatro notas, arredondada para baixo, muitas mudanças de nota não mudam a categoria. Por exemplo, a nota de CFR muda em 176 repositórios entre C1 e C2, mas só 90 mudam de categoria.

**Hipótese.** Esperávamos que entre um quarto e metade dos repositórios mudasse de categoria em pelo menos um par, kappa moderado (0,4 a 0,6), mudanças quase sempre de um degrau e a menor concordância em C1 × C2.
- **Confirmada para a proporção:** 24,1% a 33,6%. O par C1 × C3 fica no limite inferior da faixa.
- **Parcialmente confirmada para o kappa:** C1 × C2 e C2 × C3 (0,50) ficam na faixa, mas C1 × C3 (0,66) fica acima.
- **Confirmada para os degraus:** as mudanças são de um degrau, e não há trocas de três degraus.
- **Parcialmente confirmada para o par menos concordante:** C1 × C2 empata com C2 × C3 (kappa 0,50). O que os dois pares têm em comum é a troca de CFR (a) por (b). Na hipótese, apontamos o lead time como a escolha que mais mexeria na classificação, mas foi o CFR.

Seção: Resultados > RQ08 (bônus) Rework rate

**Resultado.** A rework rate é a proporção de releases corretivas, pela mesma heurística do CFR (b), sobre o total de releases da janela.

| Medida | n | Mediana | Q1 a Q3 |
|---|---:|---:|---|
| Rework rate | 300 | 0,40 | 0,20 a 0,62 |
| CFR (b) | 300 | 0,20 | 0,07 a 0,37 |
| Rework − CFR (b), por repositório | 300 | 0,10 | 0,01 a 0,29 |

As duas medidas estão correlacionadas (Spearman ρ = 0,68, p < 0,001), mas a rework rate é maior que o CFR (b) em 234 repositórios, igual em 53 e menor em 13 (Figura `rq08_rework_vs_cfr.png`).

**Em que difere do CFR (b).** A rework rate conta toda release corretiva, enquanto o CFR (b) só conta a release que é seguida por uma corretiva em até 7 dias. Uma correção publicada semanas depois da release anterior entra na rework rate, mas não no CFR (b). Por isso, a rework rate tende a ser maior, e há repositórios com CFR (b) igual a 0 e rework rate positiva. A rework rate também não depende da janela de 7 dias, que liga o CFR (b) à frequência de deploy (ver RQ05).
