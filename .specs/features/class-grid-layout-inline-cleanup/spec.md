# Spec

## Problem

The live class grid workspace still carries structural layout in inline markup.

That makes the template own proportions and spacing that should belong to the class grid workspace CSS layer.

## Users

1. operators using class grid daily
2. developers maintaining the class grid workspace

## Requirements

### Functional

1. the weekly plus monthly section must keep a 2:1 desktop split
2. vertical alignment must remain `start`
3. current reading order must remain weekly first, monthly second

### Non-functional

1. no inline structural layout remains in the target section
2. the CSS owner becomes explicit and local
3. no broader class grid runtime behavior changes

## Success criteria

1. `workspace.html` no longer contains the inline grid rule
2. `workspace.css` clearly owns the split layout
3. `manage.py check` remains clean
