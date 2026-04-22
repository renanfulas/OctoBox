# Front Display Wall Refinement Context

## User Decisions Locked

These decisions are already defined and should constrain design and execution.

1. The north star is the Front Display Wall:
   - the product must feel simple
   - fast
   - beautiful
   - easy
   - intuitive

2. The active source of direction is:
   - `docs/experience/front-display-wall.md`
   - `docs/experience/layout-decision-guide.md`
   - `.specs/codebase/CONVENTIONS.md`
   - `.specs/codebase/CONCERNS.md`

3. Export commands are not part of the main user-facing facade during this phase:
   - remove visual CSV/PDF buttons from the main flow
   - keep export infrastructure alive in the backend
   - bring export commands back only at operational closing time

4. Patch-first policy:
   - build on top of the current tools and structure whenever possible
   - if a real reconstruction opportunity appears, it must be surfaced explicitly before implementation

5. The current evaluation must combine these specialist lenses:
   - CSS and front-end cleanliness
   - performance and perceived speed
   - payment and financial UX confidence
   - prompt/critic discipline for product-contract clarity

6. The facade must not expose worksite language as the dominant tone:
   - avoid "suspended", "under reform", or similar copy as the main face of the page
   - keep transitional or technical states secondary and controlled

## Assumptions Accepted For Planning

1. This is a large multi-surface refinement, not a quick fix.
2. The first target surfaces are:
   - `students`
   - `finance`
   - `reports-hub`
3. The shell and routing base are stable enough to receive front refinement without reopening architecture.
