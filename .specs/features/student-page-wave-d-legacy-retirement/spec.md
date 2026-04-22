# Student Page Wave D Legacy Retirement Specification

## Problem Statement

Wave C closed the visual convergence of the student page at a strong production level.

The page now:

- looks like one coherent product surface
- behaves with much more confidence across `Pagamentos`, `Plano`, and `Perfil`
- carries far less visual drift than the earlier shell

That means the remaining problem is no longer presentation quality.
The remaining problem is structural residue.

Today, the student page still carries some legacy scaffolding behind the walls:

- `Pagamentos` still depends on legacy `student-financial-*` markup and styling contracts
- parts of the new shell still adapt old components by context instead of owning native page components
- the page still enters through legacy CSS flow even though the canonical shell is now different
- some visual stability still comes from wrapper adaptation instead of first-class component contracts

Wave D exists to retire that residual legacy carefully.

This is not a redesign wave.
This is not a broad backend rewrite.
This is a controlled retirement wave to make the new student page cheaper to evolve and harder to break.

## Goals

- [ ] Reduce the dependency of `Pagamentos` on legacy `student-financial-*` contracts
- [ ] Move the student page closer to native page components instead of wrapper-based adaptation
- [ ] Separate the canonical student page shell from legacy stepper-era styling pressure
- [ ] Reduce CSS and template coincidence so future changes cost less effort
- [ ] Preserve working runtime behavior while replacing fragile structural residue

## Out of Scope

Explicitly excluded in Wave D to keep the retirement wave disciplined.

| Feature | Reason |
| --- | --- |
| New visual redesign of the page | Wave D is about structural retirement, not aesthetic reinvention |
| New business rules for payments, plan, or profile | Behavior is already working and should remain stable |
| Large API redesign | Only minimal contract adjustments are allowed if strictly needed |
| Rebuilding the entire student page from zero | Too risky and unnecessary after Waves A-C |
| Full design-system rewrite | Outside the scope of this targeted cleanup |
| Replacing all legacy financial features at once | Retirement must happen incrementally and safely |

---

## User Stories

### P1: Native Payments Panel Ownership

**User Story**: As a maintainer, I want the `Pagamentos` panel to rely less on old financial-shell contracts, so that evolving the student page no longer feels like styling around a legacy island.

**Why P1**: `Pagamentos` is still the biggest leftover bridge between the new student page and the older financial workspace.

**Acceptance Criteria**:

1. WHEN the `Pagamentos` panel is updated THEN the primary layout and visual shell SHALL be controlled by student-page-native contracts
2. WHEN styling changes are made THEN fewer selectors SHALL depend on `.student-page-panel--payments .student-financial-*` adaptation
3. WHEN future refactors touch the ledger or payment summary THEN the cost of change SHALL be lower than before Wave D

**Independent Test**: Inspect the payments panel after Wave D and confirm that its main structure reads like native student-page markup, not a legacy financial workspace wearing a wrapper.

---

### P1: Cleaner Shell Boundary

**User Story**: As a maintainer, I want the student page shell to have a clearer CSS and template entry boundary, so that the new page does not keep borrowing identity from the old stepper surface.

**Why P1**: A new house should not keep depending on the old hallway light switch to stay lit.

**Acceptance Criteria**:

1. WHEN the student page shell is loaded THEN its critical styling SHALL come from its own canonical layer
2. WHEN legacy stepper styles are changed THEN the new student page SHALL suffer fewer unintended side effects
3. WHEN developers inspect ownership THEN shell-level styling and structure SHALL be easier to trace

**Independent Test**: Change-read the student page stack and verify that ownership between shell CSS and legacy stepper CSS is visibly cleaner than before Wave D.

---

### P1: Explicit Component Contracts Over Cascade Coincidence

**User Story**: As a maintainer, I want page components to depend on explicit contracts instead of coincidence of cascade, so that bug fixing feels like turning one screw instead of touching ten hidden wires.

**Why P1**: Residual styling by wrapper or descendant adaptation is the classic source of expensive front-end maintenance.

**Acceptance Criteria**:

1. WHEN a component needs a page-specific visual behavior THEN it SHALL use explicit page-level classes, partials, or modifiers
2. WHEN legacy rules remain THEN they SHALL be narrow, documented by location, and clearly transitional
3. WHEN a future engineer changes spacing or layout THEN the change SHALL not rely on guessing which old wrapper is helping

**Independent Test**: Review the page after Wave D and confirm that the most important layout and shell behaviors can be explained by explicit component ownership, not hidden adaptation.

---

### P2: Safe Legacy Retirement Without Runtime Regression

