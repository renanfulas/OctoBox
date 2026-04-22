# Spec

**Status**: Draft

## Problem

The shared metric card component still depends on a legacy premium structural host, which creates a visual contract conflict at the component level.

Because it is shared, the problem is not local. It can affect multiple surfaces at once.

## Users

1. end users reading metrics across dashboard, finance, and catalog surfaces
2. developers maintaining shared UI components
3. future theme passes that rely on stable component ownership

## Requirements

### SMC-01
The shared metric card must stop using `glass-panel-elite` as structural host.

### SMC-02
The component must preserve metric hierarchy, value prominence, signal, and sparkline readability.

### SMC-03
The component must preserve current interaction contracts such as link wrappers, actions, footer buttons, and data attributes.

### SMC-04
The CSS ownership for the component must stay aligned with the canonical theme contract.

### SMC-05
The change must be validated against real usage contexts, not just in isolation.

## Success Criteria

1. the shared metric card reads as canonical
2. the legacy host is removed from the shared component markup
3. interaction hooks remain intact
4. visual regressions are limited or absent in major usage contexts
