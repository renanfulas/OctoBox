# Context

## Why this exists

Most major front-end cleanup is done, so the next meaningful gain comes from reconciling high-visibility surfaces that may be clean technically but ambiguous semantically.

The dashboard glance strip is one of those surfaces:

1. it is visually prominent
2. it carries urgency and actionability signals
3. it already has a dedicated neon layer
4. it may still need alignment between severity language and visual contract

In simple terms:

- the alarm panel is already mounted
- now we need to decide whether its lights speak the same language as the control tower

## Runtime facts confirmed before opening this package

1. the glance neon layer lives in `glance_neon.css`
2. glance severity is driven in `dashboard_glance_card.html` through `is-emergency`, `is-warning`, `is-risk`, `is-actionable`, and `is-tranquil`
3. priority strip cards are assembled in `priority_strip.html`

## Boundaries

This package does:

1. inspect the glance surface as a contract, not just as styling
2. align severity, actionability, and visual emphasis if needed
3. keep the surface high-signal and readable

This package does not:

1. redesign the whole dashboard
2. reopen decision payload enrichment
3. touch unrelated dashboard surfaces

## Non-goals

1. no generic animation rewrite for the whole app
2. no new dashboard card system
