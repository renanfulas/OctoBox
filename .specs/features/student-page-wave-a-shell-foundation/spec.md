# Student Page Wave A Shell Foundation Specification

## Problem Statement

The current student detail surface is trying to behave like a modern, tabbed product page while still carrying the skeleton of an older form-driven flow.

That creates a maintenance trap:

- the visual shell is not canonical
- navigation authority is split across multiple scripts and hashes
- financial, plan, and profile concerns still feel like attached islands
- small UI adjustments cost too much because layout, context, and overrides are mixed together

Wave A exists to solve the foundation problem first.

This is not the phase for pixel-perfect fidelity.
This is the phase for building the right chassis so later visual convergence with the approved Figma can happen safely and cheaply.

## Goals

- [ ] Establish a canonical student detail shell with real `Pagamentos`, `Plano`, and `Perfil` tabs
- [ ] Define one clear navigation authority for hash, active tab, and initial open state
- [ ] Replace the current mixed surface feeling with a predictable page structure closer to the approved Figma
- [ ] Reduce the cost of future visual changes by separating shell structure from panel content and context overrides
- [ ] Deliver the biggest clarity jump of the refactor with the lowest operational risk

## Out of Scope

Explicitly excluded in Wave A to prevent scope drift.

| Feature | Reason |
| --- | --- |
| Pixel-perfect Figma implementation | Too expensive for the foundation wave |
| Final spacing polish and micro-interactions | Better handled after the shell is stable |
| Full removal of all legacy CSS | Wave A should reduce risk, not trigger a rewrite avalanche |
| New billing domain rules | This is a shell and UX architecture pass, not financial logic redesign |
| Rewriting every drawer contract | Existing working contracts should be preserved where possible |
| Final responsive fine-tuning for every breakpoint | Wave A only needs safe, stable desktop-first structure |

---

## User Stories

### P1: Canonical Student Detail Shell

**User Story**: As an operator, I want the student page to feel like one coherent product surface, so that `Pagamentos`, `Plano`, and `Perfil` feel like rooms in the same house instead of separate screens taped together.

**Why P1**: This is the main structural gap between the current runtime and the approved Figma.

**Acceptance Criteria**:

1. WHEN the user opens the student page THEN the system SHALL render a canonical header and a real tab strip
2. WHEN the user switches between `Pagamentos`, `Plano`, and `Perfil` THEN the system SHALL keep one active panel and a predictable page structure
3. WHEN the page loads from an existing hash THEN the system SHALL map the hash into the correct tab without ambiguous state

**Independent Test**: Open the student page from direct navigation and confirm the screen reads like a single detail page with three real panels.

---

### P1: Single Navigation Authority

**User Story**: As a maintainer, I want one clear owner for page navigation state, so that changing tab behavior does not require debugging multiple scripts competing for control.

**Why P1**: Duplicated authority is a silent tax. Every future UI change becomes more fragile if two places can decide which panel is active.

**Acceptance Criteria**:

1. WHEN the student page initializes THEN the system SHALL use one primary owner for hash and tab activation
2. WHEN the active tab changes THEN the system SHALL not depend on multiple scripts fighting over the same state
3. WHEN old entry hashes are used THEN the system SHALL preserve backward-safe behavior through explicit mapping

**Independent Test**: Trace the open-state logic and confirm there is one canonical path for deciding the active panel.

---

### P1: Structural Separation Before Visual Polish

**User Story**: As a front-end maintainer, I want shell layout, panel content, and contextual adaptation separated, so that future visual work costs less and produces fewer regressions.

**Why P1**: Right now small changes feel expensive because they touch mixed responsibilities.

**Acceptance Criteria**:

1. WHEN Wave A touches the student detail page THEN the system SHALL separate page shell structure from panel internals
2. WHEN CSS is introduced for the new shell THEN the system SHALL prefer explicit page-level structure over hidden descendant overrides
3. WHEN the payments panel is migrated first THEN the system SHALL preserve working runtime behavior while upgrading the layout foundation

**Independent Test**: Inspect the touched templates and CSS and confirm the page shell is no longer defined by scattered contextual rules.

---

### P2: Low-Cognitive-Load Reading

**User Story**: As a receptionist with low tolerance for ambiguity, I want the page to make the main navigation and main action obvious, so that I do not need to "figure out the screen" before using it.

