# C.O.R.D.A.

**Status**: Approved

## Contexto

The OctoBox already hardened the canonical theme, reception workspace, and the live intake conversion path. The class grid is now one of the strongest remaining operational surfaces with visible interaction debt across multiple views.

It sits at the intersection of:

1. agenda visibility
2. coach and manager actionability
3. occupancy reading
4. editing and deletion flows

## Objetivo

Harden the live class grid interaction contract so it becomes:

1. easier to maintain
2. safer to evolve
3. more consistent across daily and weekly views
4. aligned with canonical routing and front-end ownership rules

## Riscos

1. breaking class editing shortcuts while replacing hardcoded links
2. reducing clarity in weekly/day interaction while trying to remove inline behavior
3. cleaning one view and leaving the other with a competing contract
4. over-expanding this mountain into a full class-grid redesign

## Direcao

Treat this as a contract cleanup, not a redesign.

The correct order is:

1. prove the live daily and weekly runtime paths
2. map the edit and delete interaction contract
3. replace hardcoded routes with canonical generation
4. remove inline behavior/presentation debt from the active surfaces
5. validate that daily and weekly views still feel coherent and fast

## Acoes

### Wave 1: Evidence

1. map daily row interactions
2. map weekly day-card interactions
3. map weekly session chip edit/delete paths

### Wave 2: Routing Cleanup

1. replace hardcoded edit links
2. normalize query-string and fragment composition

### Wave 3: Markup Hardening

1. remove inline interactive styling from live surfaces
2. move interaction affordance styling to the correct CSS owner

### Wave 4: Validation

1. verify daily view behavior
2. verify weekly view behavior
3. run `python manage.py check`
