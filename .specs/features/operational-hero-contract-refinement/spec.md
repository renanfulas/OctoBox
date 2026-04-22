# Spec

## Goal

Refine the shared operational hero contract in `hero.css` so that hero spacing, heading rhythm, copy width, action density, and mobile behavior are explicit, coherent, and safely reusable.

## In scope

1. `static/css/design-system/operations/refinements/hero.css`
2. consumer inspection in operations, catalog, and any pages inheriting `operation-hero`
3. contract-level density, rhythm, and responsive behavior

## Out of scope

1. dashboard-only hero variants
2. semantic payload changes
3. unrelated Python/view logic

## Success criteria

1. shared hero rules feel more intentional across representative consumers
2. mobile readability is preserved
3. the contract is easier to reason about than before
4. the resulting diff can be committed as one clean shared-CSS story
