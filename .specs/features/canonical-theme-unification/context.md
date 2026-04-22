# Context

## Locked Decisions

1. The current theme fragmentation is real and must be solved at the root, not patched forever.
2. The four previous visual passes are useful as inspiration, but they must stop acting as concurrent authorities.
3. A single final painter will become the canonical base for the OctoBOX UI theme.
4. This canonical base must govern the entire product, starting with core primitives and then flowing into screens.
5. The desired product feel remains:
   - simple
   - fast
   - beautiful
   - easy
   - intuitive
6. The plan must respect the existing OctoBOX stack, docs, and conventions.
7. The plan must prefer migration by authority and family, not random page-by-page cosmetic edits.
8. We should avoid opening needless technical debt while normalizing the theme.
9. The canonical direction should move toward a dark premium theme that stays open, breathable, and editable.
10. The provided Gemini references should guide system language, not force literal screen cloning.

## Evidence Already Observed

1. There are many conflicting visual dialects in live use:
   - `table-card`
   - `glass-panel`
   - `glass-panel-elite`
   - `elite-glass-card`
   - `note-panel`
   - `ui-card`
2. Core theme files carry stacked authorship passes instead of a single authority:
   - `static/css/design-system/tokens.css`
   - `static/css/design-system/components/cards.css`
   - `static/css/design-system/components/hero.css`
   - `static/css/design-system/topbar.css`
   - `static/css/catalog/shared/utilities.css`
3. The codebase still contains strong signs of visual patch debt:
   - 141 template `style=` occurrences
   - 136 CSS `!important` occurrences
4. The topbar currently behaves like a parallel mini design system instead of a consumer of one shared visual authority.
5. The reference mood we want is already visible in the Gemini mockups:
   - deep navy dark base
   - frosted premium surfaces
   - soft edge glow
   - high-contrast typography
   - controlled warm accent
   - generous breathing room

## Agent's Discretion

The implementation phase may decide:

1. the exact canonical class names for each primitive family
2. whether a legacy class becomes an alias or is fully retired
3. whether specific high-conflict utility classes should be deprecated immediately or in a later wave

These choices must still obey the canonical-theme direction defined by this package.
