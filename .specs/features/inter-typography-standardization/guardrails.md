# Inter Typography Guardrails

## Canonical Rule

`Inter` is the default voice of OctoBOX product surfaces.

Use:

- `var(--font-body)` for body copy, labels, support text, standard headings, and form surfaces
- `var(--font-display)` for intentional display emphasis such as KPI values or hero-level titles

Do not introduce a new local type family when the same result can be achieved through the canonical tokens.

## Allowed Exceptions

These are healthy exceptions and do not count as typography drift:

1. emoji or symbol font stacks for:
   - emoji icons
   - symbol fallbacks
   - platform rendering support

## Drift Rule

A local `font-family` is considered drift when:

1. it changes regular product text away from `Inter`
2. it introduces a decorative family without explicit product approval
3. it bypasses `--font-body` or `--font-display` for ordinary headings, cards, forms, logs, IDs, or page copy

## Decision Ladder

Before adding `font-family` locally, ask:

1. Can this use `var(--font-body)`?
2. If not, can it use `var(--font-display)`?
3. If not, is this an emoji or symbol rendering exception?
4. If not, stop and justify the exception in the feature spec or review notes

## Review Checklist

When reviewing typography work:

1. check whether the file is product surface or technical surface
2. reject new local type families for normal product text
3. reject local type families for technical text too, unless the exception is emoji rendering
4. prefer token usage over raw family names

## Practical Examples

### Good

- `font-family: var(--font-body);`
- `font-family: var(--font-display);`

### Bad

- `font-family: "Aptos", sans-serif;` in a regular product page
- `font-family: "Rockwell", serif;` in a product card title
- `font-family: ui-monospace, SFMono-Regular, Menlo, monospace;` in technical text if the product contract now demands Inter everywhere
- adding a new family locally just to make one section “feel special”

## Child-Level Metaphor

Think of `Inter` as the school uniform.

Almost everyone should wear the same uniform.
Emoji fonts are like special shoes only for a sports presentation where the normal uniform cannot do the job.
What we do not want is random students showing up with a different uniform just because they felt like it.
