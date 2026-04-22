# Front Display Wall Refinement Specification

## Problem Statement

The OctoBOX front already has a strong structural base, but key surfaces still expose worksite signals, inline front-end debt, and weak priority framing. This breaks the Front Display Wall contract: the product should appear as a living, coherent product facade, not as a technically correct set of pages with scaffolding still visible.

The current pain is not "missing UI", but a mismatch between operational truth and facade clarity. We need to refine the visible product layer so users understand what matters now, trust the interface, and move quickly without visual noise.

## Goals

- [ ] Make the main front surfaces feel like a coherent product facade within the first 3 seconds of reading
- [ ] Remove visible worksite noise, inline front-end debt, and broken interaction details from the first-line user experience
- [ ] Improve perceived speed and action clarity without reopening the core runtime architecture

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
| --- | --- |
| Full shell rewrite | The shell is already stable enough for this phase |
| New export workflows | Export is intentionally postponed from the main facade |
| Backend financial redesign | This phase is facade-first, not domain rewrite |
| Mobile app redesign | This plan is for the current web front surfaces |
| New payment automations | Valuable, but not required to refine the visible facade |

---

## User Stories

### P1: Surface Clarity and Priority Hero ⭐ MVP

**User Story**: As an operational user, I want each main surface to show what the page is for, what is healthy, and what needs action now, so that I can decide fast without reading the whole page.

**Why P1**: This is the core promise of the Front Display Wall and the biggest current gap in the visible product.

**Acceptance Criteria**:

1. WHEN a user opens the `students` surface THEN the system SHALL show a clear top-level command layer with page purpose and current priority
2. WHEN a user opens the `finance` surface THEN the system SHALL show a clear top-level command layer with financial pressure and next action
3. WHEN a user opens the `reports-hub` surface THEN the system SHALL communicate a purposeful next step instead of worksite language

**Independent Test**: Open each surface and confirm that a first-time reader can describe the page purpose and immediate action within a few seconds.

---

### P1: Remove Front-Facing Worksite Debt ⭐ MVP

**User Story**: As a user, I want the visible interface to feel polished and intentional, so that the product does not look unfinished or fragile.

**Why P1**: Visible debt weakens trust immediately, even if the backend is stable.

**Acceptance Criteria**:

1. WHEN the main surfaces render THEN the system SHALL not rely on dominant inline CSS or inline JS for critical page behavior
2. WHEN the user sees front-facing copy THEN the system SHALL not present "worksite" messaging as the main narrative of the page
3. WHEN the user uses import or queue-related UI THEN the system SHALL not hit obvious markup or form bugs in the visible flow

**Independent Test**: Inspect the main templates and verify that the key facade no longer depends on inline styles/scripts and no visible bug remains in upload/queue markup.

---

### P1: Perceived Speed and Cognitive Lightness ⭐ MVP

**User Story**: As an operational user, I want the product to feel quick and light, so that I do not feel friction from heavy page loading or overstuffed screens.

**Why P1**: The product promise is operational fluency. Heavy front surfaces break that promise even before true latency is measured.

**Acceptance Criteria**:

1. WHEN a user opens `finance` THEN the system SHALL avoid loading or emphasizing unnecessary below-the-fold complexity before the active area matters
2. WHEN a user opens `students` THEN the system SHALL present a readable, staged surface instead of an undifferentiated slab of controls and data
3. WHEN the front uses supporting scripts THEN the system SHALL preserve graceful behavior and fallback semantics

**Independent Test**: Load the page and confirm the visible first frame feels prioritized and staged rather than dense and noisy.

---

### P2: Accessibility and Interaction Trust

**User Story**: As a keyboard or assistive-tech user, I want the main operational surfaces to expose clear focus, semantic structure, and resilient summaries, so that the interface remains trustworthy beyond mouse-heavy flows.

**Why P2**: This improves polish and stability, but it can follow the facade-defining work.

**Acceptance Criteria**:

