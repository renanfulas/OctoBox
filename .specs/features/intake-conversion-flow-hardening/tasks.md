# Intake Conversion Flow Hardening Tasks

**Design**: `.specs/features/intake-conversion-flow-hardening/design.md`
**Status**: Completed

---

## Execution Plan

### Phase 1: Discovery

```text
T1 -> T2
```

### Phase 2: Extraction

```text
T2 -> T3 -> T4
```

### Phase 3: Canonicalization

```text
T4 -> T5
```

### Phase 4: Validation

```text
T5 -> T6 -> T7
```

---

## Task Breakdown

### T1: Map Live Intake Conversion Runtime [Done]

**What**: Map the exact live path from intake queue to student conversion.
**Where**:
- `templates/onboarding/includes/intake/intake_queue_panel.html`
- `templates/onboarding/includes/intake/conversion_drawer.html`
- `static/js/pages/onboarding/conversion_drawer.js`
- `onboarding/presentation.py`
**Depends on**: None
**Requirement**: ICFH-01, ICFH-02, ICFH-03, ICFH-04

### T2: Define Drawer Interaction Contract [Done]

**What**: Define the canonical runtime decision for the drawer and its interaction contract.
**Where**:
- conversion drawer template
- conversion drawer JS
**Depends on**: T1
**Requirement**: ICFH-01, ICFH-02

### T3: Classify Dormant Drawer and Remove Live Asset Coupling [Done]

**What**: Remove dormant drawer asset loading and dormant payload weight from the live intake center page contract.
**Where**:
- `onboarding/presentation.py`
**Depends on**: T2
**Requirement**: ICFH-01, ICFH-02

### T4: Normalize Queue Conversion Link [Done]

**What**: Replace the hardcoded student-creation conversion href in the intake queue template.
**Where**:
- `templates/onboarding/includes/intake/intake_queue_panel.html`
**Depends on**: T3
**Requirement**: ICFH-03

### T5: Canonicalize Presenter Route Generation [Done]

**What**: Replace raw string route assembly with named-route generation in the onboarding presenter.
**Where**:
- `onboarding/presentation.py`
**Depends on**: T4
**Requirement**: ICFH-04

### T6: Validate Conversion Flow Integrity [Done]

**What**: Validate that queue handoff, plan selection, and payment-path intent still work coherently.
**Where**:
- touched template
- touched JS
- touched presenter
**Depends on**: T5
**Requirement**: ICFH-05

### T7: Run Runtime Verification and Publish Final Note [Done]

**What**: Run `python manage.py check` and publish the final state of the hardening pass.
**Where**:
- touched runtime files
- feature notes
**Depends on**: T6
**Requirement**: ICFH-05
