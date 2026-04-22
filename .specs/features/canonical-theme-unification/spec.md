# Canonical Theme Unification Specification

## Problem Statement

The OctoBOX theme currently behaves like multiple valid systems stacked on top of each other instead of one authoritative visual language.

This creates inconsistent cards, banners, heroes, and topbar behavior across the product, increases CSS conflict, and makes every new front-end refinement harder than it should be.

## Goals

- [ ] Establish one canonical theme authority for the product
- [ ] Normalize core visual primitives so they stop competing with each other
- [ ] Create a migration path from legacy visual dialects to the final canon
- [ ] Reduce long-term front-end maintenance cost caused by visual authority conflicts

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
| --- | --- |
| Full product redesign | This phase is about authority unification, not inventing a brand new app |
| Backend behavior changes | The problem is visual system authority, not business rules |
| Export/reporting product scope | Not part of the theme canon effort |
| Immediate retirement of every legacy class | Some aliases may need temporary coexistence during migration |

---

## User Stories

### P1: Canonical Core Primitives Star MVP

**User Story**: As a product team, we want one canonical theme authority for the core UI primitives so that the app feels like one product instead of multiple overlapping visual systems.

**Why P1**: Without a canonical base, every future front-end improvement will continue to fight the cascade and multiply inconsistency.

**Acceptance Criteria**:

1. WHEN the team works on tokens, cards, hero, banners, or topbar THEN the system SHALL define one canonical authority for each family
2. WHEN a core primitive has legacy competitors THEN the system SHALL classify them as canonical, alias, migrate, or remove
3. WHEN a new core primitive change is introduced THEN the system SHALL have one documented theme contract to follow

**Independent Test**: Review the feature package and confirm every core primitive family has one named authority and one migration direction.

---

### P1: Theme Families Stop Competing

**User Story**: As an OctoBOX user, I want banners, cards, hero blocks, and top navigation to feel like they belong to the same building so that the app feels stable and intentional.

**Why P1**: This is the user-facing proof that the canonical theme is working.

**Acceptance Criteria**:

1. WHEN the user moves between target surfaces THEN the system SHALL preserve continuity of elevation, spacing rhythm, and visual tone
2. WHEN a template uses a surface primitive THEN the system SHALL avoid mixing multiple competing base families for the same visual role
3. WHEN a top-level area is normalized THEN the system SHALL consume the canonical primitive instead of redefining it locally

**Independent Test**: Compare the migrated surfaces and verify that the same visual families are applied consistently.

---

### P2: Legacy Migration Matrix

**User Story**: As a front-end maintainer, I want a clear migration matrix for legacy visual classes so that I know what to keep, alias, migrate, and retire.

**Why P2**: This prevents the team from solving the same confusion repeatedly.

**Acceptance Criteria**:

1. WHEN a legacy class family is audited THEN the system SHALL map it to a canonical destination
2. WHEN a class is still needed temporarily THEN the system SHALL label it as alias instead of leaving its status ambiguous
3. WHEN a class family has no future under the canon THEN the system SHALL mark it for retirement

**Independent Test**: Open the design and tasks docs and verify there is an explicit mapping path for legacy families.

---

### P2: Guardrails Against New Divergence

**User Story**: As the product team, we want documented guardrails for theme authority so that new work does not reintroduce competing visual dialects.

**Why P2**: A canon without guardrails becomes another temporary wave.

**Acceptance Criteria**:

1. WHEN the team introduces a new visual pattern THEN the system SHALL route it through the canonical theme contract
2. WHEN a file tries to redefine a core primitive locally THEN the system SHALL treat that as an exception, not a new authority
3. WHEN migration is complete for a family THEN the system SHALL document which files still hold legacy debt

**Independent Test**: Review the final plan and confirm the governance rules are explicit.

---

### P3: Reduce Dominant Visual Patch Debt

**User Story**: As a maintainer, I want the most conflict-heavy visual debt reduced over time so that the CSS becomes more predictable and less fragile.

**Why P3**: This is high-value, but it can happen in waves after the canonical theme is defined.

**Acceptance Criteria**:

1. WHEN migration waves are executed THEN the system SHALL reduce high-conflict `!important` and visual patch usage in touched areas
2. WHEN a template is normalized THEN the system SHALL reduce dominant inline visual debt in that scope

**Independent Test**: Compare conflict counts and touched scopes before and after the migration waves.

---

## Edge Cases

- WHEN a legacy class is deeply reused THEN the system SHALL allow a temporary alias instead of forcing a risky global break
- WHEN topbar-specific behavior depends on its own sizing rules THEN the system SHALL migrate behavior without preserving a separate competing visual authority
- WHEN a screen still mixes multiple surface families THEN the system SHALL normalize the base role before polishing local details
- WHEN a utility class provides layout help but also visual authority THEN the system SHALL split helper responsibility from theme responsibility

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| THM-01 | P1: Canonical Core Primitives | Design | Pending |
| THM-02 | P1: Canonical Core Primitives | Design | Pending |
| THM-03 | P1: Theme Families Stop Competing | Design | Pending |
| THM-04 | P1: Theme Families Stop Competing | Design | Pending |
| THM-05 | P2: Legacy Migration Matrix | Design | Pending |
| THM-06 | P2: Legacy Migration Matrix | Design | Pending |
| THM-07 | P2: Guardrails Against New Divergence | Design | Pending |
| THM-08 | P2: Guardrails Against New Divergence | Design | Pending |
| THM-09 | P3: Reduce Dominant Visual Patch Debt | Design | Pending |
| THM-10 | P3: Reduce Dominant Visual Patch Debt | Design | Pending |

**Coverage**: 10 total, 0 mapped to tasks, 10 unmapped

---

## Success Criteria

- [ ] One canonical authority is defined for tokens, cards, banners, hero, and topbar
- [ ] Legacy visual families have an explicit migration destination
- [ ] The team can explain which classes are canonical and which are transitional
- [ ] The migrated product surfaces feel like one visual system instead of overlapping dialects
- [ ] The canonical theme becomes the base for future work
