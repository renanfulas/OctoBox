# Design

**Status**: Approved

## Scope Shape

This is a `Large` feature under SDD because it touches a live conversion flow with cross-layer impact:

1. template
2. presenter
3. JS behavior
4. route discipline

## Target Files

Primary:

1. `templates/onboarding/includes/intake/conversion_drawer.html`
2. `static/js/pages/onboarding/conversion_drawer.js`
3. `templates/onboarding/includes/intake/intake_queue_panel.html`
4. `onboarding/presentation.py`

Secondary:

1. any CSS owner needed to support selector cleanup
2. tests or verification points tied to intake conversion

## Strategy

### 1. Evidence First

Map the live runtime path before editing:

1. queue handoff button
2. conversion drawer trigger
3. plan selection behavior
4. payment path behavior
5. presenter-built conversion action links

### 2. Interaction Contract Hardening

Replace inline interaction with explicit JS hooks:

1. `data-plan-id`
2. `data-action`
3. drawer-local event delegation

The JS owner should interpret the surface.
The template should declare the surface.

### 2.0. Dormant Drawer Rule

If runtime evidence confirms that the conversion drawer is not mounted into the active intake page, then:

1. the drawer is treated as a dormant surface
2. the live hardening pass should not reactivate it by accident
3. the page should stop loading drawer-specific assets and data until an explicit activation mountain exists

In simple terms:

1. do not install the automatic door just because the motor exists in a box
2. first harden the manual door people are already using

### 2.1. Behavioral Rule

The drawer must not depend on:

1. inline `onclick`
2. manual global wiring unless absolutely required for compatibility

Preferred direction:

1. event delegation inside `conversion_drawer.js`
2. local functions scoped to the page asset
3. explicit `data-*` hooks

### 3. Route Canonicalization

Replace hardcoded conversion paths with a canonical route strategy:

1. `{% url 'student-quick-create' %}` in templates
2. `reverse('student-quick-create')` in presenter code

The `?intake=<id>#student-form-essential` tail can remain, but the base route should stop being handwritten.

### 4. UX Preservation

This hardening pass must preserve:

1. fast conversion feeling
2. visible plan choice
3. clear payment choice
4. low-friction progression into student creation

In simple terms:

1. we are changing the wiring
2. not making the door heavier to open

## Verification Model

1. inspect template cleanup
2. inspect JS hook ownership
3. verify presenter route generation
4. run `python manage.py check`
