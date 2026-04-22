# Student Page Wave C Visual Polish Specification

## Problem Statement

Wave B gave the student page a real shell, a Figma-aligned header, a stronger payments surface, and a much healthier `Plano` and `Perfil` structure.

That was the hard architectural jump.

Now the page has a different problem:

- it already looks like one product surface
- but it still does not feel fully finished
- some spacing, density, and panel rhythm still reveal where the refactor happened in layers
- responsiveness and state polish still need a deliberate pass
- a few remaining legacy style dependencies could silently raise the cost of future adjustments

Wave C exists to turn a strong refactor into a coherent, near-final product surface.

This is not the phase for redesigning the architecture again.
This is the phase for making the shell feel intentional, stable, and close to the approved Figma at the `90%` level.

## Goals

- [ ] Align `Header`, `Pagamentos`, `Plano`, and `Perfil` into one clear visual family
- [ ] Refine spacing, density, typography, and CTA hierarchy until the page feels intentionally designed instead of recently migrated
- [ ] Validate and improve responsive behavior so the shell remains readable and usable across key widths
- [ ] Standardize visual states such as `hover`, `focus`, `error`, and support text
- [ ] Remove or isolate the remaining legacy CSS pressure points that could still distort the new shell

## Out of Scope

Explicitly excluded in Wave C to keep the polish wave disciplined.

| Feature | Reason |
| --- | --- |
| Rebuilding the page shell again | The chassis is already in place from Waves A and B |
| New backend behavior or domain rules | Wave C is visual/system polish, not business logic redesign |
| Full design-system rewrite | Too expensive and unnecessary for this wave |
| Pixel-perfect obsession at any cost | The target is production-grade coherence, not infinite refinement |
| Mobile-first redesign from scratch | We only need strong responsive adaptation of the current shell |
| Replacing working drawer or AJAX contracts | Preserve runtime behavior while polishing the visual layer |

---

## User Stories

### P1: Unified Student Page Family

**User Story**: As an operator, I want `Pagamentos`, `Plano`, and `Perfil` to feel like siblings inside one product screen, so that switching tabs feels natural instead of visually jumping between generations of UI.

**Why P1**: This is the last major perceptual gap between a successful refactor and a polished product surface.

**Acceptance Criteria**:

1. WHEN the user switches between tabs THEN the shell SHALL preserve one consistent card language, spacing rhythm, and CTA hierarchy
2. WHEN the operator scans the page THEN header, tabs, and panel sections SHALL feel visually related
3. WHEN a panel is opened after another THEN the user SHALL not feel like they entered a different subsystem

**Independent Test**: Open all three tabs in sequence and confirm the page still reads like one product surface with different contexts, not three loosely related layouts.

---

### P1: Responsive Stability Without Collapse

**User Story**: As an operator using different screen widths, I want the page to remain legible and actionable, so that important information never collapses into awkward or stressful layouts.

**Why P1**: A page that looks good only at one width is still fragile.

**Acceptance Criteria**:

1. WHEN the viewport approaches tablet width THEN cards and actions SHALL reflow gracefully
2. WHEN the viewport approaches narrow mobile width THEN CTAs SHALL remain tappable and readable
3. WHEN grid sections collapse THEN hierarchy SHALL remain obvious and no critical action shall become visually lost

**Independent Test**: Validate the page at desktop, medium, tablet, and narrow widths and confirm no panel becomes visually broken or cognitively heavy.

---

### P1: State Polish and Readability

**User Story**: As a receptionist or manager, I want states like hover, focus, error, and support text to feel consistent, so that the interface feels trustworthy and easy to use under pressure.

**Why P1**: In high-pace operational software, inconsistency reads like uncertainty.

**Acceptance Criteria**:

1. WHEN the user hovers or focuses actions THEN the response SHALL match the same visual language across panels
2. WHEN the page shows help text, validation, or secondary information THEN the typography SHALL remain readable and subordinate
3. WHEN status elements appear THEN emphasis SHALL feel deliberate, not accidental

**Independent Test**: Tab through interactive elements and confirm focus, emphasis, and supporting copy follow one predictable visual grammar.

---

### P2: Legacy Drift Containment

**User Story**: As a maintainer, I want the remaining legacy overrides isolated or reduced, so that changing one panel no longer feels like touching a hidden tripwire.

