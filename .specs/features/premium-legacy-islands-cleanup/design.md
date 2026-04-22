# Design

**Status**: Approved

## Scope Shape

This is a `Large` feature under the SDD workflow because it spans multiple visible surfaces and requires coordinated migration, but it does not justify a shell-wide redesign.

The right approach is:

1. targeted migration
2. local CSS extraction
3. host replacement
4. behavior preservation

## Canonical Absorption Strategy

### 1. Advisor Narrative Island

Target files:

1. `templates/dashboard/blocks/advisor_narrative.html`
2. `templates/dashboard/blocks/advisor_manifesto_modal.html`

Design strategy:

1. map the narrative shell to canonical `hero` semantics or an approved hero-like dashboard variant
2. move inline visual logic into dashboard CSS
3. move modal behavior into existing JS or a dedicated page script if needed
4. keep the narrative voice, but make the shell look native to the canonical theme

### 2. Finance Premium Surface Absorption

Target files:

1. `templates/includes/catalog/finance/views/hero.html`
2. `templates/includes/catalog/finance/views/movements.html`

Design strategy:

1. replace legacy premium hosts with canonical `card` or `hero` hosts
2. keep local semantic classes for finance-specific tone
3. move any premium atmosphere into local modifiers, not base container ownership

### 3. Student Financial Premium Retirement

Target files:

1. `templates/includes/catalog/student_form/financial/financial_overview.html`
2. `templates/includes/catalog/student_form/financial/financial_overview_id_card.html`
3. `templates/includes/catalog/student_form/financial/financial_overview_kpis.html`
4. `templates/includes/catalog/student_form/financial/financial_overview_status.html`
5. `templates/includes/catalog/student_form/financial/stripe_elite_ledger.html`

Design strategy:

1. keep the hierarchy and importance of the financial workspace
2. migrate surfaces to canonical `card`
3. preserve emphasis with local modifiers, accent zones, and spacing
4. avoid replacing clarity with generic flatness

## Technical Constraints

1. No global token churn unless a true bug is discovered.
2. No new premium surface family may be introduced.
3. Prefer CSS extraction and semantic class tightening over template-level styling.
4. Keep JS vanilla-first and move any dominant inline behavior to static assets.

## Verification Model

Each wave should verify:

1. `python manage.py check`
2. direct inspection for `style=` and `<script>` in touched templates
3. direct inspection for `elite-glass-card` and `glass-panel-elite` in touched templates
4. visual continuity judgment against the canonical theme contract

## Migration Principle

Think of this like replacing old royal uniforms after a kingdom reform:

1. the ceremony stays
2. the meaning stays
3. the prestige stays
4. but the uniforms now obey the same crown
