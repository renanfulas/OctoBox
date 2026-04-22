# Design

**Status**: Approved

## Scope Shape

This is a `Medium` cleanup feature under SDD.

It needs more than a quick fix because deletion without proof is risky, but it does not justify broad architecture work.

## Target Files

Primary:

1. `static/css/design-system/financial.css`

Secondary evidence sources:

1. runtime templates under `templates/includes/catalog/student_form/financial/`
2. any page presenter or asset entrypoint that loads `financial.css`

## Retirement Strategy

### 1. Verify

Search for runtime references to:

1. `elite-id-card-hero*`
2. `elite-mini-stat-box*`
3. `elite-kpi-*`

### 2. Classify

Each group should be marked as one of:

1. live
2. dead
3. uncertain

### 3. Remove or defer

- dead: remove now
- uncertain: keep, document, and defer
- live: do not remove; open a migration path instead

## Verification Model

Each pass should verify:

1. repo-wide search for the target class family
2. `python manage.py check`
3. a final classification note with evidence
