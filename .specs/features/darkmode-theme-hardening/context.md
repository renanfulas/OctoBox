# Context

## Why this exists now

The project already elected a canonical theme authority, but darkmode still shows residual behavior from older visual dialects and local CSS overrides.

In practical terms, the switch to darkmode is working, but some surfaces still feel like light mode wearing a dark coat.

## What we already know

1. the official token source is `static/css/design-system/tokens.css`
2. the official shared surface hosts are `static/css/design-system/components/cards.css`, `hero.css`, `states.css`, and `topbar.css`
3. the project explicitly forbids local CSS from becoming a parallel visual authority
4. multiple local CSS files still contain hardcoded `rgba(...)`, hex colors, or page-specific dark overrides
5. `docs/architecture/design-guideless.md` defines an approved aesthetic direction for premium dark surfaces, neon role colors, glassmorphism, light-mode support, and discreet scrollbar treatment

## Evidence already visible in the runtime map

1. `static/css/design-system/tokens.css` already defines light and dark tokens, but the semantic vocabulary is still too shallow for some surfaces
2. `static/css/design-system/components/cards.css` and `hero.css` largely consume tokens, but still mix in direct visual decisions that are hard to tune globally
3. `static/css/design-system/shell.css` and `workspace.css` still carry hardcoded translucent whites and bespoke gradients that can drift from the canonical dark theme
4. `static/css/catalog/student_form_stepper.css`, `static/css/catalog/import-progress.css`, and `static/css/onboarding/intakes.css` still show strong local color ownership
5. `static/css/design-system/dashboard.css` includes page-local dark premium values that may be valid locally, but must not silently redefine global darkmode behavior

## Scope boundary for the first pass

This first pass is about theme structure, not about redesigning the whole app.

That means:

1. improve darkmode consistency
2. reduce hardcoded color debt in touched areas
3. strengthen semantic tokens for surfaces, text, borders, and emphasis
4. preserve the existing product identity and current information architecture
5. adopt the approved premium-dark palette direction with only light structural adjustments

## Design direction now approved for this feature

The user explicitly wants this feature to use `docs/architecture/design-guideless.md` as a reference for theme direction.

That means the hardening work should absorb these decisions into the canonical token layer:

1. dark premium root background around `#0a0a0f`
2. full light-mode support with an iOS-inspired light palette
3. role-based neon accents:
   - red `#ff0844` for urgent and critical
   - yellow `#ffb020` for warning and pending
   - green `#00ff88` for success and goal
   - blue `#00d4ff` for primary and info
   - purple `#af52de` for accent and premium
4. glassmorphism for primary cards and overlays
5. discreet modern custom scrollbar

These are direction constraints, not permission to bypass the canonical theme contract.

In simple terms:

1. the guideline is the mood board
2. the token file is the paint factory
3. the components are where that paint gets applied

## What would create debt if we do it the wrong way

1. fixing each broken card locally without strengthening the token layer
2. adding more `body[data-theme="dark"]` exceptions inside page CSS
3. inventing new component families instead of hardening the canonical ones
4. polishing isolated screens before stabilizing shared primitives
5. copying the guideline literally into page CSS without translating it into semantic tokens first
