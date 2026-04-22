# Spec

**Status**: Draft

## Problem

The reception payment action card currently mixes operational behavior, visual styling, and communication logic inside a single template.

This makes the surface:

1. harder to maintain
2. harder to reason about
3. more fragile under future changes

## Users

1. reception staff handling payment follow-up
2. managers reviewing the operational flow
3. developers maintaining reception and finance interaction surfaces

## Requirements

### RASH-01
The reception payment card must reduce dominant inline style usage.

### RASH-02
The reception payment card must remove inline `onclick` behavior from its WhatsApp action path.

### RASH-03
The current operational flow must remain intact:
1. confirm payment
2. open student financial overview
3. respect role-based block states
4. keep WhatsApp follow-up available where allowed

### RASH-04
The surface must remain fast and readable for desk operation.

### RASH-05
The result must be easier to extend than the current mixed template.

## Success Criteria

1. the template becomes structurally cleaner
2. dominant inline behavior moves to an appropriate asset layer
3. visual and operational clarity improve without breaking the flow
