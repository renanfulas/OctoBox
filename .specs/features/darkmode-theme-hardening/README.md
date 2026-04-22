# Darkmode Theme Hardening

Entry point for the darkmode hardening wave focused on making the product feel intentional, readable, and structurally consistent in dark surfaces.

## Open in this order

1. `context.md` - why this work exists now and what is already known
2. `corda-plan.md` - executive north, risks, direction, and first waves
3. `spec.md` - problem, goals, boundaries, and success bar
4. `design.md` - how tokens and canonical primitives should absorb the fixes
5. `tasks.md` - granular execution map

## Planning North

- `README.md`
- `docs/architecture/design-guideless.md`
- `docs/reference/design-system-contract.md`
- `docs/experience/css-guide.md`
- `.specs/codebase/CONVENTIONS.md`
- `.specs/codebase/CONCERNS.md`
- `.specs/features/canonical-theme-unification/README.md`
- `.specs/features/canonical-theme-unification/corda-plan.md`
- `.specs/features/canonical-theme-unification/design.md`

## Initial Scope

This feature hardens darkmode where the current theme contract is still leaking:

1. shared cards and surfaces
2. hero and topbar readability
3. notices, status panels, and copy contrast
4. local CSS files that still carry light-first color decisions or hardcoded values
5. premium dark palette alignment using the approved neon accent roles from `design-guideless.md`

## Status

- Status: Draft
- Created on: `2026-04-03`
- This package exists to turn darkmode from a visual toggle into a reliable theme system
