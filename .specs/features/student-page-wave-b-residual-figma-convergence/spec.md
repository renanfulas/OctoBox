# Student Page Wave B Residual Figma Convergence Specification

## Problem Statement

The original Wave B objective was to bring the student page to the `80%` convergence zone with the approved Figma.

After Waves A, B, C, and D, the page is no longer structurally far from that target.

The current reality is:

- the page already has the canonical shell
- `Pagamentos`, `Plano`, and `Perfil` already live in one visual family
- the most expensive structural debt has already been reduced
- the shell is much cheaper to change than it was before

That means the remaining Wave B work is no longer architectural.
It is residual convergence work.

Today, the page still has a few controlled gaps versus the Figma:

- `Plano` is strong, but still not as visually resolved as `Pagamentos`
- `Perfil` is coherent, but still reads more like a good operational form than a Figma-level polished panel
- the student header is close, but not yet fully aligned in proportion, spacing, and premium feel
- some spacing and hierarchy choices are already good enough for production, but not yet at the intended `80%` visual confidence level

Wave B Residual exists to close that gap without reopening architecture, state, backend behavior, or legacy retirement work.

This is not a rewrite wave.
This is not a polish obsession wave like Wave C.
This is a focused convergence wave to declare the original Wave B fully closed.

## Goals

- [ ] Elevate `Plano` to the same visual confidence as `Pagamentos`
- [ ] Reduce the remaining inherited “form-first” feeling inside `Perfil`
- [ ] Refine the student header until it reads closer to the approved Figma
- [ ] Improve spacing, panel weight, and hierarchy where fidelity is still slightly behind
- [ ] Close the original Wave B intent without reintroducing architectural churn

## Out of Scope

Explicitly excluded in Wave B Residual to prevent scope drift.

| Feature | Reason |
| --- | --- |
| New shell architecture | Already solved in Wave A |
| Legacy retirement and structural residue cleanup | Already handled in Wave D |
| Deep responsive redesign | Wave C already stabilized responsiveness |
| New AJAX or backend contracts | Not necessary for residual Figma convergence |
| Full pixel-perfect implementation | Too costly for the remaining delta |
| Reworking create-mode legacy behavior | This residual wave targets the modern student detail page, not the old create flow |

---

## User Stories

### P1: Plan Panel at the Same Visual Level

**User Story**: As an operator, I want `Plano` to feel as polished and intentional as `Pagamentos`, so that switching between these tabs feels like staying inside one premium product surface.

**Why P1**: `Plano` is already structurally good, but it still has slightly less visual authority than the best panel on the page.

**Acceptance Criteria**:

1. WHEN the user opens `Plano` THEN the panel SHALL feel as visually resolved as `Pagamentos`
2. WHEN the operator compares title, price, detail blocks, and action rows THEN hierarchy SHALL feel deliberate and premium
3. WHEN actions are scanned THEN sensitive actions SHALL remain clear without visually shouting

**Independent Test**: Open `Pagamentos`, then `Plano`, and confirm the second panel no longer feels like the “less finished sibling.”

---

### P1: Profile Panel With Lower Inherited Form Weight

**User Story**: As an operator, I want `Perfil` to feel like a polished page panel instead of a well-organized leftover form, so that it belongs naturally to the same visual system as the other tabs.

**Why P1**: `Perfil` is coherent, but still the easiest place to feel the older operational DNA.

**Acceptance Criteria**:

1. WHEN the user opens `Perfil` THEN the panel SHALL read like a page section, not a legacy form stack
2. WHEN blocks are scanned THEN `Dados cadastrais`, `Saude e observacoes`, and actions SHALL feel intentionally grouped
3. WHEN the page is compared to the Figma THEN the profile surface SHALL feel closer in rhythm and density

**Independent Test**: Open `Perfil` and confirm it reads like a designed panel, not a safe fallback.

---

### P1: Header Convergence

**User Story**: As an operator, I want the student header to feel closer to the approved Figma, so that the page starts strong and communicates production-level confidence immediately.

**Why P1**: The header is already good, but it still leaves some visual fidelity on the table.

**Acceptance Criteria**:

1. WHEN the page opens THEN the student header SHALL feel proportionally aligned and visually premium
2. WHEN the user scans avatar, name, meta row, status, and CTAs THEN the composition SHALL feel cleaner and more intentional
3. WHEN the header is compared to the Figma THEN the remaining gap SHALL feel small, not structural

**Independent Test**: Compare the rendered header against the Figma and confirm the difference is refinement, not mismatch.

