# Design

**Status**: Approved

## Scope Shape

This is a `Medium` feature under SDD because it targets a live payment action surface with shared visual and JS ownership.

## Target Files

Primary:

1. `templates/includes/catalog/student_form/financial/billing_console.html`
2. `templates/includes/catalog/student_form/financial/financial_overview_payment_management.html`
3. `static/js/pages/finance/student-financial-workspace.js`

Secondary:

1. `static/css/catalog/shared/student-financial.css`

## Strategy

### 1. Runtime-First Payment Safety

Map the live payment surface before editing:

1. billing timeline actions
2. drawer footer actions
3. payment method buttons
4. JS ownership of method submission and action dispatch

### 2. Canonical Payment Action Naming

The payment surface should use:

1. `student-financial-action-button` for local timeline and footer actions where a local semantic wrapper is useful
2. `student-financial-action-button--compact` and `student-financial-action-button--full` only as sizing modifiers
3. `student-payment-method-button` as the canonical semantic class for method CTAs
4. `is-active` and `is-disabled` state classes where visual state must be expressed
5. optional semantic modifiers on method buttons only for accent finish:
   - `is-card`
   - `is-pix`
   - `is-cash`
   - `is-debit`

It should stop using:

1. `elite-button-sm`
2. `elite-button-full`
3. `elite-stripe-btn`
4. `elite-stripe-btn-*`

### 3. JS Contract Rule

JS should rely on:

1. `data-action`
2. `data-method`
3. `.student-payment-method-button` only when styling/state reset is required
4. existing `data-payment-id` payloads for edit and split actions

JS should stop relying on:

1. `.elite-stripe-btn`

### 4. UX Preservation

The payment surface must preserve:

1. obvious primary action hierarchy
2. fast method selection
3. clear status feedback
4. immediate operator confidence
5. the same action count and same payment paths as today

In simple words:

1. we are changing the button labels on the machine
2. not changing what the machine does when you press them
