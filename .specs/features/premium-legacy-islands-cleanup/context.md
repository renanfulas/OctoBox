# Context

## Locked Decisions

1. The canonical theme contract published in `docs/experience/css-guide.md` is now the authority.
2. This phase is not a new redesign of the product shell.
3. This phase exists to retire the biggest remaining premium legacy islands still visible after the theme unification.
4. We will use patch-first migration, not broad rewrites.
5. The goal is continuity with the canonical theme, not flattening the product into something bland.

## Primary Targets

1. `templates/dashboard/blocks/advisor_narrative.html`
2. `templates/dashboard/blocks/advisor_manifesto_modal.html`
3. `templates/includes/catalog/finance/views/hero.html`
4. `templates/includes/catalog/finance/views/movements.html`
5. `templates/includes/catalog/student_form/financial/financial_overview.html`
6. `templates/includes/catalog/student_form/financial/financial_overview_id_card.html`
7. `templates/includes/catalog/student_form/financial/financial_overview_kpis.html`
8. `templates/includes/catalog/student_form/financial/financial_overview_status.html`
9. `templates/includes/catalog/student_form/financial/stripe_elite_ledger.html`

## Boundaries

1. Do not reopen the global token debate solved by `canonical-theme-unification`.
2. Do not redesign the whole student financial workflow logic.
3. Do not add new premium surface dialects.
4. Do not preserve inline style or inline script just because it currently looks good in one template.

## Working Principle

The house already has one painter now.

This phase is about walking into the remaining rooms that still have:

1. old wallpaper
2. legacy light fixtures
3. premium paint from a previous contractor

and repainting them so the whole house feels like one product.
