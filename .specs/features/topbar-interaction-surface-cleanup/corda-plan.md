# CORDA Plan

## North

Remove the last inline interaction hint from the shared topbar profile surface and hand it back to CSS ownership.

## Why now

This is a small but worthwhile pass because:

1. the topbar is global infrastructure
2. the residual is real, not hypothetical
3. the scope is tiny and low-risk

## Risks

The main risk is subtle interaction drift:

1. the profile trigger could accidentally start capturing events in the wrong child node
2. the dropdown could feel slightly different if the rule lands on the wrong selector

## Execution sequence

1. map the exact inline interaction rule
2. assign it to the proper CSS owner
3. validate that the profile trigger and dropdown still behave the same

## Success bar

This pass is done when:

1. no inline interaction style remains in the topbar profile template
2. the CSS owner expresses the same behavior semantically
3. topbar menu behavior remains unchanged for users
