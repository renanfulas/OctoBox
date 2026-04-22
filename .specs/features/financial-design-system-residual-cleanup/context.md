# Context

## Locked Decisions

1. The canonical theme remains the final authority.
2. Premium can survive only as accent and atmosphere, never as a parallel design system.
3. We should not reopen the already-cleaned advisor, finance overview surfaces, or student financial core unless a true regression is found.
4. This cleanup must stay targeted on the residual live bridge between:
   - `templates/includes/catalog/student_form/financial/financial_overview_topbar.html`
   - `static/css/design-system/financial.css`

## Why This Mountain Exists

The previous cleanup retired the visible premium legacy hosts from the student financial workspace.

But the short consistency review found one important remaining live island:

1. `financial_overview_topbar.html` still renders live `elite-*` classes
2. `financial.css` still ships `--elite-*` color usage
3. the touched financial workspace is visually cleaner than the design-system layer that still feeds parts of it

In simple words:

- the main room is already painted
- but the command desk still has old buttons wired to the previous control panel

## Boundaries

This feature should not become:

1. a full student financial redesign
2. a full finance page redesign
3. a token rewrite beyond the residual financial scope

The goal is precision, not demolition.
