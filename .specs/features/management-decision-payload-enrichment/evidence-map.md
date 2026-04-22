# Evidence Map

## Initial reading

The next strategic ceiling is no longer broad front-end hygiene.

It is payload clarity on surfaces where the UI is already cleaner than the management signals behind it.

## Confirmed targets

1. `dashboard/dashboard_snapshot_queries.py`
2. `catalog/finance_snapshot/metrics.py`
3. `catalog/presentation/finance_center_page.py`
4. `operations/queries.py`

## Hypothesis to validate

The product can now gain more by enriching:

1. dominant pressure
2. reason for urgency
3. next recommended move

than by another broad cleanup of markup or CSS.

## T1 findings

### Dashboard

The dashboard snapshot already carries strong numbers, but some strategic signals are still flatter than they should be:

1. `_build_dashboard_metric_cards()` still uses static sparkline samples for revenue instead of pressure-aware movement data
2. payment alerts still ship `href='/financeiro/'` in `_build_dashboard_payment_alert_snapshot()`
3. `_build_dashboard_glance_summary()` is the closest thing to a decision payload, but the metric card layer above it still does not clearly expose dominant pressure versus contextual health

### Finance

The finance snapshot already exposes useful movement, but `catalog/finance_snapshot/metrics.py` still stays too close to descriptive metrics:

1. `build_finance_metrics()` explains values, but not which one dominates now
2. `build_finance_pulse()` is compact but neutral; it does not encode urgency or recommended sequencing
3. `build_finance_interactive_kpis()` describes tabs well, but the tab cards still depend on presenters to infer when queue pressure should dominate

### Operations

`operations/queries.py` is stronger than before, especially for owner and reception, but gaps remain:

1. owner already has ordering logic, yet metric cards remain mostly descriptive instead of reason-attached
2. manager focus is ordered, but still lacks a stronger explicit explanation of dominant pressure versus structural cleanup
3. reception is the healthiest of the group because it already carries clearer sequencing and concrete reasons in queue items

## Initial classification

1. highest ROI for enrichment: dashboard
2. second highest ROI: finance snapshot + presenter bridge
3. third wave: manager/owner operational payload nuance

## T2 outcome

The dashboard snapshot now does three things it did not do before:

1. chooses a dominant pressure context before ordering metric cards
2. routes dashboard payment and operational links through canonical named routes
3. exposes `metric_priority_context` so the facade can explain why the lead cards changed

### Concrete improvements

1. overdue, intake, session, or revenue pressure can now reorder the lead metric cards
2. dashboard payment alerts no longer point to hardcoded finance paths
3. dashboard operational focus no longer relies on hardcoded `finance`, `students`, or `class-grid` URLs
4. the enriched card set attaches the next obvious destination directly to each metric card

### Residual note

The old metric-card builder remains in the file but is now explicitly marked as legacy, making the active path unambiguous while preserving a low-risk rollback surface during this wave.

## T3 outcome

The finance payload now carries a real decision context instead of only descriptive metrics.

### Concrete improvements

1. `build_finance_pulse()` now exposes `received_count`, closing a live gap already expected by the finance hero
2. `build_finance_priority_context()` defines:
   - dominant pressure
   - pill class and label
   - headline
   - summary
   - default tab action and panel
3. `build_finance_interactive_kpis()` now reorders KPI cards based on that context
4. the finance presenter now uses the snapshot priority context instead of inferring all sequencing locally
5. the finance facade now repeats the same priority story across intro, command snapshot, and radar card

### Resulting classification

1. finance no longer behaves like a neutral control board
2. finance now behaves like a guided management surface with an explicit opening read

## T4 outcome

Operations now exposes explicit priority context for the management surfaces that still depended too much on template-local interpretation.

### Concrete improvements

1. owner now receives `owner_priority_context` from the payload
2. manager now receives `manager_priority_context` from the payload
3. owner and manager templates consume those payload fields directly instead of hardcoding the opening rationale in markup

### Resulting classification

1. owner no longer keeps the first-read narrative trapped inside the template
2. manager now exposes dominant reading rationale from the backend, not just a static focus-sequence headline

## T5 validation

Validation confirms the enrichment pass improved decision quality without turning the product verbose.

### Resolved

1. dashboard now carries explicit metric priority context and canonical operational routing
2. finance now carries dominant reading context, default opening behavior, and a complete pulse contract
3. owner and manager now consume backend-driven priority rationale instead of hardcoded template-only logic

### Residual tolerable

1. the dashboard keeps a clearly marked legacy metric-card builder as a low-risk rollback surface
2. deeper payload enrichment for manager and owner metric cards can still happen later, but the main opening rationale is no longer ambiguous

### Strategic outcome

This feature did not redesign the UI.

It raised the intelligence of the payload beneath the UI.
