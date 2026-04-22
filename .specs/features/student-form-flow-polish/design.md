# Design

## Core questions

The student form must answer four things quickly:

1. where do I start?
2. what can wait?
3. why am I blocked?
4. when is finance the right next step?

## What we are testing

Can the student form feel:

1. shorter to think through
2. clearer under friction
3. more honest about sequencing

without becoming:

1. tutorial-heavy
2. visually cluttered
3. redundant with the form itself

## Likely flow targets

1. sequence framing near the top
2. recovery guidance when validation fails
3. transition language between registration and finance
4. possible reduction of duplicated “where to go next” signals

## Implemented direction

The chosen polish stayed intentionally light:

1. presenter now computes a real flow state instead of leaving the top map mostly static
2. stepper behavior now respects recovery gravity, especially when the problem is in plan/billing
3. recovery links no longer only point at hidden sections; they actively open the correct stage
4. the second top card now distinguishes commercial closure from true finance access
