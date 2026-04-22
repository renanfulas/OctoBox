# Management Decision Payload Enrichment

Entry point for the next strategic backend-to-front decision pass on OctoBox.

## Open in this order

1. `context.md` - locked intent, boundaries, and non-goals
2. `corda-plan.md` - executive north, risk framing, and execution sequence
3. `spec.md` - problem, users, requirements, and success bar
4. `design.md` - how payloads should express urgency, reason, and next action
5. `tasks.md` - granular execution map

## Planning North

- `README.md`
- `docs/experience/front-display-wall.md`
- `docs/experience/layout-decision-guide.md`
- `docs/reference/reading-guide.md`

## Initial Scope

This feature targets the management surfaces where the UI is already cleaner than the payload intelligence beneath it:

1. `dashboard/dashboard_snapshot_queries.py`
2. `catalog/finance_snapshot/metrics.py`
3. `catalog/presentation/finance_center_page.py`
4. `operations/queries.py`
5. local presenters only when needed to expose priority without duplicating business rules

## Status

- Status: Completed
- Created on: `2026-03-30`
- Completed on: `2026-03-30`
- This package made dashboard, finance, and management operations carry stronger priority context without reopening broad UI cleanup
