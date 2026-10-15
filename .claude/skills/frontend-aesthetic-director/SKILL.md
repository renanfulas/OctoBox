---
name: frontend-aesthetic-director
description: Create distinctive, production-grade frontend interfaces that avoid generic "AI slop" aesthetics. Use when Codex needs to design or implement a component, page, application, landing page, dashboard, or interactive interface with a clear artistic direction, memorable visual identity, refined typography, strong motion, and real working code. Trigger when the user asks for a bold frontend, a visually striking UI, a polished redesign, a premium landing page, a creative dashboard, or wants a build that feels intentionally designed instead of template-like.
---

# Frontend Aesthetic Director

Build frontends that feel authored, not auto-filled.

Treat each interface like stage design: choose the mood first, then place the lights, then decide where the actors stand. The code should work in production, but the visual direction must still leave a memory behind.

## Core Mission

Turn frontend requirements into working interfaces that are:

- production-grade and usable
- visually memorable
- cohesive around one clear aesthetic thesis
- refined in typography, layout, color, motion, and atmosphere

Do not default to generic SaaS patterns, timid palettes, or predictable component grids.

## Workflow

### 1. Read context before styling

Identify:

- purpose: what problem the interface solves
- audience: who uses it and in what emotional state
- constraints: framework, accessibility, performance, responsiveness, browser limits
- brand fit: whether to preserve an existing design system or establish a new visual direction

If the repo already has a visual system, preserve its language unless the user is explicitly asking for a new one.

For OctoBox work, align with:

- `README.md` for product context and current scope
- `docs/reference/documentation-authority-map.md` for doc precedence
- `docs/architecture/themeOctoBox.md` for official visual language
- `docs/experience/css-guide.md` for CSS ownership and structural discipline

### 2. Commit to one bold direction

Choose a deliberate aesthetic direction before coding.

Decide:

- what the interface should feel like in one sentence
- what the unforgettable signature is
- what typography pair carries the mood
- what background treatment creates atmosphere
- where the highest-impact motion moment lives

Good directions are specific. "Modern" is weak. "Editorial control room with mineral glass panels and cyan signal accents" is strong.

Use `references/aesthetic-directions.md` when you need a fast menu of directions and finishing moves.

### 3. Build the visual hierarchy first

Before polishing, establish:

- the dominant focal area
- the secondary reading path
- the CTA hierarchy
- how layout density supports the mood

Use asymmetry, overlap, staged spacing, deliberate silence, or controlled density when the concept benefits from it.

Do not add decorative effects that compete with the content. Every dramatic choice must help orientation, emotion, or memory.

### 4. Implement real code

Write working code in the stack the user asked for.

Rules:

- prefer semantic HTML and accessible structure
- keep interactions functional, not mocked
- make desktop and mobile both feel intentional
- use CSS variables or project tokens for consistency
- use animation where it creates delight or hierarchy, not noise
- favor CSS-only motion when it is enough
- in React, prefer the repo's patterns over novelty for its own sake

### 5. Refine like a product designer

Polish the details that make the work feel authored:

- type scale, tracking, and line length
- edge radii and border language
- shadow discipline
- hover and focus behavior
- loading and entrance choreography
- spacing rhythm
- empty states and supporting copy

The last 10 percent is where "good" becomes "this feels designed."

## Non-Negotiables

- Never use generic AI frontend aesthetics by reflex.
- Never default to Inter, Roboto, Arial, or a system stack unless the existing product already depends on them.
- Never ship purple-on-white gradient cliché work unless the brand already uses it.
- Never let motion, glow, or texture overpower content hierarchy.
- Never break the host design system when working inside an established product.
- Never choose intensity without intention. Minimal can be bold if it is precise.

## OctoBox Alignment

When working inside OctoBox:

- treat `docs/architecture/themeOctoBox.md` as the visual authority when theme conflicts appear
- keep premium signature scoped; not every page should become a neon showroom
- use local CSS ownership correctly instead of inventing parallel visual authorities
- build from tokens and canonical surface patterns before creating page-local exceptions

Metaphor:

The global theme is the building's architecture. Your page is one room inside it. You can light the room beautifully, but you should not secretly rebuild the whole building from inside the room.

## Delivery Pattern

When the user asks for a new UI, prefer this internal sequence:

1. summarize the interface goal in one line
2. name the chosen aesthetic direction
3. identify the memorable signature
4. implement the code
5. verify responsiveness and interaction
6. explain the result in a concise way

If the user is learning, explain technical choices in two layers:

- professional explanation
- simple analogy a child could follow

## Reference

- [Aesthetic Directions](references/aesthetic-directions.md)
