# C.O.R.D.A. Plan

## Context

The Owner command lane is structurally coupled across shared and local front-end layers.

## Objective

Refactor the three owner focus cards into a locally owned surface that still reuses the shared primitive safely.

## Risks

1. breaking the other personas by changing the shared primitive too early
2. creating a full parallel card system instead of a local variant
3. pushing new structure into late refinements and increasing technical debt
4. improving desktop while regressing tablet or mobile

## Direction

Stabilize the Owner lane locally first.

The shared system should remain the mold.
The Owner lane should gain its own bodywork.

## Actions

### Wave 1

1. register the plan in `.specs`
2. give the Owner lane explicit local ownership
3. extract an owner-local include
4. move lane styling into a dedicated owner CSS module

### Wave 2

1. reduce duplicated structure in owner refinements
2. validate hierarchy and responsiveness

### Wave 3

1. only then evaluate whether global `cards.css` can be safely reduced
