# Evidence Map

**Status**: T6 completed

## Live Runtime Composition Confirmed

### 1. Class Grid Page Root

The live class-grid page is composed in:

1. [class-grid.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/catalog/class-grid.html)

Confirmed runtime notes:

1. it mounts the workspace
2. it mounts the monthly modal
3. it mounts the weekly modal

### 2. Daily View Runtime

The daily row lives in:

1. [workspace_today_row.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/includes/catalog/class_grid/today/workspace_today_row.html)

Confirmed debt:

1. edit shortcut still uses a hardcoded `href="/grade-aulas/?...edit_session=...#edicao-aula"`
2. occupancy bar still uses inline custom-property styling:
   - `style="--bar-width: {{ item.occupancy_percent }}%;"`

The daily row is mounted through:

1. [workspace_today.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/includes/catalog/class_grid/today/workspace_today.html)

### 3. Weekly View Runtime

The weekly day card lives in:

1. [class_grid_weekly_day_card.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/includes/ui/class_grid/class_grid_weekly_day_card.html)

Confirmed debt:

1. clickable affordance still uses inline styling:
   - `style="cursor: pointer;"`
2. the card already carries keyboard semantics:
   - `role="button"`
   - `tabindex="0"`
3. it delegates child session rendering to the weekly session chip

The weekly day card is mounted through:

1. [workspace_weekly.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/includes/catalog/class_grid/views/workspace_weekly.html)
2. [weekly_modal.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/includes/catalog/class_grid/views/weekly_modal.html)

### 4. Weekly Session Chip Runtime

The weekly session chip lives in:

1. [class_grid_weekly_session_chip.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/includes/ui/class_grid/class_grid_weekly_session_chip.html)

Confirmed debt:

1. edit shortcut still uses a hardcoded `href="/grade-aulas/?...edit_session=...#edicao-aula"`
2. delete behavior already uses a form contract and hidden `return_query`

### 5. CSS Ownership Confirmed

The active CSS owners are:

1. [workspace.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/catalog/class-grid/workspace.css)
   - daily row, occupancy stack, workspace mechanics
2. [calendar.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/catalog/class-grid/calendar.css)
   - weekly day card, weekly session chip, action strip

### 6. JS Ownership Confirmed

The weekly interaction owner is:

1. [class-grid.js](C:/Users/renan/OneDrive/Documents/OctoBOX/static/js/pages/class-grid/class-grid.js)

Confirmed runtime behavior:

1. weekly day cards are opened in a modal through JS
2. keyboard `Enter`/`Space` support is already wired in JS
3. the script still injects some inline style into cloned modal content:
   - cursor reset
   - min-height reset
4. the weekly modal alternate day view also toggles `display` inline

## T1 Conclusion

The live class-grid interaction contract is real and split across:

1. daily template routing
2. weekly template affordance
3. weekly JS behavior
4. CSS owners that are already cleanly separated by daily/workspace vs weekly/calendar

In simple terms:

1. the class board is alive
2. the handles are visible
3. but some labels and some movement rules are still handwritten

## T2 Decision

The canonical contract is now locked as follows:

### Edit Links

1. use `{% url 'class-grid' %}` as the canonical base route
2. preserve the current query string when present
3. preserve `edit_session=<id>` and `#edicao-aula` as the edit intent envelope

### T3 Result

The active edit links have now been migrated in:

1. [workspace_today_row.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/includes/catalog/class_grid/today/workspace_today_row.html)
2. [class_grid_weekly_session_chip.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/includes/ui/class_grid/class_grid_weekly_session_chip.html)

Validated outcome:

1. hardcoded `/grade-aulas/?...` edit links are gone from the active daily and weekly targets
2. `edit_session=<id>` and `#edicao-aula` remain preserved
3. `python manage.py check` passes clean after the route swap

### Weekly Day Card Affordance

1. keep semantic keyboard/button behavior in markup
2. remove inline cursor styling
3. express clickability through semantic classes interpreted by `calendar.css`

