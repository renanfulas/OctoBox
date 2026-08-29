<!--
ARQUIVO: indice unico de status de todos os planos em docs/plans/.

TIPO DE DOCUMENTO:
- indice de coordenacao (cross-cutting, nao substitui nenhum plano individual)

AUTORIDADE:
- alta para "o que ja foi implementado / o que ainda esta aberto / o que esta bloqueado"
- baixa para o CONTEUDO tecnico de cada frente — isso vive no proprio plano

DOCUMENTO PAI:
- [../reference/documentation-authority-map.md](../reference/documentation-authority-map.md)

QUANDO USAR:
- antes de comecar QUALQUER frente nova (evitar retrabalho em algo ja implementado)
- quando a duvida for "isso ja foi feito?" ou "esse plano ainda vale?"
- como ponto de partida para escolher a proxima frente a atacar

POR QUE ELE EXISTE:
- docs/plans/ tem ~64 arquivos ativos + ~25 arquivados; nenhum deles se auto-atualiza
  quando o codigo evolui, e a maioria nao tem marcador interno de status.
- auditoria feita em 2026-07-28: cruzamento de cada plano contra git log e existencia
  real de arquivo/codigo. Ver metodo na secao final.

O QUE ESTE ARQUIVO FAZ:
1. classifica cada plano ativo em BLOQUEADO / REFERENCIA VIVA / ATIVO / ABERTO /
   PRECISA VERIFICACAO / DORMENTE POR DESIGN.
2. para ABERTO, aponta o proximo passo conhecido (sem re-verificar profundamente).
3. aponta para docs/plans/archive/README.md o que ja foi fechado.

PONTOS CRITICOS:
- este indice e um SNAPSHOT datado (2026-07-28). Regenere/revise antes de confiar
  cegamente nele daqui a alguns meses — nenhum hook mantem isso fresco.
- "REFERENCIA VIVA" != "aberto": sao planos cujo proximo-passo concreto ja foi
  executado, mas que continuam sendo citados por outros docs como padrao/base
  arquitetural — por isso NAO foram movidos para archive/ (moveria quebraria links
  em documentation-authority-map.md, README.md e outros planos ativos).
- se este arquivo divergir do plano individual, o plano individual (com seu proprio
  banner de STATUS, quando existir) vence — este indice e o resumo, nao a fonte.
-->

# Status dos planos — docs/plans/

Snapshot de 2026-07-28. Ver metodo na secao final antes de usar isto como verdade absoluta.

## Bloqueado

Nao falta trabalho tecnico — falta uma decisao/insumo externo.

| Plano | Bloqueado em |
|---|---|
| [student-parq-waiver-entry-gate-corda.md](student-parq-waiver-entry-gate-corda.md) | Onda E (texto vinculante do waiver) — aguardando juridico |
| [growth-engine-activation-plan.md](growth-engine-activation-plan.md) | O proprio plano proibe abrir antes da escala de 80-100 boxes |

## Referência viva (implementado, mas ainda citado como padrão — não arquivar)

O "próximo passo recomendado" de cada um já foi executado, mas o documento continua
sendo a referência que outros planos/docs canônicos apontam para entender o padrão.
Cada um tem um banner `> STATUS:` no topo do próprio arquivo com a evidência.

| Plano | Evidência resumida |
|---|---|
| [theme-implementation-final.md](theme-implementation-final.md) | Tema oficial vigente — autoridade em conflito visual (não é plano de ondas, é referência canônica) |
| [RefactorPayment.md](RefactorPayment.md) | "Encerramento operacional" — virou checklist de manutenção de pagamento |
| [top-layer-architecture-chief-assessment.md](top-layer-architecture-chief-assessment.md) | Parecer arquitetural (não é plano de ondas) |
| [catalog-page-payload-presenter-blueprint.md](catalog-page-payload-presenter-blueprint.md) | `catalog/presentation/{shared,class_grid_page,finance_*_page,student_form_page}.py` existem |
| [operations-workspace-views-refactor-corda.md](operations-workspace-views-refactor-corda.md) | `workspace_views.py` 878→231 linhas; 7 módulos-alvo existem |
| [operations-queries-and-published-history-corda.md](operations-queries-and-published-history-corda.md) | Ondas 1-6 confirmadas; **Onda 7 (poda final) não confirmada** |
| [coach-wod-approval-corda.md](coach-wod-approval-corda.md) | commit `050653b` |
| [wod-smart-paste-corda.md](wod-smart-paste-corda.md) | commit `7346748` + série de commits de Smart Paste |
| [wod-smartplan-spec.md](wod-smartplan-spec.md) | PR #64 + série; só Onda E.7 (pricing) adiada |
| [student-app-grade-wod-rm-corda.md](student-app-grade-wod-rm-corda.md) | commits `c57bbda`, `e97479b`; telas em `templates/student_app/` |
| [student-access-invite-switch-corda.md](student-access-invite-switch-corda.md) | 9/9 itens "concluída" (2026-04-17); `StudentBoxMembership` etc. em produção |

