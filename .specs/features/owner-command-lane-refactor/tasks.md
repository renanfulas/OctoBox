# Owner Command Lane Refactor Tasks

**Design**: `.specs/features/owner-command-lane-refactor/design.md`  
**Status**: In Progress

## Tasks

### T1: Save the plan in `.specs` [Done]

Create the feature package with context, C.O.R.D.A., spec, design, and tasks.

### T2: Create owner-local lane ownership [Done]

1. add local hooks and identity for the Owner lane
2. extract an Owner include for the three cards

### T3: Create an owner-local command lane CSS module [Done]

Move the Owner lane structure out of long shared selectors and into a dedicated module.

### T4: Reduce owner-local duplication [Done]

Trim duplicated structure from late refinements and keep them for finishing only.

### T5: Validate workspace integrity [Done]

Confirm:

1. owner lane still renders the same semantic actions
2. manager, coach, and reception remain stable
3. the local ownership is clearer than before
4. no safe global `cards.css` reduction was identified in this wave without cross-persona risk
