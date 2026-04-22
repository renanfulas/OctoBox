# Context

## Locked Decisions

1. The live financial topbar residual was already migrated to canonical `student-financial-*`.
2. `var(--elite-*)` was already removed from the touched live path.
3. The next step is not redesign. It is verification and retirement of the detached residual block.
4. We should not delete anything blindly just because it looks old.

## Why This Mountain Exists

The previous mountain proved something important:

1. the active residual path is solved
2. the remaining `elite-*` block in `financial.css` appears detached from current runtime use

This means we are no longer repainting a room.
We are opening the storage closet and checking whether the old furniture is still needed.

## Boundaries

This feature should not become:

1. a redesign of student financial surfaces
2. a rewrite of finance CSS architecture
3. a broad search-and-destroy of every legacy class in the repo

The scope is:

1. confirm whether the detached `elite-*` financial block is truly dead
2. classify it safely
3. retire it if evidence supports removal
