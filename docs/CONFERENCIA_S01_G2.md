# Conferência S01-G2 — nº de releases e lead time de 2 repositórios

Portão de conferência da S01 (Issue #21, dono B). Objetivo: verificar, fora do pipeline,
se o número de releases e o lead time gravados em `data/metricas.csv` batem com o que o
GitHub mostra.

Executada em 2026-10-21 sobre o `data/metricas.csv` da `main` (amostra final de 300 repos).

## Como foi feito

- **Repositórios:** `expressjs/express` e `zellij-org/zellij`. Escolhidos entre os que têm
  poucas releases na janela (5 e 6), nenhuma pré-release, nenhum `compare` 404 e nenhum
  lead time negativo, para que a conta pudesse ser refeita à mão release por release.
- **Fonte independente:** um script avulso de ~40 linhas (abaixo), com `urllib` da
  biblioteca padrão, sem token e **sem importar nada de `pipeline/` ou `metricas/`**. Ele
  refaz a regra do enunciado do zero: releases com `draft=false` e `prerelease=false`
  publicadas na janela (01/10/2025 a 30/09/2026, UTC); base da primeira release da janela =
  última release não-pré-release anterior à janela; commits por `compare/{anterior}...{R}`
  com paginação; data do commit = `commit.author.date`.
- **Conferência visual:** a lista de releases foi aberta também no site
  ([express](https://github.com/expressjs/express/releases),
  [zellij](https://github.com/zellij-org/zellij/releases)).

## Resultado

| Repositório | Releases na janela (CSV) | Releases (conferência) | Lead time (a) CSV | Lead time (a) conferência | Lead time (b) CSV | Lead time (b) conferência |
|---|---:|---:|---:|---:|---:|---:|
| expressjs/express | 5 | 5 | 445,872 d | 445,872 d | 406,926 d | 406,926 d |
| zellij-org/zellij | 6 | 6 | 19,977 d | 19,977 d | 19,066 d | 19,066 d |

**Os dois repositórios batem exatamente**, nas releases e nas duas variantes do lead time.

### Releases e lead time (a) por release

`expressjs/express` (base anterior à janela: `v5.1.0`):

| Anterior → R | Publicada (UTC) | Commits | Lead time (a) |
|---|---|---:|---:|
| v5.1.0 → 4.22.0 | 2025-12-01 16:19 | 23 | 445,87 d |
| 4.22.0 → v5.2.0 | 2025-12-01 16:21 | 244 | 4.162,55 d |
| v5.2.0 → v5.2.1 | 2025-12-01 20:54 | 2 | 0,10 d |
| v5.2.1 → v4.22.1 | 2025-12-01 20:55 | 25 | 446,06 d |
| v4.22.1 → v4.22.2 | 2026-05-11 18:54 | 6 | 158,87 d |

`zellij-org/zellij` (base anterior à janela: `v0.43.1`):

| Anterior → R | Publicada (UTC) | Commits | Lead time (a) |
|---|---|---:|---:|
| v0.43.1 → v0.44.0 | 2026-03-23 08:03 | 139 | 226,78 d |
| v0.44.0 → v0.44.1 | 2026-04-07 13:07 | 34 | 12,29 d |
| v0.44.1 → v0.44.2 | 2026-05-05 06:43 | 18 | 27,67 d |
| v0.44.2 → v0.44.3 | 2026-05-13 07:49 | 13 | 6,70 d |
| v0.44.3 → v0.45.0 | 2026-08-20 09:05 | 82 | 107,07 d |
| v0.45.0 → v0.45.1 | 2026-08-28 09:21 | 19 | 4,08 d |

**Lead time conferido em detalhe:** `zellij v0.44.3`. Publicada em 2026-05-13 07:49 UTC; o
`compare v0.44.2...v0.44.3` tem 13 commits, e o mais antigo é de 6,70 dias antes da
publicação. As medianas por repositório (19,98 d em (a); 19,07 d em (b)) são as do CSV.

## Achado para o artigo

O `expressjs/express` mantém **duas linhas de versão em paralelo** (4.x e 5.x) e publica
releases das duas no mesmo dia. Como a "release anterior" é a anterior **por data**, o
pipeline compara `4.22.0...v5.2.0`, que atravessa as duas linhas e traz commits de anos
atrás: o lead time dessa release dá 4.162 dias. A mediana por repositório amortece o caso
(445,9 d), mas o valor ainda é inflado pelas comparações entre linhas. É o mesmo problema
de *backport* que levou à v2 da heurística de release corretiva
(`artigo/metodologia_definicoes.md`) e deve entrar em **Ameaças à validade — construto**:
o lead time por `compare` com a release anterior por data supõe uma única linha de
releases.

## Script usado

```python
"""Conferência independente (S01-G2): nº de releases e lead time, sem usar o pipeline."""
import json, re, statistics, sys, urllib.request
from datetime import datetime, timezone

S = datetime(2025, 10, 1, tzinfo=timezone.utc)
E = datetime(2026, 9, 30, 23, 59, 59, tzinfo=timezone.utc)

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})) as r:
        nxt = re.search(r'<([^>]+)>; rel="next"', r.headers.get("Link") or "")
        return json.load(r), (nxt.group(1) if nxt else None)

def d(s): return datetime.fromisoformat(s.replace("Z", "+00:00"))

repo = sys.argv[1]
rels, url = [], f"https://api.github.com/repos/{repo}/releases?per_page=100"
while url:
    page, url = get(url); rels += page
pub = sorted((r for r in rels if not r["draft"] and not r["prerelease"] and r["published_at"]), key=lambda r: r["published_at"])
jan = [r for r in pub if S <= d(r["published_at"]) <= E]
antes = [r for r in pub if d(r["published_at"]) < S]
print(repo, "releases na janela, não-pré:", len(jan))
base = antes[-1:] + jan
por_release, por_commit = [], []
for ant, r in zip(base, base[1:]):
    commits, url = [], f"https://api.github.com/repos/{repo}/compare/{ant['tag_name']}...{r['tag_name']}?per_page=100"
    while url:
        page, url = get(url); commits += page["commits"]
    rd = d(r["published_at"])
    lts = [(rd - d(c["commit"]["author"]["date"])).total_seconds() / 86400 for c in commits]
    lts = [x for x in lts if x >= 0]
    lt = max(lts) if lts else None
    por_release.append(lt); por_commit += lts
    print(f"  {ant['tag_name']} -> {r['tag_name']}  publicada {r['published_at']}  commits={len(commits)}  lead(a)={lt}")
print("  lead_time_a (mediana) =", statistics.median([x for x in por_release if x is not None]))
print("  lead_time_b (mediana) =", statistics.median(por_commit))
```

Uso: `python conferir.py expressjs/express` (sem token cabe na cota anônima de 60
requisições por hora: ~15 chamadas para os dois repositórios).
