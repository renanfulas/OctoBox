# Evidence Map

## T1 Result

This map records the repo-wide search result for the detached `elite-*` financial families.

## Families Searched

1. `elite-id-card-hero*`
2. `elite-avatar-large`
3. `elite-mini-stat-box*`
4. `elite-kpi-*`

## Repo-Wide Result

During the T1 search, these families were found only in:

1. `static/css/design-system/financial.css`

No active runtime template, Python file, or JS file referenced these families during this pass.

## Preliminary Classification Signal

### Likely Dead

1. `elite-id-card-hero*`
2. `elite-avatar-large`
3. `elite-mini-stat-box*`
4. `elite-kpi-*`

Reason:

1. the search found CSS definitions only
2. no runtime template usage was found
3. no JS or presenter coupling was found

## Risk Note

This is strong evidence, but T2 must still classify these families formally before removal.

In simple terms:

- the furniture appears to be sitting only in the storage room
- but we still make one formal checklist pass before throwing it out

## T2 Formal Classification

### `elite-id-card-hero*`

- Status: `dead`
- Evidence:
1. found only in [financial.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/design-system/financial.css)
2. no active template reference found
3. no Python or JS coupling found

### `elite-avatar-large`

- Status: `dead`
- Evidence:
1. found only in [financial.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/design-system/financial.css)
2. no active template reference found
3. no presenter or interaction coupling found

### `elite-mini-stat-box*`

- Status: `dead`
- Evidence:
1. found only in [financial.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/design-system/financial.css)
2. no active template reference found
3. no JS or runtime data dependency found

### `elite-kpi-*`

- Status: `dead`
- Evidence:
1. found only in [financial.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/design-system/financial.css)
2. no active template reference found
3. responsive rules also point only to the same detached block

## Classification Summary

### `live`

1. none found in the detached residual family

### `dead`

1. `elite-id-card-hero*`
2. `elite-avatar-large`
3. `elite-mini-stat-box*`
4. `elite-kpi-*`

### `uncertain`

1. none at this stage

## T4 Validation Result

After removal:

1. the detached residual families no longer appear in repo-wide search results
2. `python manage.py check` passes
3. the remaining `financial.css` file now contains only the canonical contextual topbar support

## T5 Outcome Summary

### Removed

1. `elite-id-card-hero*`
2. `elite-avatar-large`
3. `elite-mini-stat-box*`
4. `elite-kpi-*`

### Retained

1. `student-financial-topbar*`

### Next Residual Risk

1. no active financial design-system residual family remains in this specific file
2. the next front-end cleanup should come from a different live contrast, not from `financial.css`
