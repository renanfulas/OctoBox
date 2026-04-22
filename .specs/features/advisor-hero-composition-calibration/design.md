# Design

## Composition question

The original local hypothesis described a stronger centering move, but the current live diff is narrower.

The current live change only does two things inside the `@media (max-width: 720px)` block:

1. removes `--operation-hero-heading-max-width: 100%`
2. removes `--operation-hero-heading-size: clamp(1.8rem, 9vw, 2.3rem)`

## What we are testing

Does removing those mobile overrides make the advisor hero feel:

1. more composed
2. more premium
3. more intentional

without making it feel:

1. generic
2. cramped on mobile
3. less operational

## Decision options

### Keep

Chosen.

Removing the mobile overrides improves contract hygiene because those tokens are not the main selectors driving the advisor narrative hero.

### Soften

Not needed at this stage.

### Discard

Rejected.

There is no evidence that these two removed tokens are carrying the advisor hero composition in practice.
