# Evidence Map

## Runtime evidence

### Live workspace shell

- `templates/includes/catalog/class_grid/views/workspace.html`

### Confirmed inline structural rule

1. `grid-template-columns: 2fr 1fr`
2. `align-items: start`
3. `gap: 16px`

### Confirmed CSS owner

- `static/css/catalog/class-grid/workspace.css`

### Live section mapping

1. the inline rule sits on the wrapper that contains `workspace_weekly.html` first and `workspace_monthly_preview.html` second
2. the live reading order is weekly -> monthly
3. the intended desktop rhythm is a 2:1 split with local `16px` gap
4. the surrounding shell already uses `section-gap`, so only the side-by-side structural split needs extraction

### Extraction result

1. `workspace.html` now exposes a semantic hook: `class-grid-workspace-split`
2. `workspace.css` now owns the 2fr / 1fr split, start alignment, and `16px` local gap

## Decision

This package exists because the remaining gap is:

- live
- structural
- local
- cheap to fix
- worth fixing before calling the class grid shell fully polished

## Validation

1. no inline `style=` remains in `templates/includes/catalog/class_grid/views/`
2. the live reading order remains weekly first and monthly second
3. the split remains a `2fr / 1fr` desktop rhythm owned by `workspace.css`
4. `python manage.py check` passed clean after extraction

## Residual classification

1. no further layout-inline debt was found in this workspace shell after the split extraction
2. any remaining class grid refinements are now optional polish, not structural debt
