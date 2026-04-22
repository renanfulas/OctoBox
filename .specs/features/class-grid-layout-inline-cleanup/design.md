# Design

## Canonical ownership rule

The workspace template should declare:

1. structure
2. reading order
3. local semantic hook names

The workspace CSS should declare:

1. proportions
2. alignment
3. spacing

## Proposed local hook

The weekly-plus-monthly split should receive a dedicated semantic class, owned by `workspace.css`.

That class should express:

1. two-column layout
2. 2fr / 1fr proportion
3. start alignment
4. local gap

## Residual tolerance

If responsive files already govern the mobile collapse indirectly, that is acceptable.
The debt here is the inline desktop structure, not the full responsive system.
