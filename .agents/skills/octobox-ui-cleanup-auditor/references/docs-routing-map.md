# Docs Routing Map

Use this map to decide what to read before touching CSS or templates.

## Always Start Here

Read in this base order:

1. `README.md`
2. `docs/reference/documentation-authority-map.md`
3. `docs/plans/front-end-restructuring-guide.md`
4. `docs/experience/css-guide.md`
5. `docs/reference/front-end-ownership-map.md`
6. `docs/reference/design-system-contract.md`

This base stack answers:

1. what the product is
2. which doc wins when guidance conflicts
3. how the front should be structured now
4. where CSS should live
5. who owns the screen
6. which shared layer should carry the change

## If The Problem Is Theme Or Visual Authority

Add:

1. `docs/architecture/themeOctoBox.md`

Use it when the change can affect:

1. palette
2. glow discipline
3. hero hierarchy
4. card authority
5. premium scope

## If The Problem Is Legacy CSS Or Safe Deletion

Add:

1. `docs/plans/front-legacy-rule-retirement-sdd.md`
2. `docs/plans/front-legacy-rule-retirement-wave1-inventory.md`

Use them when the task is about:

1. old class families
2. transition aliases
3. rule retirement
4. safe removal sequencing

## If The Problem Is Screen Ownership

Prioritize:

1. `docs/reference/front-end-ownership-map.md`
2. the screen template
3. the view or presenter
4. the page CSS
5. the page JS

This is the shortest reliable chain for:

1. override tracing
2. "where should this class live?"
3. "why is this surface inheriting from the wrong layer?"

## If The Problem Is Overrides Or Smell Detection

Add:

1. `.agents/GHOST_AUDIT.md`
2. `.agents/scripts/ghost_audit.py`
3. `scripts/frontend_forensics.py`

Use these as scanners and heuristics, not as final authority.

## Legacy Interpretation Rule

Some older skill text or notes may reference `docs/map/*`.

Before trusting the path:

1. verify whether the file exists in `docs/reference/*`
2. verify whether the file exists in `docs/map/*`
3. use the live file that matches the current repo
4. if both exist, prefer the one that the active README and current docs chain point to

## Fast Routing By User Request

If the user asks to:

- `limpar CSS`
  Read the base stack, then the legacy retirement docs, then run the scanner.

- `achar overrides`
  Read the base stack, ownership map, design-system contract, then run the scanner.

- `refatorar HTML/CSS`
  Read the base stack, ownership map, then trace `template -> include -> CSS -> JS -> payload`.

- `unused selectors`
  Read the base stack, legacy retirement docs, then run the scanner and classify as `candidate-unused` until proven dead.

- `legacy UI cleanup`
  Read the base stack, theme guide if visuals are involved, then the retirement docs and scanner output.