## Ativo agora

| Plano | Nota |
|---|---|
| [signal-mesh-retry-scheduler-runbook.md](signal-mesh-retry-scheduler-runbook.md) | Ligado à frente "Hardening de pagamentos — P1 sweep de dead-letter do Stripe" no `in-flight-board.md` — **snapshot de 2026-06-20/21, confirmar se ainda é real antes de continuar** |

## Aberto — próximo passo conhecido

Não re-verificado a fundo nesta auditoria (classificação herdada da varredura de 2026-07-28).

| Plano | Área | Próximo passo |
|---|---|---|
| [wod-app-alunos-implementation-waves.md](wod-app-alunos-implementation-waves.md) | WOD | Onda A (adapter WhatsApp) |
| [wod-ui-ux-revolution-corda.md](wod-ui-ux-revolution-corda.md) | WOD | Onda 7 (limpeza de CSS/tokens) |
| [wod-test-ownership-split-corda.md](wod-test-ownership-split-corda.md) | WOD | Onda 5 (higiene final e docs) |
| [wod-historico-tabs-corda.md](wod-historico-tabs-corda.md) | WOD | Wave 1 (builders puros primeiro) |
| [wod-llm-in-product-corda-plan.md](wod-llm-in-product-corda-plan.md) | WOD | Hardening do LLM em produção (kill switch, rate limit) — **arquivo ainda não commitado no repo** |
| [coach-session-workout-editor-refactor-corda.md](coach-session-workout-editor-refactor-corda.md) | WOD | Ondas 1-7 (dispatcher, actions, queries, presenter) — Onda 0 já fechada |
| [student-app-smart-cache-plan.md](student-app-smart-cache-plan.md) | Student app | Onda 10 (5 pontos frios restantes da Home) |
| [student-app-views-refactor-corda.md](student-app-views-refactor-corda.md) | Student app | Onda 0 (inventário e cinturão de segurança) |
| [student-identity-staff-views-refactor-corda.md](student-identity-staff-views-refactor-corda.md) | Student app | Onda 0 (inventário e cinturão de segurança) |
| [student-onboarding-funnel-metrics-plan.md](student-onboarding-funnel-metrics-plan.md) | Student app | Onda inicial não confirmada — precisa leitura própria |
| [student-registration-oauth-polish-plan.md](student-registration-oauth-polish-plan.md) | Student app | Checklist com itens `[ ]` em aberto — Ondas 1-5 |
| [intelligent-student-onboarding-plan.md](intelligent-student-onboarding-plan.md) | Student app | Onda 1 (formalizar as 3 jornadas — boa parte do runtime relacionado já existe) |
| [views-foundation-file-movement-plan.md](views-foundation-file-movement-plan.md) | Student app | Onda 1 (student_identity) — **pode estar superado por** `student-app-views-refactor-corda.md` / `student-identity-staff-views-refactor-corda.md` (ambos também abertos) |
| [reception-module-plan.md](reception-module-plan.md) | Recepção | Fase 1 (unificação de linguagem, redução de hardcodes) |
| [reception-phase0-baseline.md](reception-phase0-baseline.md) | Recepção | Fase 0 concluída — segue para Fase 1 do plano acima |
| [manager-copilot-boards-corda-plan.md](manager-copilot-boards-corda-plan.md) | Manager | Onda 1 (inventário de headers hardcoded) |
| [dashboard-pattern-propagation-plan.md](dashboard-pattern-propagation-plan.md) | Front-end | Onda 3 (manager) |
| [finance-darkmode-corda-plan.md](finance-darkmode-corda-plan.md) | Finance | Onda 1 (inventário de hosts) |
| [finance-ia-traditional-foundation-split-plan.md](finance-ia-traditional-foundation-split-plan.md) | Finance | O próprio doc recomenda abrir a fundação de split imediatamente |
| [finance-visual-bridge-risk-inventory.md](finance-visual-bridge-risk-inventory.md) | Finance | Inventário de risco — verificar se os riscos listados ainda procedem |
| [front-end-performance-master-plan.md](front-end-performance-master-plan.md) | Front-end | Sprints 0-8 arquivados/executados; escolher entre financeiro, validação visual ou Lighthouse/trace (sem onda concreta definida) |
| [front-end-restructuring-guide.md](front-end-restructuring-guide.md) | Front-end | Guia de arquitetura CSS — verificar aderência atual |
| [front-legacy-rule-retirement-sdd.md](front-legacy-rule-retirement-sdd.md) | Front-end | Onda 2 (rebaixamento seguro) — Onda 1 já fechada |
| [security-surface-hardening-corda-plan.md](security-surface-hardening-corda-plan.md) | Segurança | Onda 0 (safety rails) — checar sobreposição com S1 de `audit-hardening-sprint-2026-06.md` |
| [deep-access-control-rollout-plan.md](deep-access-control-rollout-plan.md) | Segurança | Fase 1 (mapear o que hoje depende do Django admin) |
| [auto-callables-smoke-retirement-corda.md](auto-callables-smoke-retirement-corda.md) | Testes | Onda 0 (construir substituto estrutural de smoke) |
| [sprint-9-test-followups.md](sprint-9-test-followups.md) | Testes | Follow-up A (independente) + auditoria B.1 |
| [hotspots-builders-and-queries-corda.md](hotspots-builders-and-queries-corda.md) | Arquitetura | Ondas 1-3 parecem prontas; **Ondas 4-7 não verificadas** (`student_queries.py`, `finance_*_analytics.py`) |
| [unit-cascade-architecture-plan.md](unit-cascade-architecture-plan.md) | Arquitetura | Onda 1 (contrato de cascata) |
| [surface-runtime-contract-corda-plan.md](surface-runtime-contract-corda-plan.md) | Arquitetura | Doc fundacional — próximo passo não claro num skim, precisa leitura própria |
| [cross-box-operational-intelligence-corda.md](cross-box-operational-intelligence-corda.md) | Arquitetura | Onda 1 (taxonomia oficial) — estágio inicial, provavelmente não iniciado |
| [scale-transition-20-100-open-multitenancy-plan.md](scale-transition-20-100-open-multitenancy-plan.md) | Escala | Fase 1 — overlap com `schema-per-tenant-migration-plan.md` |
| [schema-per-tenant-migration-plan.md](schema-per-tenant-migration-plan.md) | Escala | Sprint 1 Tier 1 — parcialmente iniciado (Bucket B landed 2026-05-19) |
| [phase1-closed-beta-20-boxes-corda.md](phase1-closed-beta-20-boxes-corda.md) | Rollout | Onda 1 (auditoria real da Fase 1) |
| [hostinger-vps-first-client-corda-plan.md](hostinger-vps-first-client-corda-plan.md) | Infra | Checklist de go-live (14 itens) — **não confirmado cumprido** |
| [lead-import-pipeline-corda-plan.md](lead-import-pipeline-corda-plan.md) | Leads | "Critério de pronto" próprio não confirmado atingido |
| [leads-ml-foundation-and-network-intelligence-plan.md](leads-ml-foundation-and-network-intelligence-plan.md) | Leads/ML | Estágio inicial — provavelmente **compartilha o mesmo bloqueio de escala** de `growth-engine-activation-plan.md` (não confirmado) |
| [leads-ml-technical-execution-guide.md](leads-ml-technical-execution-guide.md) | Leads/ML | Guia técnico do plano acima — mesmo status |
| [octobox-mobile-execution-plan.md](octobox-mobile-execution-plan.md) | Mobile | Passo 1 (garantir acesso e sessão mobile) |
| [octobox-mobile-screen-blueprint.md](octobox-mobile-screen-blueprint.md) | Mobile | Blueprint de telas — acompanha o plano acima |
| [vertical-sky-beam-execution-roadmap.md](vertical-sky-beam-execution-roadmap.md) | Cross-capability | Fase 1, seguindo a conclusão de `reception-phase0-baseline.md` |
| [vertical-sky-beam-readiness-guide.md](vertical-sky-beam-readiness-guide.md) | Cross-capability | Guia de prontidão — acompanha o roadmap acima |
| [top-layer-architecture-execution-plan.md](top-layer-architecture-execution-plan.md) | Arquitetura | Fase 0/1 já fechadas — próximo: frentes de Alert Siren / Red Beacon |
| [PaymentUI.md](PaymentUI.md) | Pagamentos | Ondas 1-4 — sem evidência de conclusão, verificar contra a UI atual antes de retomar |
| [divulgacao-launch-plan.md](divulgacao-launch-plan.md) | Comercial | Ciclo semanal 80/20 agente/humano (indicação, cold e-mail, LinkedIn, landing/SEO, Instagram/Facebook) — revisado em 2026-08-29; ver [divulgacao-pipeline-tracker.md](divulgacao-pipeline-tracker.md) para o estado do funil |

