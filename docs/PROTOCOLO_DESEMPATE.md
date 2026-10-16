# Protocolo de consenso e desempate da amostra-ouro (S02-O2.4)

Este documento registra como os rótulos independentes dos três avaliadores viram o
**rótulo de consenso** usado na avaliação da heurística de release corretiva (RQ03 b) e
no fator "tipo do projeto" (RQ06). O processamento é feito por `validacao/consolidar.py`:

```
python -m validacao.consolidar          # lê rotulos/A.csv, B.csv, C.csv; sem token, sem rede
```

Saídas: `rotulos/kappa.csv` (concordância por dimensão) e `rotulos/consenso.csv` (rótulo de
consenso por item). Código de saída `0` quando todos os itens têm consenso, `1` quando falta
alguma planilha e `2` quando há rótulo inválido ou empate 1-1-1 sem decisão registrada.

## 1. Rotulagem independente

- Amostra: 60 repositórios sorteados com `df.sample(n=60, random_state=42)` e 5 releases por
  repositório (semente 42), gerados por `validacao/gerar_planilhas.py`. São 60 itens por
  repositório (`tipo_projeto`, `entregas_reais`) e 300 itens por release (`corretiva`).
- Cada avaliador preencheu só o próprio arquivo (`rotulos/A.csv`, `B.csv`, `C.csv`), sem
  consultar os outros e sem ver a saída da heurística, que ainda não existia (Onda 3).
- Antes do cálculo, `carregar_rotulos` confere que as três planilhas têm os mesmos itens na
  mesma ordem, que nenhum rótulo está vazio e que todos pertencem ao vocabulário de
  `validacao.concordancia.DIMENSOES`. Maiúsculas e espaços nas pontas são ignorados.

## 2. Regra de consenso

1. **Unânime** (3-0): o rótulo comum.
2. **Maioria simples** (2-1): o rótulo de dois avaliadores. O voto vencido fica registrado
   na coluna `votos_<dimensao>`.
3. **Empate 1-1-1** (só é possível em `tipo_projeto` e `entregas_reais`; `corretiva` é
   binária): o item fica `pendente` e é **decidido em reunião** dos três avaliadores. A
   decisão é registrada em `rotulos/decisoes_reuniao.csv`, com as colunas
   `nivel,repo,tag,dimensao,rotulo,justificativa`. O script aplica a decisão e marca a
   origem como `reuniao`. Ele recusa decisões para itens que não estão empatados, de modo
   que uma reunião não pode reverter uma maioria.

A coluna `origem_<dimensao>` de `consenso.csv` vale `unanime`, `maioria`, `reuniao` ou
`pendente`.

**O consenso não é alterado depois de conhecida a saída da heurística.** O refino da
heurística (S02-O3.3) parte deste arquivo como verdade de referência; mudar um rótulo para
melhorar o F1 é proibido (docs/ISSUES.md).

## 3. Resultado

Executado em 2026-10-16 sobre os três arquivos de rótulos da `main`.

| Dimensão | Itens | Kappa de Fleiss | Concordância observada | Unânimes | Maioria | Reunião |
|---|---:|---:|---:|---:|---:|---:|
| `tipo_projeto` | 60 | 0,912 | 0,944 | 55 | 5 | 0 |
| `entregas_reais` | 60 | 0,383 | 0,967 | 57 | 3 | 0 |
| `corretiva` | 300 | 0,860 | 0,933 | 270 | 30 | 0 |

Não houve empate 1-1-1, então **nenhuma decisão de reunião foi necessária** e não existe
`rotulos/decisoes_reuniao.csv`. Todos os 420 itens têm consenso por unanimidade ou maioria.

Distribuição do consenso:

- `tipo_projeto`: 27 aplicação/serviço, 22 biblioteca/framework, 9 ferramenta CLI, 2 outro.
- `entregas_reais`: 58 sim, 2 incerto (asterinas/asterinas e vuejs/vitepress).
- `corretiva`: 115 sim, 185 não.

### Leitura dos kappas (achados para o artigo)

- Pela escala de Landis e Koch, `tipo_projeto` (0,91) e `corretiva` (0,86) têm concordância
  **quase perfeita**. O critério de release corretiva é aplicável de forma consistente por
  pessoas diferentes, o que sustenta usá-lo como referência para a heurística.
- `entregas_reais` tem kappa **razoável** (0,38), apesar de 57 dos 60 repositórios serem
  unânimes. É o **paradoxo do kappa**: quase todos os rótulos são `sim`, a concordância
  esperada por acaso fica muito alta, e qualquer divergência pesa muito no kappa. Por isso
  a tabela também reporta a concordância observada (P̄ de Fleiss, 0,97). As três
  divergências (capcut-mate, asterinas, vitepress) envolvem `incerto`: releases sem notas,
  com notas "TODO" ou só versões *alpha*. O critério "entrega real" é ambíguo exatamente
  nesses casos, e isso deve ser discutido no artigo.

## 4. Ameaças à validade da rotulagem

- **Uso de ferramentas automáticas pelos avaliadores.** Os rótulos de A foram produzidos com
  auxílio de LLM. B usou um script de pré-rotulagem por palavras-chave
  (`validacao/pre_rotular.py`, Issue #29) e revisou as sugestões. Ferramentas que leem o
  mesmo texto (notas e mensagens de commit) tendem a errar nos mesmos casos, o que pode
  inflar a concordância. O kappa deve ser lido como limite superior da concordância
  entre julgamentos humanos independentes. Pelo mesmo motivo, a pré-rotulagem por
  palavras-chave se parece com a heurística a ser avaliada, o que pode favorecer o F1.
- **Critério de "corretiva".** O avaliador A tratou como não corretivas as releases que
  misturam funcionalidades novas e correções. Como o consenso tem 115 corretivas em 300, uma
  heurística que marque qualquer release com `fix` tende a ter precisão menor contra ele.
