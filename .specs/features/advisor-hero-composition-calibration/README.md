# Advisor Hero Composition Calibration

Entry point for a focused calibration of the advisor dashboard hero composition, centered on whether the current local hero-centering adjustment should be adopted, softened, or discarded.

## Open in this order

1. `context.md` - why this calibration exists
2. `corda-plan.md` - executive north, risks, and execution logic
3. `spec.md` - scope, success criteria, and non-goals
4. `design.md` - composition question and validation criteria
5. `tasks.md` - granular execution map
6. `evidence-map.md` - runtime anchors and local change evidence

## Planning North

- `README.md`
- `docs/experience/front-display-wall.md`
- `docs/experience/layout-decision-guide.md`
- `templates/dashboard/conselheiro.html`
- `templates/dashboard/blocks/advisor_narrative.html`
- `static/css/design-system/dashboard.css`

## Scope

This package exists to evaluate and finish the local dashboard hero composition adjustment now sitting in `dashboard.css`.

## Status

- Status: Completed
- Created on: `2026-03-31`
- Outcome: the advisor-specific change is a valid small cleanup in `dashboard.css`, while `operations/refinements/hero.css` is a separate broader hero refactor that should not be mixed into the same commit
