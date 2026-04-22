# Student Page Wave C Residual Premium Polish Specification

## Problem Statement

The original Wave C already delivered the big polish layer for the student page:

- the shared shell is stable
- `Pagamentos`, `Plano`, and `Perfil` already read like one product family
- responsive behavior and interaction states already received a deliberate pass
- the most dangerous legacy visual pressure points were reduced

That means the original Wave C is not the right target anymore.

What remains now is a **Wave C residual**:

- small premium-fidelity gaps against the approved Figma
- minor rhythm differences between panels
- a few visual details that still feel "very good" instead of "final"
- selective polish that can increase perceived quality without reopening architecture

This wave exists to capture the remaining high-signal polish work while keeping the rules strict:

1. no shell redesign
2. no new architecture churn
3. no backend changes unless a tiny binding fix is strictly necessary
4. no polish that adds noise or future maintenance cost

In simple terms:

The house is already built, painted, and clean.
This wave is about aligning the cushions, the curtains, and the lamps so the house feels intentionally finished.

## Goals

- [ ] Push the page from "strong production UI" toward "premium finished UI"
- [ ] Close the most visible remaining fidelity gaps between the page and the approved Figma
- [ ] Harmonize micro-rhythm across `Header`, `Pagamentos`, `Plano`, and `Perfil`
- [ ] Improve polish without creating new hidden CSS debt
- [ ] Keep the shell structurally frozen while refining the surface

## Out of Scope

| Feature | Reason |
| --- | --- |
| Rebuilding shell, tabs, or panel architecture again | This was already solved in Waves A/B |
| Reopening large responsive rewrites | Wave C already stabilized key widths |
| Business logic changes | This wave is visual polish only |
| Replacing working AJAX/drawer contracts | Runtime behavior is already healthy |
| Chasing pixel-perfect at any maintenance cost | Premium polish must still be sustainable |
| Pulling `create` mode into the same effort | Too much scope for too little gain in this residual wave |

---

## User Stories

### P1: Premium Header Finish

**User Story**: As an operator, I want the page header to feel fully resolved and intentional, so that the first impression matches the confidence of the rest of the screen.

**Acceptance Criteria**:

1. WHEN the page loads THEN the header SHALL feel visually balanced in avatar, title, badge, metadata, and CTA hierarchy
2. WHEN the screen is scanned quickly THEN the main action SHALL remain obvious without making the secondary actions feel misplaced
3. WHEN compared against the Figma THEN the header gap SHALL feel like refinement only, not redesign

---

### P1: Panel Rhythm Harmony

**User Story**: As an operator, I want `Pagamentos`, `Plano`, and `Perfil` to share one consistent visual cadence, so that changing tabs feels effortless and unsurprising.

**Acceptance Criteria**:

1. WHEN switching tabs THEN internal card spacing and section hierarchy SHALL feel related
2. WHEN reading section heads and support text THEN typography and spacing SHALL feel deliberate and consistent
3. WHEN a panel contains less content than another THEN it SHALL still feel intentional, not visually unfinished

---

### P1: Premium Surface Details

**User Story**: As an operator, I want the page details such as rows, support copy, status chips, and empty density zones to feel polished, so that the product feels premium and trustworthy.

**Acceptance Criteria**:

1. WHEN scanning ledgers, details, or meta cards THEN the page SHALL feel tidy and calm
2. WHEN hover/focus or support text appears THEN it SHALL reinforce confidence instead of adding visual noise
3. WHEN comparing the page to the Figma THEN remaining differences SHALL mostly be micro-details, not obvious structural mismatches

---

## Edge Cases

- WHEN a student has very sparse profile information THEN `Perfil` SHALL still feel balanced
- WHEN a student has debt or open charge states THEN the premium polish SHALL not reduce urgency clarity
- WHEN the plan section contains little detail THEN the card rhythm SHALL still feel intentional
- WHEN actions wrap at medium widths THEN visual polish SHALL preserve action hierarchy

---

## Risks and Fix Strategy

| Risk | Why it matters | Fix strategy |
| --- | --- | --- |
| Premium polish turns into endless tweaking | The work can drift into subjective loops | Use explicit before/after goals and stop after visible gaps are closed |
| Visual refinement adds noise | A premium look can become busy or theatrical | Keep `clarity > decoration` as the gating rule |
| Small CSS changes create hidden drift | Fine polish is where duplication can quietly return | Keep all new polish in `student-page-shell.css` and avoid legacy backslides |
| Figma pursuit becomes expensive beyond its value | The last 5% can cost too much | Optimize for premium coherence, not perfect mimicry |

---

## Operational Output Contract

All execution or review output under this residual wave must:

1. stay under **800 words per step**
2. begin with:
   - `Status`
   - `Foco`
   - `Decisao central`
   - `Principal risco`
   - `Proximo passo`
3. clearly separate:
   - what was polished
   - what was intentionally deferred
   - what premium-fidelity gap was reduced
4. avoid generic phrases like "looks nicer now" without naming what became more aligned

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| SPWCR-01 | P1: Premium Header Finish | Design | Pending |
| SPWCR-02 | P1: Premium Header Finish | Design | Pending |
| SPWCR-03 | P1: Premium Header Finish | Design | Pending |
| SPWCR-04 | P1: Panel Rhythm Harmony | Design | Pending |
| SPWCR-05 | P1: Panel Rhythm Harmony | Design | Pending |
| SPWCR-06 | P1: Panel Rhythm Harmony | Design | Pending |
| SPWCR-07 | P1: Premium Surface Details | Design | Pending |
| SPWCR-08 | P1: Premium Surface Details | Design | Pending |
| SPWCR-09 | P1: Premium Surface Details | Design | Pending |

**Coverage:** 9 total, 0 mapped to tasks, 9 unmapped warning

---

## Success Criteria

- [ ] The header feels premium and balanced without losing operational clarity
- [ ] `Pagamentos`, `Plano`, and `Perfil` share one refined visual cadence
- [ ] Remaining differences from the Figma feel like micro-refinement, not obvious gaps
- [ ] The polish work does not reintroduce hidden CSS debt
- [ ] The page feels more "finished" without feeling more complicated

## Success Verdict

This residual Wave C is only successful when the student page stops feeling like:

"a great refactor that already looks good"

and starts feeling like:

"a final product surface that just happens to be well engineered underneath."

Child-level metaphor:

The toy car already drives, shines, and has good wheels.
This wave is only about making sure the doors, stickers, and steering wheel all feel like they came from the same box.
