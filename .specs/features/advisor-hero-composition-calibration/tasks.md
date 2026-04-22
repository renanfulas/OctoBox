# Advisor Hero Composition Calibration Tasks

**Design**: `.specs/features/advisor-hero-composition-calibration/design.md`  
**Status**: In Progress

## Tasks

### T1: Inspect Local Composition Change [Completed]

Confirmed that the live local diff is smaller than the original hypothesis:

1. it removes the mobile-scoped hero tokens `--operation-hero-heading-max-width: 100%`
2. it removes the mobile-scoped hero token `--operation-hero-heading-size: clamp(1.8rem, 9vw, 2.3rem)`
3. it does not currently include the broader centering rules that motivated opening this micro-mountain
4. the live advisor contract still comes from `dashboard.css` + `advisor_narrative.html`, with the hero already collapsing to a tighter single-column rhythm under `960px`

### T2: Decide Keep / Soften / Discard [Completed]

Decision: Keep the local removal.

Why:

1. the removed mobile tokens live in the generic operation hero contract, not in the advisor narrative selectors
2. `advisor_narrative.html` renders a `dashboard-hero dashboard-advisor-narrative`, not an `operation-hero`
3. the advisor hero title/body/actions are already driven by explicit dashboard selectors
4. keeping the removal trims a dead local exception instead of preserving dashboard-only drift with no clear runtime value

### T3: Apply Final Calibration [Completed]

Applied with a minimal-change decision:

1. keep the local `dashboard.css` removal as the approved runtime outcome for this micro-front
2. do not expand scope into `operations/refinements/hero.css`, because that file now shows a broader parallel hero refactor
3. preserve separation of stories so the advisor calibration remains a small dashboard-only cleanup instead of accidentally absorbing a system-wide hero rewrite

### T4: Validate and Close [Completed]

Validation outcome:

1. `python manage.py check` passed cleanly
2. the advisor dashboard micro-change remains isolated to the `dashboard.css` removal itself
3. the worktree is not commit-ready as a single story yet, because `operations/refinements/hero.css` is also modified by a broader parallel refactor
4. the micro-mountain is therefore closed conceptually, but requires file separation before any clean commit
