# Design

**Status**: Approved

## Scope Shape

This is a `Medium/Large` cleanup feature under the SDD workflow.

It is not broad enough to justify a system-wide redesign, but it touches a live runtime partial plus the financial design-system layer that feeds it.

The correct strategy is:

1. targeted mapping
2. semantic rename
3. token cleanup
4. short verification

## Target Files

1. `templates/includes/catalog/student_form/financial/financial_overview_topbar.html`
2. `static/css/design-system/financial.css`

Optional adjacent inspection only if needed:

1. student financial workspace templates that host the topbar
2. page-level CSS imports that still load `financial.css`

## Migration Strategy

### 1. Topbar Host Migration

Replace `elite-*` classes with local financial semantic classes that communicate role, not nostalgia.

Example direction:

1. topbar shell
2. search wrapper
3. search icon
4. search input
5. action strip
6. notification strip
7. avatar

The exact naming should favor:

1. `student-financial-*` if the scope is the student workspace
2. `financial-overview-*` if the scope is the overview module

### 2. Token Cleanup

Residual `--elite-*` usage in `financial.css` should be replaced with:

1. canonical `--theme-*`
2. existing finance-local semantic vars if the block needs its own accent

### 3. Preserve Importance Without Parallel Theme

The topbar still needs to feel like a command rail.

That means:

1. clear search affordance
2. quiet but visible pills
3. crisp avatar presence
4. enough contrast to feel like a financial command area

## Verification Model

Each implementation pass should verify:

1. `python manage.py check`
2. direct scan for `elite-*` in the touched runtime scope
3. direct scan for `var(--elite-*)` in the touched CSS
4. visual continuity judgment against the canonical theme contract
