# Class Grid Interaction Contract Cleanup Tasks

**Design**: `.specs/features/class-grid-interaction-contract-cleanup/design.md`
**Status**: Approved

---

## Execution Plan

### Phase 1: Discovery

```text
T1 -> T2
```

### Phase 2: Routing

```text
T2 -> T3
```

### Phase 3: Markup Hardening

```text
T3 -> T4 -> T5
```

### Phase 4: Validation

```text
T5 -> T6
```

---

## Task Breakdown

### T1: Map Live Class Grid Interaction Runtime [Done]

**What**: Map the exact live daily and weekly interaction paths in the class grid.
**Where**:
- `templates/includes/catalog/class_grid/today/workspace_today_row.html`
- `templates/includes/ui/class_grid/class_grid_weekly_day_card.html`
- `templates/includes/ui/class_grid/class_grid_weekly_session_chip.html`
**Depends on**: None
**Requirement**: CGICC-01, CGICC-02, CGICC-03

### T2: Define Canonical Edit and Interaction Contract [Done]

**What**: Define how edit shortcuts, delete forms, and clickable affordances should be expressed canonically.
**Where**:
- active class-grid interaction surfaces
- supporting CSS owner if needed
**Depends on**: T1
**Requirement**: CGICC-01, CGICC-03, CGICC-05

### T3: Replace Hardcoded Edit Routes [Done]

**What**: Replace handwritten class-grid edit links with canonical route generation while preserving query/fragment behavior.
**Where**:
- daily row
- weekly session chip
**Depends on**: T2
**Requirement**: CGICC-01, CGICC-04

### T4: Remove Inline Interaction Styling From Weekly Day Card [Done]

**What**: Replace inline clickable affordance styling with semantic classes and CSS-owned styling.
**Where**:
- `templates/includes/ui/class_grid/class_grid_weekly_day_card.html`
- owning CSS file if needed
**Depends on**: T3
**Requirement**: CGICC-02, CGICC-03

### T5: Normalize Remaining Active Interaction Debt [Done]

**What**: Remove any remaining inline presentational debt from the active targets touched by this pass.
**Where**:
- touched class-grid templates
- supporting class-grid CSS owner
**Depends on**: T4
**Requirement**: CGICC-02, CGICC-04

### T6: Validate Daily and Weekly Interaction Integrity [Done]

**What**: Validate that daily and weekly class-grid views remain coherent and operationally clear.
**Where**:
- touched templates
- touched CSS owners
**Depends on**: T5
**Requirement**: CGICC-04, CGICC-05
