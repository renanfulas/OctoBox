<!--
ARQUIVO: indice da categoria rollout.

TIPO DE DOCUMENTO:
- indice operacional

AUTORIDADE:
- alta para navegacao da categoria

DOCUMENTO PAI:
- [../reference/documentation-authority-map.md](../reference/documentation-authority-map.md)

QUANDO USAR:
- quando a duvida for "onde mora o checklist X" ou "qual runbook usar agora"
- quando precisar saber o que ja foi executado e o que continua ativo

POR QUE ELE EXISTE:
- impede que docs de rollout virem zumbis sem ninguem saber qual ainda vale
- separa runbooks recorrentes de evidencias datadas
- explicita o status (ATIVO, CONCLUIDO, PARCIAL, ARQUIVADO) de cada peca

PONTOS CRITICOS:
- este indice nao substitui o runbook em si; ele apenas aponta
- se um doc mudar de status, atualizar aqui tambem
- arquivados em `archive/` nao governam operacao atual; existem apenas como evidencia historica
-->

# Rollout — indice operacional

Pasta que abriga **runbooks, checklists, playbooks e evidencias** de toda operacao real do OctoBox.

A regra de leitura e simples:

1. ATIVO = use hoje
2. CONCLUIDO = leitura historica (mantido por referencia)
3. PARCIAL = parte feita, parte pendente — abrir antes de prosseguir
4. ARQUIVADO = movido para `archive/` (superado ou snapshot datado)

---

## Primeiro box (frente principal)

| Doc | Status |
|-----|--------|
| [first-box-onboarding-runbook.md](first-box-onboarding-runbook.md) | ATIVO (runbook generico, reutilizavel) |
| [first-box-rollout-plan.md](first-box-rollout-plan.md) | ATIVO (plano de rollout) |
| [first-box-pilot-intake-sheet.md](first-box-pilot-intake-sheet.md) | ATIVO (template de coleta) |
| [first-box-system-setup-checklist.md](first-box-system-setup-checklist.md) | ATIVO (checklist generico) |
| [first-box-production-execution-checklist.md](first-box-production-execution-checklist.md) | ATIVO (execucao Fase 1) |
| [first-box-endorfina-cross-setup-plan.md](first-box-endorfina-cross-setup-plan.md) | CONCLUIDO (Sprint 5 em 2026-05-23) |
| [first-box-endorfina-onboarding-day-checklist-2026-04-15.md](first-box-endorfina-onboarding-day-checklist-2026-04-15.md) | CONCLUIDO (data passou) |
| [pilot-support-playbook.md](pilot-support-playbook.md) | ATIVO (fase piloto assistida) |

---

## Beta interno

| Doc | Status |
|-----|--------|
| [beta-internal-release-gate.md](beta-internal-release-gate.md) | ATIVO (gate de release) |
| [beta-role-test-agenda.md](beta-role-test-agenda.md) | ATIVO (agenda de teste por papel) |
| [beta-team-test-script.md](beta-team-test-script.md) | ATIVO (script de execucao) |

---

## Sprint 5 — multi-tenant em producao

| Doc | Status |
|-----|--------|
| [sprint5-tenant-rollout-checklist.md](sprint5-tenant-rollout-checklist.md) | **PARCIAL** (Fases 1-5 executadas em 2026-05-23; Fases 6-8 pendentes) |

Para a evidencia da execucao, consultar:
- workflows: `sprint5-stage0-discover`, `sprint5-stage1-backup-shared`, `sprint5-stage2-provision`, `sprint5-stage3-migrate-and-smoke`
- marco em [../history/mudaram-o-nivel-do-projeto.md](../history/mudaram-o-nivel-do-projeto.md)

---

## Fase 1 (beta fechado ate 20 boxes)

| Doc | Status |
|-----|--------|
| [phase1-closed-beta-operations-matrix.md](phase1-closed-beta-operations-matrix.md) | ATIVO (matriz de acompanhamento) |
| [restore-and-rollback-drill.md](restore-and-rollback-drill.md) | ATIVO (drill repetivel) |

Evidencia datada arquivada em [archive/phase1-execution-evidence-2026-04-13.md](archive/phase1-execution-evidence-2026-04-13.md).

---

## VPS Hostinger (rota de producao atual)

