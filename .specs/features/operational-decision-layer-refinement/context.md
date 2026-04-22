# Context

## Why this feature exists

The heavy cleanup cycle is done.

The next gain is no longer "remove debt that screams".
The next gain is "help the operator decide faster".

In practical terms:

1. the runtime is cleaner
2. the visual language is more unified
3. the main surfaces already feel like the same product
4. the remaining gap is decision choreography, not structural rescue

## What problem we are solving

Several live workspaces already contain the right information, but the reading order is still partially implicit.

That creates friction such as:

1. operators needing to infer what to look at first
2. important action surfaces competing with context surfaces
3. depth arriving too early in the page
4. hero, focus lane, queue, and support cards not always speaking with one operational cadence

## In scope

1. explicit reading order on key workspaces
2. hierarchy between command, queue, context, and depth
3. copy and structure refinements that clarify next action
4. local CSS support required to sustain the new decision grammar

## Out of scope

1. redesigning the entire visual language
2. changing business rules
3. reopening already closed hardening work unless a real contradiction is found
4. broad data model or presenter rewrites

## Working assumption

We should prefer low-risk structural clarity:

1. small markup moves
2. explicit sequencing blocks
3. semantic support in CSS
4. only minimal JS changes if absolutely required
