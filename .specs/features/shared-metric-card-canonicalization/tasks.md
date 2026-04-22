# Shared Metric Card Canonicalization Tasks

**Design**: `.specs/features/shared-metric-card-canonicalization/design.md`
**Status**: Approved

---

## Execution Plan

### Phase 1: Discovery

```text
T1 -> T2
```

### Phase 2: Component Canonicalization

```text
T2 -> T3 -> T4
```

### Phase 3: Validation

```text
T4 -> T5
```

---

## Task Breakdown

### T1: Map Shared Metric Card Usage and Ownership [Done]

**What**: Find where the shared metric card is used and which CSS actually owns its visual contract.
**Where**:
- `templates/includes/ui/shared/metric_card.html`
- related CSS ownership
**Depends on**: None
**Requirement**: SMC-04, SMC-05

### T2: Define Canonical Host Strategy for the Shared Metric Card [Done]

**What**: Decide the canonical structural host and allowed accent layer for the component.
**Where**:
- shared metric card component
- owning CSS layer
**Depends on**: T1
**Requirement**: SMC-01, SMC-04

### T3: Migrate the Shared Metric Card Markup [Done]

**What**: Remove the structural legacy host from the shared metric card markup.
**Where**:
- `templates/includes/ui/shared/metric_card.html`
**Depends on**: T2
**Requirement**: SMC-01, SMC-03

### T4: Adjust Canonical Styling and Accent Finish [Done]

**What**: Re-skin the component under the canonical theme without flattening the metric experience.
**Where**:
- owning CSS for the shared metric card
**Depends on**: T3
**Requirement**: SMC-02, SMC-04

### T5: Validate Major Usage Contexts [Done]

**What**: Check major surfaces using the component and confirm behavior and visual continuity.
**Where**:
- representative runtime contexts
**Depends on**: T4
**Requirement**: SMC-03, SMC-05
