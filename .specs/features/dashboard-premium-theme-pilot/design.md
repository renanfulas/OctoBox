# Design

## Visual translation map

### Import

Bring these ideas from `Refactoruiuxdesign` into the dashboard:

1. dark navy temperature instead of flat dark gray
2. premium card breathing room
3. disciplined neon accents by meaning
4. subtle glass layering on shell surfaces
5. cleaner premium shell rhythm for header and dashboard blocks

### Import as concrete pilot rules

1. shell backgrounds may deepen toward navy if text contrast stays strong
2. dashboard support surfaces may gain a more premium layered gradient
3. glance cards may gain slightly richer border/light depth
4. the topbar may gain more integrated glass polish inside dashboard scope
5. metric and status surfaces may feel more editorial and composed, not just functional

### Adapt

Adapt these instead of copying them literally:

1. glow intensity
2. blur amount
3. radius scale
4. hover lift
5. accent color usage

Reason:

OctoBox is an operational product, not a pure showcase UI.

### Adapt as execution constraints

1. glow must remain localized and lower than the reference repo default
2. blur must reinforce depth, not fog the UI
3. radius must stay compatible with current OctoBox surface family
4. hover lift must stay subtle enough for operational reading
5. copy and CTA hierarchy must remain OctoBox-native even if the skin becomes more premium

### Avoid

Do not import these directly:

1. React/Tailwind component patterns
2. heavy blur everywhere
3. excessive purple premium signaling
4. prototype-level copy or placeholder behavior
5. status-card dramatization that makes every card feel equally urgent

## OctoBox-to-reference translation

### Dashboard shell

Current owner:
- `static/css/design-system/dashboard.css`

Pilot direction:
- deeper navy atmosphere
- slightly more premium hero and support surfaces
- more coherent shell lighting
- richer but still disciplined background layering
- stronger sense of one continuous control room

### Topbar

Current owner:
- `static/css/design-system/topbar.css`

Pilot direction:
- make it feel more integrated with the dashboard shell
- preserve contract and interaction clarity
- refine it toward premium glass rail, not separate widget strip

### Glance strip

Current owners:
- `glance_cards.css`
- `glance_neon.css`

Pilot direction:
- keep semantically strong severity/actionability
- refine surface presence, border glow, and premium calm
- preserve urgency hierarchy before decorative appeal
- make tranquil cards look calmer, not merely dimmer

## Order of application

1. shell atmosphere first
2. topbar integration second
3. glance strip refinement third
4. side/support calibration last

Reason:

The room should get its lighting before the alarm panel gets retuned.

## Visual guardrails

1. red remains urgent, not decorative
2. yellow remains warning, not generic highlight
3. blue can carry premium information and shell atmosphere
4. green remains relief or success, not ambient wallpaper
5. purple, if used at all, stays accent-only

## Pilot success question

After implementation, the key question is:

Does the dashboard feel more like a premium control room while staying easier to read under pressure?

## T3 implementation snapshot

The pilot implementation was kept CSS-local on purpose.

Implemented surfaces:

1. `static/css/design-system/dashboard.css`
2. `static/css/design-system/components/dashboard/glance/glance_cards.css`
3. `static/css/design-system/components/dashboard/glance/glance_neon.css`
4. `static/css/design-system/components/dashboard/side.css`

Not changed in T3:

1. dashboard templates
2. payload semantics
3. navigation order

Reason:

For the pilot, the safest proof is atmosphere and surface refinement first, without rewriting dashboard markup or changing operational meaning.
