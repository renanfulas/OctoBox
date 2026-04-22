# Context

## Why this exists

The class grid interaction contract was already cleaned up, but one structural inline layout rule still remains in the workspace shell:

- `style="grid-template-columns: 2fr 1fr; align-items: start; gap: 16px;"`

That is not a behavior bug. It is a small ownership leak.

In simple terms:

- the classroom board is already organized
- but one wall is still being held by painter's tape instead of the actual bracket

## Runtime facts confirmed before opening this package

1. the live workspace shell is `templates/includes/catalog/class_grid/views/workspace.html`
2. the correct CSS owner is `static/css/catalog/class-grid/workspace.css`
3. the affected section is the weekly plus monthly side-by-side split

## Boundaries

This package does:

1. remove the inline structural layout from the class grid workspace shell
2. move that split to semantic CSS ownership
3. preserve current reading order and proportions

This package does not:

1. redesign weekly or monthly cards
2. reopen class grid interaction logic
3. change planner or quick edit behavior

## Non-goals

1. no visual redesign of the class grid
2. no responsive overhaul unless the extraction reveals an obvious local need