**Why P2**: Wave A is not final polish, but it must already reduce interpretation cost.

**Acceptance Criteria**:

1. WHEN the page opens THEN the active tab SHALL be obvious in under a few seconds
2. WHEN the user looks at the header THEN the primary action area SHALL be clear without reading the whole page
3. WHEN the user moves between tabs THEN the transition SHALL feel like changing context inside one page, not launching another subsystem

---

## Edge Cases

- WHEN the user lands on an old financial hash THEN the page SHALL map it safely to `Pagamentos`
- WHEN the student has no pending charge THEN the `Pagamentos` panel SHALL still feel intentional, not empty or broken
- WHEN legacy drawers are opened from the new shell THEN the refactor SHALL not break their current operational behavior
- WHEN plan or profile data are sparse THEN the page SHALL still preserve the canonical shell and tab rhythm

---

## Risks and Fix Strategy

| Risk | Why it matters | Fix strategy |
| --- | --- | --- |
| Hash and tab regression | Users may land on the wrong panel or see conflicting open states | Define one navigation owner and add explicit mapping for legacy hashes before removing old branching behavior |
| Visual shell looks new but runtime still feels split | A pretty shell on top of old authority creates hidden debt | Treat shell structure and navigation authority as the true deliverable of Wave A, not only CSS cosmetics |
| Drawer and panel contracts break during migration | Payment actions and plan flows are already operationally sensitive | Preserve working drawer hooks and migrate shell around them instead of rewriting their internals in the same wave |
| CSS override drift continues | New styles may get swallowed by older contextual selectors | Introduce page-level shell classes and avoid relying on invisible descendant overrides for the new layout |
| Wave A accidentally grows into a rewrite | Scope creep would delay value and increase risk | Enforce strict out-of-scope boundaries and reserve polish, deep cleanup, and pixel-perfect work for later waves |

---

## Operational Output Contract

All execution or review output produced under this Wave A spec must follow these guardrails:

1. maximum of **800 words per implementation/report step**
2. always start with:
   - `Status`
   - `Foco`
   - `Decisao central`
   - `Principal risco`
   - `Proximo passo`
3. separate clearly:
   - what enters Wave A
   - what is explicitly deferred
   - which risk is being reduced
4. no vague "looks better now" conclusions without structural evidence

The goal here is simple: keep output tight enough to think clearly, but complete enough that nobody gets lost.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| SPWA-01 | P1: Canonical Student Detail Shell | Design | Pending |
| SPWA-02 | P1: Canonical Student Detail Shell | Design | Pending |
| SPWA-03 | P1: Canonical Student Detail Shell | Design | Pending |
| SPWA-04 | P1: Single Navigation Authority | Design | Pending |
| SPWA-05 | P1: Single Navigation Authority | Design | Pending |
| SPWA-06 | P1: Single Navigation Authority | Design | Pending |
| SPWA-07 | P1: Structural Separation Before Visual Polish | Design | Pending |
| SPWA-08 | P1: Structural Separation Before Visual Polish | Design | Pending |
| SPWA-09 | P1: Structural Separation Before Visual Polish | Design | Pending |
| SPWA-10 | P2: Low-Cognitive-Load Reading | Design | Pending |
| SPWA-11 | P2: Low-Cognitive-Load Reading | Design | Pending |
| SPWA-12 | P2: Low-Cognitive-Load Reading | Design | Pending |

**Coverage:** 12 total, 0 mapped to tasks, 12 unmapped warning

---

## Success Criteria

How we know Wave A was a success:

- [ ] The student page has one canonical shell with `Pagamentos`, `Plano`, and `Perfil`
- [ ] The page no longer feels architecturally split between "essential form" and "financial island"
- [ ] One navigation authority clearly owns hash and active tab behavior
- [ ] The payments panel is the first migrated panel and already feels structurally closer to the approved Figma
- [ ] Future visual work can be done with less risk because shell layout is no longer defined by scattered overrides

## Success Verdict

Wave A is only considered **successful** when the page becomes easier to change than it was before.

That is the real test.

If the layout looks nicer but changing a tab, header, or panel still feels like pulling one thread from a sweater and hoping the whole thing does not unravel, then the operation was not a success.
