# Spec

## Problem

The three cards inside `#owner-command-lane` are difficult to maintain because their markup and visual contract are spread across too many layers.

## Users

1. owner users who need a clean command lane
2. engineers maintaining operational surfaces

## Requirements

1. the Owner lane must have an owner-local include
2. the Owner lane must have owner-local CSS ownership
3. the shared primitive classes may remain as the base layer
4. other personas must keep working without visual regression
5. the refactor must improve discoverability through local hooks and semantic classes

## Success bar

1. changing an Owner command card no longer requires editing the shared include first
2. the Owner lane structure is understandable from local files
3. the Owner lane keeps the current semantic payload and action flow
