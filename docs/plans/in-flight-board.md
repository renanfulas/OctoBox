<!--
ARQUIVO: quadro leve de frentes em voo (branches/worktrees) entre sessoes paralelas.

TIPO DE DOCUMENTO:
- board operacional de coordenacao (cross-cutting, nao por frente)

AUTORIDADE:
- alta para "o que esta sendo tocado agora" e higiene de branch/worktree
- baixa para tese/arquitetura (isso vive em architecture/plans especificos)

DOCUMENTO PAI:
- [../reference/documentation-authority-map.md](../reference/documentation-authority-map.md)

QUANDO USAR:
- antes de comecar QUALQUER frente nova (evitar colisao)
- depois de mergear um PR (evitar branch/worktree orfa)
- quando aparecer "isso ja foi feito por outra sessao?"

POR QUE ELE EXISTE:
- o fluxo multi-worktree/multi-sessao e potente, mas gera dois problemas:
  (1) duas sessoes implementam a MESMA coisa (colisao); (2) branches squash-merged
  que ninguem deleta (orfas). Em 2026-06-20 duas sessoes tocaram o superdev em
  paralelo — uma ja estava mergeada (#131).
- este quadro e o ponto unico de "o que esta em voo" + a higiene pos-merge.

PONTOS CRITICOS:
- a "Fila de higiene" e um SNAPSHOT datado; regenere com o comando da secao
  "Gerar a verdade agora" — nao confie na fila antiga.
- `git branch --no-merged` ENGANA com squash merge (ver secao dedicada).
- ATIVO.
-->

# Quadro in-flight — frentes, branches e worktrees em voo

Ponto único de coordenação entre sessões/worktrees paralelos. Objetivo duplo: **não colidir** (duas sessões na mesma feature) e **não deixar órfã** (branch/worktree de PR já mergeado).

## Protocolo — antes de começar uma frente

1. `git -C C:\dev\OctoBox fetch origin`
2. `gh pr list --state open` e `gh pr list --state merged --limit 40` (a feature já existe/foi feita?)
3. Olhe a tabela **Frentes ativas declaradas** abaixo + as branches remotas.
4. **Declare sua frente** na tabela (1 linha) antes de codar.
5. Trabalhe em **worktree isolado fora do OneDrive** (`%LOCALAPPDATA%\octobox-wt\<frente>`), branch a partir de `origin/main`, `git add` com paths explícitos.

## Protocolo — ao terminar (anti-órfã)

Depois que o PR mergear:

1. `git push origin --delete <branch>` (ou ative "auto-delete head branches" no GitHub).
2. `git -C C:\dev\OctoBox worktree remove <path>` (remova o worktree).
3. Apague sua linha da tabela **Frentes ativas declaradas**.

## Por que `git branch --no-merged` engana

Com **squash merge** (o padrão deste repo), o commit do `main` é novo — a branch original nunca aparece como ancestral. Logo `--no-merged` lista branches **já mergeadas** como se estivessem vivas. Detecção correta = cruzar branch remota com **PRs mergeados**:

### Gerar a verdade agora (PowerShell)

```powershell
$merged = (gh pr list --repo renanfulas/OctoBox --state merged --limit 60 --json headRefName | ConvertFrom-Json).headRefName
git -C C:\dev\OctoBox fetch origin --quiet
git -C C:\dev\OctoBox branch -r --format='%(refname:short)' |
  Where-Object { $_ -notmatch 'origin/HEAD|origin/main' } |
  ForEach-Object {
    $b = $_ -replace '^origin/',''
    [pscustomobject]@{ Branch=$b; Status= if ($merged -contains $b) {'ÓRFÃ (mergeada) → deletar'} else {'viva (checar PR aberto)'} }
  } | Sort-Object Status, Branch | Format-Table -Auto
git -C C:\dev\OctoBox worktree list
```

---

## Frentes ativas declaradas

> Mantida à mão. 1 linha por frente realmente em andamento. Remova ao mergear.

| Frente | Branch | Worktree | Dono/sessão | Status |
|---|---|---|---|---|
| Docs de prontidão (registry + este quadro) | `docs/ops-readiness` | `octobox-wt/ops-docs` | sessão 2026-06-20 | PR aberto |
| Hardening de pagamentos — guardrails P0 (rate-limit, mark_paid, copy) | `feat/payment-p0-guardrails` | `octobox-wt/payment-p0-guardrails` | sessão 2026-06-21 | P0 em andamento (verificação no CI) |

---

## Fila de higiene — snapshot 2026-06-20

Branches remotas que o `--no-merged` lista mas **já estão mergeadas** (squash) → **deletar**. Regenere com o comando acima.

| Branch remota | PR mergeado | Ação |
|---|---|---|
| `feat/superdev-support-membership` | #131 | deletar |
| `feat/tenant-isolation-logs-exports` | #134 | deletar |
| `refactor/security-throttle-consolidation` | #135 | deletar |
| `test/stripe-onboarding-coverage` | #133 | deletar |
| `docs/student-app-prints` | #132 | deletar |
| `test/student-app-coverage` | #130 | deletar |
| `feat/student-app-perfil-rows` | #129 | deletar (checked out em `C:\dev\OctoBox` — trocar p/ `main` antes) |
| `feature/student-app-v2-shell` | #128 | deletar |
| `feat/workouts-juliana-bruno-update` | #127 | deletar |
| `fix/tenant-boundary-skip-locale` | #126 | deletar |
| `chore/coverage-ratchet-74` | #125 | deletar |
| `test/student-identity-presenters-coverage` | #119 | deletar |
| `test/student-identity-membership-actions-coverage` | #118 | deletar |
| `test/student-identity-invite-actions-coverage` | #117 | deletar |
| `test/student-identity-delivery-actions-coverage` | #116 | deletar |
| `docs/adr-013-superdev-support-access` | #136 | deletar |
| `docs/update-handover-fase-2` | — (sem PR) | **investigar** — antiga (2026-05-25), abandonar ou retomar |

**Worktrees a remover** (apontam para branch já mergeada): `superdev`, `tenant-iso`, `sec-throttle`, `stripe-cov`, `student-tests`, `workouts-juliana-bruno`, `css-import-cache`, `docs-prints`, `ledger`, `adr-superdev`. Comando: `git -C C:\dev\OctoBox worktree remove <path>`.

> O diretório principal `C:\dev\OctoBox` está em `feat/student-app-perfil-rows` (mergeada) — convém voltar para `main` para não confundir HEAD entre sessões.

## Referências

- Memória do fluxo: trabalhar em worktree isolado fora do OneDrive, `add` com paths explícitos.
- [../rollout/environment-activation-registry.md](../rollout/environment-activation-registry.md) — o irmão "mergeado ≠ ativado".
