# Evidence Map

## Runtime evidence

### Live glance files

1. `static/css/design-system/components/dashboard/glance/glance_neon.css`
2. `templates/includes/ui/dashboard/dashboard_glance_card.html`
3. `templates/dashboard/blocks/priority_strip.html`

### Confirmed class contract at package creation time

1. `is-emergency`
2. `is-warning`
3. `is-risk`
4. `is-actionable`
5. `is-tranquil`

### Live contract mapping

1. `priority_strip.html` hard-assigns textual kickers in positional order: first card = `Emergência`, second = `Urgente`, third = `Risco`
2. `dashboard_glance_card.html` derives severity classes from the kicker text instead of a dedicated payload field
3. `dashboard_glance_card.html` derives actionability from `card.value > 0`
4. dashboard payload work already enriches `metric_priority_context`, but the glance strip itself still depends on positional and textual severity mapping
5. `dashboard/presentation.py` also carries `card_class` and `indicator_class` values like `is-risk`, creating a partially overlapping signal vocabulary

### Neon layer inspection

1. `glance_cards.css` owns the passive base card, tranquil state, and static indicator variants
2. `glance_neon.css` cleanly owns pulse animation and actionable severity accenting
3. the neon layer only activates on `.is-actionable`, which is good and keeps tranquil cards from competing
4. the main ambiguity is not excess animation volume; it is that severity color currently depends on kicker text and positional labeling rather than a dedicated canonical severity field
5. current neon treatment is therefore technically local and readable, but semantically downstream from a fragile class-composition contract

### Reconciliation result

1. `dashboard/presentation.py` now emits explicit `severity` and `is_actionable` fields for each priority card
2. `dashboard_glance_card.html` now composes severity and actionable classes from semantic payload fields instead of kicker text and raw value comparison
3. `priority_strip.html` no longer hard-assigns severity through positional kicker overrides
4. the neon layer can now keep doing its job while depending on a cleaner upstream contract

## Validation

1. `python manage.py check` passed clean after the reconciliation
2. severity still renders as three clear lanes: emergency, warning, and risk
3. actionable emphasis still depends on explicit state, while tranquil cards remain visually calmer
4. the surface is now less dependent on positional coincidence and more dependent on canonical payload meaning

## Residual classification

1. the neon layer itself is acceptable and does not need a heavy rewrite
2. remaining local worktree changes in topbar files belong to a separate package and were intentionally not folded into this validation

## Decision

This package exists because the remaining gap is:

- central
- high-visibility
- semantic more than structural
- worth reconciling before calling the dashboard strip fully mature
