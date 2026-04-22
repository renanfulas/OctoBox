# Student Financial Payment Surface Hardening Tasks

**Design**: `.specs/features/student-financial-payment-surface-hardening/design.md`
**Status**: Approved

---

## Execution Plan

### Phase 1: Discovery

```text
T1 -> T2
```

### Phase 2: Surface Hardening

```text
T2 -> T3 -> T4
```

### Phase 3: Validation

```text
T4 -> T5
```

---

## Task Breakdown

### T1: Map Live Student Financial Payment Surface [Done]

**What**: Confirm the live payment templates, CSS owner, and JS selectors still carrying legacy naming.
**Where**:
- `templates/includes/catalog/student_form/financial/billing_console.html`
- `templates/includes/catalog/student_form/financial/financial_overview_payment_management.html`
- `static/js/pages/finance/student-financial-workspace.js`
**Depends on**: None
**Requirement**: SFPH-01, SFPH-03

### T2: Define Canonical Payment Button Contract [Done]

**What**: Lock the canonical naming and allowed state model for payment action buttons.
**Where**:
- touched payment templates
- owning CSS
- JS selector contract
**Depends on**: T1
**Requirement**: SFPH-01, SFPH-02, SFPH-03

### T3: Migrate Live Payment Surface Markup [Done]

**What**: Replace legacy button naming in the live payment templates.
**Where**:
- `billing_console.html`
- `financial_overview_payment_management.html`
**Depends on**: T2
**Requirement**: SFPH-01, SFPH-04

### T4: Migrate JS and Supporting CSS Contract [Done]

**What**: Move the JS selector contract and any local visual state support to canonical naming.
**Where**:
- `student-financial-workspace.js`
- `student-financial.css`
**Depends on**: T3
**Requirement**: SFPH-02, SFPH-03, SFPH-05

### T5: Validate Payment Surface Integrity [Done]

**What**: Validate that the payment surface remains clear, fast, and technically coherent.
**Where**:
- touched templates
- touched CSS owner
- touched JS owner
**Depends on**: T4
**Requirement**: SFPH-04, SFPH-05
