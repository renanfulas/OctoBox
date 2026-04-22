# Design

## Translation rules

Finance may inherit:

1. premium navy shell atmosphere in moderated form
2. layered panel surfaces instead of flat support cards
3. quieter border, shadow, and inset-light discipline
4. topbar and shell continuity where relevant

Finance must adapt:

1. support-card depth
2. command intro richness
3. board section atmosphere

Finance must avoid:

1. dashboard-specific glance theater
2. strong alert pulse behavior
3. all-clear emotional choreography

## Visual goal

Finance should feel like:

1. a premium operations room
2. a clearer decision center
3. a transactional surface with confidence

Not like:

1. a second dashboard
2. a noisy showcase
3. a glowing control panel with weak readability

## Likely target zones

1. `templates/catalog/finance.html`
2. `static/css/catalog/finance/_boards.css`
3. finance support cards and intros
4. command surfaces that already carry priority framing

## T1 mapped expansion zones

The finance surface naturally separates into three zones.

### Zone A. Command layer

Anchors:

1. `templates/catalog/finance.html`
2. `templates/includes/catalog/finance/views/command_snapshot.html`

Role:

1. hero continuation
2. priority intro
3. first command framing before denser boards

Interpretation:

This zone can absorb exported premium shell grammar with relatively low risk because it already behaves like a decision front.

### Zone B. Guided board surfaces

Anchors:

1. `templates/includes/catalog/finance/views/priority_rail.html`
2. `templates/includes/catalog/finance/boards/queue_board.html`
3. `templates/includes/catalog/finance/boards/control_board.html`
4. `static/css/catalog/finance/_boards.css`

Role:

1. queue pressure
2. action rails
3. filter and context support
4. board-level support cards

Interpretation:

This zone should receive adapted premium depth, not dashboard-level spectacle.

### Zone C. Deep support and lower-intensity boards

Anchors:

1. `templates/includes/catalog/finance/boards/portfolio_board.html`
2. `templates/includes/catalog/finance/boards/mix_board.html`
3. `templates/includes/catalog/finance/boards/trend_boards.html`

Role:

1. secondary depth
2. portfolio context
3. longer-reading support material

Interpretation:

This zone should stay quieter than the command layer and inherit only subdued premium atmosphere.

## T2 finance-specific translation rules

The finance expansion should use three intensity levels.

### Level 1. Full exported grammar

Apply to:

1. finance shell framing
2. command intro
3. command snapshot surfaces

Allowed treatments:

1. premium navy atmosphere in moderated form
2. layered premium surfaces
3. shell-to-topbar continuity where relevant
4. richer border and inset-light discipline

Reason:

These areas carry reading authority and can support stronger product presence.

### Level 2. Adapted premium depth

Apply to:

1. priority rail
2. queue board
3. control board
4. guide notes and support cards in `_boards.css`

Allowed treatments:

1. calmer layered backgrounds
2. quieter premium shadows
3. stronger but disciplined borders
4. more coherent support-card rhythm

Forbidden at this level:

1. pulse behavior
2. dashboard-style glow amplitude
3. urgency theater beyond actual queue semantics

### Level 3. Quiet premium support

Apply to:

1. portfolio board
2. mix board
3. trend boards

Allowed treatments:

1. subtle surface depth
2. cleaner premium spacing and contrast
3. light shell-family cohesion

Reason:

These zones are for longer reading and should not compete with urgent queue surfaces.

## Finance-specific avoid list

Do not import into finance:

1. dashboard all-clear emotional treatment
2. dashboard glance pulse choreography
3. high-theater alert lighting
4. showcase-like glow that makes all cards feel equally urgent

## Finance success test

If the finance screen feels more premium but slower to parse, the pass failed.

If it feels calmer, richer, and clearer in the first 3 seconds, the pass succeeded.

## T3 implementation snapshot

Implemented in:

1. `static/css/catalog/finance/_shell.css`
2. `static/css/catalog/finance/_hero.css`
3. `static/css/catalog/finance/_boards.css`

What changed:

1. finance shell gained moderated premium atmosphere and layered board surfaces
2. finance hero and command surfaces gained richer but quieter depth
3. guide cards, support cards, intros, and filter context gained calmer premium polish

What did not change:

1. finance templates
2. payload semantics
3. queue order or command order

Reason:

The first finance pass should prove visual translation without changing transactional logic.

## T4 validation result

The finance pass passed the transactional-clarity test.

### What stayed intact

1. command order in `templates/catalog/finance.html`
2. queue-first reading when the recorte asks for it
3. separation between command, guided boards, and deeper support zones
4. payload semantics and decision logic

### What improved

1. shell coherence
2. support-surface depth
3. premium continuity between hero, intro, queue, and support boards

### Why it still fits Front Display Wall

1. the screen feels more like a product and less like a stack of panels
2. pressure is still visible
3. next action is still legible
4. atmosphere supports reading instead of replacing it

### Delivery caution

This finance pass is ready conceptually, but the worktree still contains an unrelated parallel modification in:

1. `static/css/design-system/dashboard.css`

That file should be isolated before any finance-only commit is created.