| Doc | Status |
|-----|--------|
| [hostinger-vps-bootstrap-checklist.md](hostinger-vps-bootstrap-checklist.md) | ATIVO (preparo da maquina) |
| [hostinger-vps-production-deploy.md](hostinger-vps-production-deploy.md) | ATIVO (deploy oficial) |
| [hostinger-vps-post-deploy-smoke-checklist.md](hostinger-vps-post-deploy-smoke-checklist.md) | ATIVO (smoke pos-deploy) |
| [hostinger-vps-backup-and-restore-runbook.md](hostinger-vps-backup-and-restore-runbook.md) | ATIVO (backup + restore) |
| [hostinger-vps-restore-postgres.md](hostinger-vps-restore-postgres.md) | ATIVO (template de restore curto) |
| [hostinger-vps-update-and-rollback-runbook.md](hostinger-vps-update-and-rollback-runbook.md) | ATIVO (update + rollback) |

Rota antiga (Hostgator) arquivada em [archive/hostgator-vps-observability-and-backup.md](archive/hostgator-vps-observability-and-backup.md).

---

## Homologacao PostgreSQL

| Doc | Status |
|-----|--------|
| [postgres-homolog-provisioning-checklist.md](postgres-homolog-provisioning-checklist.md) | ATIVO (checklist generico) |
| [postgres-homolog-restore-runbook.md](postgres-homolog-restore-runbook.md) | ATIVO (runbook generico) |
| [postgres-homolog-restore-checklist-template.md](postgres-homolog-restore-checklist-template.md) | ATIVO (template para preencher por rodada) |

Rodadas preenchidas datadas em [archive/postgres-homolog-provisioning-round-2026-04-13.md](archive/postgres-homolog-provisioning-round-2026-04-13.md) e [archive/postgres-homolog-restore-checklist-2026-04-13.md](archive/postgres-homolog-restore-checklist-2026-04-13.md).

---

## Playbooks operacionais

| Doc | Status |
|-----|--------|
| [operations-realtime-war-room-playbook.md](operations-realtime-war-room-playbook.md) | ATIVO (rodada controlada multi-papel) |
| [student-drawer-realtime-concurrency-playbook.md](student-drawer-realtime-concurrency-playbook.md) | ATIVO (concorrencia drawer) |
| [student-onboarding-5-minute-smoke-checklist.md](student-onboarding-5-minute-smoke-checklist.md) | ATIVO (smoke curto recorrente) |

---

## Generais — deploy + backup + restore

| Doc | Status |
|-----|--------|
| [backup-guide.md](backup-guide.md) | ATIVO (guia conceitual de backup) |
| [deploy-homologation.md](deploy-homologation.md) | ATIVO (guia de deploy em homolog) |
| [homologation-deploy-checklist.md](homologation-deploy-checklist.md) | ATIVO (checklist do guia anterior) |
| [local-format-restore-runbook.md](local-format-restore-runbook.md) | ATIVO (restore local) |

---

## Arquivados (`archive/`)

| Doc | Motivo |
|-----|--------|
| [archive/phase1-execution-evidence-2026-04-13.md](archive/phase1-execution-evidence-2026-04-13.md) | Snapshot datado de execucao da Fase 1 |
| [archive/postgres-homolog-provisioning-round-2026-04-13.md](archive/postgres-homolog-provisioning-round-2026-04-13.md) | Snapshot datado de provisionamento |
| [archive/postgres-homolog-restore-checklist-2026-04-13.md](archive/postgres-homolog-restore-checklist-2026-04-13.md) | Snapshot datado de checklist preenchido |
| [archive/hostgator-vps-observability-and-backup.md](archive/hostgator-vps-observability-and-backup.md) | Hostgator superseded — producao migrou para Hostinger |

---

## Regra de manutencao

1. quando um doc terminar sua funcao, adicionar `STATUS: CONCLUIDO` no front-matter
2. quando virar snapshot datado de algo ja executado, mover para `archive/`
3. quando uma rota for substituida por outra, mover a antiga para `archive/` com nota no commit
4. **nao apagar docs** — arquivar preserva contexto historico
5. atualizar este README sempre que mover ou adicionar um doc

---

## Marcos registrados

Eventos de altitude (sprint cruzando marco simbolico) sao registrados em [../history/mudaram-o-nivel-do-projeto.md](../history/mudaram-o-nivel-do-projeto.md).

Em especial, o primeiro box em producao (2026-05-23) tem secao propria em "Nota sobre o primeiro aluno em producao".
