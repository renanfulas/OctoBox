# Spec

**Status**: Draft

## Problem

The intake conversion flow is live, valuable, and still carries behavioral and routing debt inside the template layer.

Today the flow still depends on:

1. inline `onclick`
2. hardcoded student-creation hrefs
3. a JS contract exposed through global functions
4. presenter-side URL assembly by string concatenation

That makes the flow harder to maintain and riskier to evolve even though it sits on a high-value business path.

## Users

1. owner
2. reception
3. future maintainers of onboarding and student creation flows

## Requirements

### ICFH-01
The conversion drawer template must stop using inline `onclick`.

### ICFH-02
The conversion interaction contract must move into the onboarding JS asset layer using explicit selectors or `data-*` hooks.

### ICFH-03
The intake queue conversion link must stop using a hardcoded `/alunos/novo/?intake=...` path in template markup.

### ICFH-04
Presenter-generated conversion links must use named routes or a canonical route-building strategy instead of raw string assembly.

### ICFH-05
The business behavior must remain intact:

1. open conversion from the queue
2. select a plan
3. choose payment method
4. continue into student creation without extra friction

## Success Criteria

1. no inline `onclick` remains in `conversion_drawer.html`
2. no hardcoded conversion href remains in `intake_queue_panel.html`
3. presenter output no longer builds conversion links by raw path concatenation
4. the drawer interaction remains operationally clear
5. `python manage.py check` passes after the change
