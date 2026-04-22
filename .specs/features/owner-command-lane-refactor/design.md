# Design

## Core thesis

This is a local-ownership refactor, not a global card redesign.

The shared `fdw` card remains the primitive.
The Owner command lane becomes a local variant with its own include and CSS module.

## Ownership split

### Shared layer

Keeps:

1. base card primitive
2. base focus list behavior
3. generic focus metadata structure

### Owner layer

Owns:

1. lane markup
2. stable structural hooks
3. card hierarchy and local composition
4. responsive behavior specific to the owner command lane

## Allowed moves

1. owner-local include extraction
2. owner-local semantic classes
3. owner-local CSS module
4. payload identity tweaks that do not inflate semantics

## Forbidden moves

1. reworking the payload into a new schema
2. editing all personas in one pass
3. using `!important`
4. hiding new structure inside `refinements/owner-simple.css`
