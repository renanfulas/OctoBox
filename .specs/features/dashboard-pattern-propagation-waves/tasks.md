# Dashboard Pattern Propagation Waves Tasks

**Feature**: `.specs/features/dashboard-pattern-propagation-waves/spec.md`
**Status**: Draft

---

## Execution Plan

### Phase 1: Planning and Governance

T1 -> T2 -> T3

### Phase 2: Shared First

T4 -> T5

### Phase 3: Family Waves

T6 -> T7 -> T8

### Phase 4: Final Validation

T9

---

## Task Breakdown

### T1: Consolidate wave strategy in docs

**What**: registrar o plano oficial da frente em `docs/plans`
**Where**: `docs/plans/dashboard-pattern-propagation-plan.md`
**Depends on**: None
**Reuses**: `docs/plans/front-legacy-rule-retirement-sdd.md`
**Done when**:

- [ ] o plano descreve C.O.R.D.A.
- [ ] as ondas estao nomeadas
- [ ] cada onda tem objetivo, risco e criterio de pronto

### T2: Create SDD feature record

**What**: registrar a frente em `.specs/features`
**Where**: `.specs/features/dashboard-pattern-propagation-waves/`
**Depends on**: T1
**Reuses**: `.specs/features/canonical-hero-card-variants/`
**Done when**:

- [ ] existem `spec.md`, `design.md`, `tasks.md` e `corda-plan.md`
- [ ] a frente fica rastreavel no workflow SDD

### T3: Lock execution guardrails

**What**: fixar os skills e a regra shared-first como parte da frente
**Where**:
1. `.specs/features/dashboard-pattern-propagation-waves/design.md`
2. `docs/plans/dashboard-pattern-propagation-plan.md`
**Depends on**: T2
**Done when**:

- [ ] `octobox-design` esta nomeado como autoridade visual
- [ ] `CSS Front end architect` esta nomeado como autoridade de ownership e hygiene
- [ ] a regra shared-first aparece como criterio de decisao

### T4: Execute Onda 1 Foundation Shared

**What**: promover primeiro os padroes compartilhados
**Where**: design system e shell
**Depends on**: T3
**Done when**:

- [ ] os ajustes reutilizaveis saem do dashboard para o shared
- [ ] nenhuma copia local ampla e usada como atalho

### T5: Validate page anchor before family rollout

**What**: escolher e validar uma pagina ancora da proxima familia
**Where**: primeira pagina da onda ativa
**Depends on**: T4
**Done when**:

- [ ] a pagina ancora confirma o padrao
- [ ] o que e shared versus local fica evidente

### T6: Execute Onda 2 Catalog Core

**What**: aplicar shared nas paginas do catalogo
**Where**:
1. `students`
2. `finance`
3. `finance-plan-form`
4. `class-grid`
**Depends on**: T5
**Done when**:

- [x] `students` foi estabilizada sem reintroduzir snapshot indevido
- [x] `finance-plan-form` recebeu adaptacao local segura
- [x] `class-grid` recebeu adaptacao local segura
- [x] a familia de catalogo validada (`students`, `finance-plan-form`, `class-grid`) parece do mesmo predio visual
- [x] cada pagina validada preserva sua composicao local
- [ ] `finance` segue como trilha manual separada e nao bloqueia a onda

### T7: Execute Onda 3 Operations Roles

**What**: aplicar shared nas paginas operacionais por papel
**Where**:
1. `manager`
2. `reception`
3. `coach`
4. `dev`
**Depends on**: T6
**Done when**:

- [x] as roles compartilham familia visual
- [x] cada role continua com identidade operacional propria
- [x] `owner` esta registrada como ancora visual oficial da Onda 3
- [x] `manager` foi usada como pagina de entrada da execucao
- [x] `reception` foi ajustada depois da ancora e corrigida apos inspecao visual
- [x] `coach` foi ajustada depois da ancora
- [x] `dev` foi ajustada por ultimo e corrigida apos inspecao visual

### Nota operacional de transicao

- `finance` saiu do fechamento da Onda 2 e agora existe como pendencia manual rastreada
- a entrada da Onda 3 esta liberada mesmo com `finance` aberta

### T8: Execute Onda 4 Special Cases

**What**: tratar superficies especiais sem poluir o design system
**Where**:
1. `reports-hub`
2. `access-overview`
3. `whatsapp-placeholder`
4. `system-map`
5. `operational-settings`
**Depends on**: T7
**Done when**:

- [ ] casos especiais foram absorvidos sem excecao global desnecessaria
- [x] `reports-hub` foi classificado como heranca controlada da familia principal
- [x] `access-overview` foi classificada como heranca controlada da familia principal
- [x] `whatsapp-placeholder` foi classificado como isolamento local e placeholder visivel
- [ ] `system-map` foi classificado como trilho de guia com semantica propria
- [ ] `operational-settings` foi classificada como trilho de governanca com semantica propria

### T9: Execute Onda 5 Polish and Validation

**What**: fechar dark/light, mobile e limpeza residual
**Where**: superficies tocadas nas ondas anteriores
**Depends on**: T8
**Done when**:

- [ ] dark e light continuam da mesma familia
- [ ] mobile nao perde hierarquia
- [ ] sobras locais desnecessarias foram reduzidas
