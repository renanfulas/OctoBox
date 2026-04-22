# Spec

## Problem

The shared topbar profile template still carries one inline interaction rule.

That makes the template own a behavior hint that should belong to the topbar surface CSS.

## Users

1. every logged-in user who sees the shared shell
2. developers maintaining global shell surfaces

## Requirements

### Functional

1. the profile meta block must remain non-interactive if that is still the intended runtime behavior
2. the topbar profile trigger must keep working as it works today
3. the dropdown surface must remain untouched in semantics and routing

### Non-functional

1. no inline interaction style remains in the template
2. CSS ownership becomes explicit and local
3. no broader shell behavior changes

## Success criteria

1. `topbar_profile.html` no longer contains the inline `pointer-events` rule
2. the proper topbar stylesheet owns the rule
3. `manage.py check` remains clean
