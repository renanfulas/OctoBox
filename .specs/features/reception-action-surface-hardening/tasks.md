# Reception Action Surface Hardening Tasks

**Design**: `.specs/features/reception-action-surface-hardening/design.md`
**Status**: Approved

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

### Phase 3: Validation

```text
T4 -> T5
```

---

## Task Breakdown

### T1: Map Reception Payment Card Behavior and Debt [Done]

**What**: Map the live behaviors, inline styles, and data dependencies in the reception payment card.
**Where**:
- `templates/operations/includes/reception/reception_payment_card.html`
**Depends on**: None
**Requirement**: RASH-01, RASH-02, RASH-03

### T2: Define Extraction Strategy for WhatsApp and Block States [Done]

**What**: Define how the inline WhatsApp flow and blocked states will move into safer structure.
**Where**:
- reception payment card
- supporting JS/CSS owners
**Depends on**: T1
**Requirement**: RASH-02, RASH-03

### T3: Extract Inline Behavior Into Asset Layer [Done]

**What**: Move inline `onclick` logic into static JS with explicit data hooks.
**Where**:
- reception payment card template
- supporting JS asset
**Depends on**: T2
**Requirement**: RASH-02, RASH-03

### T4: Extract Inline Visual Debt and Normalize Surface Layout [Done]

**What**: Remove dominant inline style usage and normalize the action surface visually.
**Where**:
- reception payment card template
- supporting CSS owner
**Depends on**: T3
**Requirement**: RASH-01, RASH-04, RASH-05

### T5: Validate Desk Flow Integrity [Done]

**What**: Validate that the reception payment flow remains operationally clear and intact.
**Where**:
- touched template
- supporting assets
**Depends on**: T4
**Requirement**: RASH-03, RASH-04
