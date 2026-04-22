# Evidence Map

## Governing docs

1. `docs/experience/front-display-wall.md`
2. `docs/experience/layout-decision-guide.md`

## Consolidation anchors

1. `.specs/features/dashboard-premium-theme-consolidation/README.md`
2. `.specs/features/dashboard-premium-theme-consolidation/design.md`
3. `.specs/features/dashboard-premium-theme-consolidation/evidence-map.md`

## Runtime anchors

1. `templates/catalog/finance.html`
2. `static/css/catalog/finance/_boards.css`
3. finance support and board surfaces

## Initial hypothesis

Finance is the first safe expansion because:

1. it already behaves like a decision center
2. it can absorb shell grammar without becoming a showcase clone
3. its boards and support cards map well to adapted premium surfaces

## T1 mapped zones

### Command layer

Anchors:

1. `templates/catalog/finance.html`
2. `templates/includes/catalog/finance/views/command_snapshot.html`

Fit:

1. strongest entry point for exported premium shell grammar
2. already carries command framing and reading order

### Guided board surfaces

Anchors:

1. `templates/includes/catalog/finance/views/priority_rail.html`
2. `templates/includes/catalog/finance/boards/queue_board.html`
3. `templates/includes/catalog/finance/boards/control_board.html`
4. `static/css/catalog/finance/_boards.css`

Fit:

1. good target for adapted support-surface depth
2. must remain calmer than dashboard

### Deep support zone

Anchors:

1. `templates/includes/catalog/finance/boards/portfolio_board.html`
2. `templates/includes/catalog/finance/boards/mix_board.html`
3. `templates/includes/catalog/finance/boards/trend_boards.html`

Fit:

1. lower-intensity premium treatment only
2. should not compete with queue and command surfaces

## T2 translation levels

### Level 1. Full exported grammar

Targets:

1. `templates/catalog/finance.html`
2. `templates/includes/catalog/finance/views/command_snapshot.html`

### Level 2. Adapted premium depth

Targets:

1. `templates/includes/catalog/finance/views/priority_rail.html`
2. `templates/includes/catalog/finance/boards/queue_board.html`
3. `templates/includes/catalog/finance/boards/control_board.html`
4. `static/css/catalog/finance/_boards.css`

### Level 3. Quiet premium support

Targets:

1. `templates/includes/catalog/finance/boards/portfolio_board.html`
2. `templates/includes/catalog/finance/boards/mix_board.html`
3. `templates/includes/catalog/finance/boards/trend_boards.html`

## T2 hard constraints

1. no dashboard-style pulse choreography in finance
2. no all-clear theatrical treatment in finance
3. no glow strong enough to flatten queue hierarchy

## T3 implementation evidence

### Shell and command layer

1. `static/css/catalog/finance/_shell.css`
2. `static/css/catalog/finance/_hero.css`

Applied:

1. moderated navy atmosphere
2. premium layered shell surfaces
3. richer command framing with quieter depth

### Guided boards and support surfaces

1. `static/css/catalog/finance/_boards.css`

Applied:

1. adapted premium guide-card depth
2. richer section intro and support-card surfaces
3. quieter dark-mode premium treatment

## T4 validation evidence

### Runtime integrity

1. `python manage.py check` passed
2. `templates/catalog/finance.html` still preserves command -> queue/boards -> deep support order

### Product integrity

1. finance now feels more premium and unified
2. it does not import dashboard pulse theater
3. it preserves transactional clarity in the first reading pass

### Worktree caution

1. finance CSS files are ready for an isolated commit
2. `static/css/design-system/dashboard.css` is currently a parallel unrelated modification and should not be mixed into the finance story
