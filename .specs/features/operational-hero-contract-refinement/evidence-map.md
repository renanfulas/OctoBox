# Evidence Map

## Runtime anchors

1. `static/css/design-system/operations/refinements/hero.css`
2. `static/css/design-system/workspace.css`
3. `templates/includes/ui/layout/page_hero.html`
4. `static/css/design-system/operations/manager/scene.css`
5. `static/css/design-system/operations/reception/scene.css`
6. `static/css/catalog/students/scene.css`
7. `static/css/catalog/finance/_hero.css`

## Governing docs

1. `docs/experience/front-display-wall.md`
2. `docs/experience/layout-decision-guide.md`

## Current live hypothesis

The shared hero diff appears to be trying to:

1. increase compositional rhythm
2. relax stack and copy width
3. standardize action density
4. formalize mobile heading behavior

Inspection refined the hypothesis:

1. the shared contract truly feeds many screens via `page_hero.html`
2. manager and reception intentionally tighten the hero locally
3. student and finance also apply local caps and spacing rules
4. therefore the open question is not whether the diff is real, but which parts deserve shared authority versus local ownership

Representative evidence supports the following classification:

1. `manager/scene.css`, `reception/scene.css`, and `dev-coach/coach.css` keep denser hero overrides
2. `catalog/students/scene.css` and `catalog/finance/_hero.css` also cap width locally
3. `owner` variants tolerate more editorial width and presence
4. therefore shared authority must remain cross-surface safe rather than adopting the loosest possible values as baseline
