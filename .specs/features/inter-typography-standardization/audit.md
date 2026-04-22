# Inter Typography Audit and Phases

## Canonical Rule

- `Inter` is the canonical type family for product surfaces
- `--font-body` and `--font-display` are the official entry points
- local `font-family` declarations are exceptions and must be justified

## Exception Matrix

| Surface | File | Current state | Classification | Decision |
| --- | --- | --- | --- | --- |
| Global product shell | `static/css/design-system/tokens.css` | Already uses `Inter` via tokens | Canonical | Keep |
| Global layout | `templates/layouts/base.html` | Loads `Inter` from Google Fonts | Canonical | Keep |
| Login page body and headings | `static/css/design-system/pages/login.css` | Uses `Aptos` and `Rockwell` | Product drift | Migrate to `Inter` |
| Financial ledger numeric amounts | `static/css/catalog/shared/student-financial.css` | Uses `Inter` via token | Canonical | Keep |
| Import progress error log | `static/css/catalog/import-progress.css` | Uses `Inter` via token | Canonical | Keep |
| Sidebar emoji/icon fallback | `static/css/design-system/sidebar/sidebar_nav.css` | Uses emoji/symbol fonts | Healthy rendering exception | Keep |
| Dashboard KPI display values | `static/css/design-system/components/dashboard/metrics.css` | Uses `var(--font-display)` | Canonical | Keep |

## Audit by Phases

### Phase 1 — Canonical Entry and High-Value Drift

Focus:

- confirm canonical ownership of `Inter`
- migrate the most visible product drift first

What enters:

- login page body and heading migration to `Inter`
- explicit documentation of healthy exceptions

What stays out:

- broad visual redesign

### Phase 2 — Product Surface Sweep

Focus:

- audit cards, dashboards, student pages, finance pages, and operational shells for local `font-family`

What enters:

- product-surface overrides that conflict with `Inter`
- residual display/body mismatches

Phase 2 findings:

- no additional product-surface drift was found after the login migration
- `dashboard/metrics.css` uses `var(--font-display)`, which is canonical and already resolves to `Inter`
- remaining local font declarations are canonical token usage or emoji-only exceptions

### Phase 3 — Guardrails and Debt Cleanup

Focus:

- reduce future typography drift

What enters:

- document rule: tokens first, local `font-family` only by exception
- remove dead or redundant local font declarations when payoff is clear

What stays out:

- rebranding
- unrelated spacing or layout cleanup

### Phase 4 — Final Verification

Focus:

- confirm that the product speaks with one typographic voice

Checks:

- core product pages feel typographically continuous
- exceptions are technical, not stylistic drift
- new deviations are easier to detect

## Success Read

This front is successful when the product stops feeling like:

"Inter almost everywhere, plus a few leftover font dialects"

and starts feeling like:

"one product voice, with a few technical tools using their own proper instrument"
