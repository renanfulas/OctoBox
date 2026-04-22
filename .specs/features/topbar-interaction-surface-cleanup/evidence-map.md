# Evidence Map

## Runtime evidence

### Live residual

- `templates/includes/ui/layout/topbar/topbar_profile.html`

### Confirmed inline interaction rule

1. `pointer-events: none`

### Confirmed CSS owners

1. `static/css/design-system/topbar.css`
2. `static/css/design-system/components/topbar_profile_menu.css`

### Ownership mapping

1. `topbar.css` owns the shared profile surface structure and typography
2. `topbar_profile_menu.css` owns the profile interaction affordance and dropdown behavior
3. the inline `pointer-events: none` sits on `.profile-meta`, which is part of the clickable profile trigger but should not become the interaction owner itself

### Extraction result

1. `topbar_profile.html` no longer carries the inline interaction hint
2. `topbar_profile_menu.css` now owns the `.profile-meta { pointer-events: none; }` rule

## Decision

This package exists because the remaining gap is:

- global
- visible
- low-risk
- tiny in scope
- worth finishing before calling the shared shell fully polished

## Validation

1. no inline `style=` remains in `templates/includes/ui/layout/topbar/`
2. `.profile-meta` now gets `pointer-events: none` from `topbar_profile_menu.css`
3. `python manage.py check` passed clean after extraction

## Residual classification

1. no further inline interaction debt was found in the shared topbar profile template
2. the parallel change in `static/css/design-system/components/dashboard/glance/glance_neon.css` is external to this package and was intentionally left untouched
