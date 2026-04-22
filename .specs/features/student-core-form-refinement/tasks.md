# Student Core Form Refinement Tasks

**Design**: `.specs/features/student-core-form-refinement/design.md`
**Status**: Completed

---

## Execution Plan

### Phase 1: Structural Hygiene (Sequential)

```text
T1 -> T2
```

### Phase 2: Step Continuity and Hierarchy (Parallel OK)

```text
T2 -> T3
T2 -> T4
T2 -> T5
```

### Phase 3: Trust and Product Voice (Sequential)

```text
T3/T4/T5 -> T6 -> T7
```

---

## Task Breakdown

### T1: Remove Dominant Inline Debt From Main Form Actions [Done]

**What**: Replace inline hidden-state shortcuts in the step actions with safer class-based behavior.
**Where**:
- `templates/includes/catalog/student_form/main_form/main_form_actions.html`
**Depends on**: None
**Requirement**: SCR-02, SCR-03

### T2: Clean Intake Banner and Shell Continuity [Done]

**What**: Remove visible shortcut styling and align the intake banner with the refined product tone.
**Where**:
- `templates/includes/catalog/student_form/main_form/main_form_intake_banner.html`
- nearby shell hooks if needed
**Depends on**: T1
**Requirement**: SCR-01, SCR-02

### T3: Refine Essential/Profile/Health Step Readability [Done]

**What**: Make the early form steps easier to scan and calmer to read.
**Where**:
- `main_form_step_essential.html`
- `main_form_step_profile.html`
- `main_form_step_health.html`
**Depends on**: T2
**Requirement**: SCR-01, SCR-04

### T4: Refine Plan/Billing Step Continuity [Done]

**What**: Improve the handoff from plan choice into billing without changing rules.
**Where**:
- `main_form_step_plan.html`
- `main_form_step_billing.html`
**Depends on**: T2
**Requirement**: SCR-01, SCR-04

### T5: Clarify Stepper and Final Action Language [Done]

**What**: Make the flow feel less mechanical and more trustworthy.
**Where**:
- `main_form.html`
- `main_form_actions.html`
- related presenter copy if needed
**Depends on**: T2
**Requirement**: SCR-03, SCR-04

### T6: Reduce Residual Visual Debt In Touched Scope [Done]

**What**: Do a final pass on the touched core form scope for dominant remaining legacy smell.
**Where**:
- touched `main_form/*` templates
- local CSS/JS as needed
**Depends on**: T3, T4, T5
**Requirement**: SCR-02, SCR-05

### T7: Deep Trust and Accessibility Pass [Done]

**What**: Improve focus, keyboard flow, and predictable action feedback in the touched student core form.
**Where**:
- touched `main_form/*` templates
- stepper and action hooks
**Depends on**: T6
**Requirement**: SCR-06
