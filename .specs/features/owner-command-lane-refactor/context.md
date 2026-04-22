# Context

The Owner workspace uses the shared `page_reading_list` host for the three command cards rendered below the hero.

Today this surface is hard to evolve because the same cards are influenced by:

1. shared template markup
2. shared card primitive styles
3. operation-level overrides
4. owner-local refinements

That makes the lane expensive to change and fragile to split.

## Locked scope

This feature targets only:

1. `templates/operations/owner.html`
2. a new owner-local include for the command lane
3. owner-local CSS modules for the lane
4. owner payload identity only when needed for local ownership

## Non-goals

1. redesigning Manager, Coach, or Reception
2. reopening the global `cards.css` primitive in the first wave
3. rewriting the owner page payload shape
