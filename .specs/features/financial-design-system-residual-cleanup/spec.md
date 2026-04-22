# Spec

**Status**: Draft

## Problem

The financial design-system layer still contains live visual residue from the old `elite-*` dialect, even after the canonical theme and premium legacy islands cleanup.

This creates three problems:

1. a real runtime component still uses legacy class naming
2. the financial design-system file still references `--elite-*` tokens
3. future finance work inherits a visual map that disagrees with the current canon

## Users

1. managers and owners using the student financial workspace
2. developers maintaining finance-facing UI
3. future UX passes that need a clean canonical base

## Requirements

### FDR-01
The live financial overview topbar must stop using `elite-*` naming as its primary runtime vocabulary.

### FDR-02
The touched financial design-system CSS must stop depending on `--elite-*` tokens.

### FDR-03
The migrated financial topbar must preserve search, action, and notification readability.

### FDR-04
No already-cleaned canonical finance or student financial surface should regress into a parallel theme.

### FDR-05
The result must remain visually aligned with the canonical dark premium open theme.

### FDR-06
The cleanup must remain targeted to the live residual scope and avoid turning into a broad financial redesign.

## Success Criteria

1. `financial_overview_topbar.html` reads as part of the canonical financial workspace
2. `financial.css` no longer exposes live `--elite-*` styling in the touched path
3. `python manage.py check` passes
4. the resulting naming is easier to extend than the previous residual layer
