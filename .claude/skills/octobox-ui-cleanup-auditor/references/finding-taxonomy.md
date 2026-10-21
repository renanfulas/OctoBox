# Finding Taxonomy

Use this taxonomy to keep audits consistent and deletion-safe.

## `dead`

Meaning:

1. no live consumer found
2. no protected alias role
3. no active bridge responsibility

Typical examples:

1. backup files
2. orphaned selectors from retired families
3. artifacts with no references outside dead code

Default action:

1. remove with low caution
2. still re-check asset loading before final deletion

## `candidate-unused`

Meaning:

1. looks unused
2. evidence is incomplete
3. may still be referenced indirectly or through a narrow page contract

Default action:

1. keep out of deletion commits until usage is disproven
2. search templates, JS, Python payload strings, and page-level asset loading

This is the default bucket for uncertain unused CSS.

## `override-hotspot`

Meaning:

1. specificity is too high
2. `!important` is present
3. inline style or local authority is fighting the canonical layer
4. selector depth suggests a future override war

Default action:

1. trace the ownership chain
2. move the authority to the correct layer
3. reduce specificity instead of adding more force

## `legacy-bridge`

Meaning:

1. the class or rule is historical
2. it still powers a real surface
3. deleting it now would risk visual regression

Default action:

1. keep it alive temporarily
2. document what should replace it
3. migrate the consuming surface first

## `duplicate-rule`

Meaning:

1. the same selector or responsibility appears in multiple places
2. ownership is ambiguous
3. future edits will drift

Default action:

1. pick the canonical owner
2. merge or delete the shadow copy
3. re-check all affected screens

## `structural-do-not-touch`

Meaning:

1. the rule looks suspicious
2. but it still belongs to an active shared host or protected structure
3. removing it without a broader migration would be unsafe

Default action:

1. do not delete in a narrow cleanup
2. escalate to a migration plan if replacement is needed

## `canonical-alias`

Meaning:

1. the name may be historical
2. but the rule is canonized in the current live design system or support layer

Typical examples:

1. `note-panel*`
2. `legacy-copy*` when still documented and active

Default action:

1. preserve in tactical cleanup
2. only rename or migrate with an explicit compatibility plan

## `mirror-tree-only`

Meaning:

1. the finding exists only in a mirror tree, legacy reference tree, or captured artifact area
2. the active runtime does not currently load that path
3. treating it as live would create false-positive cleanup pressure

Default action:

1. do not patch the active runtime because of this finding alone
2. confirm runtime boundaries in settings, asset loading, and template roots
3. only clean the mirror tree when the task explicitly includes drift retirement or archive cleanup

## Reporting Format

For each finding, report:

1. classification
2. file path
3. selector, token, or block
4. evidence
5. risk
6. safest next action
