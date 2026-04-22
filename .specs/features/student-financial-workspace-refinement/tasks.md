# Student Financial Workspace Refinement Tasks

**Design**: `.specs/features/student-financial-workspace-refinement/design.md`
**Status**: Completed

---

## Execution Plan

### Phase 1: Structural Hygiene (Sequential)

Tasks that must be done first, in order.

```text
T1 -> T2 -> T3
```

### Phase 2: Student Workspace Hierarchy (Parallel OK)

After hygiene, the student-facing improvements can move in parallel.

```text
      -> T4 --
T3 -> -> T5 -- -> T7
      -> T6 --
```

### Phase 3: Internal Finance Continuity (Sequential)

```text
T7 -> T8 -> T9
```

### Phase 4: Trust and Accessibility (Sequential)

```text
T9 -> T10
```

---

## Task Breakdown

### T1: Fix Residual Finance Markup Integrity [Done]

**What**: Correct known broken semantic wrappers in the remaining finance internals before any new polish.
**Where**:
- `templates/includes/catalog/finance/boards/portfolio_board.html`
- nearby finance residual boards if the same pattern is confirmed
**Depends on**: None
**Reuses**: Existing board structure
**Requirement**: SFW-07

**Tools**:

- Skill: `CSS Front end architect`

**Done when**:

- [ ] Known mismatched closing tags are fixed
- [ ] The current board layout remains stable
- [ ] No residual invalid wrapper mismatch remains in the touched boards

**Verify**:

- Inspect the touched templates directly
- Run `python manage.py check`

---

### T2: Remove Dominant Inline Debt From Student Form Shell [Done]

**What**: Move dominant inline presentation out of the student form shell and preserve lock behavior safely.
**Where**:
- `templates/catalog/student-form.html`
- related CSS/JS assets
**Depends on**: T1
**Reuses**:
- `static/js/catalog/student_form_lock.js`
- existing student form classes and shell contract
**Requirement**: SFW-03, SFW-08, SFW-09

**Tools**:

- Skill: `CSS Front end architect`

**Done when**:

- [ ] Dominant inline style debt is removed from the student form shell
- [ ] Lock banners still behave correctly
- [ ] No functional regression is introduced in the lock flow

**Verify**:

- Inspect the template for remaining dominant `style=`
- Run `python manage.py check`

---

### T3: Normalize Encoding and Low-Trust Copy in Internal Finance Surfaces [Done]

**What**: Clean encoding corruption and rough wording in the internal finance surfaces that still feel older than the facade.
**Where**:
- `templates/includes/catalog/finance/views/movements.html`
- touched finance partials as needed
**Depends on**: T2
**Reuses**: Existing finance copy and state components
**Requirement**: SFW-04, SFW-05

**Tools**:

- Skill: `prompt-engineer`
- Skill: `OctoBox UI/UX Payments Expert`

**Done when**:

- [ ] The touched templates no longer expose corrupted visible text
- [ ] Financial language reads clearly and calmly
- [ ] Empty states remain informative without sounding brittle

**Verify**:

- Read the touched PT-BR copy in the rendered template source
- Run `python manage.py check`

---

### T4: Strengthen Student Form Workspace Framing [Done]

**What**: Refine the student form upper workspace so the user understands where they are and what matters now before diving into dense detail.
**Where**:
- `templates/catalog/student-form.html`
- `templates/includes/catalog/student_form/plans/hero.html`
- optional local CSS modules
**Depends on**: T3
**Reuses**: Existing hero grammar and student workspace shell
**Requirement**: SFW-01, SFW-02

**Tools**:

- Skill: `prompt-engineer`
- Skill: `CSS Front end architect`

**Done when**:

- [ ] The student form top makes the workspace purpose legible
- [ ] The shift between essential and financial areas feels more guided
- [ ] The page feels like a natural continuation of the refined facade

**Verify**:

- Open the template and confirm the workspace framing is explicit
- Run `python manage.py check`

---

### T5: Refine Student Financial Overview Hierarchy [Done]

**What**: Reorganize the dense student financial overview so status, current plan, and action zones are easier to scan.
**Where**:
- `templates/includes/catalog/student_form/financial/financial_overview.html`
- related partials under `student_form/financial/`
**Depends on**: T3
**Reuses**: Existing financial partial split
**Requirement**: SFW-01, SFW-10, SFW-11

**Tools**:

- Skill: `OctoBox UI/UX Payments Expert`
- Skill: `CSS Front end architect`

**Done when**:

- [ ] The overview is grouped more clearly
- [ ] Status and current plan information are easier to identify
- [ ] The financial area feels less slab-like and less tiring

**Verify**:

- Read the target partial flow top to bottom
- Run `python manage.py check`

---

