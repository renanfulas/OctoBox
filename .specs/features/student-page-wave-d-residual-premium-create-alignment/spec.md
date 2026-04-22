# Student Page Wave D Residual Premium and Create Alignment Specification

## Problem Statement

The original Wave D already achieved its core mission:

- the student page no longer depends on the worst legacy shell scaffolding
- `Pagamentos` owns more of its structure explicitly
- CSS entry boundaries are cleaner
- cascade coincidence is lower
- the canonical student page feels much more independent

That means the original retirement wave is complete.

What remains now is a **Wave D residual** with three optional but high-value goals:

1. push premium fidelity a little further where the page still feels "almost final"
2. retire more legacy residue where the cost-benefit is still favorable
3. decide whether `create` mode should move closer to the canonical student page language

This residual wave exists because the page is already strong enough that the next work must be selective.

This is not a mandatory cleanup wave.
This is an elective high-leverage wave.

In simple terms:

The treehouse already stands on its own.
Now we are deciding whether to:

- sand the railings even more
- replace the last old boards still hidden in the floor
- and maybe build the ladder in the same style as the treehouse itself

## Goals

- [ ] Close the most visible premium-fidelity gaps that still remain after the residual Wave C polish
- [ ] Retire any remaining high-friction legacy residue with clear maintenance payoff
- [ ] Evaluate and optionally align `create` mode with the canonical student-page language
- [ ] Preserve runtime stability while raising the ceiling of long-term maintainability
- [ ] Keep the wave disciplined so it does not drift into a broad rewrite

## Out of Scope

| Feature | Reason |
| --- | --- |
| Rebuilding the student page architecture again | The shell is already healthy |
| Backend redesign or domain rule changes | This wave is about surface maturity and residual debt |
| Full replacement of all create-mode flows | Too expensive unless we target the most valuable slice |
| Pixel-perfect mimicry regardless of cost | The goal is premium coherence with sane maintenance cost |
| Design-system rewrite of unrelated pages | This wave must stay scoped to the student page |

---

## User Stories

### P1: Residual Premium Fidelity

**User Story**: As a product owner, I want the student page to feel even closer to the approved Figma where the remaining gap is still noticeable, so that the page feels intentionally premium from top to bottom.

**Acceptance Criteria**:

1. WHEN scanning the page THEN the remaining differences from the Figma SHALL feel like micro-detail, not unfinished resolution
2. WHEN comparing `Header`, `Pagamentos`, `Plano`, and `Perfil` THEN the page SHALL feel premium and consistent across all major zones
3. WHEN polish is added THEN operational clarity SHALL remain stronger than decoration

---

### P1: Last High-Value Legacy Retirement

**User Story**: As a maintainer, I want the last meaningful legacy pressure points reduced when the payoff is clear, so that the student page becomes even cheaper to evolve without reopening the whole system.

**Acceptance Criteria**:

1. WHEN a remaining legacy dependency is kept THEN its reason SHALL be explicit and acceptable
2. WHEN a remaining legacy dependency is removed THEN the maintenance benefit SHALL be clear and local
3. WHEN future edits are made THEN fewer layout or style decisions SHALL depend on old student-form pathways

---

### P2: Optional Create Alignment

**User Story**: As an operator creating a new student, I may want the create flow to feel closer to the canonical student page, so that update and create no longer feel like cousins from different product generations.

**Acceptance Criteria**:

1. WHEN the team decides to align `create` mode THEN the alignment SHALL happen in a scoped and safe way
2. WHEN `create` mode is not fully aligned THEN the residual mismatch SHALL be intentional and documented
3. WHEN create-mode improvements are made THEN they SHALL not destabilize existing student creation behavior

---

## Edge Cases

- WHEN the team decides not to touch `create` mode yet THEN the wave SHALL still be successful through premium fidelity and targeted legacy retirement
- WHEN residual polish exposes a hidden legacy dependency THEN the work SHALL stop at the local boundary instead of expanding blindly
- WHEN the student has minimal data THEN premium refinement SHALL not create empty-looking or decorative-only panels
- WHEN the page is already "good enough" THEN this wave SHALL prefer discipline over perfectionism

---

## Risks and Fix Strategy

| Risk | Why it matters | Fix strategy |
| --- | --- | --- |
| Residual work becomes an open-ended perfection loop | Late polish can consume effort without proportional gain | Define specific premium gaps before editing and stop after they close |
| Legacy retirement with low payoff wastes time | Not every old piece is worth replacing now | Retire only residue with clear maintenance benefit |
| `create` alignment silently becomes a rewrite | Create mode still protects useful older behavior | Treat create alignment as optional and slice-based |
| Premium fidelity introduces visual noise | Chasing beauty can weaken operational clarity | Keep `clarity > decoration` as a hard rule |

---

## Operational Output Contract

All execution or review output under this residual Wave D must:

1. stay under **800 words per step**
2. begin with:
   - `Status`
   - `Foco`
   - `Decisao central`
   - `Principal risco`
   - `Proximo passo`
3. clearly separate:
   - what premium gap was reduced
   - what legacy residue was retired
   - what was intentionally preserved
4. avoid vague claims like "even better now" without naming the exact payoff

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| SPWDR-01 | P1: Residual Premium Fidelity | Design | Pending |
| SPWDR-02 | P1: Residual Premium Fidelity | Design | Pending |
| SPWDR-03 | P1: Residual Premium Fidelity | Design | Pending |
| SPWDR-04 | P1: Last High-Value Legacy Retirement | Design | Pending |
| SPWDR-05 | P1: Last High-Value Legacy Retirement | Design | Pending |
| SPWDR-06 | P1: Last High-Value Legacy Retirement | Design | Pending |
| SPWDR-07 | P2: Optional Create Alignment | Design | Pending |
| SPWDR-08 | P2: Optional Create Alignment | Design | Pending |
| SPWDR-09 | P2: Optional Create Alignment | Design | Pending |

**Coverage:** 9 total, 0 mapped to tasks, 9 unmapped warning

---

## Success Criteria

- [ ] Remaining premium gaps are reduced to elective micro-details
- [ ] The last high-value legacy pressure points are either retired or intentionally documented
- [ ] The team has a clear decision on whether `create` mode stays legacy or begins alignment
- [ ] No new technical debt is introduced while chasing polish

## Success Verdict

This residual Wave D is successful when the student page feels like:

"a mature, premium page with mostly native bones and only deliberate legacy left"

instead of:

"a great page that still has a few old parts we have not decided about yet."

Child-level metaphor:

The bike already rides fast and straight.
This wave is only about deciding whether to swap the last old pedal and make the training wheels match the new paint.
