# Student Financial Workspace Refinement Context

## User Decisions Locked

These decisions are already defined and should constrain design and execution.

1. The north star remains the Front Display Wall:
   - the product must feel simple
   - fast
   - beautiful
   - easy
   - intuitive

2. The last phase already refined the facade:
   - `students`
   - `finance`
   - `reports-hub`
   - this next phase must carry that same quality inward, not restart the facade work

3. Patch-first policy stays active:
   - build on top of the current tools and structure whenever possible
   - if a true reconstruction opportunity appears, it must be surfaced explicitly before implementation

4. Export commands remain outside the main user-facing flow during this phase:
   - no return of visual CSV/PDF commands to the main operational pages
   - backend export infrastructure stays intact

5. The active source of direction is:
   - `docs/experience/front-display-wall.md`
   - `docs/experience/layout-decision-guide.md`
   - `.specs/codebase/CONVENTIONS.md`
   - `.specs/codebase/CONCERNS.md`
   - `.specs/features/front-display-wall-refinement/corda-plan.md`

6. The next mountain is not "make it fancy".
   It is:
   - reduce visible debt in deep operational surfaces
   - improve hierarchy and calm in dense work areas
   - strengthen trust in financial and student editing flows

## Assumptions Accepted For Planning

1. This is a medium-to-large refinement, not a quick fix.
2. The structural shell and routing are stable enough for local UI/UX hardening.
3. The highest remaining UX debt now sits in:
   - `templates/catalog/student-form.html`
   - `templates/includes/catalog/student_form/financial/*`
   - `templates/includes/catalog/finance/views/movements.html`
   - `templates/includes/catalog/finance/boards/portfolio_board.html`
4. The main risk is not missing features; it is deep operational surfaces still feeling older than the refined facade.
