# Evidence Map

## Runtime anchors

1. `templates/catalog/student-form.html`
2. `catalog/presentation/student_form_page.py`
3. student-form partials directly involved in hero, guide, sequence, or finance handoff

## Governing docs

1. `docs/experience/front-display-wall.md`
2. `docs/experience/layout-decision-guide.md`

## Current live hypothesis

The student form has already improved structurally, but still likely carries the most remaining product-flow friction because:

1. it combines the highest number of domains in one surface
2. it asks the user to switch mental modes from registration to finance
3. it handles both happy path and recovery path in the same space

The open question is which small improvements will most reduce friction without making the surface heavier.

Implementation confirmed the strongest small improvements were:

1. making recovery choose the correct step automatically
2. making step-target links open the right stage
3. making the top map reflect the real current flow state
4. keeping the rest of the form structurally intact instead of layering more explanation on top
