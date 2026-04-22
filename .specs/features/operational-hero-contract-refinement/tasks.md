# Operational Hero Contract Refinement Tasks

**Design**: `.specs/features/operational-hero-contract-refinement/design.md`  
**Status**: In Progress

## Tasks

### T1: Inventory the Shared Hero Diff [Completed]

Mapped the live `hero.css` diff by contract dimension:

1. spatial rhythm
   - `--operation-hero-gap`
   - `--operation-hero-main-gap`
   - `--operation-hero-stack-gap`
2. text mass and reading width
   - `--operation-hero-stack-max-width`
   - `--operation-hero-copy-max-width`
   - `--operation-hero-copy-line-height`
3. action rail density
   - `--operation-hero-actions-gap`
   - `justify-content`
   - `align-items`
   - `margin-inline`
4. button density
   - `--operation-hero-button-min-height`
   - `--operation-hero-button-padding`
   - button font size / weight
5. baseline typography behavior
   - `.operation-hero-main .eyebrow`
   - mobile `--operation-hero-heading-size`
6. responsive heading behavior
   - explicit `@media (max-width: 720px)` heading-size / copy-size / stack-gap

Representative consumers inspected:

1. `operations/manager/scene.css`
2. `operations/reception/scene.css`
3. `catalog/students/scene.css`
4. `catalog/finance/_hero.css`

Main insight:

1. `hero.css` is true shared authority for hero rhythm
2. several consumers already override density locally
3. this means T2 must separate good baseline improvements from values that should remain consumer-specific

### T2: Classify Keep / Soften / Revert [Completed]

Classification completed by contract dimension:

1. Keep in shared authority
   - explicit mobile fallback for heading / copy / stack rhythm
   - eyebrow baseline typography
   - action row `justify-content: flex-start`
   - action row `align-items: flex-start`
   - action row `margin-inline: 0`
   - explicit `--operation-hero-actions-gap`
2. Soften in shared authority
   - wider stack/copy mass is directionally good, but must not become too editorial for fast operational screens
   - global rhythm clamps are good, but need to stay modest because manager / reception / coach already tighten locally
   - button density increase is directionally good, but should remain conservative in the shared layer
3. Revert or avoid as shared authority
   - nothing in the live diff is rejected as conceptually wrong
   - however, any values that force transactional heroes to feel slower or heavier should remain consumer-level overrides instead of shared defaults

Decision north:

1. shared contract should keep the clearer structure and mobile safeguards
2. shared contract should not overreach into editorial-width defaults that local fast surfaces clearly keep tighter

### T3: Apply the Final Shared Contract [Completed]

Applied the moderated shared contract in `hero.css`:

1. kept explicit mobile fallback rules
2. kept eyebrow baseline and cleaner action-row alignment defaults
3. softened shared width / spacing / button-density values so fast operational consumers are not forced into an overly editorial baseline
4. left the worktree with only `hero.css` modified for this story

### T4: Validate Representative Consumers and Close [Completed]

Validation outcome:

1. `python manage.py check` passed cleanly
2. the runtime worktree for this story is isolated to `static/css/design-system/operations/refinements/hero.css`
3. the moderated contract keeps shared readability guardrails without forcing dashboard-like editorial mass onto fast operational consumers
4. the story is now commit-ready as a clean shared-CSS refactor