**Why P2**: Wave C is the right moment to retire the most annoying invisible styling debt before it hardens again.

**Acceptance Criteria**:

1. WHEN styling is adjusted in the new shell THEN the effect SHALL be driven by `student-page-shell.css` or explicit panel modifiers
2. WHEN a legacy rule is still needed THEN its scope SHALL be explicit and justified
3. WHEN future edits are made THEN the number of hidden descendant overrides affecting the new shell SHALL be lower than before Wave C

---

## Edge Cases

- WHEN the student is in debt status THEN the alert and the payments summary SHALL remain readable without overpowering the rest of the shell
- WHEN the student has sparse profile data THEN `Perfil` SHALL still feel intentional and balanced
- WHEN the student has no active enrollment THEN `Plano` SHALL still preserve structure and not collapse into an awkward empty state
- WHEN buttons stack on smaller widths THEN they SHALL preserve meaning and visual hierarchy
- WHEN dark mode is active THEN support text, borders, and status chips SHALL remain distinguishable without becoming noisy

---

## Risks and Fix Strategy

| Risk | Why it matters | Fix strategy |
| --- | --- | --- |
| Over-polishing turns into structural churn | The page could drift back into rewrite mode instead of refinement | Treat Wave C as a polish wave with strict architecture freeze |
| Responsive fixes create desktop regressions | Good desktop rhythm can break if responsive overrides are rushed | Validate breakpoints in descending order and keep grid changes local |
| State styling becomes inconsistent across panels | Hover/focus polish can accidentally diverge between sections | Define shared visual rules first, then adjust panel-specific exceptions |
| Legacy CSS still leaks into the shell | Hidden descendant rules can make future work expensive again | Prefer shell-level or panel-level selectors and retire legacy rules incrementally |
| The page becomes visually “busy” while chasing fidelity | Closer to Figma should not mean noisier than the product needs | Keep the filter `clarity > decoration` on every spacing and emphasis decision |

---

## Operational Output Contract

All execution or review output produced under this Wave C spec must follow these guardrails:

1. maximum of **800 words per implementation/report step**
2. always start with:
   - `Status`
   - `Foco`
   - `Decisao central`
   - `Principal risco`
   - `Proximo passo`
3. clearly separate:
   - what was polished
   - what was intentionally deferred
   - which visual or maintenance risk was reduced
4. avoid vague conclusions like “looks better now” without naming the concrete visual or structural gain

The goal is to keep the output lean enough to think clearly and precise enough that the operation does not drift.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| SPWC-01 | P1: Unified Student Page Family | Design | Pending |
| SPWC-02 | P1: Unified Student Page Family | Design | Pending |
| SPWC-03 | P1: Unified Student Page Family | Design | Pending |
| SPWC-04 | P1: Responsive Stability Without Collapse | Design | Pending |
| SPWC-05 | P1: Responsive Stability Without Collapse | Design | Pending |
| SPWC-06 | P1: Responsive Stability Without Collapse | Design | Pending |
| SPWC-07 | P1: State Polish and Readability | Design | Pending |
| SPWC-08 | P1: State Polish and Readability | Design | Pending |
| SPWC-09 | P1: State Polish and Readability | Design | Pending |
| SPWC-10 | P2: Legacy Drift Containment | Design | Pending |
| SPWC-11 | P2: Legacy Drift Containment | Design | Pending |
| SPWC-12 | P2: Legacy Drift Containment | Design | Pending |

**Coverage:** 12 total, 0 mapped to tasks, 12 unmapped warning

---

## Success Criteria

How we know Wave C was a success:

- [ ] `Pagamentos`, `Plano`, and `Perfil` feel like one polished product family
- [ ] the page keeps its hierarchy and usability at key responsive widths
- [ ] hover, focus, support text, errors, and status elements feel consistent
- [ ] the remaining invisible override pressure on the new shell is lower than before Wave C
- [ ] the page is visually close enough to the approved Figma that the remaining gap is refinement, not redesign

## Success Verdict

Wave C is only considered **successful** when the page stops feeling like “a strong refactor that still needs explanation” and starts feeling like “the screen was always supposed to look this way.”

In child-level metaphor:

If the house is standing but still looks like workers left tools on the floor, Wave C is not done.
Wave C ends when the house feels lived-in, clean, and easy to walk through without tripping on anything.
