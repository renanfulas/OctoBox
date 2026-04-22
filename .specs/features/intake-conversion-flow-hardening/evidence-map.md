# Evidence Map

**Status**: T1 completed

## Live Runtime Path Confirmed

### 1. Page Composition

The intake center page is composed in:

1. [intake_center.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/onboarding/intake_center.html)

Confirmed runtime notes:

1. the queue lives in `tab-intake-queue`
2. the drawer is not included directly in this page template
3. the page loads the onboarding JS asset through the presenter layer

### 2. Queue Handoff Surface

The queue conversion trigger lives in:

1. [intake_queue_panel.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/onboarding/includes/intake/intake_queue_panel.html)

Confirmed debt:

1. conversion CTA uses hardcoded `href="/alunos/novo/?intake={{ intake.id }}#student-form-essential"`
2. the trigger uses `data-action="convert-intake-to-student"`
3. the JS extracts runtime data from the surrounding `.intake-card`

### 3. Drawer Surface

The drawer surface lives in:

1. [conversion_drawer.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/onboarding/includes/intake/conversion_drawer.html)

Confirmed debt:

1. plan selection still uses inline `onclick="selectDrawerPlan(...)"`
2. PIX and card submission still use inline `onclick="submitExpressConversion(...)"`
3. the drawer depends on `id`-based DOM lookup for student name and phone
4. the success state still injects inline styles into generated HTML

### 4. JS Behavior Owner

The behavior owner is:

1. [conversion_drawer.js](C:/Users/renan/OneDrive/Documents/OctoBOX/static/js/pages/onboarding/conversion_drawer.js)

Confirmed runtime behavior:

1. the asset listens for clicks on `[data-action="convert-intake-to-student"]`
2. it opens the drawer by scraping name, phone, and intake id from the queue card DOM
3. it exposes global hooks through:
   - `window.selectDrawerPlan`
   - `window.submitExpressConversion`
   - `window.copyAndNotify`
4. it posts to a hardcoded API path:
   - `/api/v1/onboarding/express-convert/`
5. it appends a success overlay into the drawer after successful conversion

### 5. Presenter Layer

The presenter owner is:

1. [onboarding/presentation.py](C:/Users/renan/OneDrive/Documents/OctoBOX/onboarding/presentation.py)

Confirmed debt:

1. hero action `Converter primeiro` still builds its href by raw string assembly
2. hero fallback `Nova entrada` still builds its href by raw string assembly
3. the asset loading already includes:
   - `js/pages/onboarding/conversion_drawer.js`

### 6. API Endpoint

The express conversion endpoint is already named in the API router:

1. [api/v1/urls.py](C:/Users/renan/OneDrive/Documents/OctoBOX/api/v1/urls.py)
   - `name='api-v1-express-convert'`

This is important because:

1. the JS is still using a raw path string
2. but the route already has a canonical name available in the backend

## T1 Conclusion

The live intake conversion flow is real and high-value, and the debt is concentrated in four places:

1. hardcoded conversion link in queue markup
2. inline `onclick` in the drawer
3. global JS contract in the drawer asset
4. raw string route generation in the presenter

In simple terms:

1. the conversion machine is working
2. but the trigger, the control panel, and part of the route map are still taped together

## Runtime Decision After T1

The drawer is currently classified as:

1. `dormant, not mounted into the live intake center page`

Therefore the first hardening pass should:

1. canonicalize the live queue handoff
2. canonicalize presenter route generation
3. remove dormant drawer assets and payload weight from the live page

Not:

1. reactivate the drawer without an explicit UX decision
