# Operations Action Redirect Contract Cleanup

Entry point for the next short operational hardening pass on OctoBox.

## Open in this order

1. `context.md` - locked intent, boundaries, and non-goals
2. `corda-plan.md` - executive north, risk framing, and execution sequence
3. `spec.md` - problem, users, requirements, and success bar
4. `design.md` - canonical redirect contract after real operational mutations
5. `tasks.md` - granular execution map

## Planning North

- `README.md`
- `docs/experience/front-display-wall.md`
- `docs/experience/layout-decision-guide.md`
- `docs/reference/reading-guide.md`

## Initial Scope

This feature targets live operational action views whose fallback navigation still depends on handwritten paths:

1. `operations/action_views.py`
2. manager return flows
3. coach return flows
4. fragment-preserving redirects only where they are already part of the runtime contract

## Status

- Status: Completed
- Created on: `2026-03-30`
- Completed on: `2026-03-30`
- This package hardened manager and coach operational redirects so live mutations now return through named route contracts instead of handwritten paths
