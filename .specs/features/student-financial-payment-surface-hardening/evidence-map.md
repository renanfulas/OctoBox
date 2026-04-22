# Evidence Map

**Status**: T5 completed

## T1 Result

This map records the live runtime path and ownership for the student financial payment surface.

## Live Runtime Surface

The live payment surface is rendered through:

1. [billing_console.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/includes/catalog/student_form/financial/billing_console.html)
2. [financial_overview_payment_management.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/includes/catalog/student_form/financial/financial_overview_payment_management.html)

The interaction owner is:

1. [student-financial-workspace.js](C:/Users/renan/OneDrive/Documents/OctoBOX/static/js/pages/finance/student-financial-workspace.js)

The visual owner is:

1. [student-financial.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/catalog/shared/student-financial.css)

## Live Legacy Naming Confirmed

Live templates still use:

1. `elite-button-sm`
2. `elite-button-full`
3. `elite-stripe-btn`
4. `elite-stripe-btn-card`
5. `elite-stripe-btn-pix`
6. `elite-stripe-btn-cash`
7. `elite-stripe-btn-debit`

The live JS still queries:

1. `.elite-stripe-btn`

## Runtime Risk Classification

This is live debt, not dead code, because:

1. billing console actions dispatch `edit-payment`, `split-payment`, `vacation-freeze`, and `close-drawers`
2. payment management buttons dispatch `submit-stripe` with live `data-method` values
3. JS resets button state by selecting the legacy payment button class directly

## T1 Conclusion

The payment flow itself is already cleanly delegated through `data-action`, but the naming contract of the buttons remains legacy.

In simple terms:

1. the cashier knows which drawer to open
2. but the buttons on the panel still use the old sticker pack

## T2 Canonical Contract

The canonical payment button contract is now locked as:

1. timeline and drawer footer actions use `student-financial-action-button`
2. size modifiers are expressed as:
   - `student-financial-action-button--compact`
   - `student-financial-action-button--full`
3. method CTAs use `student-payment-method-button`
4. method accent variants are expressed through semantic modifiers:
   - `is-card`
   - `is-pix`
   - `is-cash`
   - `is-debit`
5. JS state uses:
   - `is-active`
   - `is-disabled`

## T2 Decision Note

This means:

1. the button's role comes from the canonical room it lives in
2. the payment method is declared semantically
3. the JS no longer needs to know the old family surname `elite-*`

## T3 Runtime Markup Migration

The live payment markup has now been migrated in:

1. [billing_console.html](C:/Users\\renan\\OneDrive\\Documents\\OctoBOX\\templates\\includes\\catalog\\student_form\\financial\\billing_console.html)
2. [financial_overview_payment_management.html](C:/Users\\renan\\OneDrive\\Documents\\OctoBOX\\templates\\includes\\catalog\\student_form\\financial\\financial_overview_payment_management.html)

The runtime now uses:

1. `student-financial-action-button`
2. `student-financial-action-button--compact`
3. `student-financial-action-button--full`
4. `student-payment-method-button`
5. semantic method modifiers:
   - `is-card`
   - `is-pix`
   - `is-cash`
   - `is-debit`

The runtime no longer uses live `elite-*` button naming in these touched templates.

## T4 JS and CSS Contract Migration

The supporting contract has now been migrated in:

1. [student-financial-workspace.js](C:/Users\\renan\\OneDrive\\Documents\\OctoBOX\\static\\js\\pages\\finance\\student-financial-workspace.js)
2. [student-financial.css](C:/Users\\renan\\OneDrive\\Documents\\OctoBOX\\static\\css\\catalog\\shared\\student-financial.css)

Validated outcome:

1. JS no longer queries `.elite-stripe-btn`
2. payment method state now uses `.student-payment-method-button`
3. local visual hierarchy for compact, full-width, and method CTAs now lives in the student financial CSS owner

## T5 Final Validation

Final validation confirms:

1. the touched payment surface remains fast and action-oriented
2. the touched templates are clean from live `elite-button-*` and `elite-stripe-btn*` naming
3. the JS contract is coherent with the new markup
4. `python manage.py check` passes clean

## Final Classification

Resolved:

1. live `elite-button-sm` naming in the billing console
2. live `elite-button-full` naming in the billing console footer
3. live `elite-stripe-btn*` naming in the payment method selector
4. `.elite-stripe-btn` JS selector dependency

Residual tolerable:

1. untouched student financial surfaces outside this payment scope may still carry old naming and should be assessed independently

Feature status:

1. the live student financial payment surface hardening pass is complete
