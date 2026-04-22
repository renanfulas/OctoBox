# Runtime Map

## T1 Result

This map records what in `financial.css` is still alive in runtime versus what is currently likely residual/dead.

## Live Runtime References

The following classes are still used by the live runtime in:

- `templates/includes/catalog/student_form/financial/financial_overview_topbar.html`

Live classes:

1. `elite-financial-topbar`
2. `elite-search-wrapper`
3. `elite-search-icon`
4. `elite-search-input`
5. `elite-topbar-actions`
6. `elite-notification-pill-strip`
7. `elite-ping-dot`
8. `elite-avatar-small`

These classes define the remaining active residual command rail inside the student financial workspace.

## Likely Dead or Detached Residual Classes

The following classes were found in:

- `static/css/design-system/financial.css`

But were not found in active runtime template usage during this pass:

1. `elite-id-card-hero`
2. `elite-id-card-hero__inner`
3. `elite-id-card-hero__identity`
4. `elite-avatar-large`
5. `elite-id-card-hero__stats`
6. `elite-kpi-grid`
7. `elite-kpi-card`
8. `elite-kpi-card__head`
9. `elite-kpi-card__label`
10. `elite-kpi-card__value`
11. `elite-kpi-card__meta`

These should be treated as:

1. likely-dead residual code
2. or detached legacy support that no longer feeds the current student financial workspace

## Residual Token Evidence

This evidence was true during T1:

1. `var(--elite-accent)` in the ping dot accent
2. `var(--elite-accent)` in the large avatar accent

After T5:

1. the touched live path no longer uses `var(--elite-*)`
2. the contextual topbar now depends on canonical semantic vars
3. the remaining residue is class naming in a likely-dead detached block, not token authority in the live path

## Explicit Migration Scope for T2-T6

The next implementation scope should focus on:

1. the live topbar runtime markup
2. the matching topbar styles in `financial.css`
3. the touched `--elite-*` token usage in that same path

The likely-dead `elite-id-card-hero` and `elite-kpi-*` block should not be redesigned blindly in the next step.

First, we migrate the live command rail.
Then, if needed, we decide whether the detached residual block deserves:

1. deletion
2. archival
3. a later dead-code cleanup mountain

## T2 Naming Decision

The canonical naming for the live residual command rail is:

1. `student-financial-topbar`
2. `student-financial-topbar-search`
3. `student-financial-topbar-search-icon`
4. `student-financial-topbar-search-input`
5. `student-financial-topbar-actions`
6. `student-financial-topbar-notice-strip`
7. `student-financial-topbar-notice-label`
8. `student-financial-topbar-notice-value`
9. `student-financial-topbar-ping`
10. `student-financial-topbar-avatar`

Reasoning:

1. it stays inside the `student-financial-*` namespace already used by the current workspace
2. it describes role, not old prestige
3. it avoids creating a new parallel host family beside the canonical theme

## T7 Final Classification

### Resolvido

1. the live topbar runtime no longer uses `elite-*`
2. the touched live CSS no longer uses `var(--elite-*)`
3. the residual command rail now reads as canonical `student-financial-*`

### Residual toleravel

1. `elite-id-card-hero*`
2. `elite-mini-stat-box*`
3. `elite-kpi-*`

These still exist in `financial.css`, but they remain detached from the main runtime path inspected in this mountain.

### Proxima montanha real

If we want to go further after this cleanup, the next smart move is:

1. a dead-code cleanup or residual retirement pass for the detached `elite-*` financial block
2. not a redesign of the already-cleaned live topbar path
