# Spec

## Problem

The live student financial payment surface still depends on legacy `elite-*` naming in its action buttons and JS selectors.

This creates avoidable maintenance risk in a money-sensitive flow.

## Users

1. reception and management operators handling payment actions
2. developers maintaining the student financial workspace

## Requirements

### SFPH-01

Live payment actions must stop using `elite-*` naming in the touched payment surface.

### SFPH-02

The payment method CTA group must remain visually clear and fast to parse.

### SFPH-03

The workspace JS must rely on canonical selectors compatible with the new markup.

### SFPH-04

No new click or step may be introduced into the working payment flow.

### SFPH-05

The resulting surface must remain coherent with the canonical student financial theme.

## Success Bar

We are successful when:

1. the touched templates no longer expose live `elite-*` button naming
2. the JS no longer queries `.elite-stripe-btn`
3. `python manage.py check` passes
4. the surface still reads as an important payment action area, not a flattened generic form
