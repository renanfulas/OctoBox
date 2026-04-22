# Canonical Theme Unification Tasks

**Design**: `.specs/features/canonical-theme-unification/design.md`
**Status**: Completed

---

## Execution Plan

### Phase 1: Audit and Canon Selection (Sequential)

Tasks that must be done first, in order.

```
T1 -> T2 -> T3
```

### Phase 2: Core Primitive Normalization (Parallel OK)

After the canon is defined, these can run in parallel with careful scope ownership.

```
      -> T4 --
T3 -> -> T5 -- -> T8
      -> T6 --
      -> T7 --
```

### Phase 3: Surface Migration and Legacy Retirement (Sequential)

```
T8 -> T9 -> T10
```

---

## Task Breakdown

### T1: Build Theme Authority Inventory [Done]

**What**: Audit the active theme families, conflict points, and authority overlaps across the design-system and high-impact templates.
**Where**:
- `static/css/design-system/tokens.css`
- `static/css/design-system/components/cards.css`
- `static/css/design-system/components/hero.css`
- `static/css/design-system/topbar.css`
- `static/css/catalog/shared/utilities.css`
- representative templates in `templates/catalog/`, `templates/dashboard/`, and `templates/operations/`
**Depends on**: None
**Reuses**: Existing codebase docs and refined surface work
**Requirement**: THM-01, THM-05

**Tools**:

- Skill: `OctoBox Master Debugger`
- Skill: `CSS Front end architect`
- Skill: `prompt-engineer`

**Done when**:

- [ ] Active core families are inventoried
- [ ] Conflicting authorities are listed with concrete file references
- [ ] The audit identifies which families are currently competing for the same role

**Verify**:

- Produce a concise inventory matrix inside the feature package
- Confirm the audit covers tokens, cards, hero, banners/notices, and topbar

---

### T2: Elect the Canonical Theme Families [Done]

**What**: Choose the canonical authority for each core visual family and define the final painter contract.
**Where**:
- `.specs/features/canonical-theme-unification/design.md`
- `.specs/features/canonical-theme-unification/corda-plan.md`
- `.specs/features/canonical-theme-unification/theme-matrix.md`
**Depends on**: T1
**Reuses**: Audit findings from T1
**Requirement**: THM-01, THM-02, THM-03

**Tools**:

- Skill: `prompt-engineer`
- Skill: `CSS Front end architect`

**Done when**:

- [ ] Tokens, card/surface, hero, banner/notice, and topbar each have one named authority
- [ ] The final painter contract is explicit
- [ ] The previous four painters are reframed as inspiration, not authority
- [ ] The dark premium open direction is captured as canonical theme intent

**Verify**:

- Review the feature docs and confirm each family has one canonical owner

---

### T3: Create the Migration Matrix [Done]

**What**: Classify active visual families as canonical, alias, migrate, or remove.
**Where**:
- `.specs/features/canonical-theme-unification/design.md`
- `.specs/features/canonical-theme-unification/tasks.md`
- `.specs/features/canonical-theme-unification/theme-matrix.md`
**Depends on**: T2
**Reuses**: T1 inventory and T2 canon decisions
**Requirement**: THM-05, THM-06

**Tools**:

- Skill: `prompt-engineer`
- Skill: `OctoBox Master Debugger`

**Done when**:

- [ ] Every high-impact active family has a migration status
- [ ] Temporary aliases are clearly marked as transitional
- [ ] Removal targets are explicitly named

**Verify**:

- Open the design doc and confirm the matrix covers all identified core families

---

### T4: Normalize Token Authority [Done]

**What**: Refactor the token layer so semantic theme values come from one authority instead of stacked competing passes.
**Where**: `static/css/design-system/tokens.css`
**Depends on**: T3
**Reuses**: Existing semantic variables where valid
**Requirement**: THM-01, THM-02, THM-09

**Tools**:

- Skill: `CSS Front end architect`
- Skill: `OctoBox High Performance Architect`

**Done when**:

- [ ] Token ownership is simplified
- [ ] Competing visual ideology blocks are removed or demoted
- [ ] Core primitives can consume stable semantic variables

**Verify**:

- Inspect the token file and confirm only one semantic authority remains
- Re-test touched surfaces for visual stability

---

### T5: Normalize Surface and Card Primitives [Done]

**What**: Unify the base surface/card family and demote competing card dialects into aliases or migration targets.
**Where**:
- `static/css/design-system/components/cards.css`
- touched CSS modules that still redefine card identity
**Depends on**: T3
**Reuses**:
- `table-card`
- best structural parts of refined surface work
**Requirement**: THM-03, THM-04, THM-09

**Tools**:

- Skill: `CSS Front end architect`
- Skill: `OctoBox Master Debugger`

**Done when**:

- [ ] One card/surface family is canonical
- [ ] Competing card dialects have migration or alias status
- [ ] Touched templates stop mixing multiple base families for the same role

**Verify**:

- Inspect representative templates and confirm surface roles are no longer mixed

---

### T6: Normalize Hero and Banner Families [Done]

**What**: Unify hero and notice/banner grammar so they communicate through one editorial and visual system.
**Where**:
- `static/css/design-system/components/hero.css`
- canonical banner/notice host to be selected during implementation
- touched templates using notice and hero blocks
**Depends on**: T3
**Reuses**:
- current hero grammar
- `note-panel`
- refined facade work
**Requirement**: THM-03, THM-04, THM-08

**Tools**:

- Skill: `CSS Front end architect`
- Skill: `prompt-engineer`

**Done when**:

- [ ] Hero authority is singular
- [ ] Banner/notice styling has one canonical contract
- [ ] Competing local hero/banner passes are removed or demoted

**Verify**:

- Compare migrated heroes and notices across target surfaces for continuity

---

### T7: Normalize Topbar Authority [Done]

**What**: Rework the topbar so it consumes the canonical theme instead of running a parallel visual system.
**Where**: `static/css/design-system/topbar.css`
**Depends on**: T3
**Reuses**: Existing responsive and interaction behavior
**Requirement**: THM-03, THM-04, THM-07

**Tools**:

- Skill: `CSS Front end architect`
- Skill: `OctoBox High Performance Architect`
- Skill: `OctoBox Master Debugger`

**Done when**:

- [ ] Topbar visual language is token-driven by the canonical theme
- [ ] Parallel topbar-only visual authority is removed
- [ ] Global shell continuity improves without navigation regressions

**Verify**:

- Load authenticated surfaces and compare topbar continuity against the rest of the shell

---

### T8: Migrate the Highest-Impact Product Surfaces [Done]

**What**: Apply the canonical primitives to the most visible product surfaces.
**Where**:
- `templates/catalog/students.html`
- `templates/catalog/finance.html`
- `templates/dashboard/`
- `templates/operations/reports-hub.html`
- relevant local CSS modules
**Depends on**: T4, T5, T6, T7
**Reuses**: Refined facade and workspace work already shipped
**Requirement**: THM-03, THM-04, THM-09, THM-10

**Tools**:

- Skill: `CSS Front end architect`
- Skill: `prompt-engineer`
- Skill: `OctoBox Master Debugger`

**Done when**:

- [ ] The target surfaces visibly belong to the same theme system
- [ ] Local patches no longer compete with the canonical primitives in touched areas
- [ ] The migrated pages remain functional and readable

**Verify**:

- Run visual comparison across the migrated target surfaces
- Run `python manage.py check`

---

### T9: Retire High-Conflict Legacy Paths [Done]

**What**: Reduce or remove the most conflict-heavy legacy overrides and utility-authority overlaps in touched areas.
**Where**:
- touched design-system CSS
- touched shared utility files
- touched templates with dominant inline visual debt
**Depends on**: T8
**Reuses**: Migration matrix from T3
**Requirement**: THM-06, THM-09, THM-10

**Tools**:

- Skill: `OctoBox Master Debugger`
- Skill: `CSS Front end architect`
- Skill: `OctoBox High Performance Architect`

**Done when**:

- [ ] High-conflict `!important` usage is reduced in touched scope
- [ ] The most dangerous authority overlaps are removed
- [ ] Legacy aliases still required are explicitly documented

**Verify**:

- Recount conflict markers in touched files
- Search touched templates for dominant inline visual debt

---

### T10: Publish the Theme Governance Contract [Done]

**What**: Document the canonical theme rules and prevent the return of competing painters.
**Where**:
- `docs/experience/css-guide.md`
- feature package docs
- any additional governance doc chosen during implementation
**Depends on**: T9
**Reuses**: Final migration results
**Requirement**: THM-07, THM-08

**Tools**:

- Skill: `prompt-engineer`
- Skill: `CSS Front end architect`

**Done when**:

- [ ] The canonical theme contract is documented
- [ ] The team can tell which primitives are canonical
- [ ] New divergence is explicitly discouraged by the docs

**Verify**:

- Read the updated governance docs and confirm the canon is explicit

---

## Parallel Execution Map

Phase 1 (Sequential):
  T1 -> T2 -> T3

Phase 2 (Parallel):
  T3 complete, then:
    - T4 [P]
    - T5 [P]
    - T6 [P]
    - T7 [P]

Phase 3 (Sequential):
  T4, T5, T6, T7 complete, then:
    T8 -> T9 -> T10

---

## Task Granularity Check

- T1-T3 define the plan and authority map
- T4-T7 normalize one primitive family each
- T8 migrates the highest-value surfaces using the normalized primitives
- T9 retires the most dangerous residual conflicts
- T10 closes the loop with governance so the problem does not return
