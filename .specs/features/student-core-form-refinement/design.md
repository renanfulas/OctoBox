# Design

## Strategy

Use local refinement, not rebuild.

The stepper, forms, and server-side contracts already work.
We refine the shell, the banners, the actions, and the continuity between steps.

## Target Areas

1. `main_form_actions.html`
2. `main_form_intake_banner.html`
3. `main_form_step_essential.html`
4. `main_form_step_profile.html`
5. `main_form_step_health.html`
6. `main_form_step_plan.html`
7. `main_form_step_billing.html`

## Design Intent

The user should feel:

- where they are
- what this step is for
- what needs attention now
- what the next safe move is

## Technical Notes

- prefer CSS classes over inline style
- preserve current form field names and IDs
- preserve existing JS hooks unless there is a local trust/accessibility improvement
- keep copy in PT-BR and code in English-friendly structure

## Non-Goals

- changing validation rules
- changing backend form composition
- introducing a new step system
