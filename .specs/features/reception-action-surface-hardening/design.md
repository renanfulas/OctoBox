# Design

**Status**: Approved

## Scope Shape

This is a `Large` feature under SDD because it touches a live operational flow with mixed responsibilities.

## Target Files

Primary:

1. `templates/operations/includes/reception/reception_payment_card.html`

Secondary:

1. a reception or operations JS asset for the extracted WhatsApp/fetch behavior
2. a CSS owner for the card cleanup if needed

## Strategy

### 1. Behavior Mapping

Identify all live actions in the card:

1. confirm payment submit
2. update payment submit
3. blocked WhatsApp state
4. unlocked WhatsApp action
5. hover/explanatory microcopy

### 2. Inline Behavior Extraction

Move `onclick` logic into a static JS asset using:

1. `data-*` hooks
2. explicit URLs and payload metadata
3. predictable event delegation

### 3. Inline Style Extraction

Move dominant inline styling into the correct CSS owner while preserving:

1. dense desk layout
2. blocked-state clarity
3. right-aligned action balance

## Verification Model

1. inspect the template for remaining inline debt
2. validate the operational flow after extraction
3. run `python manage.py check`
