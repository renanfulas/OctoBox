# Canonical Theme Matrix

**Status**: Approved direction
**Purpose**: translate the chosen dark premium reference line into editable system rules

## Authority Election

This matrix is not only aesthetic direction.
It is also the canonical authority table for the final painter.

| Family | Canonical Name | Current Reality | Direction |
| --- | --- | --- | --- |
| Tokens | `theme semantic tokens` | stacked base + SaaS + FDW token passes | unify in one semantic authority |
| Surface/Card | `card family` | `.card`, `.table-card`, `.glass-panel`, premium dialects | `.card` base, `.table-card` structured variant |
| Hero | `hero family` | one primitive with multiple active passes | keep `.hero`, remove competing authorship |
| Banner/Notice | `notice-panel family` | `note-panel` plus local banners | `.notice-panel` in `states.css`, migrate `note-panel` into it |
| Topbar | `topbar family` | topbar behaves like parallel mini system | keep `.topbar`, remove separate authority |

## Theme Intent

The canonical theme should feel:

1. dark
2. premium
3. calm
4. breathable
5. editable

It should **not** feel:

1. pure black
2. overly neon
3. boxed-in
4. heavy and closed
5. so stylized that every future change becomes painful

In simple terms:

- not a cave
- not a nightclub
- more like a luxury cockpit at night

---

## 1. Colors

### Canonical Direction

- primary background: deep navy dark
- secondary background: slightly lifted navy slate
- tertiary background: softened dark steel
- primary text: high-contrast cool white
- secondary text: muted blue-gray
- accent primary: warm amber/orange
- accent support: electric blue kept under control
- semantic success: emerald/cyan leaning premium, not default green
- semantic warning: amber
- semantic danger: coral/red softened for dark UI

### Rules

1. avoid pure `#000000` as main background
2. avoid purple-first dark themes
3. avoid rainbow accents fighting in the same frame
4. keep one warm commercial accent and a small semantic palette

### Why

This keeps the theme elegant and adjustable.
It is like choosing a tailored dark suit instead of painting the whole room black.

---

## 2. Surfaces

### Canonical Direction

- surfaces should feel like soft glass or smoked acrylic
- low-to-medium opacity lift over the main background
- internal gradients may exist, but must stay subtle
- content should still read clearly without depending on the glow

### Rules

1. surfaces must breathe
2. avoid thick sealed boxes
3. avoid opaque slabs unless the context truly requires weight
4. use depth to separate layers, not random background colors

### Why

The product should feel premium and open.
Like a modern dashboard under glass, not a stack of metal drawers.

### Authority Rule

- `.card` owns the main container role
- `.table-card` is a structured sibling in the same family
- `.glass-panel` may help atmosphere, but does not own structural identity anymore

---

## 3. Borders

### Canonical Direction

- borders are thin
- lightly luminous
- soft enough to frame, not hard enough to trap

### Rules

1. prefer subtle translucent borders over hard solid outlines
2. use edge separation to clarify structure, not to cage components
3. radius should feel refined and consistent, not improvised per file

### Why

Bordas devem funcionar como lapis fino em volta do componente, nao como grade de cela.

---

## 4. Glow

### Canonical Direction

- glow should be atmospheric
- mostly peripheral
- used to suggest energy, status, and premium presence

### Rules

1. never let glow become the only source of contrast
2. avoid full-neon borders by default
3. use glow stronger on hero moments and priority states, lighter on normal cards
4. glows should sit behind or around surfaces, not flood text areas

### Why

Glow is perfume, not dinner.
If we overuse it, the interface becomes tiring fast.

---

## 5. Hero

### Canonical Direction

- hero areas should feel like calm command banners
- large text
- strong clarity
- generous spacing
- subtle depth and edge light

### Rules

1. hero must answer what the page is and what matters now
2. hero should feel premium without becoming a giant locked capsule
3. large illustration or ambient graphic is optional, not required
4. CTA should stand out, but not scream

### Why

The hero is the handshake of the page.
It should feel confident, not stiff.

### Authority Rule

- `.hero` remains the official shared hero primitive
- visual passes must be merged into one grammar instead of remaining layered

---

## 6. Topbar

### Canonical Direction

- topbar should feel like a dark glass control rail
- compact
- elegant
- aligned with the shell, not visually detached from it

### Rules

1. topbar must consume canonical tokens
2. chips and indicators should be small, precise, and calm
3. avatar, search, and quick status should share the same visual family
4. avoid turning the topbar into a separate theme engine

### Why

Today the topbar behaves too much like its own kingdom.
The canonical theme should turn it back into part of the same empire.

### Authority Rule

- `.topbar` remains the shell rail
- all topbar visuals must consume canonical tokens
- topbar-specific variables may exist only for behavior or layout, not for sovereign theme authorship

---

## 7. Cards

### Canonical Direction

- cards should feel modular, clean, and quietly premium
- information density can vary, but card identity must stay stable

### Rules

1. one card family owns the role of main container
2. premium variants may exist, but only as extensions of the same family
3. avoid mixing `table-card`, `glass-panel`, `elite-glass-card`, and `ui-card` for the same structural role
4. card hierarchy must come from spacing, border, and depth before decorative tricks

### Why

If every card has a different accent, shape, and glow logic, the eye stops trusting the system.

### Authority Rule

- `.card` is the canonical card
- `.table-card` is the canonical structured variant
- `elite-glass-card`, `glass-panel-elite`, and `ui-card` are not independent final families

---

## Translation Into Tokens

The implementation phase should convert this matrix into semantic theme tokens such as:

- `--theme-bg-root`
- `--theme-bg-surface`
- `--theme-bg-surface-strong`
- `--theme-border-soft`
- `--theme-border-glow`
- `--theme-shadow-soft`
- `--theme-glow-accent`
- `--theme-text-primary`
- `--theme-text-secondary`
- `--theme-accent-primary`
- `--theme-accent-support`

These names are direction only.
Final naming can be adjusted during implementation if the canon remains clear.

---

## Non-Goals

This matrix does not mean:

1. pixel-copy the Gemini images
2. lock every page into one rigid composition
3. forbid future iteration

It means:

1. choose one visual grammar
2. keep it elegant
3. keep it flexible
4. stop letting five grammars compete at once
