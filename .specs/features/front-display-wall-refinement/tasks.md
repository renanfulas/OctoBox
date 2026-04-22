# Front Display Wall Refinement Tasks

**Design**: `.specs/features/front-display-wall-refinement/design.md`
**Status**: In Progress

---

## Execution Plan

### Phase 1: Integrity and Hygiene (Sequential)

Tasks that must be done first, in order.

```
T1 -> T2 -> T3 -> T4
```

### Phase 2: Facade and Command Layer (Parallel OK)

After integrity fixes and baseline hygiene, these can run in parallel.

```
      -> T5 --
T4 -> -> T6 -- -> T8
      -> T7 --
```

### Phase 3: Perceived Speed and Accessibility (Sequential)

```
T8 -> T9 -> T10
```

---

## Task Breakdown

### T1: Fix Student Import Form Contract [Done]

**What**: Correct the upload form contract in the students header so the visible import action is no longer structurally broken.
**Where**: `templates/catalog/students.html`
**Depends on**: None
**Reuses**: Existing student import flow
**Requirement**: FDW-06

**Tools**:

- Skill: `CSS Front end architect`

**Done when**:

- [ ] Upload form uses the correct `multipart/form-data` contract
- [ ] The visible import CTA remains intact in the current layout
- [ ] No template syntax regression is introduced

**Verify**:

- Open the template and confirm the form contract is correct
- Run `python manage.py check`

---

### T2: Fix Finance Queue Markup Integrity [Done]

**What**: Correct the queue board closing structure so the finance facade has valid section markup.
**Where**: `templates/includes/catalog/finance/boards/queue_board.html`
**Depends on**: T1
**Reuses**: Existing finance board structure
**Requirement**: FDW-06

**Tools**:

- Skill: `CSS Front end architect`

**Done when**:

- [ ] Queue board opens and closes with matching semantic container tags
- [ ] The current visual layout remains stable
- [ ] No invalid section/article mismatch remains

**Verify**:

- Inspect the template structure directly
- Run `python manage.py check`

---

### T3: Extract Inline Front Debt From Priority Surfaces [Done]

**What**: Move dominant inline CSS and inline JS out of the main facade surfaces into stable static assets.
**Where**:
- `templates/operations/reports-hub.html`
- `templates/catalog/includes/student/student_directory_panel.html`
- `templates/includes/catalog/finance/views/hero.html`
- related files in `static/css/` and `static/js/`
**Depends on**: T2
**Reuses**:
- `static/css/design-system/components/`
- `static/css/catalog/`
- `static/js/pages/`
**Requirement**: FDW-04, FDW-05

**Tools**:

- Skill: `CSS Front end architect`
- Skill: `OctoBox High Performance Architect`

**Done when**:

- [ ] Critical inline styles are moved into CSS files
- [ ] Critical inline JS is moved into page-local or shared JS files
- [ ] IDs and data hooks remain stable for current behavior
- [ ] Page behavior remains functionally equivalent

**Verify**:

- Search the touched templates for remaining dominant `style=` and inline `<script>` blocks
- Run `python manage.py check`

---

### T4: Define Shared Front Command Layer Contract [Done]

**What**: Establish the shared command-layer structure for the top of `students`, `finance`, and `reports-hub`.
**Where**:
- `templates/catalog/students.html`
- `templates/catalog/finance.html`
- `templates/operations/reports-hub.html`
- relevant CSS modules
**Depends on**: T3
**Reuses**:
- hero grammar from `static/css/design-system/components/hero.css`
- shared states and actions modules
**Requirement**: FDW-01, FDW-02, FDW-03

**Tools**:

- Skill: `CSS Front end architect`
- Skill: `prompt-engineer`

**Done when**:

- [ ] Each target page has a clear top-of-page command contract
- [ ] The contract answers page purpose, current pressure, and next action
- [ ] The pages still feel part of the same building

**Verify**:

- Open each target template and confirm the top-of-page contract is explicit
- Compare the three tops for continuity of voice and hierarchy

---

### T5: Refine Students Facade Hero and Priority Layer [Done]

**What**: Rework the students top surface so it feels like a command facade instead of header + controls + data slab.
**Where**:
- `templates/catalog/students.html`
- `templates/catalog/includes/student/student_filters_panel.html`
- `templates/catalog/includes/student/student_directory_panel.html`
- students local CSS/JS
**Depends on**: T4
**Reuses**:
- existing KPI cards
- student filters and table partials
**Requirement**: FDW-01, FDW-08, FDW-10

**Tools**:

- Skill: `CSS Front end architect`
- Skill: `prompt-engineer`

**Done when**:

- [ ] Students page purpose is legible without reading deep table content
- [ ] A visible priority block or notice exists above the dense operational area
- [ ] Bulk-action behavior remains functional after facade refinement

**Verify**:

- Load the students page and confirm first-read clarity
- Run `python manage.py check`

---

### T6: Refine Finance Facade Hero and Pressure Map [Done]

**What**: Rework the finance top surface so pressure, queue, and next action are clearer and more staged.
**Where**:
- `templates/catalog/finance.html`
- `templates/includes/catalog/finance/views/hero.html`
- `templates/includes/catalog/finance/views/priority_rail.html`
- `templates/includes/catalog/finance/boards/control_board.html`
- finance local CSS/JS
**Depends on**: T4
**Reuses**:
- finance hero
- priority rail
- shared notice/state components
**Requirement**: FDW-02, FDW-07, FDW-11

