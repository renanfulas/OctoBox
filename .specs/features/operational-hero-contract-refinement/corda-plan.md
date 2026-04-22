# C.O.R.D.A. Plan

## Context

`hero.css` is a shared operational contract, not a local skin.

## Objective

Determine which parts of the live diff improve the hero system and finish the refactor without creating cross-screen drift.

## Risks

1. changing shared hero density can break multiple screens at once
2. a premium-looking hero can still fail if command readability drops
3. mixing local exceptions with shared contract work creates rollback confusion

## Direction

Inspect first, classify second, apply only what preserves command authority and cross-surface coherence.

## Actions

1. map live diffs against the current shared contract
2. classify changes as keep / soften / revert
3. validate representative consumers
4. commit only after the shared story is isolated
