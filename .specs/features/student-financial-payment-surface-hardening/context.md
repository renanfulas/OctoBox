# Context

## Why This Exists

The student financial workspace has already been pulled back under the canonical theme, but the payment surface still carries live residual naming from the former premium dialect.

The problem is no longer:

1. broken visual hierarchy
2. parallel surface ownership

The problem now is:

1. action buttons still using `elite-*` naming in a live payment flow
2. JS still querying those legacy classes directly
3. payment actions sitting in a sensitive money path where ambiguity costs more than usual

## Locked Direction

This pass should:

1. preserve the current operator flow
2. preserve the low-friction payment actions already working in the student workspace
3. remove live `elite-*` naming from payment buttons and button groups touched by this scope
4. move the JS contract to semantic `data-*` and canonical class names

This pass should not:

1. redesign the whole financial workspace
2. reopen unrelated financial history or overview cards
3. add more clicks to the payment flow

## Simple Analogy

The payment room is already inside the right house.

Now we are replacing:

1. the old labels on the buttons
2. the old wiring names behind those buttons

without moving the cashier desk itself.
