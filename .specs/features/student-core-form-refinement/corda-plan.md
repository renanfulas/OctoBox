# C.O.R.D.A. | Student Core Form Refinement

## Context

The student workflow already has:

- a refined facade
- a refined financial interior

But the main form still carries visible shortcuts and older interaction patterns in the core registration flow.

This makes the product feel slightly split-brain:

- the financial room feels curated
- the main form still shows bits of workshop tape

## Objective

Refine the student core form so the essential registration flow feels:

- calm
- guided
- trustworthy
- visually consistent with the rest of the refined product

without reopening architecture or rewriting the form system.

## Risks

1. Over-refactoring a flow that already works
2. Breaking the stepper while trying to beautify it
3. Adding decorative complexity instead of reducing friction
4. Leaving hidden inline debt that keeps leaking legacy smell later

## Direction

Patch-first.

We will:

- remove dominant inline debt
- clarify step transitions and final actions
- improve tone and continuity
- harden interaction trust and accessibility

We will not:

- redesign the whole student form from zero
- change business rules
- split the form into a new architecture

## Actions

### Wave 1

- remove dominant inline debt from the main form shell
- normalize step actions and intake banner

### Wave 2

- improve hierarchy across essential, profile, health, plan, and billing steps
- make the stepper feel more guided and less mechanical

### Wave 3

- align copy and trust language with the refined facade and financial workspace
- reduce remaining visual debt in touched templates

### Wave 4

- harden accessibility and interaction trust
- validate keyboard, focus, and predictable button states