**Tools**:

- Skill: `OctoBox UI/UX Payments Expert`
- Skill: `CSS Front end architect`
- Skill: `OctoBox High Performance Architect`

**Done when**:

- [ ] Finance top communicates pressure and next step clearly
- [ ] The active recorte summary supports reading without behaving like an export console
- [ ] The priority rail feels more like guided action than list noise

**Verify**:

- Load the finance page and confirm the first-read decision path
- Run `python manage.py check`

---

### T7: Reframe Reports Hub as Controlled Secondary Surface [Done]

**What**: Rewrite the reports hub facade so it feels purposeful and alive without visible export CTAs.
**Where**:
- `templates/operations/reports-hub.html`
- related CSS assets
**Depends on**: T4
**Reuses**:
- current card structure
- shared notice/state language
**Requirement**: FDW-03, FDW-13, FDW-14

**Tools**:

- Skill: `prompt-engineer`
- Skill: `CSS Front end architect`

**Done when**:

- [ ] The hub avoids dominant worksite language
- [ ] Each card offers a valid operational next step or status
- [ ] The page feels deliberate instead of paused

**Verify**:

- Load the reports hub and confirm it no longer reads like a placeholder
- Run `python manage.py check`

---

### T8: Normalize Front Voice Across Target Surfaces [Done]

**What**: Align titles, microcopy, and CTA language with the "O Silencio Que Acolhe" direction.
**Where**:
- `templates/catalog/students.html`
- `templates/catalog/finance.html`
- `templates/operations/reports-hub.html`
- touched partials
**Depends on**: T5, T6, T7
**Reuses**:
- Front Display Wall manifesto
- layout decision guide
**Requirement**: FDW-01, FDW-02, FDW-03, FDW-05

**Tools**:

- Skill: `prompt-engineer`

**Done when**:

- [ ] The three surfaces sound like the same product voice
- [ ] The copy invites action without shouting
- [ ] Technical or transitional messaging is no longer the dominant tone

**Verify**:

- Read the three page tops side by side
- Confirm tone continuity and clarity

---

### T9: Improve Perceived Speed and Staged Loading [Done]

**What**: Reduce visual and cognitive first-load weight on the heavy surfaces.
**Where**:
- `templates/catalog/finance.html`
- finance local JS/CSS
- `templates/catalog/students.html`
- students local JS/CSS
**Depends on**: T8
**Reuses**:
- `interactive_tabs.js`
- existing page payloads
**Requirement**: FDW-07, FDW-08, FDW-09, FDW-15, FDW-16

**Tools**:

- Skill: `OctoBox High Performance Architect`
- Skill: `CSS Front end architect`

**Done when**:

- [ ] The visible first frame is more staged and less slab-like
- [ ] Heavy secondary areas are visually or technically deferred where safe
- [ ] The page still behaves correctly with current data and navigation

**Verify**:

- Compare first render behavior before and after
- Run `python manage.py check`

---

### T10: Accessibility and Interaction Trust Pass [Done]

**What**: Harden focus, semantics, summaries, and actionable behavior across target surfaces.
**Where**:
- `templates/catalog/includes/student/student_directory_panel.html`
- `templates/includes/catalog/finance/boards/control_board.html`
- `templates/catalog/finance.html`
- supporting CSS/JS
**Depends on**: T9
**Reuses**:
- current IDs and data hooks
- shared action and state systems
**Requirement**: FDW-10, FDW-11, FDW-12

**Tools**:

- Skill: `CSS Front end architect`
- Skill: `OctoBox UI/UX Payments Expert`

**Done when**:

- [ ] Actionable areas no longer depend solely on mouse-heavy interaction
- [ ] Filter summaries can communicate changes accessibly
- [ ] Focus and semantics are clearer in the touched areas

**Verify**:

- Keyboard-walk the touched interfaces
- Run `python manage.py check`

---

## Parallel Execution Map

```text
Phase 1 (Sequential):
  T1 -> T2 -> T3 -> T4

Phase 2 (Parallel):
  T4 complete, then:
    |- T5 [P]
    |- T6 [P]
    \- T7 [P]

Phase 3 (Sequential):
  T5, T6, T7 complete, then:
    T8 -> T9 -> T10
```

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: Fix student import form contract | 1 template fix | Good |
| T2: Fix finance queue markup integrity | 1 template fix | Good |
| T3: Extract inline front debt | Multiple related surface files | OK if executed surgically |
| T4: Define shared front command layer contract | Cross-surface design task | OK |
| T5: Refine students facade hero | One surface | Good |
| T6: Refine finance facade hero | One surface | Good |
| T7: Reframe reports hub | One surface | Good |
| T8: Normalize front voice | Cross-surface copy refinement | OK |
| T9: Improve perceived speed and staged loading | Cross-surface front optimization | OK |
| T10: Accessibility and interaction trust pass | Cross-surface hardening | OK |

---

## Notes for Execution

1. This plan should use the project's existing visual tools first.
2. If a task uncovers a true local rebuild opportunity, pause and surface it before implementation.
3. Avoid reopening backend or model architecture unless a front fix proves impossible otherwise.
