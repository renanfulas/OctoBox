# Premium Legacy Islands Cleanup Tasks

**Design**: `.specs/features/premium-legacy-islands-cleanup/design.md`
**Status**: Approved

---

## Execution Plan

### Phase 1: Advisor Island Cleanup (Sequential)

```text
T1 -> T2 -> T3
```

### Phase 2: Finance Legacy Absorption (Sequential)

```text
T3 -> T4 -> T5
```

### Phase 3: Student Financial Legacy Retirement (Sequential)

```text
T5 -> T6 -> T7 -> T8
```

### Phase 4: Final Consistency Pass (Sequential)

```text
T8 -> T9 -> T10
```

---

## Task Breakdown

### T1: Extract Advisor Narrative Inline Debt [Done]

**What**: Remove dominant inline style from the advisor narrative shell and move structure into canonical dashboard CSS.
**Where**:
- `templates/dashboard/blocks/advisor_narrative.html`
- related dashboard CSS assets
**Depends on**: None
**Reuses**:
- canonical `hero` language
- dashboard semantic classes already introduced in the advisor pass
**Requirement**: PLI-01, PLI-02, PLI-04

**Tools**:

- Skill: `CSS Front end architect`
- Skill: `prompt-engineer`

**Done when**:

- [ ] Dominant inline style is removed from the advisor narrative
- [ ] The block still feels premium and intentional
- [ ] The narrative shell reads as part of the canonical theme

**Verify**:

- Inspect the target template for `style=`
- Run `python manage.py check`

---

### T2: Rebuild Advisor Manifesto Modal as Canonical Surface [Done]

**What**: Convert the manifesto modal from a legacy premium popup into a canonical system surface with controlled styling and behavior.
**Where**:
- `templates/dashboard/blocks/advisor_manifesto_modal.html`
- related dashboard CSS/JS assets
**Depends on**: T1
**Reuses**:
- canonical card/surface system
- dashboard page script if suitable
**Requirement**: PLI-01, PLI-02, PLI-04, PLI-07

**Tools**:

- Skill: `CSS Front end architect`
- Skill: `prompt-engineer`
- Skill: `OctoBox Master Debugger`

**Done when**:

- [ ] Dominant inline style and inline script are removed
- [ ] The modal still opens, closes, and reads clearly
- [ ] The modal feels native to the canonical theme

**Verify**:

- Inspect the target template for `style=`, `<style>`, and `<script>`
- Run `python manage.py check`

---

### T3: Align Advisor Voice and Surface Rhythm [Done]

**What**: Harmonize the advisor narrative and manifesto so they sound and feel like the same product as the newly governed shell.
**Where**:
- `templates/dashboard/blocks/advisor_narrative.html`
- `templates/dashboard/blocks/advisor_manifesto_modal.html`
**Depends on**: T2
**Reuses**:
- `docs/experience/front-display-wall.md`
- `docs/experience/css-guide.md`
**Requirement**: PLI-01, PLI-04, PLI-09

**Tools**:

- Skill: `prompt-engineer`

**Done when**:

- [ ] Advisor surfaces no longer feel like a visual time capsule
- [ ] Tone remains premium, calm, and operational
- [ ] The advisor area feels continuous with the shell

**Verify**:

- Read the touched blocks side by side with the canonical dashboard chrome

---

### T4: Absorb Finance Hero Into Canonical Host [Done]

**What**: Replace legacy premium host ownership in the finance hero with the canonical host system.
**Where**:
- `templates/includes/catalog/finance/views/hero.html`
- related finance CSS
**Depends on**: T3
**Reuses**:
- canonical `hero`
- finance-specific local classes
**Requirement**: PLI-01, PLI-03, PLI-05

**Tools**:

- Skill: `CSS Front end architect`
- Skill: `OctoBox UI/UX Payments Expert`

**Done when**:

- [ ] `glass-panel-elite` no longer governs the finance hero
- [ ] The hero still feels elevated and clear
- [ ] The block reads as part of the canonical theme

**Verify**:

- Inspect the template for `glass-panel-elite`
- Run `python manage.py check`

---

### T5: Absorb Finance Movements Surface Into Canonical Card Language [Done]

**What**: Retire the legacy premium host from the finance movements panel and align it with canonical surfaces.
**Where**:
- `templates/includes/catalog/finance/views/movements.html`
- related finance CSS
**Depends on**: T4
**Reuses**:
- canonical `card`
- existing finance movement semantics
**Requirement**: PLI-01, PLI-03, PLI-05

**Tools**:

- Skill: `CSS Front end architect`
- Skill: `OctoBox UI/UX Payments Expert`

