# Context

## Why this exists

The shared shell is already much cleaner, but one visible residual remains in the topbar profile surface:

- `style="pointer-events: none;"`

That is a tiny inline interaction rule sitting in shared infrastructure.

In simple terms:

- the front desk is already polished
- but one little note is still taped on the glass saying "don't touch here"

## Runtime facts confirmed before opening this package

1. the live residual sits in `templates/includes/ui/layout/topbar/topbar_profile.html`
2. topbar styling already has canonical owners in `topbar.css` and `components/topbar_profile_menu.css`
3. the goal is not to redesign the menu, only to move this interaction hint into the proper owner

## Boundaries

This package does:

1. remove inline interaction styling from the shared topbar profile surface
2. give that rule semantic CSS ownership
3. preserve current dropdown behavior and visual reading

This package does not:

1. redesign the topbar
2. rewrite menu behavior
3. reopen shell celebration or neon work

## Non-goals

1. no visual redesign of the avatar/profile cluster
2. no changes to menu item routing or logout behavior
