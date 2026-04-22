# Canonical Hero Card Variants Tasks

**Feature**: `.specs/features/canonical-hero-card-variants/spec.md`
**Status**: Draft

---

## Task List

### T1: Map host versus repaint debt

- **What**: identify where `hero`, `card`, and `table-card` are being repainted by local CSS
- **Where**:
  1. `static/css/design-system/components/hero.css`
  2. `static/css/design-system/components/cards.css`
  3. local CSS in dashboard, finance, owner, and system pages
- **Done when**:
  1. the main repaint hotspots are listed
  2. each hotspot is classified as host concern, variant concern, or local composition concern
  3. the audit proves whether the project already has reusable variant patterns

### T2: Define canonical variant vocabulary

- **What**: choose the smallest useful first set of hero and card variants
- **Where**: `design.md`
- **Done when**:
  1. hero variants are named
  2. card variants are named
  3. each variant has a semantic purpose
  4. the first vocabulary is intentionally small and reusable

---

## Wave 1 Outcome

Wave 1 is complete when:

1. the audit confirms that the project already contains proto-variants worth absorbing
2. repaint hotspots are classified by ownership
3. the minimal first vocabulary for hero and card variants is defined
4. Wave 2 can start without rediscovering naming or ownership

### T3: Create hero variants layer

- **What**: introduce official hero variants powered by custom properties
- **Where**:
  1. `static/css/design-system/components/hero.css`
  2. `static/css/design-system/components/hero-variants.css`
- **Done when**:
  1. at least the first official hero variants exist
  2. they tune the host instead of repainting it

### T4: Create card variants layer

- **What**: introduce official card and table-card variants powered by custom properties
- **Where**:
  1. `static/css/design-system/components/cards.css`
  2. `static/css/design-system/components/card-variants.css`
- **Done when**:
  1. support and priority-style variants exist
  2. side/support rail cases can use official variants instead of custom repaint

### T5: Migrate dashboard to official variants

- **What**: move dashboard hero and support cards to the new variant system
- **Where**:
  1. dashboard templates
  2. dashboard CSS modules
- **Done when**:
  1. dashboard-local repainting shrinks materially
  2. hero and support cards use official variants
  3. at least one focus-card family starts using official card variants in markup

### T6: Migrate finance and owner pilot surfaces

- **What**: validate the architecture on finance and owner
- **Where**:
  1. finance CSS modules
  2. owner simple CSS modules
- **Done when**:
  1. the most important hero and card surfaces use the variant system
  2. legacy dark repainting shrinks in those flows
  3. the pilot includes at least one non-operational placeholder or edge surface

### T7: Document governance

- **What**: update CSS guide to forbid local repaint of canonical hosts
- **Where**: `docs/experience/css-guide.md`
- **Done when**:
  1. the rule is explicit
  2. future work has a clear decision path

---

## Wave 4 Outcome

Wave 4 is complete when:

1. the CSS guide names official variants as a first-class layer
2. the design-system contract explicitly covers variant authority
3. at least one low-risk local repaint is removed after a variant-backed migration
4. dark overrides stop duplicating variant-provided surfaces in pilot flows

---

## Wave 5 Outcome

Wave 5 is complete when:

1. dashboard-local hero styling keeps layout authority but drops duplicated surface authority
2. at least one finance surface switches from local repaint to official card-variant consumption
3. dead selectors created by the pre-variant era are removed
