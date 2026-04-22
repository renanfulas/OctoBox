# Theme Migration Matrix

**Status**: T3 completed
**Purpose**: classify the active visual families into `canonical`, `alias`, `migrate`, or `remove`

## Status Meanings

| Status | Meaning |
| --- | --- |
| `canonical` | official final authority for that visual role |
| `alias` | temporary bridge that may remain during migration but does not own the role |
| `migrate` | active family that must be absorbed into a canonical family |
| `remove` | family or pattern that should disappear once migration is complete |

---

## Core Family Matrix

| Family / Class | Current Role | Status | Destination | Why |
| --- | --- | --- | --- | --- |
| `theme semantic tokens` | root theme semantics | canonical | stays in `tokens.css` | one source of truth is mandatory |
| `.card` | generic container | canonical | stays in `cards.css` | best host for the final surface family |
| `.table-card` | structured container | canonical | stays in `cards.css` as variant | high-footprint structured sibling of `.card` |
| `.hero` | command banner | canonical | stays in `hero.css` | already the shared page-top primitive |
| `.topbar` | shell control rail | canonical | stays in `topbar.css` under shared tokens | central shell primitive that must obey the same empire |
| `.notice-panel` | contextual messaging target | canonical | stays in `states.css` | notices need a first-class design-system home |
| `.state-notice` | state template contract | canonical | stays in `states.css` as canonical alias | existing state include now shares the same grammar |
| `.glass-panel` | atmospheric surface helper | alias | helper/atmosphere layer over canonical card family | too reused to kill immediately, but not fit as sovereign container |
| `.finance-glass-panel` | finance-specific atmosphere helper | alias | same logic as `.glass-panel` | can remain as scoped helper while finance migrates |
| `.note-panel` | current notice family | migrate | `notice-panel family` | useful footprint, wrong authority host |
| `.note-panel-success` | semantic notice variant | migrate | canonical notice success variant | should inherit from same notice grammar |
| `.note-panel-warm` | semantic notice variant | migrate | canonical notice warning/warm variant | same family, new host |
| `.note-panel-cream` | semantic notice variant | migrate | canonical notice neutral/warm variant | same family, new host |
| `.note-panel-success-soft` | semantic notice variant | migrate | canonical notice success-soft variant | same family, new host |
| `.note-panel-danger` | semantic notice variant | migrate | canonical notice danger variant | same family, new host |
| `.glass-panel-elite` | premium local surface dialect | migrate | canonical card premium variant | must stop competing as separate container language |
| `.elite-glass-card` | premium local surface dialect | migrate | canonical card premium variant | same reason as above |
| `.elite-panel--compact` | premium density modifier | alias | canonical premium card modifier | compactness can survive, autonomy cannot |
| `.ui-card` | isolated card dialect | remove or migrate | canonical card family | footprint is too small to justify sovereignty |

---

## File-Level Authority Moves

| File | Current State | Migration Action |
| --- | --- | --- |
| `static/css/design-system/tokens.css` | base + SaaS + FDW stacked | merge into one semantic authority |
| `static/css/design-system/components/cards.css` | base + interaction + facade + artistic + rollback | keep as canonical host, remove competing author layers |
| `static/css/design-system/components/hero.css` | base + facade + artistic | keep as canonical host, collapse to one grammar |
| `static/css/design-system/topbar.css` | behavior plus parallel theme logic | keep as canonical host, strip sovereign theme role |
| `static/css/catalog/shared/utilities.css` | helpers plus theme authority | retain helpers, demote visual authority |

---

## Template-Level Interpretation Rules

### Rule 1: Never mix base container families for the same role

Bad:

- `table-card glass-panel`
- `card glass-panel-elite`
- `ui-card` beside `card` for the same structural job

Good:

- `card` plus optional helper class
- `table-card` plus optional helper class
- one canonical surface family per role

### Rule 2: Atmosphere may decorate, but not define structure

That means:

- `glass-panel` can survive as a skin helper
- it cannot remain the thing that decides what the container fundamentally is

### Rule 3: Premium is a variant, not a kingdom

That means:

- premium cards may still exist
- but they must inherit from the same base card family

---

## Removal Candidates

These are the main removal or strong-retirement candidates once migration is mature:

1. `ui-card`
2. free-floating local hero passes inside `hero.css`
3. stacked artistic/facade passes inside `cards.css`
4. topbar-only sovereign visual variables that duplicate theme authority
5. local use of `glass-panel-elite` and `elite-glass-card` as separate families

---

## Transitional Alias Policy

The following may remain temporarily as bridges:

1. `.glass-panel`
2. `.finance-glass-panel`
3. `.elite-panel--compact`

But only under two rules:

1. they cannot redefine the canonical role
2. they must have a retirement or absorption destination

---

## What Changes in Practice

Before:

- the same screen could choose between multiple visual religions

After this matrix:

- the religion is chosen once
- helpers can still decorate
- but they no longer write the law

In simple terms:

- one king
- some governors
- a few temporary advisors
- and a list of nobles losing the castle
