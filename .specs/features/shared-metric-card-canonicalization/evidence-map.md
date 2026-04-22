# Evidence Map

## T1 Result

This map records the real runtime path and visual ownership for the shared metric card.

## Runtime Template Authority

The live Django runtime uses:

1. [metric_card.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/includes/ui/shared/metric_card.html)

Evidence:

1. the active settings module comes from `config.settings`
2. [config/settings/base.py](C:/Users/renan/OneDrive/Documents/OctoBOX/config/settings/base.py) uses `DIRS = [BASE_DIR / 'templates']`
3. therefore the root `templates/` directory wins template resolution in the current runtime

## Shadow Template Warning

A second copy exists at:

1. [metric_card.html](C:/Users/renan/OneDrive/Documents/OctoBOX/OctoBox/templates/includes/ui/shared/metric_card.html)

This should be treated as:

1. a shadow or historical duplicate
2. not the first runtime authority for the current project settings

## Current Markup Risk

The canonical runtime template still uses:

1. `glass-panel-elite`
2. `metric-card-elite`
3. `elite-card-link-wrapper`

This confirms the shared component still carries legacy premium structure in the live path.

## Major Usage Contexts Found

Representative live includes were found in:

1. [finance.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/catalog/finance.html)
2. [student_interactive_kpis.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/catalog/includes/student/student_interactive_kpis.html)
3. [metrics_cluster.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/dashboard/blocks/metrics_cluster.html)
4. [intake_center.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/onboarding/intake_center.html)
5. owner/manager/coach/reception metric sections under:
   - [owner_metrics_section.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/operations/includes/owner/owner_metrics_section.html)
   - [manager_metrics_section.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/operations/includes/manager/manager_metrics_section.html)
   - [coach_metrics_section.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/operations/includes/coach/coach_metrics_section.html)
   - [reception_metrics_section.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/operations/includes/reception/reception_metrics_section.html)

## CSS Ownership Map

The shared metric card contract is currently owned across three layers:

1. [cards.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/design-system/components/cards.css)
   - owns the canonical base `card`, `card-footer`, `card-value`, `card-copy`, compact padding

2. [metrics.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/design-system/components/dashboard/metrics.css)
   - owns metric-specific inner behavior for dashboard KPI contexts
   - includes `card-value-row`, `card-signal`, sparkline, jumbo value tuning

3. [summary.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/design-system/components/dashboard/summary.css)
   - owns signal arrow presentation

## T1 Conclusion

1. the live runtime path is confirmed
2. the component is shared across multiple surfaces
3. the host legacy debt is real in the live template
4. the next step must preserve cross-surface behavior while replacing the structural legacy host

## T2 Canonical Host Strategy

The canonical host strategy is now locked as:

1. `card` remains the only structural surface authority
2. `metric-card` becomes the semantic shared host for the component
3. `metric-card-compact` remains only as a density modifier
4. `card.card_class` remains the approved extension point for contextual accents such as `dashboard-kpi-card`
5. the optional link wrapper should move from `elite-card-link-wrapper` to `metric-card-link`

## T2 Accent Decision

The premium experience should remain visible through:

1. canonical card glow and border finish
2. signal chips
3. sparkline treatment
4. contextual scene classes that decorate the component without redefining its surface

The premium experience should not remain through:

1. `glass-panel-elite`
2. `metric-card-elite`
3. any second surface host competing with `card`

## T2 Conclusion

The component can preserve presence without preserving legacy sovereignty.

In simple words:

1. `card` is the house
2. `metric-card` is the room name
3. premium is the lighting and varnish
4. `glass-panel-elite` is no longer allowed to be the concrete wall

## T3 Runtime Migration Result

The live shared component template was migrated at:

1. [metric_card.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/includes/ui/shared/metric_card.html)

The runtime markup now uses:

1. `card metric-card`
2. `metric-card-compact` when dense mode is requested
3. `metric-card-link` for the optional wrapper

The runtime markup no longer uses:

1. `glass-panel-elite`
2. `metric-card-elite`
3. `elite-card-link-wrapper`

## T3 Validation

1. direct template inspection confirmed the new naming
2. direct search in the runtime template returned clean for the removed legacy names
3. `python manage.py check` passed after the markup migration

## T4 Styling Strategy

The canonical styling layer for the shared component now lives in:

1. [cards.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/design-system/components/cards.css)

The new visual finish is implemented as:

1. a `metric-card-link` block wrapper with canonical focus behavior
2. a `metric-card` accent layer that decorates the canonical `card`
3. no dependency on `glass-panel-elite` or `metric-card-elite`

## T4 Context Note

Some runtime callers still pass local helper classes through `extra_classes`, including `glass-panel` in a few contexts such as:

1. [student_interactive_kpis.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/catalog/includes/student/student_interactive_kpis.html)
2. [intake_center.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/onboarding/intake_center.html)

This does not block the shared metric card canonicalization, but it should be checked during T5 so we distinguish:

1. component-level canonicalization
2. caller-level residual decoration

## T5 Representative Context Validation

Representative runtime validation was checked across the major usage contexts listed in T1.

### Contexts validated as clean at the shared-component contract level

1. [metrics_cluster.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/dashboard/blocks/metrics_cluster.html)
2. [finance.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/catalog/finance.html)
3. [manager_metrics_section.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/operations/includes/manager/manager_metrics_section.html)
4. [coach_metrics_section.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/operations/includes/coach/coach_metrics_section.html)
5. [reception_metrics_section.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/operations/includes/reception/reception_metrics_section.html)

These callers now inherit the shared component through the canonical `card metric-card` path without reintroducing a structural premium helper at the call site.

### Contexts with caller-level residual decoration

1. [student_interactive_kpis.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/catalog/includes/student/student_interactive_kpis.html)
2. [intake_center.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/onboarding/intake_center.html)
3. [owner_metrics_section.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/operations/includes/owner/owner_metrics_section.html)

In these contexts, the shared metric card itself is canonicalized, but the caller still passes `glass-panel` through `extra_classes`.

This means:

1. the factory mold is fixed
2. a few callers are still placing an old decorative overlay on top of the finished part

## T5 Outcome Classification

### Resolved in the component

1. the live shared component no longer uses `glass-panel-elite`
2. the live shared component no longer uses `metric-card-elite`
3. the live shared component no longer uses `elite-card-link-wrapper`
4. the canonical host is now `card metric-card`
5. the canonical finish now lives in [cards.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/design-system/components/cards.css)

### Residual in callers

1. `glass-panel` passed via `extra_classes` in the student KPI surface
2. `glass-panel` passed via `extra_classes` in the intake KPI surface
3. `glass-panel` passed via `extra_classes` in the owner metrics surface

### Highest ROI Next Cut

The next highest ROI cut after this feature is a small caller cleanup pass for the shared metric card contexts still injecting `glass-panel`.

Primary targets:

1. [student_interactive_kpis.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/catalog/includes/student/student_interactive_kpis.html)
2. [intake_center.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/onboarding/intake_center.html)
3. [owner_metrics_section.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/operations/includes/owner/owner_metrics_section.html)

## T5 Verification

1. representative include sites were inspected directly
2. the remaining caller-level `glass-panel` usage is now localized and explicit
3. `python manage.py check` passed after the shared component canonicalization
