# Darkmode Theme Hardening Tasks

**Feature**: `.specs/features/darkmode-theme-hardening/spec.md`
**Phase**: Wave 1 audit and execution planning
**Status**: Draft

---

## Task List

### T1: Lock the Wave 1 audit classification

- **What**: confirm and document the three Wave 1 buckets: token gaps, canonical primitive drift, and local residual debt
- **Where**: `.specs/features/darkmode-theme-hardening/design.md`
- **Depends on**: existing audit evidence from `tokens.css`, `shell.css`, `workspace.css`, `cards.css`, `hero.css`, `topbar.css`, `student_form_stepper.css`, `intakes.css`, `import-progress.css`
- **Requirement**: supports darkmode governance and shared system consistency goals
- **Done when**:
  1. the design doc names the three buckets
  2. each major darkmode hotspot is assigned to one bucket
  3. the document makes clear which layer owns the fix

### T2: Translate the approved palette into implementation direction

- **What**: define how `design-guideless.md` becomes semantic theme behavior rather than local styling
- **Where**: `.specs/features/darkmode-theme-hardening/design.md`
- **Depends on**: T1
- **Requirement**: approved palette alignment and restrained premium-dark direction
- **Done when**:
  1. the approved neon palette is listed by semantic role
  2. canonical hosts are named for each design concern
  3. the design doc explicitly forbids bypassing the token layer

### T3: Prioritize the Wave 2 implementation order

- **What**: create the safest execution order for token, primitive, and local cleanup work
- **Where**: `.specs/features/darkmode-theme-hardening/design.md`
- **Depends on**: T1
- **Requirement**: reduce regression risk while hardening darkmode
- **Done when**:
  1. shared token and shell work are scheduled before local cleanup
  2. high-risk shared files are clearly ordered
  3. local residual debt files are listed after canonical hosts

### T4: Break Wave 1 into actionable engineering tasks

- **What**: define the concrete work items needed to leave audit mode and enter implementation mode
- **Where**: `.specs/features/darkmode-theme-hardening/tasks.md`
- **Depends on**: T1, T2, T3
- **Requirement**: execution readiness
- **Done when**:
  1. tasks are concrete and scoped
  2. dependencies are clear
  3. the first implementation wave can start without re-discovering the problem

---

## Wave 2 Preview Tasks

These are not executed yet in Wave 1.
They are the approved next queue after the audit is locked.

### T5: Expand the darkmode semantic token vocabulary

- **What**: align the approved premium-dark palette with token roles for root, glass surfaces, support text, chrome, scrollbars, and accent semantics
- **Where**: `static/css/design-system/tokens.css`
- **Depends on**: T1, T2, T3, T4
- **Done when**:
  1. dark premium root is represented semantically
  2. role accents map to red, yellow, green, blue, and purple as approved
  3. scrollbar and shell-chrome concerns have token-backed values

### T6: Harden the shell and canonical shared surfaces

- **What**: reduce hardcoded atmosphere values in shell, cards, hero, and topbar by routing them through the expanded token layer
- **Where**:
  1. `static/css/design-system/shell.css`
  2. `static/css/design-system/components/cards.css`
  3. `static/css/design-system/components/hero.css`
  4. `static/css/design-system/topbar.css`
- **Depends on**: T5
- **Done when**:
  1. direct dark-only repainting is reduced
  2. canonical components consume the new token vocabulary
  3. glass treatment remains subtle and readable

### T7: Reduce workspace-level dark authority drift

- **What**: shrink `workspace.css` from local theme engine toward composition and scoped overrides
- **Where**: `static/css/design-system/workspace.css`
- **Depends on**: T5, T6
- **Done when**:
  1. workspace panels and hero overrides rely more on tokens and canonical primitives
  2. repeated raw values are reduced
  3. shared visual ownership becomes clearer

### T8: Clean the highest-priority local residual debt

- **What**: migrate local hardcoded darkmode styling out of the most drift-heavy page files
- **Where**:
  1. `static/css/catalog/student_form_stepper.css`
  2. `static/css/onboarding/intakes.css`
  3. `static/css/catalog/import-progress.css`
- **Depends on**: T5, T6, T7
- **Done when**:
  1. status colors use semantic roles
  2. page surfaces inherit shared system behavior more cleanly
  3. `body[data-theme="dark"]` local repainting shrinks in touched scopes

### T9: Validate premium-dark restraint across representative screens

- **What**: verify that the approved palette improved the product without making the UI loud or unstable
- **Where**: representative dark and light mode surfaces after implementation
- **Depends on**: T8
- **Done when**:
  1. cards, topbar, helper copy, and status surfaces feel related
  2. light mode remains coherent
  3. neon accents stay role-driven and restrained

### T10: Normalize residual dashboard card hosts to the canonical family

- **What**: audit and reduce dashboard-local repainting on hosts that already declare canonical card and hero primitives
- **Where**:
  1. `static/css/design-system/dashboard.css`
  2. `static/css/design-system/neon.css`
  3. dashboard templates using `dashboard-side-card`, `dashboard-support-card`, `dashboard-table-card`, `layout-panel`, `layout-panel--stack`, `owner-sessions-panel`, and `dashboard-hero`
- **Depends on**: T9
- **Done when**:
  1. dashboard-local wrappers stop redefining the base card family where `.card`, `.table-card`, or `.hero` should already govern
  2. local dashboard classes keep semantic layout responsibility without becoming a parallel visual authority
  3. affected dashboard surfaces read as part of the same dark premium system as the rest of the product

### T11: Validate card conformance on sticky and support rails

- **What**: verify that sticky side cards, support cards, sessions panels, and metric bodies still look intentional after card normalization
- **Where**: representative dashboard side rails and owner support surfaces
- **Depends on**: T10
- **Done when**:
  1. sticky cards preserve hierarchy and readability
  2. support panels no longer feel visually detached from canonical cards
  3. `card-body` and `card-body-metric` compositions still scan correctly after theme cleanup

### T12: Convert dashboard narrative hero into a canonical hero variant

- **What**: make the dashboard narrative banner inherit the shared `.hero` family while keeping its local copy and CTA structure
- **Where**:
  1. `templates/dashboard/blocks/advisor_narrative.html`
  2. `static/css/design-system/dashboard.css`
- **Depends on**: T10
- **Done when**:
  1. the narrative banner declares the canonical hero host
  2. dashboard-specific styling is expressed as hero-variable tuning instead of a separate surface family
  3. dark and light theme behavior stay aligned with the premium glass system

---

## Wave 1 Exit Criteria

Wave 1 is complete when:

1. `design.md` contains the approved classification and host ownership
2. `tasks.md` defines the next implementation queue
3. the team can start Wave 2 without re-opening the discovery phase
