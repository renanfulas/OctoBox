# Darkmode Theme Hardening Specification

## Problem Statement

The OctoBOX darkmode already exists, but parts of the interface still behave like a light-first system patched after the fact.

This shows up in cards, text contrast, gradients, notices, and page-local CSS where colors and surfaces are still decided too close to the screen instead of coming from the canonical theme contract.

## Goals

- [ ] Make darkmode feel like one system instead of multiple partial interpretations
- [ ] Strengthen semantic tokens so shared primitives can be tuned centrally
- [ ] Reduce local hardcoded color debt in touched darkmode scopes
- [ ] Improve readability of cards, copy, and supporting panels in dark surfaces
- [ ] Align the shared theme with the approved premium-dark palette and neon role mapping from `docs/architecture/design-guideless.md`
- [ ] Preserve complete light-mode support while the dark palette is hardened
- [ ] Add discreet shared scrollbar styling consistent with the theme system
- [ ] Preserve the existing product structure while improving darkmode consistency

## Out of Scope

Explicitly excluded to prevent scope creep.

| Feature | Reason |
| --- | --- |
| Full product redesign | This work is about darkmode hardening, not a brand-new visual identity |
| Rewriting every CSS file in one pass | Too risky for a live brownfield front-end |
| Introducing a new component dialect | The project already has canonical theme authorities |
| Loud neon-heavy restyling | The direction is premium and restrained, not visual noise |
| Backend or template behavior changes unrelated to theme | This is a theme structure problem |

---

## User Stories

### P1: Shared Surfaces Stay Readable in Darkmode

**User Story**: As an OctoBOX user, I want cards and panels to remain readable and balanced in darkmode so that I can scan information without visual fatigue.

**Why P1**: Shared surfaces are the walls of the house. If the walls are inconsistent, every room feels off.

**Acceptance Criteria**:

1. WHEN the user views shared cards in darkmode THEN the system SHALL preserve readable text contrast and coherent elevation
2. WHEN a screen uses canonical cards or table-cards THEN the system SHALL avoid local overrides for baseline darkmode appearance
3. WHEN shared surfaces are adjusted THEN the system SHALL centralize the change in canonical tokens or primitives

**Independent Test**: Open representative darkmode screens and confirm shared cards read consistently without screen-specific patch styling.

---

### P1: Theme Tokens Cover Darkmode Intent

**User Story**: As a maintainer, I want semantic theme tokens that describe darkmode intent clearly so that global tuning does not depend on hunting hardcoded values across files.

**Why P1**: Without the right token vocabulary, every new dark fix becomes a local patch.

**Acceptance Criteria**:

1. WHEN a shared darkmode surface needs tuning THEN the system SHALL expose a semantic token for that concern
2. WHEN a shared component needs darkmode emphasis or softness THEN the system SHALL consume semantic tokens instead of direct raw colors where practical
3. WHEN new darkmode work is added THEN the system SHALL have a clearer token path to follow

**Independent Test**: Inspect touched shared CSS and confirm important darkmode decisions are routed through tokens rather than duplicated raw color values.

---

### P1: Approved Palette Becomes Semantic Theme Language

**User Story**: As the product team, we want the approved premium-dark palette to live inside the canonical theme contract so that the interface feels intentional without each screen improvising color usage.

**Why P1**: A chosen palette only helps if it becomes system behavior instead of remaining a style note in a document.

**Acceptance Criteria**:

1. WHEN shared theme tokens are updated THEN the system SHALL map urgent, warning, success, primary, and premium accents to the approved palette values
2. WHEN dark surfaces consume accent colors THEN the system SHALL use them by semantic role rather than arbitrary decorative usage
3. WHEN light mode is rendered THEN the system SHALL remain fully supported under the same semantic theme model

**Independent Test**: Review the token layer and confirm the approved palette is represented as semantic theme roles consumed by shared primitives.

---

### P2: Local Darkmode Debt Stops Competing with Canon

**User Story**: As a front-end maintainer, I want local CSS files to stop acting like small theme engines so that darkmode remains predictable.

**Why P2**: Local theme ownership is the main source of visual drift and maintenance cost.

**Acceptance Criteria**:

1. WHEN a local file still owns major darkmode colors THEN the system SHALL classify whether that value becomes a token, a canonical variant, or a justified local exception
2. WHEN a touched local screen can inherit a shared primitive safely THEN the system SHALL prefer inheritance over bespoke darkmode repainting
3. WHEN a local override remains necessary THEN the system SHALL keep it explicit and scoped

**Independent Test**: Review touched local files and confirm that darkmode ownership is reduced rather than expanded.

---

### P2: Notices and Support Copy Keep Clear Hierarchy

**User Story**: As a user, I want notices, helper copy, and supporting text to remain calm and legible in darkmode so that warnings and next actions are obvious without shouting.

**Why P2**: Darkmode fails quietly when secondary text and state panels lose hierarchy.

**Acceptance Criteria**:

1. WHEN a notice or helper panel appears in darkmode THEN the system SHALL preserve clear title, copy, and accent separation
2. WHEN supporting text is rendered on dark surfaces THEN the system SHALL avoid muddy low-contrast copy
3. WHEN state styles are tuned THEN the system SHALL align with the canonical notice family

**Independent Test**: Compare darkmode notices and supporting copy before and after the hardening wave and verify improved hierarchy.

---

### P3: Glass and Scrollbar Treatment Stay Premium but Light

**User Story**: As a user, I want glass surfaces and supporting chrome like scrollbars to feel polished and modern without distracting from operations.

**Why P3**: These details shape perceived quality, but they must stay subtle in an operational product.

**Acceptance Criteria**:

1. WHEN a shared card or overlay uses glass treatment THEN the system SHALL keep translucency, blur, and borders restrained and readable
2. WHEN shared scrollbar styling is applied THEN the system SHALL remain discreet, modern, and theme-aware
3. WHEN premium accents are used THEN the system SHALL avoid overloading one surface with too many neon signals

**Independent Test**: Compare updated surfaces and scrollbar behavior in dark and light modes and confirm the result feels premium but controlled.

---

## Edge Cases

- WHEN a page still depends on a legacy glass helper THEN the system SHALL allow a temporary bridge instead of forcing a risky cutover
- WHEN a local file mixes layout concern with theme concern THEN the system SHALL separate them before migrating values
- WHEN a dashboard-local premium treatment is intentional THEN the system SHALL preserve the local identity without letting it redefine the shared canon
- WHEN darkmode contrast improves in one surface but over-brightens another THEN the system SHALL tune the semantic token layer before adding local exceptions
- WHEN neon accents appear on the same surface THEN the system SHALL keep usage restrained and role-driven instead of combining multiple strong signals casually

---

## Success Criteria

- [ ] Darkmode shared surfaces feel visually related across major screens
- [ ] Shared primitives require fewer local darkmode overrides
- [ ] Touched local files contain less hardcoded color debt
- [ ] Notices, helper copy, and card text maintain strong hierarchy in darkmode
- [ ] The approved premium-dark palette is represented in the canonical theme layer
- [ ] Light mode remains coherent under the same semantic token system
- [ ] Shared glass surfaces and scrollbar styling feel premium and subtle rather than loud
- [ ] Future darkmode tuning can happen more from tokens and less from page patches
