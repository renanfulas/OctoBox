---
name: octobox-ui-cleanup-auditor
description: Forensic CSS/HTML cleanup and safe front-end refactoring for OctoBOX. Use when Codex needs to audit UI debt, map template-to-include-to-CSS-to-JS-to-payload ownership, find override hotspots, detect !important or inline styles, classify legacy UI rules, investigate unused or duplicated selectors, or plan safe cleanup/refactors in Django templates and static CSS. Trigger on requests like limpar CSS, achar overrides, regras inutilizadas, codigo morto, refatorar HTML/CSS, unused selectors, override hotspots, legacy UI cleanup, or front-end forensic audit.
---

# OctoBox UI Cleanup Auditor

Audit the OctoBOX front-end like a building inspector before demolition.

Default to `audit-first`: map the structure, trace the active wires, classify what is live or dead, and only then propose cleanup or refactoring.

## Read Order

Read these sources in order before proposing cleanup:

1. `README.md`
2. `docs/reference/documentation-authority-map.md`
3. `docs/plans/front-end-restructuring-guide.md`
4. `docs/experience/css-guide.md`
5. `docs/reference/front-end-ownership-map.md`
6. `docs/reference/design-system-contract.md`
7. `docs/architecture/themeOctoBox.md` when the task can affect theme, atmosphere, or premium scope
8. `docs/plans/front-legacy-rule-retirement-sdd.md`
9. `docs/plans/front-legacy-rule-retirement-wave1-inventory.md`
10. `.agents/skills/css_front_end_architect/SKILL.md`
11. `.agents/GHOST_AUDIT.md`
12. `.agents/scripts/ghost_audit.py`

Then load only the reference file that fits the job:

- `references/docs-routing-map.md` for doc order and routing
- `references/legacy-patterns-map.md` for legacy families, protected aliases, and hotspots
- `references/finding-taxonomy.md` for classification, risk, and recommended action

If the audit may be contaminated by duplicate trees, mirror roots, or collected static output, also read:

- `docs/map/front-end-runtime-boundary-map.md`

If the task mentions KPI clicks, `data_action`, shell reactions, sidebar blink, topbar alert, board highlight, or "clicked and nothing happened", also read:

- `docs/map/front-end-dashboard-action-contract-map.md`
- `docs/map/front-end-neon-contract-map.md`
- `docs/map/front-end-data-action-debug-checklist.md`

## Default Workflow

### 1. Map ownership first

Identify the real owner of the surface before touching code:

1. route or view
2. page payload or presenter
3. template
4. include chain
5. local CSS
6. page JS
7. shared design-system or catalog layer

If a prompt mentions an older doc path, verify the live path in the repo before trusting it.

### 2. Trace the rendering chain

Follow this chain explicitly:

1. `template -> include -> CSS -> JS -> payload`
2. list which files are truly loaded by the page
3. separate local semantics from shared primitives
4. record where the page is inheriting behavior by accident instead of contract

### 3. Run forensics before cleanup

Use `scripts/frontend_forensics.py` for the first pass when the task is about visual debt, overrides, dead code, or legacy CSS.

Example:

```powershell
py .agents\skills\octobox-ui-cleanup-auditor\scripts\frontend_forensics.py --base-path . --report "$env:TEMP\octobox-frontend-forensics.json"
```

Use the script output as evidence, not as final truth.

By default, the scanner should reflect the active runtime tree. Only include mirror trees such as `OctoBox/` when the task explicitly asks for drift archaeology.

### 3A. Debug `data_action` before touching visuals

When the issue is "clicked and nothing reacted" or any KPI-to-shell interaction feels broken, do this before changing CSS:

1. prove the payload still emits `data_action`
2. prove the template still exposes `data-action`
3. prove `shell.js` still listens to the matching action family
4. prove the target still exists with the expected selector
5. prove the CSS still recognizes the temporary class applied by the shell

Use `docs/map/front-end-data-action-debug-checklist.md` as mandatory ritual for these cases.

Translate action families like this:

1. `blink-topbar-foo` -> look for `[data-ui="topbar-foo-alert"]`
2. `blink-board-foo` -> look for `#dashboard-foo-board`
3. `blink-sidebar-foo` -> look for `a[data-nav-key="foo"]`

For sidebar cases, treat `docs/map/front-end-neon-contract-map.md` as the contract of truth before proposing visual changes.

### 4. Classify findings

Use the taxonomy in `references/finding-taxonomy.md` and classify each finding as one of:

- `dead`
- `candidate-unused`
- `override-hotspot`
- `legacy-bridge`
- `duplicate-rule`
- `structural-do-not-touch`
- `canonical-alias`
- `mirror-tree-only`

Always attach evidence:

1. file path
2. selector, class, or block involved
3. why it was classified that way
4. safest next action

### 5. Propose the safest cleanup path

Default to this order:

1. isolate ownership
2. move authority to the canonical layer
3. downgrade legacy bridges
4. remove only what has evidence of non-use

Only refactor on the first pass when the user explicitly asks for execution or the path is already proven safe.

## Guardrails

### Treat runtime as truth

Docs are maps. Runtime and actual file loading are the terrain.

If docs and code diverge, trust the real loading path and note the doc drift.

### Do not delete on grep alone

Never delete CSS because one search looks empty.

Before removing a rule, cross-check:

1. templates
2. JS selectors
3. Python payload strings
4. page-specific asset loading
5. legacy bridge docs

If proof is incomplete, classify as `candidate-unused`, not `dead`.

### Protect canonized aliases

Do not classify `note-panel*` or `legacy-copy*` as dead by default.

These may look old by name, but they are documented as active or protected aliases in the current system.

### Prefer the canonical ladder

When moving or replacing style authority, prefer:

1. token
2. canonical primitive
3. local semantic class
4. neutral helper

Never invert this ladder just to win specificity quickly.

### Avoid authority fights

Treat these as smell indicators:

1. `!important`
2. inline `style=""`
3. `<style>` blocks in templates
4. duplicated selectors in multiple files
5. local files redefining canonical surfaces
6. helpers turning into a second design system
7. `data_action` contracts being "fixed" with CSS instead of by restoring payload, shell, or target alignment

### Respect visual scope

If cleanup can alter theme signature, glow discipline, hero hierarchy, card authority, or premium scope, read `docs/architecture/themeOctoBox.md` before proposing changes.

## Delivery Pattern

When reporting findings, use this order:

1. what owns the surface
2. what is actually loaded
3. highest-risk findings first
4. what can be removed now
5. what must be migrated before deletion
6. what must not be touched yet

If the task involves interactive KPI behavior or `data_action`, add this checkpoint explicitly:

1. where the command was emitted
2. where it was exposed in HTML
3. where the shell resolved the target
4. where the visual class was applied
5. which layer actually broke

Keep the first pass evidence-heavy and action-light.

The goal is not to "make CSS smaller" by reflex.

The goal is to remove fake authority, preserve real authority, and leave the front-end easier to reason about.
