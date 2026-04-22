# Student Financial Payment Surface Hardening

Entry point for the completed financial hardening pass on the live payment surface inside the student workspace.

## Open in this order

1. `context.md` - locked decisions and scope boundaries
2. `corda-plan.md` - executive north, risks, direction, and execution waves
3. `evidence-map.md` - live runtime proof for payment actions, naming, and ownership
4. `spec.md` - the problem, users, requirements, and success bar
5. `design.md` - how the payment surface should be canonicalized without raising checkout friction
6. `tasks.md` - granular execution map

## Planning North

- `README.md`
- `docs/experience/front-display-wall.md`
- `docs/experience/css-guide.md`
- `docs/reference/reading-guide.md`
- `.specs/codebase/CONVENTIONS.md`
- `.specs/codebase/CONCERNS.md`
- `.agents/workflows/SDD/SKILL.md`

## Final Scope

This feature targets the live student financial payment surface:

1. `templates/includes/catalog/student_form/financial/billing_console.html`
2. `templates/includes/catalog/student_form/financial/financial_overview_payment_management.html`
3. `static/js/pages/finance/student-financial-workspace.js`
4. the owning student financial CSS layer only where needed to support canonical naming and state

## Status

- Status: Completed
- Created on: `2026-03-30`
- Approved on: `2026-03-30`
- Completed on: `2026-03-30`
- This package records the hardening of the live student financial payment surface without reopening the whole student financial workspace
