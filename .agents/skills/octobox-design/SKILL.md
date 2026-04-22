---
name: octobox-design
description: Apply when the user asks for any OctoBox interface, component, screen, layout, token, hero, card, CTA, shell, or visual system work, or for any product that should follow the Luxo Futurista 2050 theme. Also use when there is conflict between previous visual directions and the current OctoBox visual theme, because this skill wins on theme and atmosphere. Do not use for purely logical, data-only, backend-only, or text-only tasks without interface decisions.
---

# OctoBox Design Skill

Build OctoBox UI with the official Luxo Futurista 2050 language.

Treat this skill as the visual authority layer for interface work. When there is conflict between older design directions and the current theme, this skill wins on theme, atmosphere, palette, glow discipline, and premium signature.

## Read First

Before proposing or implementing any interface change, read these docs in this order:

1. `README.md`
2. `docs/map/documentation-authority-map.md`
3. `docs/architecture/themeOctoBox.md`
4. `docs/map/design-system-contract.md`
5. `docs/experience/css-guide.md`

If the task is a front-end implementation, use `docs/map` to understand the ownership path and where the change belongs before editing code.

Important:

- The repository path is `docs/map`, not `docs/maps`.
- If a prompt, note, or older instruction says `docs/maps`, interpret it as `docs/map`.

## Core Thesis

Make OctoBox feel like a premium near-future SaaS cockpit.

It is not:

- a neon nightclub
- a hacker terminal
- a neutral commodity dashboard

It is:

- welcoming without feeling old
- modern without feeling hostile
- luminous with control, not aggression
- premium, precise, and inviting at the same time

## Absolute Rule: Performance Before UI

Never sacrifice performance for visual effect.

If an effect hurts loading, repaint cost, responsiveness, or readability, remove or simplify it.

Apply these rules:

1. Prefer native CSS over JS for visual behavior.
2. Animate `transform` and `opacity`, not paint-heavy properties.
3. Keep transitions fast, usually `150ms` to `250ms ease`.
4. Put glow and halo work on `::before` and `::after` when possible to isolate repaint.
5. Do not use animated background gradients.
6. Use heavy `backdrop-filter` only when there is a solid fallback.

## Aesthetic Hierarchy

### Layer 1: Brutalist and Immersive

This is the dominant personality, about 75 percent of the product mood.

Favor:

- high contrast as the default
- typography with presence
- intentional visual tension
- deep dark environments
- exposed grid logic when it helps hierarchy
- atmospheric depth instead of flat backgrounds
- borders that suggest material, not bureaucracy

### Layer 2: Clay Softness

This is the balancing layer, about 25 percent of the product mood.

Use it to add breath and warmth without neutralizing the brutalist base.

Favor:

- generous whitespace, usually at least `24px`
- rounded surfaces, usually `12px` to `20px`
- diffuse shadows
- clarity that supports decision-making

## Official Theme

### Dark Mode

Dark mode is the protagonist.

Target direction:

- base background: `#0F0F0F` or `#0A0E1A`
- surfaces: controlled glass with clean mineral feel
- stage: subtle atmospheric gradient, never dead-flat
- texture: only very light noise or grid when it truly helps

### Light Mode

Light mode is the same family, not a different identity.

Target direction:

- same hierarchy
- same material logic
- less glow
- more air
- bright surfaces without lifeless pure white

## Canonical Palette

Use brand colors to build identity:

- cyan `#00E5FF` for primary focus, technology, and the main CTA
- celestial blue `#4A90E2` for depth and navigation support
- neon magenta `#FF00C8` for premium energy and contrast signature

Use semantic colors only for state:

- ruby for critical
- amber for warning
- emerald for healthy or positive

Semantic colors inform state. They do not replace the identity palette.

## The Jaguar Rule for Neon

Neon is the moment of maximum visual tension. Use it like eyes in the dark: it appears when action matters.

Use neon for:

- primary CTA
- critical metrics
- active focus
- hero signature
- highest-priority card

Do not use neon for:

- body text
- page backgrounds
- decorative borders
- secondary icons
- elements without action or priority

Hard limit:

- neon should occupy at most about 10 percent of the visible area

If the page feels like carnival, the neon budget is broken.

## Visual Grammar

### Hero

Treat the hero like a command portal:

- strong presence
- controlled luminous signature
- unmistakable primary CTA
- lively supporting panel that stays subordinate

### Cards

Cards should feel like one family with role-based intensity:

- decision card: more energy, more glow discipline
- queue or context card: quieter
- support card: almost neutral

### CTA

Primary CTA:

- energized
- premium
- futuristic
- obvious

Secondary CTA:

- colder
- quieter
- never competing with the primary

### Glow and Halo

Glow is composition, not decoration.

Correct uses:

- primary CTA
- hero
- priority card
- active focus
- meaningful state signal

Wrong uses:

- everything glowing
- all cards shouting with the same intensity
- shine that beats content in the first glance

Hard rule:

- if two areas ask for attention at the same time, the composition failed

### Shadow

Use shadow to suggest depth and luxury, never to compensate for poor hierarchy.

### Chips, Rails, and Alerts

These are orientation tools, not toys:

- chips inform
- rails organize
- alerts surface risk

None of them should hijack the whole page.

## Typography

Use:

- `Inter` or `Geist` for interface text
- `Roboto Mono` or `Geist Mono` for code and dense data

Rules:

- body line-height should be at least `1.5`
- no UI data smaller than `13px`
- do not introduce decorative fonts in functional UI

## Premium Scope Rule

Not every screen deserves the full 2050 signature.

Promote a screen to premium scope only when at least two of these are true:

1. it is a primary facade for the user's role
2. it concentrates operational decision-making on first glance
3. it sustains commercial value perception
4. it contains a memorable hero, dominant CTA, or executive reading moment
5. it appears frequently enough to shape overall product quality perception

Do not apply premium scope when:

1. the screen is an intermediate utility flow or form
2. the screen needs silence more than signature
3. the content hierarchy is not mature yet
4. the screen would compete with more important surfaces

Analogy:

The global theme is the building. Premium scope is the showcase lighting. Not every hallway should become a showcase.

## Required Delivery Checklist

Before delivering any OctoBox interface decision, verify:

- content beats glow within 3 seconds
- neon stays under the 10 percent budget
- the CTA remains the clearest call for attention
- dark and light feel like the same visual family
- no effect introduces harmful performance cost
- hierarchy still works even if glow is removed
- shadows and glows are isolated cleanly when possible

## Forbidden Anti-Patterns

Never ship:

1. aggressive neon or neon backgrounds
2. gaming aesthetics with saturation everywhere
3. universal glow on every surface
4. multiple loud surfaces without hierarchy
5. dark themes based on medium gray backgrounds
6. animated background gradients
7. colored shadows, except for very controlled CTA hover energy
8. competing visual languages on the same screen
9. hot and cold premium signatures fighting each other
10. any effect that meaningfully harms performance

## Working Method

When this skill triggers, follow this flow:

1. confirm the screen goal and user role
2. read the authority docs listed above
3. decide whether the work is global design-system, shared component, or page-local CSS
4. choose whether the screen deserves premium scope or only the stable base theme
5. implement hierarchy before glow
6. validate performance, responsiveness, and readability
7. explain choices in two layers when the user is learning:
   professional explanation
   simple child-level analogy

## Final Rule

If the screen feels futuristic but tiring, it failed.

If it feels welcoming but without signature, it failed.

If it costs meaningful loading performance, it failed.

The target is:

- near future
- high perceived value
- operational clarity
- controlled energy
- immediate desire to interact