## Precisa verificação manual (não dá pra confirmar só pelo repositório)

| Plano | Por quê |
|---|---|
| [octobox-phase1-sql-wave-plan.md](octobox-phase1-sql-wave-plan.md) | Só 1 commit de criação, nenhum marcador interno de progresso; downstream (`schema-per-tenant-migration-plan.md`) sugere que ao menos parte foi feita |
| [wod-post-publication-operational-loop.md](wod-post-publication-operational-loop.md) | 21 ondas, escrito em tom de "já funciona" — não auditado onda a onda nesta passada |
| [jobs-retry-cron-runbook.md](jobs-retry-cron-runbook.md) | Depende de instalação manual de cron/systemd fora do repo (na VPS) |
| [lead-import-night-scheduler-linux.md](lead-import-night-scheduler-linux.md) | Idem — infra fora do repo |

## Dormente por design (não é "aberto" no sentido acionável)

| Plano | Por quê |
|---|---|
| [finance-ml-foundation-refactor-watch-plan.md](finance-ml-foundation-refactor-watch-plan.md) | O próprio doc diz para não refatorar agora — é gatilho, não plano ativo |
| [operational-contact-memory-migration-plan.md](operational-contact-memory-migration-plan.md) | Idem |

## Coordenação (não é plano de execução)