### T6: Harden Student Lock and Sensitive Feedback Presentation [Done]

**What**: Improve the visibility and trust contract around edit locks and sensitive state changes in the student workspace.
**Where**:
- `templates/catalog/student-form.html`
- related local CSS/JS hooks
**Depends on**: T3
**Reuses**: Current lock state behavior and JS
**Requirement**: SFW-03, SFW-12, SFW-13

**Tools**:

- Skill: `CSS Front end architect`
- Skill: `prompt-engineer`

**Done when**:

- [ ] Lock states are visually clear and semantically safer
- [ ] The banner presentation no longer feels bolted on
- [ ] Sensitive feedback remains understandable after page load changes

**Verify**:

- Inspect the lock markup and hooks
- Run `python manage.py check`

---

### T7: Consolidate Student Workspace Voice [Done]

**What**: Align the student form and its finance interior with the same calm, premium product voice used in the facade pass.
**Where**:
- `templates/catalog/student-form.html`
- touched student financial partials
**Depends on**: T4, T5, T6
**Reuses**:
- `docs/experience/front-display-wall.md`
- prior voice decisions from the facade phase
**Requirement**: SFW-01, SFW-04

**Tools**:

- Skill: `prompt-engineer`

**Done when**:

- [ ] The student workspace sounds like the same product as the refined facade
- [ ] Copy invites calm action instead of sounding bureaucratic or stale
- [ ] Sensitive areas remain direct without sounding cold

**Verify**:

- Read the main student workspace copy side by side with `students` and `finance`
- Confirm tone continuity

---

### T8: Refine Residual Finance Boards for Calm and Continuity [Done]

**What**: Bring the remaining finance internal boards up to the new product standard.
**Where**:
- `templates/includes/catalog/finance/views/movements.html`
- `templates/includes/catalog/finance/boards/portfolio_board.html`
- adjacent touched residual boards if needed
**Depends on**: T7
**Reuses**:
- finance local CSS modules
- shared state components
**Requirement**: SFW-04, SFW-05, SFW-10

**Tools**:

- Skill: `OctoBox UI/UX Payments Expert`
- Skill: `CSS Front end architect`

**Done when**:

- [ ] Residual finance boards feel calmer and more current
- [ ] Row rhythm, headings, and states are easier to scan
- [ ] No dominant legacy smell remains in the touched finance interior

**Verify**:

- Review the touched finance partials together
- Run `python manage.py check`

---

### T9: Reduce Remaining Internal Visual Debt [Done]

**What**: Do a targeted pass on the remaining dominant internal debt in the refined scope.
**Where**:
- touched student and finance interior templates
- supporting local CSS/JS as needed
**Depends on**: T8
**Reuses**: Existing local assets
**Requirement**: SFW-06, SFW-09

**Tools**:

- Skill: `CSS Front end architect`
- Skill: `OctoBox High Performance Architect`

**Done when**:

- [ ] Remaining dominant inline debt in the target scope is reduced
- [ ] The refined interior remains stable and lightweight
- [ ] No broad rebuild was needed to achieve the gain

**Verify**:

- Search the touched target scope for remaining dominant `style=` and inline `<script>` usage
- Run `python manage.py check`

---

### T10: Deep Workspace Accessibility and Trust Pass [Done]

**What**: Extend the accessibility and interaction trust hardening into the deeper student and finance flows.
**Where**:
- student form shell
- student financial overview partials
- touched residual finance boards
**Depends on**: T9
**Reuses**:
- current IDs, hooks, and state blocks
- prior facade accessibility patterns
**Requirement**: SFW-12, SFW-13

**Tools**:

- Skill: `CSS Front end architect`
- Skill: `OctoBox UI/UX Payments Expert`

**Done when**:

- [ ] Focus and semantic grouping are clearer in the touched deep surfaces
- [ ] Sensitive feedback remains understandable
- [ ] The interior workspace feels as trustworthy as the facade

**Verify**:

- Keyboard-walk the touched interface zones where practical
- Run `python manage.py check`

---

## Parallel Execution Map

```text
Phase 1 (Sequential):
  T1 -> T2 -> T3

Phase 2 (Parallel):
  T3 complete, then:
    |- T4 [P]
    |- T5 [P]
    \- T6 [P]

Phase 3 (Sequential):
  T4, T5, T6 complete, then:
    T7 -> T8 -> T9

Phase 4 (Sequential):
  T9 -> T10
```

---

## Notes for Execution

1. Do not reopen billing behavior or enrollment rules unless a real bug forces that conversation.
2. Preserve the modular split of the student financial partials.
3. If a task reveals a true local rebuild opportunity, pause and surface it before implementation.
4. Prefer improving hierarchy and trust over adding decorative complexity.