**User Story**: As an operator, I want the page to remain fully functional while the internal legacy is cleaned up, so that technical cleanup never creates operational confusion.

**Why P2**: The product already works well enough to be dangerous if cleanup is rushed.

**Acceptance Criteria**:

1. WHEN Wave D removes or replaces legacy residue THEN payments, plan actions, and profile editing SHALL continue to work
2. WHEN AJAX fragments update the page THEN the visible result SHALL remain correct
3. WHEN tabs are switched or deep-linked THEN page navigation SHALL remain stable

---

## Edge Cases

- WHEN the student has overdue payments THEN the page SHALL preserve alert clarity while the payments structure is being modernized
- WHEN the student has no active enrollment THEN `Plano` SHALL still preserve its new shell without depending on removed legacy wrappers
- WHEN the student page is opened in create mode THEN legacy create behavior SHALL continue if Wave D targets only update-mode shell ownership
- WHEN AJAX fragment replacement occurs after a payment or enrollment action THEN the page SHALL not lose shell coherence
- WHEN legacy CSS is removed or narrowed THEN no hidden dependency SHALL quietly collapse spacing or structure in unrelated panels

---

## Risks and Fix Strategy

| Risk | Why it matters | Fix strategy |
| --- | --- | --- |
| Retiring legacy too aggressively breaks working flows | Payments and enrollment actions are already productive runtime paths | Migrate in slices, keep behavior stable, validate after each structural move |
| Native student page markup drifts from current fragment contracts | AJAX surfaces still depend on known IDs and replacement points | Preserve fragment interface or replace it only with equivalent named contracts |
| Cleaning CSS boundaries exposes hidden dependencies | Some visuals may still be standing because of wrapper adaptation | Move one responsibility at a time and test immediately after each removal |
| Wave D accidentally turns into rewrite mode | Late-stage cleanup can become open-ended if not scoped | Keep the wave centered on ownership and residue retirement, not new design ambition |
| Legacy create flow gets caught in the cleanup | Create mode still intentionally reuses older structure | Treat create-mode legacy as protected unless explicitly targeted in a later wave |

---

## Operational Output Contract

All execution or review output produced under this Wave D spec must follow these guardrails:

1. maximum of **800 words per implementation/report step**
2. always start with:
   - `Status`
   - `Foco`
   - `Decisao central`
   - `Principal risco`
   - `Proximo passo`
3. clearly separate:
   - what legacy residue was retired
   - what was intentionally preserved
   - what maintenance risk was reduced
4. avoid vague claims like “cleaner now” without naming which dependency, wrapper, selector, or contract was actually removed or replaced

The goal is to make cleanup observable, not mystical.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| SPWD-01 | P1: Native Payments Panel Ownership | Design | Pending |
| SPWD-02 | P1: Native Payments Panel Ownership | Design | Pending |
| SPWD-03 | P1: Native Payments Panel Ownership | Design | Pending |
| SPWD-04 | P1: Cleaner Shell Boundary | Design | Pending |
| SPWD-05 | P1: Cleaner Shell Boundary | Design | Pending |
| SPWD-06 | P1: Cleaner Shell Boundary | Design | Pending |
| SPWD-07 | P1: Explicit Component Contracts Over Cascade Coincidence | Design | Pending |
| SPWD-08 | P1: Explicit Component Contracts Over Cascade Coincidence | Design | Pending |
| SPWD-09 | P1: Explicit Component Contracts Over Cascade Coincidence | Design | Pending |
| SPWD-10 | P2: Safe Legacy Retirement Without Runtime Regression | Design | Pending |
| SPWD-11 | P2: Safe Legacy Retirement Without Runtime Regression | Design | Pending |
| SPWD-12 | P2: Safe Legacy Retirement Without Runtime Regression | Design | Pending |

**Coverage:** 12 total, 0 mapped to tasks, 12 unmapped warning

---

## Success Criteria

How we know Wave D was a success:

- [ ] `Pagamentos` depends less on wrapper adaptation and more on native student-page ownership
- [ ] the shell no longer relies on obvious legacy CSS pressure points to remain visually correct
- [ ] cascade coincidence is lower than before Wave D
- [ ] future edits to page layout and panel structure feel more local and predictable
- [ ] runtime behavior remains stable while structural debt meaningfully drops

## Success Verdict

Wave D is only considered **successful** when the student page stops feeling like “a polished new surface still attached to old scaffolding” and starts feeling like “a mature page with its own bones.”

In child-level metaphor:

If the new treehouse still depends on ropes tied to the old shed, Wave D is not done.
Wave D ends when the treehouse can stand on its own without anyone wondering which old nail is secretly holding the floor.
