# Shell Celebration and Neon Contract Cleanup

**Status**: Completed  
**Completed on**: 2026-03-30

## Objective

Harden the authenticated shell so celebration and neon feedback keep their visual energy without relying on inline style ownership in JS.

## Scope

- `static/js/core/shell.js`
- `static/css/design-system/topbar.css`
- `static/css/design-system/components/dashboard/sessions_board.css`

## Outcome

1. confetti pieces no longer receive inline style ownership from JS
2. celebration toast exit state now uses semantic CSS classing
3. sessions neon overlay now animates from CSS instead of inline geometry/animation style
4. topbar scroll affordance no longer depends on direct style mutation
