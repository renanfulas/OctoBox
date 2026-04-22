# Student Form Flow Polish Tasks

**Design**: `.specs/features/student-form-flow-polish/design.md`  
**Status**: Completed

## Tasks

### T1: Map Student Form Friction [Completed]

Mapped the main friction points:

1. the page had multiple sequence signals close together, but not all of them reflected the real current state
2. the recovery guide could point at step 2 while the stepper still opened on step 1
3. recovery links did not actively switch the stepper to the target stage
4. the top workspace map still treated the second phase too generically instead of distinguishing commercial closure from true finance handoff

### T2: Define Minimum-Weight Flow Improvements [Completed]

Chose the smallest high-ROI changes:

1. make the presenter compute the current flow state explicitly
2. make the stepper start on the correct stage when recovery points to commercial closure
3. make recovery and map links switch to the correct step
4. make the top map speak more honestly about whether the next layer is commercial closure or financial workspace

### T3: Implement the Flow Polish [Completed]

Implemented in:

1. `catalog/presentation/student_form_page.py`
2. `templates/catalog/student-form.html`
3. `templates/includes/catalog/student_form/main_form/main_form.html`
4. `templates/includes/catalog/student_form/main_form/main_form_recovery.html`
5. `static/js/pages/students/student-form-stepper.js`
6. `static/css/catalog/student_form_stepper.css`

### T4: Validate Completion Clarity [Completed]

Validation outcome:

1. `python manage.py check` passed cleanly
2. the student form now opens on the right step when recovery points to plan/billing friction
3. recovery links and top-map links can push the stepper to the correct stage
4. the top sequence now distinguishes registration, commercial closure, and finance handoff more honestly
