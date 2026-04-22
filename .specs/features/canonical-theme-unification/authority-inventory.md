# Theme Authority Inventory

**Status**: T1 completed
**Purpose**: capture the real authority and conflict map of the current OctoBOX theme before canon selection

## Executive Summary

The current OctoBOX theme is not suffering from one old CSS file.
It is suffering from **stacked authority layers** that still compete for the same visual roles.

### Confirmed signals

- `133` CSS `!important` occurrences in `static/css`
- `141` template `style=` occurrences in `templates`
- `114` occurrences of `table-card`
- `49` occurrences of `glass-panel`
- `23` occurrences of `note-panel`
- `9` occurrences of `elite-glass-card`
- `6` occurrences of `glass-panel-elite`
- `2` occurrences of `ui-card`

In simple terms:

- the app does have a design system
- but it also has several local dialects still speaking over the microphone

---

## Canonical Conflict Matrix

| Family | Current Authority Host | Evidence | Conflict Type | Severity | T2 Direction |
| --- | --- | --- | --- | --- | --- |
| Tokens | `static/css/design-system/tokens.css` | base tokens at line `30`, SaaS pass at line `225`, Front Display Wall tokens at line `342` | three stacked token authorities in one file | Critical | choose one semantic token authority |
| Surface/Card | `static/css/design-system/components/cards.css` | base card at line `15`, interaction pass at line `463`, facade pass at line `485`, artistic pass later, dark rollback around line `619` | same primitive re-authored multiple times | Critical | elect one canonical card/surface family |
| Hero | `static/css/design-system/components/hero.css` | base hero at line `11`, facade hero pass at line `256`, artistic hero pass at line `286` | multiple visual ideologies in one primitive | High | elect one canonical hero grammar |
| Topbar | `static/css/design-system/topbar.css` | Fibonacci subsystem starts at line `19`, dark behavior scattered through file, comment at line `909` says FDW block was removed to avoid conflict | topbar behaves like parallel design system | Critical | normalize topbar to consume canonical tokens |
| Utility surface dialect | `static/css/catalog/shared/utilities.css` | `.glass-panel` at line `61`, `.note-panel` at line `376`, utility engine and forced dark overrides later | utilities are carrying theme authority instead of helper-only role | High | split helper role from theme role |
| Premium/local dialects | local CSS and templates | `elite-glass-card`, `glass-panel-elite`, `ui-card` | small but conflicting premium sub-families | Medium | alias or retire |

---

## Core Evidence by File

### 1. Token Authority Conflict

**File**: [tokens.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/design-system/tokens.css)

Observed authority layers:

1. base token layer at line `30`
2. dark token overrides starting around line `82`
3. `SaaS Consistency Pass` beginning at line `224`
4. `Front Display Wall facade tokens` beginning at line `341`

What this means:

- one file is trying to be
  - theme foundation
  - consistency pass
  - facade identity layer

That is like putting foundation, wallpaper, and neon signs in the same concrete mix.

### 2. Card Authority Conflict

**File**: [cards.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/design-system/components/cards.css)

Observed stacked ownership:

1. base `.card` / `.table-card` at line `15`
2. baseline dark-mode overrides around lines `40-56`
3. Front Display Wall focus-card family in the middle of the file
4. `Card Interaction Consistency` pass at line `463`
5. `Front Display Wall facade cards pass` at line `485`
6. `Front Display Wall artistic cards pass` later in the same file
7. dark-mode forced rollback with `!important` around lines `619-631`

What this means:

- the same card primitive is created
- then decorated
- then redecorated
- then partially rolled back with force

This is the clearest proof that one painter never took final ownership.

### 3. Hero Authority Conflict

**File**: [hero.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/design-system/components/hero.css)

Observed stacked ownership:

1. base hero contract at line `11`
2. dark hero adjustments around line `210`
3. `Front Display Wall facade hero pass` at line `256`
4. `Front Display Wall artistic hero pass` at line `286`

What this means:

- hero is treated as one primitive in name
- but several in visual authorship

### 4. Topbar Parallel Kingdom

**File**: [topbar.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/design-system/topbar.css)

Observed signals:

1. own Fibonacci sizing subsystem starts at line `19`
2. uses many local `!important` variables right at the top
3. topbar-specific visual contract is large and self-contained
4. comment near line `909` explicitly states an FDW block was removed to avoid conflict with the Fibonacci design system

What this means:

- the topbar is not just styled
- it is governing itself as if it were its own design system

### 5. Utility Layer Carrying Theme Authority

**File**: [utilities.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/catalog/shared/utilities.css)

Observed signals:

1. `.glass-panel` at line `61`
2. `.note-panel` family starts around line `376`
3. utility-engine classes later in the file use `!important`
4. dark-mode overrides for notes and disclosure surfaces are forced later

What this means:

- utilities are doing more than utility work
- they are acting like theme primitives

That makes migration slower because helpers and visual authority are glued together.

---

## Live Template Collision Examples

### Mixed surface family in one component

**File**: [student_intake_panel.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/catalog/includes/student/student_intake_panel.html#L7)

Current class mix:

- `table-card`
- `layout-panel`
- `layout-panel--stack`
- `glass-panel`

Why this matters:

- one element should not need multiple base surface dialects to explain its identity

### Feature shell still uses utility glass instead of canonical container

**File**: [students.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/catalog/students.html#L44)

Current class mix:

- `glass-panel`
- `rounded-xl`
- `border-soft`
- `overflow-hidden`

Why this matters:

- this suggests the page is still composing its own container language locally

### Local premium dialect inside refined student financial workspace

**File**: [financial_overview_status.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/includes/catalog/student_form/financial/financial_overview_status.html#L2)

Current class mix:

- `card`
- `glass-panel-elite`
- `elite-panel--compact`

Why this matters:

- even a refined surface still carries a premium sub-dialect outside the core canonical family

### Reports hub isolated card dialect

**File**: [reports-hub.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/operations/reports-hub.html#L13)

Current class:

- `ui-card`

Why this matters:

- the hub is speaking a separate card language with almost no shared footprint elsewhere

---

## Family Footprint Snapshot

| Family | Approximate Footprint | Reading |
| --- | --- | --- |
| `table-card` | `114` | dominant structural family |
| `glass-panel` | `49` | broad atmospheric utility family competing with main surfaces |
| `note-panel` | `23` | notice family with wide local authority |
| `elite-glass-card` | `9` | premium local dialect |
| `glass-panel-elite` | `6` | competing premium local dialect |
| `ui-card` | `2` | isolated dialect, low footprint but high inconsistency |

---

## Root Cause

The root cause is not "old CSS" alone.

The root cause is:

1. no single final authority for the theme
2. multiple passes still alive in production files
3. utilities carrying visual identity
4. templates mixing structural and atmospheric classes in the same role
5. local variants that never got absorbed or retired

---

## T1 Conclusion

The current theme has enough evidence to justify the canonical-theme effort immediately.

This is not premature optimization.
It is overdue governance.

### What T2 must answer next

1. which family becomes the canonical surface/card primitive
2. whether `glass-panel` becomes alias or helper-only layer
3. how `note-panel` is absorbed into canonical notice/banner language
4. how topbar is normalized without breaking shell behavior
5. which premium dialects survive only as variants and which are retired