---

### P2: Residual Figma Fidelity Without Architectural Drift

**User Story**: As a maintainer, I want the remaining Figma gap reduced without reopening structural work, so that the visual finish improves while maintenance stays calm.

**Why P2**: After Wave D, the project must protect its structural gains.

**Acceptance Criteria**:

1. WHEN this residual wave is implemented THEN backend contracts SHALL remain unchanged
2. WHEN visual fidelity increases THEN no new cross-panel architectural coupling SHALL be introduced
3. WHEN the wave ends THEN the work SHALL still feel like a refinement layer, not a hidden rewrite

---

## Edge Cases

- WHEN the student is overdue THEN the header and payments banner SHALL remain readable without stealing all visual oxygen
- WHEN plan data are sparse THEN `Plano` SHALL still feel premium and intentional
- WHEN profile data are incomplete THEN `Perfil` SHALL still preserve balance and hierarchy
- WHEN the operator jumps between tabs quickly THEN perceived visual quality SHALL remain consistent
- WHEN dark mode is active THEN the residual convergence work SHALL not create louder contrast than the rest of the product

---

## Risks and Fix Strategy

| Risk | Why it matters | Fix strategy |
| --- | --- | --- |
| Residual Wave B turns into hidden Wave C/D work | The project may reopen already closed fronts | Keep scope limited to visual convergence only |
| Figma fidelity work becomes decorative noise | Stronger fidelity should not reduce clarity | Keep `clarity > fidelity gimmicks` as the final filter |
| Plan and Profile over-correct and lose operational calm | A more premium panel can still become visually louder than needed | Promote hierarchy and spacing, not ornament |
| Header refinement introduces CTA imbalance | The top area is operationally sensitive | Adjust proportions and spacing without creating CTA competition |
| Residual wave becomes endless polish | The last 10% can consume too much attention | Define a strict finish line at “Wave B fully closed,” not pixel obsession |

---

## Operational Output Contract

All execution or review output produced under this Wave B Residual spec must follow these guardrails:

1. maximum of **800 words per implementation/report step**
2. always start with:
   - `Status`
   - `Foco`
   - `Decisao central`
   - `Principal risco`
   - `Proximo passo`
3. clearly separate:
   - what visual convergence improved
   - what was intentionally preserved
   - which Figma gap was reduced
4. avoid vague claims like “closer now” without naming which panel, hierarchy, or spacing issue was improved

The goal is to make residual refinement measurable and finite.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| SPWBR-01 | P1: Plan Panel at the Same Visual Level | Design | Pending |
| SPWBR-02 | P1: Plan Panel at the Same Visual Level | Design | Pending |
| SPWBR-03 | P1: Plan Panel at the Same Visual Level | Design | Pending |
| SPWBR-04 | P1: Profile Panel With Lower Inherited Form Weight | Design | Pending |
| SPWBR-05 | P1: Profile Panel With Lower Inherited Form Weight | Design | Pending |
| SPWBR-06 | P1: Profile Panel With Lower Inherited Form Weight | Design | Pending |
| SPWBR-07 | P1: Header Convergence | Design | Pending |
| SPWBR-08 | P1: Header Convergence | Design | Pending |
| SPWBR-09 | P1: Header Convergence | Design | Pending |
| SPWBR-10 | P2: Residual Figma Fidelity Without Architectural Drift | Design | Pending |
| SPWBR-11 | P2: Residual Figma Fidelity Without Architectural Drift | Design | Pending |
| SPWBR-12 | P2: Residual Figma Fidelity Without Architectural Drift | Design | Pending |

**Coverage:** 12 total, 0 mapped to tasks, 12 unmapped warning

---

## Success Criteria

How we know Wave B Residual was a success:

- [ ] `Plano` feels as visually strong as `Pagamentos`
- [ ] `Perfil` no longer reads like the least-finished panel
- [ ] the student header feels closer to the approved Figma in rhythm, spacing, and weight
- [ ] the remaining gap to the Figma feels like optional premium polish, not an unfinished wave
- [ ] structural calm from Waves A-D remains intact

## Success Verdict

Wave B Residual is only considered **successful** when the student page feels like it has fully crossed the `80%` line promised by the original plan.

In child-level metaphor:

If the house already stands, is painted, and has working lights, but one room still looks like the moving boxes were never fully unpacked, Wave B Residual is not done.
It ends when every main room looks like it belongs to the same house without anyone pointing at one corner and saying “that part still feels temporary.”
