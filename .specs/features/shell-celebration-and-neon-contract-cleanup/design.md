# Design

## Canonical Decision

JS remains responsible for:

1. deciding when celebration or blink events happen
2. inserting and removing transient nodes
3. preserving event routing and timing

CSS becomes responsible for:

1. visual composition of confetti pieces
2. toast dismissal transition
3. sessions neon overlay animation
4. topbar scroll affordance cursor

## Implementation Notes

1. confetti piece variants are now expressed through deterministic `:nth-child()` rules
2. toast dismissal is expressed through `.is-dismissing`
3. sessions neon overlay uses `.sessions-board-neon-overlay.is-active`
4. topbar scroll affordance uses `.topbar.is-shell-scroll-trigger`
