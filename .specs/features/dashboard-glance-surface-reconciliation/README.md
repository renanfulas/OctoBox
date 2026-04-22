# Dashboard Glance Surface Reconciliation

Entry point for the next dashboard surface refinement pass on OctoBox.

## Open in this order

1. `context.md` - locked intent, boundaries, and non-goals
2. `corda-plan.md` - executive north, risk framing, and execution sequence
3. `spec.md` - problem, users, requirements, and success bar
4. `design.md` - canonical relationship between glance card severity, actionability, and neon surface treatment
5. `tasks.md` - granular execution map

## Planning North

- `README.md`
- `docs/experience/front-display-wall.md`
- `docs/experience/layout-decision-guide.md`
- `docs/reference/reading-guide.md`

## Initial Scope

This feature targets the high-visibility dashboard glance surface and its neon severity treatment:

1. `static/css/design-system/components/dashboard/glance/glance_neon.css`
2. `templates/includes/ui/dashboard/dashboard_glance_card.html`
3. `templates/dashboard/blocks/priority_strip.html`

## Status

- Status: Completed
- Created on: `2026-03-30`
- Completed on: `2026-03-30`
- This package reconciled the dashboard glance strip so severity and actionability now come from semantic payload fields instead of positional text inference
