# Design

**Status**: Approved

## Scope Shape

This is a `Large` feature under SDD because it touches a live operational surface with multiple interaction entry points:

1. daily row
2. weekly day card
3. weekly session chip
4. edit and delete affordances

## Target Files

Primary:

1. `templates/includes/catalog/class_grid/today/workspace_today_row.html`
2. `templates/includes/ui/class_grid/class_grid_weekly_day_card.html`
3. `templates/includes/ui/class_grid/class_grid_weekly_session_chip.html`

Secondary:

1. class-grid CSS owners that support interaction affordances
2. any template that composes the same edit/query/fragment contract

## Strategy

### 1. Evidence First

Map the live runtime path before editing:

1. daily row edit shortcut
2. weekly session chip edit shortcut
3. weekly day-card click affordance
4. delete-session form contract

### 2. Route Canonicalization

Replace handwritten class-grid routes with a canonical route strategy:

1. `{% url 'class-grid' %}` in templates
2. preserve query-string and fragment behavior
3. keep edit intent explicit and readable

### 2.1. Canonical Edit Link Rule

Edit shortcuts in the class grid should follow this rule:

1. base route always comes from `{% url 'class-grid' %}`
2. query composition remains explicit in the template because it depends on `page.behavior.current_query_string`
3. the edit intent remains encoded as:
   - `edit_session=<session_id>`
   - `#edicao-aula`

In simple terms:

1. the street name comes from the official map
2. the apartment number and room note stay attached to the envelope

### 3. Interaction Grammar Hardening

The active class-grid surfaces should express interactivity through:

1. semantic classes
2. `data-action` hooks when needed
3. CSS-owned affordances

Not through:

1. inline `style="cursor: pointer;"`
2. scattered local interaction hints
3. mixed daily/weekly interaction grammar

### 3.1. Weekly Day Card Affordance Rule

The weekly day card should keep:

1. `role="button"`
2. `tabindex="0"`
3. `data-day-date`

The weekly day card should stop using:

1. inline cursor styling

The clickable affordance should come from:

1. semantic state class on the card, such as a dedicated interactive marker
2. CSS in the weekly/calendar owner
3. JS behavior already bound through the weekly modal logic

### 3.2. JS State Rule

What should leave inline JS:

1. `style.display = ...` toggles for weekly modal views
2. inline style injected into `weeklyDayView.innerHTML`
3. clone-specific cursor and min-height overrides expressed through `element.style.*`
4. header cursor styling done by JS

What may remain as JS-controlled state:

1. switching between `full` and `day` modal modes
2. cloning the clicked day card into the modal view
3. keyboard and click event handling
4. title updates for the modal

Preferred translation:

1. JS should toggle classes or semantic state attributes
2. CSS should interpret those classes
3. markup should declare the interactive surface

### 4. UX Preservation

This pass must preserve:

1. fast access to edit actions
2. weekly scanning speed
3. occupancy reading
4. low-friction delete workflow for allowed roles

In simple terms:

1. we are standardizing the handles on the drawers
2. not moving the drawers to another wall

## Verification Model

1. inspect hardcoded route removal
2. inspect inline-style removal from active interaction surfaces
3. inspect edit/delete contract clarity
4. run `python manage.py check`
