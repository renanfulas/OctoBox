# Legacy Patterns Map

Use this map to avoid confusing historical naming with real current authority.

## Protected Aliases

These families may look old by name, but they are documented as active or protected:

| Family | Default classification | Why |
| --- | --- | --- |
| `note-panel*` | `canonical-alias` | Documented in the current states layer and still used by real screens. |
| `legacy-copy*` | `canonical-alias` or `structural-do-not-touch` | Historical naming debt, but still active in live UI layers. |

Rule:

1. do not mark these as dead on first pass
2. only propose migration when there is an explicit plan to replace them
3. if they appear in canonical files, preserve them until a controlled migration exists

## Legacy Bridges

These families are historically risky because they can compete with the new authority ladder:

| Family | Default classification | Reading |
| --- | --- | --- |
| `glass-panel` | `legacy-bridge` | Often carries historical atmosphere or surface behavior. |
| `finance-glass-panel` | `legacy-bridge` | Finance-specific historical bridge. |
| `elite-glass-card` | `dead` or `candidate-unused` | Usually legacy residue; confirm before deletion. |
| `glass-panel-elite` | `dead` or `candidate-unused` | Usually legacy residue; confirm before deletion. |
| `ui-card` | `dead` or `candidate-unused` | Historical generic surface; confirm before deletion. |

Rule:

1. if still used, classify as `legacy-bridge`
2. if not referenced in templates, JS, or payload strings, classify as `candidate-unused`
3. only classify as `dead` when the rule has no live consumer and no protected bridge role

## Known Hotspots

These places deserve immediate suspicion during audits:

| Path | Why it matters |
| --- | --- |
| `static/css/catalog/shared/utilities.css` | Concentrates historical helpers, utilities, and prior theme residue. |
| `static/css/catalog/shared.css` | Broadly loaded shared layer that can spread legacy behavior. |
| `static/css/design-system/components/states.css` | Canonical home for some state aliases; do not misclassify active hosts as dead. |
| `static/css/design-system/components/dashboard/summary.css.bkp` | Residual backup artifact and strong dead-code candidate. |

## Ownership Reminder

When a class looks old, do not ask only "does the name feel legacy?"

Ask:

1. where is it defined?
2. where is it loaded?
3. which screen still consumes it?
4. is it a bridge, an alias, or a dead branch?

## Safe Retirement Order

Prefer this order when cleaning legacy rules:

1. classify
2. isolate
3. migrate authority
4. downgrade the bridge
5. delete only after proof

In simple terms:

1. find the wire
2. see whether it still powers a room
3. reroute the power
4. then remove the old wire
