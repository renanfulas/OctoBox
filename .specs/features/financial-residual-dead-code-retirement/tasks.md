# Financial Residual Dead-Code Retirement Tasks

**Design**: `.specs/features/financial-residual-dead-code-retirement/design.md`
**Status**: Approved

---

## Execution Plan

### Phase 1: Evidence Gathering

```text
T1 -> T2
```

### Phase 2: Classification and Removal

```text
T2 -> T3 -> T4
```

### Phase 3: Final Validation

```text
T4 -> T5
```

---

## Task Breakdown

### T1: Search the Detached Financial Residual Families [Done]

**What**: Search repo-wide for the detached `elite-*` families in `financial.css`.
**Where**:
- `static/css/design-system/financial.css`
- repo-wide evidence search
**Depends on**: None
**Requirement**: FDRR-01

**Done when**:

- [ ] Each detached family has a search result summary
- [ ] We know whether usage is present, absent, or uncertain

**Verify**:

- repo-wide search for the detached class families

---

### T2: Classify Each Residual Family by Risk [Done]

**What**: Classify each detached family as live, dead, or uncertain.
**Where**:
- planning notes for this feature
**Depends on**: T1
**Requirement**: FDRR-01, FDRR-03

**Done when**:

- [ ] Each family is classified with evidence
- [ ] Removal candidates are explicit

**Verify**:

- read the classification summary top to bottom

---

### T3: Retire Dead Residual Classes from `financial.css` [Done]

**What**: Remove the detached classes that are sufficiently proven dead.
**Where**:
- `static/css/design-system/financial.css`
**Depends on**: T2
**Requirement**: FDRR-02

**Done when**:

- [ ] Dead classes are removed
- [ ] No uncertain or live class is removed by accident

**Verify**:

- inspect the file diff for only the intended class families

---

### T4: Run Runtime Integrity Validation [Done]

**What**: Validate the cleanup after removal.
**Where**:
- repo root
**Depends on**: T3
**Requirement**: FDRR-04

**Done when**:

- [ ] `python manage.py check` passes
- [ ] no removed family reappears in a live reference search

**Verify**:

- `python manage.py check`
- repo-wide search for the removed class families

---

### T5: Publish the Classification Outcome [Done]

**What**: Record what was removed, what remained, and why.
**Where**:
- local feature notes
**Depends on**: T4
**Requirement**: FDRR-05

**Done when**:

- [ ] removed families are listed
- [ ] retained families, if any, are explained
- [ ] next residual risk is clear

**Verify**:

- read the outcome summary and ensure it matches the code
