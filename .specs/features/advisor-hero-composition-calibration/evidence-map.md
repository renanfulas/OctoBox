# Evidence Map

## Runtime anchors

1. `static/css/design-system/dashboard.css`
2. `templates/dashboard/conselheiro.html`
3. `templates/dashboard/blocks/advisor_narrative.html`

## Governing docs

1. `docs/experience/front-display-wall.md`
2. `docs/experience/layout-decision-guide.md`

## Current live hypothesis

The original hypothesis was that the advisor hero might benefit from:

1. stronger central composition
2. narrower copy mass
3. more editorial alignment

The inspection changed the picture:

1. the current live diff in `dashboard.css` only removes two mobile hero tokens
2. the large centering experiment is not currently present in the worktree
3. `advisor_narrative.html` uses `dashboard-hero dashboard-advisor-narrative`, not `operation-hero`
4. the advisor title/body/actions are governed by dashboard-specific selectors, so the removed tokens do not appear to be active control points for this hero
5. the real T2 decision becomes whether to keep trimming this dead local exception, and the answer is yes
