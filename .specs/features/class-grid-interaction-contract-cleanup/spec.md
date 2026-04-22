# Spec

**Status**: Draft

## Problem

The class grid is live and important, but its interaction contract is still partially expressed through hardcoded links, inline styling, and view-specific local decisions.

This makes it harder to maintain and weakens consistency across:

1. the daily view
2. the weekly view
3. edit/delete actions
4. clickable day navigation cues

## Users

1. owner
2. manager
3. coach
4. future maintainers of the class-grid flow

## Requirements

### CGICC-01
Live class-grid edit links must stop relying on handwritten hardcoded routes.

### CGICC-02
Inline presentational debt on active interaction surfaces must move to the correct CSS owner.

### CGICC-03
The weekly day card interaction affordance must be represented through canonical classes and behavior hooks instead of raw inline styling.

### CGICC-04
Daily and weekly class-grid surfaces must preserve their current business behavior while becoming more structurally consistent.

### CGICC-05
The resulting contract must remain clear for users who can edit or delete sessions.

## Success Criteria

1. no hardcoded class-grid edit routes remain in the active daily/weekly targets
2. no inline style remains in the active interaction targets touched by this mountain
3. the daily and weekly surfaces share a cleaner interaction grammar
4. `python manage.py check` passes after the change
