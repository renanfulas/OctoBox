# Financial Design-System Residual Cleanup Tasks

**Design**: `.specs/features/financial-design-system-residual-cleanup/design.md`
**Status**: Approved

---

## Execution Plan

### Phase 1: Residual Mapping

```text
T1 -> T2
```

### Phase 2: Runtime Host Migration

```text
T2 -> T3 -> T4
```

### Phase 3: Design-System Cleanup

```text
T4 -> T5 -> T6
```

### Phase 4: Final Verification

```text
T6 -> T7
```

---

## Task Breakdown

### T1: Map Live References in the Financial Residual Scope [Done]

**What**: Confirm which classes and tokens in the residual financial design-system scope are still alive in runtime.
**Where**:
- `templates/includes/catalog/student_form/financial/financial_overview_topbar.html`
- `static/css/design-system/financial.css`
**Depends on**: None
**Requirement**: FDR-01, FDR-02, FDR-06

**Done when**:

- [ ] Live runtime classes are identified
- [ ] Dead or likely-unused residual classes are separated from live ones
- [ ] The migration scope is explicit

**Verify**:

- Search for live class usage across templates

---

### T2: Define the Canonical Financial Topbar Naming [Done]

**What**: Choose the new semantic naming for the remaining financial command strip.
**Where**:
- `financial_overview_topbar.html`
- `financial.css`
**Depends on**: T1
**Requirement**: FDR-01, FDR-05

**Done when**:

- [ ] The new naming is semantically clear
- [ ] It does not create a new parallel host family
- [ ] It fits the canonical theme contract

**Verify**:

- Compare the proposed naming against `css-guide.md`

---

### T3: Migrate the Financial Overview Topbar Markup [Done]

**What**: Replace the live `elite-*` markup with canonical local naming.
**Where**:
- `templates/includes/catalog/student_form/financial/financial_overview_topbar.html`
**Depends on**: T2
**Requirement**: FDR-01, FDR-03

**Done when**:

- [ ] The topbar template no longer depends on `elite-*` classes
- [ ] Search, actions, and pills remain readable
- [ ] The rail still feels important

**Verify**:

- Inspect the target template for `elite-`

---

### T4: Re-Skin the Financial Topbar in the Design-System Layer [Done]

**What**: Update `financial.css` to support the new runtime naming without reviving a shadow theme.
**Where**:
- `static/css/design-system/financial.css`
**Depends on**: T3
**Requirement**: FDR-03, FDR-04, FDR-05

**Done when**:

- [ ] The new naming is fully styled
- [ ] The topbar keeps command clarity
- [ ] Premium remains accent, not system

**Verify**:

- Read the touched CSS together with the touched template

---

### T5: Remove Residual `--elite-*` Tokens in the Touched Financial CSS [Done]

**What**: Replace residual `--elite-*` token usage in the touched scope.
**Where**:
- `static/css/design-system/financial.css`
**Depends on**: T4
**Requirement**: FDR-02, FDR-05

**Done when**:

- [ ] The touched financial CSS no longer uses `var(--elite-*)`
- [ ] Accent values now come from canonical or finance-local semantic vars

**Verify**:

- Search the touched CSS for `var(--elite-`

---

### T6: Normalize Financial CSS Header, Comments, and Intent [Done]

**What**: Rewrite the file header and any legacy framing so the file documents the canonical intent instead of the old elite phase.
**Where**:
- `static/css/design-system/financial.css`
**Depends on**: T5
**Requirement**: FDR-04, FDR-06

**Done when**:

- [ ] Legacy naming in comments no longer frames the file
- [ ] The file reads as a maintained canonical support layer

**Verify**:

- Read the file header and touched sections top to bottom

---

### T7: Final Verification and Residual Classification [Done]

**What**: Perform a short final verification and classify what was solved versus what may remain for a later mountain.
**Where**:
- touched runtime template
- touched financial CSS
**Depends on**: T6
**Requirement**: FDR-01, FDR-02, FDR-04, FDR-05

**Done when**:

- [ ] The residual financial design-system scope feels canonical
- [ ] Any remaining debt is explicitly classified
- [ ] `python manage.py check` passes

**Verify**:

- Run `python manage.py check`
- Re-scan the touched scope for `elite-` and `var(--elite-`