**Done when**:

- [ ] `glass-panel-elite` no longer governs the movement panel
- [ ] The panel keeps urgency and readability
- [ ] The panel feels visually continuous with the rest of finance

**Verify**:

- Inspect the template for `glass-panel-elite`
- Run `python manage.py check`

---

### T6: Retire Premium Legacy Hosts in Student Financial Overview [Done]

**What**: Remove `elite-glass-card` from the main student financial overview surfaces and migrate them to the canonical card family.
**Where**:
- `templates/includes/catalog/student_form/financial/financial_overview.html`
- `templates/includes/catalog/student_form/financial/financial_overview_id_card.html`
- `templates/includes/catalog/student_form/financial/financial_overview_kpis.html`
**Depends on**: T5
**Reuses**:
- canonical `card`
- local financial workspace classes
**Requirement**: PLI-01, PLI-03, PLI-06

**Tools**:

- Skill: `CSS Front end architect`
- Skill: `OctoBox UI/UX Payments Expert`

**Done when**:

- [ ] `elite-glass-card` stops acting as primary host in the touched overview scope
- [ ] The overview still feels important and premium
- [ ] Scanability stays strong

**Verify**:

- Inspect the touched templates for `elite-glass-card`
- Run `python manage.py check`

---

### T7: Retire Premium Legacy Hosts in Student Financial Status and Ledger [Done]

**What**: Remove `glass-panel-elite` and `elite-glass-card` from the status and ledger areas while preserving trust and contrast.
**Where**:
- `templates/includes/catalog/student_form/financial/financial_overview_status.html`
- `templates/includes/catalog/student_form/financial/stripe_elite_ledger.html`
**Depends on**: T6
**Reuses**:
- canonical `card`
- current ledger semantics
**Requirement**: PLI-01, PLI-03, PLI-06, PLI-07

**Tools**:

- Skill: `CSS Front end architect`
- Skill: `OctoBox UI/UX Payments Expert`
- Skill: `OctoBox Master Debugger`

**Done when**:

- [ ] Legacy premium hosts are removed from the touched status and ledger scope
- [ ] The financial area still feels trustworthy and high-value
- [ ] No interaction contract is broken

**Verify**:

- Inspect the touched templates for `elite-glass-card` and `glass-panel-elite`
- Run `python manage.py check`

---

### T8: Tighten Local CSS to Make Premium an Accent, Not a Parallel System [Done]

**What**: Normalize the local CSS in touched advisor, finance, and student financial areas so premium survives only as an accent layer.
**Where**:
- touched dashboard CSS
- touched finance CSS
- touched student financial CSS
**Depends on**: T7
**Reuses**:
- canonical theme tokens
- current local semantic classes
**Requirement**: PLI-01, PLI-08, PLI-09

**Tools**:

- Skill: `CSS Front end architect`
- Skill: `OctoBox High Performance Architect`

**Done when**:

- [ ] The touched CSS no longer behaves like a shadow theme
- [ ] Premium cues exist as accent and finish, not as sovereign grammar
- [ ] Local CSS still stays fast and understandable

**Verify**:

- Inspect touched CSS for legacy host ownership patterns
- Run `python manage.py check`

---

### T9: Perform a Short Visual Consistency Review on the Touched Islands [Done]

**What**: Re-check the touched islands after migration and identify any remaining dominant contrast.
**Where**:
- advisor touched templates
- finance touched templates
- student financial touched templates
**Depends on**: T8
**Reuses**:
- canonical theme contract
- post-governance review method
**Requirement**: PLI-01, PLI-09

**Tools**:

- Skill: `CSS Front end architect`
- Skill: `prompt-engineer`

**Done when**:

- [ ] The touched areas feel like the same product
- [ ] Any remaining contrast is small enough to classify as residual polish
- [ ] No new parallel visual authority appears

**Verify**:

- Read and compare the touched templates and CSS together

---

### T10: Publish the Outcome and Lock the Next Residuals

**What**: Record what was retired, what remains, and what future cleanup should avoid reopening.
**Where**:
- `docs/experience/css-guide.md` if governance needs a small extension
- local feature notes if applicable
**Depends on**: T9
**Reuses**:
- canonical theme governance
- migration decisions from this feature
**Requirement**: PLI-08

**Tools**:

- Skill: `prompt-engineer`

**Done when**:

- [ ] The cleanup outcome is documented where needed
- [ ] The next residuals are clearly identified
- [ ] The team has a stable handoff point after the cleanup

**Verify**:

- Read the updated guidance and confirm it matches the implemented cleanup
