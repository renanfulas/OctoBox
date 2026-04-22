# Context

## What just happened

The student financial workspace was refined end to end:

- structural hygiene
- hierarchy and command clarity
- calmer copy
- residual finance cleanup
- accessibility and trust hardening

That mountain is now complete.

## What contrast remains

The strongest remaining contrast in the student workflow is the main form itself.

The scan of `templates/includes/catalog/student_form/main_form/` still shows visible legacy shortcuts:

- `main_form_actions.html` still hides buttons with inline `style="display: none;"`
- `main_form_intake_banner.html` still uses inline spacing style
- the step flow still deserves a continuity pass so the essential form feels as mature as the financial interior

## Locked decisions

1. Do not reopen business rules for enrollment, billing, or lead conversion unless a real bug forces it.
2. Stay patch-first.
3. Preserve the current stepper flow and form contract.
4. Improve trust, clarity, and visual continuity before adding decoration.
5. Keep the product simple, fast, beautiful, easy, and intuitive.

## Why this phase matters

Right now the experience is like a well-designed hospital with one hallway still showing exposed maintenance tape.

The app works.
The operator can trust the financial room.
Now the front desk flow needs the same polish.
