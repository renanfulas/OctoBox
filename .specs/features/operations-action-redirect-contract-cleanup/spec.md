# Spec

## Problem

Live operational action views still contain fallback URLs written by hand.

Even though the rest of the product increasingly uses named routes, these mutations still hardcode manager and coach return paths.

## Users

1. manager
2. coach
3. developers maintaining operations flows

## Requirements

### Functional

1. manager mutation flows must fall back through named manager routes
2. coach mutation flows must fall back through named coach routes
3. referer-first behavior must remain intact
4. fragment append behavior must remain intact where already in use

### Non-functional

1. no change in permission checks
2. no change in side effects of the mutations themselves
3. no new duplicate redirect helper paths

## Success criteria

1. no handwritten fallback route strings remain in live operations mutations
2. `manage.py check` remains clean
3. role return behavior is still obvious when reading the file