### T4 Result

The weekly day-card affordance has now been normalized in:

1. [class_grid_weekly_day_card.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/includes/ui/class_grid/class_grid_weekly_day_card.html)
2. [calendar.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/catalog/class-grid/calendar.css)

Validated outcome:

1. inline `style="cursor: pointer;"` is gone from the active weekly day card
2. the card now declares interactivity through a semantic `is-interactive` class
3. pointer, hover, and focus-visible affordances now live in the weekly CSS owner
4. `python manage.py check` passes clean after the affordance move

### JS vs CSS Ownership

JS keeps:

1. opening weekly modal in `full` or `day` mode
2. cloning the chosen day card
3. updating modal title
4. wiring click and keyboard events

JS should stop owning:

1. cursor styling
2. display-mode styling through raw inline style when a class can express the mode
3. clone appearance overrides through `element.style.*`

CSS should own:

1. pointer affordance
2. modal day/full visibility states
3. clone-specific visual adjustments

### T5 Result

The remaining active interaction debt has now been normalized in:

1. [weekly_modal.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/includes/catalog/class_grid/views/weekly_modal.html)
2. [workspace_weekly.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/includes/catalog/class_grid/views/workspace_weekly.html)
3. [calendar.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/catalog/class-grid/calendar.css)
4. [class-grid.js](C:/Users/renan/OneDrive/Documents/OctoBOX/static/js/pages/class-grid/class-grid.js)

Validated outcome:

1. the weekly modal no longer depends on inline `display` styling
2. weekly modal day rendering no longer injects inline layout styling through JS
3. weekly clone appearance no longer depends on `element.style.*`
4. the weekly board header now declares interactive behavior semantically in markup and CSS
5. `python manage.py check` passes clean after the weekly modal cleanup

### T5 Deliberate Non-Change

The occupancy bar in:

1. [workspace_today_row.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/includes/catalog/class_grid/today/workspace_today_row.html)

still uses an inline custom property for `--bar-width`.

This was kept intentionally because:

1. it is part of a shared mix-bar pattern already used in other live financial and class-grid surfaces
2. it carries dynamic numeric presentation data, not ad-hoc interaction styling
3. replacing it here without a broader shared-component pass would likely create worse debt, not less

## T6 Final Validation

The daily and weekly class-grid interaction surfaces are now validated as coherent after the cleanup.

Validated surfaces:

1. [workspace_today_row.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/includes/catalog/class_grid/today/workspace_today_row.html)
2. [class_grid_weekly_day_card.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/includes/ui/class_grid/class_grid_weekly_day_card.html)
3. [class_grid_weekly_session_chip.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/includes/ui/class_grid/class_grid_weekly_session_chip.html)
4. [weekly_modal.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/includes/catalog/class_grid/views/weekly_modal.html)
5. [workspace_weekly.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/includes/catalog/class_grid/views/workspace_weekly.html)
6. [calendar.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/catalog/class-grid/calendar.css)
7. [class-grid.js](C:/Users/renan/OneDrive/Documents/OctoBOX/static/js/pages/class-grid/class-grid.js)

Final verdict:

1. daily and weekly edit entry points now share the same canonical route contract
2. weekly interactive affordance is now declared semantically and rendered by CSS, not inline markup or JS
3. weekly modal day/full switching remains owned by JS, but visual expression now belongs to markup and CSS
4. `python manage.py check` passes clean
5. the only remaining inline style in the active daily target is the intentional shared `mix-bar` custom property

## Final Classification

Resolved:

1. hardcoded edit links in the active daily and weekly targets
2. inline clickable affordance on the weekly day card
3. inline modal visibility styling
4. inline clone appearance styling in weekly JS
5. JS-owned cursor styling on the weekly board header

Residual tolerable:

1. the inline `--bar-width` custom property in the daily occupancy bar, by explicit shared-pattern decision

Feature status:

1. the live class-grid interaction contract cleanup is complete
