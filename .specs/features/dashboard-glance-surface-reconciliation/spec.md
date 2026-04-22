# Spec

## Problem

The dashboard glance strip may be technically separated already, but it still needs confirmation that:

1. severity classes are mapped correctly
2. actionability is emphasized correctly
3. neon treatment is not overshooting the real operational hierarchy

## Users

1. owner
2. manager
3. dashboard maintainers

## Requirements

### Functional

1. emergency, urgent, and risk glance states must remain distinguishable
2. actionable cards must still feel actionable
3. non-actionable cards must not compete with live pressure

### Non-functional

1. the surface must stay readable
2. the urgency strip must stay coherent with the product's decision-first language
3. any changes should be local and intentional

## Success criteria

1. the glance strip severity contract is explicitly understood and documented
2. any needed reconciliation lands in local glance files only
3. `manage.py check` remains clean