| Doc | Papel |
|---|---|
| [in-flight-board.md](in-flight-board.md) | Quadro de frentes em voo entre sessões/worktrees. Sua "Fila de higiene" é snapshot datado — regenerar com o comando descrito no próprio arquivo antes de confiar |

## Fechados / arquivados

Ver [archive/README.md](archive/README.md) para a lista completa (25 documentos até este snapshot,
incluindo 5 movidos nesta auditoria de 2026-07-28).

## Método desta auditoria (2026-07-28)

1. Levantamento inicial: skim de cabeçalho + seções de status de cada plano, cruzado com `git log --oneline -5 -- <path>`.
2. Para os candidatos a "implementado": confirmação por (a) existência real dos arquivos/módulos prescritos, (b) commits com mensagem batendo a entrega descrita.
3. Antes de mover qualquer arquivo para `archive/`: checagem de referências (`grep -rl <filename> docs/ README.md CLAUDE.md`) — 8 candidatos a "implementado" foram **mantidos no lugar** por serem citados por `documentation-authority-map.md`, `README.md`, mapas de ownership ou outros planos ainda ativos.
4. Links relativos corrigidos nos arquivos efetivamente movidos (o `../` muda de nível ao entrar em `archive/`).
5. Os ~7 casos "status ambíguo" da varredura original foram investigados individualmente; 4 continuam sem confirmação possível a partir do repositório (listados acima).
6. Os ~30 planos "aberto com próximo passo claro" **não foram re-verificados** nesta rodada — a tabela acima reflete a classificação da varredura, não uma nova auditoria de cada um.