1. WHEN a user navigates filters, tabs, and table actions THEN the system SHALL expose usable focus and semantic landmarks
2. WHEN a filter summary changes THEN the system SHALL communicate that change accessibly
3. WHEN a row is actionable THEN the system SHALL not depend solely on row click behavior

**Independent Test**: Navigate with keyboard and confirm focus, summary updates, and action access remain understandable.

---

### P2: Reports Hub as Controlled Secondary Surface

**User Story**: As an owner or manager, I want the reports hub to feel deliberate and useful even without visible export buttons, so that it supports the product story instead of looking like a paused feature.

**Why P2**: The hub is secondary right now, but its tone still affects product trust.

**Acceptance Criteria**:

1. WHEN an authorized user opens `reports-hub` THEN the system SHALL present a valid operational purpose and next step
2. WHEN export actions are intentionally hidden THEN the system SHALL explain the state without sounding like unfinished work

**Independent Test**: Open the hub and confirm it feels like a controlled technical room, not a dead-end placeholder.

---

### P3: Advanced Loading and Snapshot Enhancements

**User Story**: As a frequent user, I want heavy surfaces to feel near-instant even as the system grows, so that the product scales without turning into a slow panel.

**Why P3**: High value, but can follow the main facade cleanup.

**Acceptance Criteria**:

1. WHEN heavy metrics are needed THEN the system SHALL support snapshot or cache-backed reads where appropriate
2. WHEN financial tabs are not yet active THEN the system SHALL be eligible for staged or lazy rendering

---

## Edge Cases

- WHEN a page has no urgent items THEN the system SHALL still communicate purpose and calm next steps without looking empty or dead
- WHEN filters are active THEN the system SHALL show the active context without dominating the page
- WHEN exports remain hidden THEN the system SHALL avoid dead-end copy or suspended-feature language in the main facade
- WHEN inline behavior is moved out of templates THEN the system SHALL preserve functional parity for current operational actions
- WHEN a first-time user opens a page THEN the system SHALL understand the page purpose before reading deep detail

---

## Requirement Traceability

Each requirement gets a unique ID for tracking across design, tasks, and validation.

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| FDW-01 | P1: Surface Clarity and Priority Hero | Design | Pending |
| FDW-02 | P1: Surface Clarity and Priority Hero | Design | Pending |
| FDW-03 | P1: Surface Clarity and Priority Hero | Design | Pending |
| FDW-04 | P1: Remove Front-Facing Worksite Debt | Design | Pending |
| FDW-05 | P1: Remove Front-Facing Worksite Debt | Design | Pending |
| FDW-06 | P1: Remove Front-Facing Worksite Debt | Design | Pending |
| FDW-07 | P1: Perceived Speed and Cognitive Lightness | Design | Pending |
| FDW-08 | P1: Perceived Speed and Cognitive Lightness | Design | Pending |
| FDW-09 | P1: Perceived Speed and Cognitive Lightness | Design | Pending |
| FDW-10 | P2: Accessibility and Interaction Trust | Design | Pending |
| FDW-11 | P2: Accessibility and Interaction Trust | Design | Pending |
| FDW-12 | P2: Accessibility and Interaction Trust | Design | Pending |
| FDW-13 | P2: Reports Hub as Controlled Secondary Surface | Design | Pending |
| FDW-14 | P2: Reports Hub as Controlled Secondary Surface | Design | Pending |
| FDW-15 | P3: Advanced Loading and Snapshot Enhancements | Design | Pending |
| FDW-16 | P3: Advanced Loading and Snapshot Enhancements | Design | Pending |

**Coverage:** 16 total, 0 mapped to tasks, 16 unmapped warning

---

## Success Criteria

How we know the feature is successful:

- [ ] The top of `students`, `finance`, and `reports-hub` communicates purpose, pressure, and next action clearly
- [ ] The front no longer leads with worksite language or visible structural sloppiness
- [ ] Critical front bugs and markup inconsistencies are removed from the main flow
- [ ] The visible facade feels lighter, more staged, and more intentional without reopening the architecture
