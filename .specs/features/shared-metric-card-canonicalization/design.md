# Design

**Status**: Approved

## Scope Shape

This is a `Large` feature under SDD because it touches a shared component with cross-surface impact.

## Target Files

Primary:

1. `templates/includes/ui/shared/metric_card.html`

Secondary:

1. the CSS file that truly owns metric card styling in the design system
2. representative usage contexts for validation

## Strategy

### 1. Evidence First

Map where the component is used and which CSS rules currently control:

1. host surface
2. metric value hierarchy
3. signal badge
4. sparkline block
5. footer/action strip

### 2. Host Canonicalization

Replace the structural legacy host with the canonical host family:

1. `card`
2. local semantic metric classes only where needed

### 2.1. Canonical Host Decision

The shared metric card should be structured as:

1. `card` as the only sovereign surface host
2. `metric-card` as the shared semantic component host
3. `metric-card-compact` only as a density modifier
4. contextual classes from `card.card_class` as scene-specific extensions, not as competing hosts

The link wrapper should be renamed from the legacy wrapper to:

1. `metric-card-link`

This keeps the component readable as a shared design-system part instead of a legacy premium island.

### 3. Accent Preservation

Allow premium cues only as:

1. glow accents
2. signal tones
3. subtle finish

Never as a parallel surface system.

### 3.1. Allowed Premium Finish

The premium finish must survive only through controlled accent layers such as:

1. the canonical `card` pseudo-elements and border glow
2. metric-specific signal chips and tone states
3. sparkline contrast and highlight treatment
4. contextual accent classes like `dashboard-kpi-card` and `status-*`

The premium finish must not survive through:

1. `glass-panel-elite`
2. `metric-card-elite`
3. wrapper-only premium host classes
4. a second background or glass family competing with `card`

### 3.2. Practical Translation

In simple terms:

1. the wood and walls come from `card`
2. the polished varnish comes from `metric-card` and context accents
3. the room mood comes from scene classes like `dashboard-kpi-card`

Not the other way around.

## Verification Model

1. inspect the shared component for legacy host removal
2. validate representative usage contexts
3. run `python manage.py check`
