# Evidence Map

**Status**: Completed

## Known Starting Facts

1. the live intake flow uses the direct `student-quick-create` path
2. the conversion drawer exists but is not mounted into `intake_center.html`
3. the drawer and its JS were hardened so they can now be evaluated without inline-noise dominating the decision

## T1 Live Runtime Confirmation

The current live intake runtime is confirmed as:

1. [intake_center.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/onboarding/intake_center.html) does not mount the conversion drawer
2. [intake_queue_panel.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/onboarding/includes/intake/intake_queue_panel.html) sends convertible entries directly to `{% url 'student-quick-create' %}?intake=<id>#student-form-essential`
3. [onboarding/presentation.py](C:/Users/renan/OneDrive/Documents/OctoBOX/onboarding/presentation.py) builds hero actions around the same direct path

Conclusion:

1. the business path currently in production is direct intake-to-student
2. the drawer is not participating in the live conversion contract

## T2 Flow Comparison

### Direct Flow

Current steps:

1. operator clicks convert
2. system opens student quick-create already scoped to the intake
3. operator lands directly in the student form

Strengths:

1. lowest click count
2. no modal dependency
3. route already canonicalized
4. no ambiguity about where data entry continues

Costs:

1. no intermediate plan-selection shortcut
2. no embedded payment-method pre-choice

### Drawer Flow

Potential steps:

1. operator clicks convert
2. drawer opens
3. operator chooses plan
4. operator chooses payment path
5. conversion API runs
6. operator handles success state and follow-up

Strengths:

1. more guided “micro-checkout” feeling
2. faster for a very specific express-conversion scenario
3. early payment framing

Costs:

1. adds one more decision layer before reaching the current student workflow
2. introduces a second conversion grammar in onboarding
3. duplicates part of the business logic already represented in the student quick-create flow
4. would need explicit product alignment before activation because it changes sales and enrollment behavior

## T3 Recommendation

Recommendation:

1. retire the dormant drawer from the active roadmap for now
2. keep the direct canonical intake-to-student flow as the official path
3. only revisit a conversion drawer if the business explicitly wants a dedicated express-checkout product experiment

Why retirement wins today:

1. the direct path is already live, clean, and canonical
2. the drawer does not solve a broken runtime; it introduces an alternative runtime
3. the extra modal step increases decision friction before the operator reaches the student form
4. the main value of the drawer is strategic experimentation, not current operational hardening

Simple analogy:

1. today the front door already opens straight into the right room
2. the drawer would be adding a vestibule with a nice concierge
3. that can be great in a luxury hotel
4. but if the current goal is speed and clarity, the vestibule is more ceremony than help

## T4 Formal Retirement Completed

Retirement actions applied:

1. removed [conversion_drawer.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/onboarding/includes/intake/conversion_drawer.html)
2. removed [conversion_drawer.js](C:/Users/renan/OneDrive/Documents/OctoBOX/static/js/pages/onboarding/conversion_drawer.js)
3. removed [conversion_drawer.css](C:/Users/renan/OneDrive/Documents/OctoBOX/static/css/onboarding/conversion_drawer.css)
4. removed [onboarding_views.py](C:/Users/renan/OneDrive/Documents/OctoBOX/api/v1/onboarding_views.py)
5. removed `api-v1-express-convert` from [urls.py](C:/Users/renan/OneDrive/Documents/OctoBOX/api/v1/urls.py)
6. renamed live handoff actions in:
   - [intake_queue_panel.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/onboarding/includes/intake/intake_queue_panel.html)
   - [student_intake_panel.html](C:/Users/renan/OneDrive/Documents/OctoBOX/templates/catalog/includes/student/student_intake_panel.html)

Result:

1. the codebase no longer advertises a drawer-based conversion path that does not exist in runtime
2. the live handoff names now match the actual quick-create flow
