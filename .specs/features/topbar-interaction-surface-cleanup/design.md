# Design

## Canonical ownership rule

The template should declare:

1. structure
2. content
3. semantic hooks

The stylesheet should declare:

1. interaction affordance
2. non-interactive subregions
3. pointer behavior details

## Likely local hook

The profile meta block should receive an explicit semantic class or continue using its current class, with the non-interactive rule moved into the topbar CSS owner.

## Residual tolerance

If the current class name is already sufficient, no new markup complexity is needed.
The debt is the inline interaction rule, not the class naming itself.
