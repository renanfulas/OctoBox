<!--
FILE: main public overview of the project.

WHY IT EXISTS:
- Explains the product, its architecture, execution flow, and onboarding path for anyone entering the repository.

WHAT THIS FILE DOES:
1. Summarizes the current functional scope.
2. Explains the project structure.
3. Documents local execution and deploy/staging paths.

DOCUMENT TYPE:
- institutional and strategic entry point

AUTHORITY:
- high for general repository context

PARENT DOCUMENT:
- none; this is the public starting point of the repository

WHEN TO USE:
- when the question is what the product is, what the main direction is, and which document to open first

CRITICAL POINTS:
- This file must stay aligned with the product reality so it does not sell a false version of the system.
- This file must not become a detailed debugging guide or an exhaustive code map.
-->

# OctoBox Control

Official README in English. The Portuguese version is available as an annex in [README.pt-BR.md](README.pt-BR.md).

OctoBox is an operational hub for boxes and gyms that need to move beyond improvised WhatsApp workflows, spreadsheets, and an admin surface that is too raw for day-to-day reality.

## Visual Preview

Below are glimpses of OctoBox's modern interface.

<p align="center">
  <img src="docs/screenshots/dashboard-dark.png" width="48%" alt="Dashboard Dark" />
  <img src="docs/screenshots/dashboard-light.png" width="48%" alt="Dashboard Light" />
</p>

<p align="center">
  <img src="docs/screenshots/class-grid-dark.png" width="48%" alt="Class Grid" />
  <img src="docs/screenshots/students-list-dark.png" width="48%" alt="Student Management" />
</p>

## The problem OctoBox solves

In practice, many boxes grow with fragmented operations: leads in WhatsApp, students in spreadsheets, billing in manual controls, scheduling in team memory, and management decisions without trustworthy visibility. The result is usually rework, lost commercial opportunities, financial delays, follow-up failures, and a routine that depends too much on whoever happens to be serving at the moment.

## The solution proposed by the project

OctoBox was designed to concentrate that operation into a single, clear, and day-to-day usable flow. It connects students, intake, plans, enrollments, billing, class scheduling, attendance, auditing, and management visibility in an operational base that is simple to navigate. The project's proposal is to turn scattered routine into a visible, traceable, and actionable process for reception, management, coaches, and owners.

## Execution milestone

The first functional milestone of the project was delivered in less than 24 hours.

Timeline of this first cycle:

1. project started on 2026-03-10
2. main functional milestone reached on 2026-03-11
3. first version ready for operation, with a validated functional base and future evolution focused on new features, refinements, and improvements

## Current scope

- student base with legacy primary phone, but WhatsApp channel identity already hardened through a searchable blind index
- intake center for leads and provisional entries before definitive registration, with structured payloads for future traceability
- lightweight student registration and edit flow with intake conversion
- immediate connection between student, plan, enrollment, and initial billing
- one-time, installment, or recurring billing from the student record
- direct actions in the student record to update billing, mark payment, cancel, refund, regenerate, and reactivate enrollment
- visual finance center with filters by time window, plan, status, and method
- shell navigation and operational shortcuts consolidated through a central route contract
- initial dashboard for fast operational reading
- classes, attendance, check-in, check-out, absences, and operational incidents
- built-in authentication with owner, dev, manager, reception, and coach roles
- role-filtered navigation
- audit trail for login, logout, admin changes, and sensitive product actions

## Current operational state

- recent hardening wave already landed on `main`
- WhatsApp identity contract with blind index, historical backfill, and uniqueness constraint
- shell navigation contract stabilized across the core surfaces
- visual student and finance flows updated and protected by catalog and finance tests
- CI workflow for performance and integrity already tracks migrate, fixture loading, and a supported PostgreSQL baseline
- admin hardened with a configurable private path and centralized role gate
- scope-based throttling active for login, admin, writes, exports, dashboard, heavy reads, and autocomplete
- optional shared cache through Redis, with local fallback and safe degradation when external cache fails
- presenters and page payloads consolidated across the main dashboard, catalog, guide, and operations surfaces

## How to use the documentation

Use the docs by question level:

1. this README explains the product, current state, and overall direction
2. [docs/reference/documentation-authority-map.md](docs/reference/documentation-authority-map.md) tells you which doc wins when there is conflict, age, or ambiguity
3. docs in [docs/architecture](docs/architecture) define the thesis, principles, and structural direction
4. docs in [docs/plans](docs/plans) define active fronts and execution order
5. [docs/reference/reading-guide.md](docs/reference/reading-guide.md) is for navigating the code and debugging the codebase, not for defining product direction
6. docs in [docs/rollout](docs/rollout) are for release, staging, and field operations

## OctoBox governance

The project uses three governance rails so it does not become a construction site where each person is looking at a different map:

1. documentation and precedence: [docs/reference/documentation-authority-map.md](docs/reference/documentation-authority-map.md)
2. technical conventions and C.O.R.D.A.: [.specs/codebase/CONVENTIONS.md](.specs/codebase/CONVENTIONS.md)
3. technical runtime reading: [docs/reference/reading-guide.md](docs/reference/reading-guide.md)

Practical translation:

1. `C.O.R.D.A.` means `Context`, `Objective`, `Risks`, `Direction`, and `Actions`
2. use this framework when we are closing beta, prioritizing UX, or deciding between polish and structural correction
3. first we align the ground, then we choose the route; this avoids putting varnish on a door that still does not close properly

## Quick product reading

Today the system has three main layers:

1. role-based operations
2. visual catalog for students and finance
3. admin back office and auditing

Important for the current technical reading:

1. `boxcore` should no longer be read as the center of the runtime
2. it remains in the project as a legacy Django state app
3. the current runtime should prefer real apps such as `access`, `catalog`, `operations`, `students`, `finance`, `auditing`, `communications`, `api`, `integrations`, and `jobs`

In the areas with the highest rule density, the codebase was organized more explicitly:

1. domain-based HTTP views
2. read queries and snapshots
3. business rule actions and workflows

This README stops at the institutional and strategic layer. To navigate file by file, reading sequence, bug hotspots, and runtime technical boundaries, use [docs/reference/reading-guide.md](docs/reference/reading-guide.md).

If you want to study the codebase in pedagogical order, use [docs/reference/reading-guide.md](docs/reference/reading-guide.md).

If you want to understand how the project's CSS should be organized, expanded, and debugged without turning into accumulated patchwork, use [docs/experience/css-guide.md](docs/experience/css-guide.md).

If a visual change appears in `static/` but does not show up in the UI, audit static drift before assuming the CSS is wrong:

1. run `.\.venv\Scripts\python.exe .\manage.py check_static_drift --strict`
2. if drift is detected, run `.\.venv\Scripts\python.exe .\manage.py collectstatic --noinput`
3. for fast local mirroring, use `.\.venv\Scripts\python.exe .\manage.py sync_runtime_assets --collectstatic`

If you want to understand the official visual theme of the product, which aesthetic language wins when there is conflict, and how OctoBox defines its Futuristic Luxury 2050 signature, use [docs/architecture/themeOctoBox.md](docs/architecture/themeOctoBox.md).

If you want to understand specifically what still holds historical state inside `boxcore`, use [docs/architecture/boxcore-model-state-plan.md](docs/architecture/boxcore-model-state-plan.md) and [docs/architecture/boxcore-state-residue-inventory.md](docs/architecture/boxcore-state-residue-inventory.md).

If you want to understand the technical direction for growing without losing simplicity, use [docs/architecture/architecture-growth-plan.md](docs/architecture/architecture-growth-plan.md).

If you want to understand where operational intelligence, scoring, prediction, and ML belong in the architecture without contaminating the transactional core, use [docs/architecture/operational-intelligence-ml-layer.md](docs/architecture/operational-intelligence-ml-layer.md).

If you want to understand the specific strategy for making the business stop depending on Django as the core, use [docs/architecture/django-core-strategy.md](docs/architecture/django-core-strategy.md) and [docs/architecture/django-decoupling-blueprint.md](docs/architecture/django-decoupling-blueprint.md).

If you want to understand the official declaration of what becomes the conceptual center of the system, use [docs/architecture/octobox-conceptual-core.md](docs/architecture/octobox-conceptual-core.md).

If you want to understand the new architectural CENTER that separates access level and internal core, use [docs/architecture/center-layer.md](docs/architecture/center-layer.md).

If you want to understand the complementary structure of signals, integrations, and cross-system expansion, use [docs/architecture/signal-mesh.md](docs/architecture/signal-mesh.md).

If you want to understand how the architecture treats temporary construction supports without confusing them with the final structure, use [docs/architecture/scaffold-agents.md](docs/architecture/scaffold-agents.md).

If you want to understand the large front display wall of the product, where the visible experience must stay clean even with side construction and architectural transition, use [docs/experience/front-display-wall.md](docs/experience/front-display-wall.md).

If you want the practical implementation order for the official visual theme, including risk, checklist, and acceptance criteria, use [docs/plans/theme-implementation-final.md](docs/plans/theme-implementation-final.md).

If you want the official plan for reorganizing the front end in alignment with the Front Display Wall, with clear screen contracts and future fit into the Django decoupling movement, use [docs/plans/front-end-restructuring-guide.md](docs/plans/front-end-restructuring-guide.md).

If you want the specific catalog blueprint to standardize `page payload` and `presenter` in students, records, finance, plans, and class grid, use [docs/plans/catalog-page-payload-presenter-blueprint.md](docs/plans/catalog-page-payload-presenter-blueprint.md).

If you want the official step-by-step guide for thinking through, assembling, and validating site layouts while keeping priority, pending work, and next action as structural criteria, use [docs/experience/layout-decision-guide.md](docs/experience/layout-decision-guide.md).

If you want to understand the plan for the new Reception module, its functional boundary, current cost versus future cost, and why this area was reinterpreted as the visible triumph of the construction, use [docs/plans/reception-module-plan.md](docs/plans/reception-module-plan.md).

If you want to understand the official direction of the product's second floor for the mobile app, its visual cleanliness rule, its essential navigation, and the thesis for how OctoBox should become a favorite in people's hands, use [docs/experience/octobox-mobile-guide.md](docs/experience/octobox-mobile-guide.md).

If you want the translation of that direction into concrete screens, prototyping order, and mobile app navigation hierarchy, use [docs/plans/octobox-mobile-screen-blueprint.md](docs/plans/octobox-mobile-screen-blueprint.md).

If you want to understand the upper layer of visible emission and trustworthy signaling of system state, use [docs/architecture/red-beacon.md](docs/architecture/red-beacon.md).

If you want to understand the maximum alert escalation and the defensive posture shift of the building, use [docs/architecture/vertical-sky-beam.md](docs/architecture/vertical-sky-beam.md) and [docs/architecture/alert-siren.md](docs/architecture/alert-siren.md).

If you want the operational security baseline for deploys, throttles, trusted proxies, and an initial blocklist criterion without guesswork, use [docs/reference/production-security-baseline.md](docs/reference/production-security-baseline.md) and [docs/reference/external-security-edge-playbook.md](docs/reference/external-security-edge-playbook.md).

If you want the direct translation of that into Cloudflare rules and a locked-down admin posture, use [docs/reference/cloudflare-edge-rules.md](docs/reference/cloudflare-edge-rules.md).

If you want a consolidated view of the entire architectural building in a single document, use [docs/architecture/octobox-architecture-model.md](docs/architecture/octobox-architecture-model.md).

This structure is also now defined as elastic, with a fixed baseline, controlled expansion, and safe return to the basal state whenever there is structural risk.

If you want to study the architectural criteria behind the decisions, reapply this method in other projects, and learn the terms in plain language, use [docs/reference/personal-architecture-framework.md](docs/reference/personal-architecture-framework.md), [docs/reference/architecture-terms-glossary.md](docs/reference/architecture-terms-glossary.md), and [docs/reference/personal-growth-roadmap.md](docs/reference/personal-growth-roadmap.md).

If you want to understand the reasoning behind the first delivery, the decisions taken, and what I learned during the process, see [docs/history/v1-retrospective.md](docs/history/v1-retrospective.md).

## Project map

```text
boxcore/
|-- access/
|   |-- context_processors.py    -> builds sidebar and global context by role
|   |-- roles/                   -> rules and capabilities for owner, dev, manager, and coach
|   |-- urls.py                  -> login, logout, access, and system entry
|   `-- views.py                 -> access pages and role views
|-- auditing/
|   |-- __init__.py              -> auditing entry point
|   `-- services.py              -> records sensitive events in a standardized way
|-- admin/
|   |-- audit.py                 -> audit trail admin
|   |-- finance.py               -> plans, enrollments, and payments admin
|   |-- onboarding.py            -> intake center admin
|   |-- operations.py            -> operational admin
|   |-- students.py              -> student admin
|   `-- __init__.py              -> registers everything in Django admin
|-- catalog/
|   |-- forms.py                 -> lightweight forms for students, finance, and class grid
|   |-- student_queries.py       -> student area snapshots and reads
|   |-- finance_queries.py       -> finance area snapshots and reads
|   |-- class_grid_queries.py    -> class grid reads
|   |-- urls.py                  -> visual catalog screen routes
|   |-- views/
|   |   |-- catalog_base_views.py -> shared catalog HTTP base
|   |   |-- student_views.py      -> directory, lightweight registration, and student record
|   |   |-- finance_views.py      -> visual finance, plans, and communications
|   |   `-- class_grid_views.py   -> visual class grid
|   `-- services/
|       |-- student_workflows.py             -> lightweight student creation and edit flow
|       |-- student_enrollment_actions.py    -> enrollment actions in the student record
|       |-- student_payment_actions.py       -> billing actions in the student record
|       |-- finance_communication_actions.py -> finance communication and follow-up
|       |-- membership_plan_workflows.py     -> plan creation and editing
|       |-- class_schedule_workflows.py      -> recurring creation and class grid limits
|       |-- class_grid_commands.py           -> operational commands for the class grid
|       |-- class_grid_dispatcher.py         -> form_kind and class grid action dispatcher
|       |-- class_grid_policy.py             -> class grid edit and deletion rules
|       |-- class_grid_messages.py           -> centralized operational messages for the class grid
|       `-- operational_queue.py             -> operational queue and retention metrics
|-- dashboard/
|   |-- dashboard_snapshot_queries.py -> consolidated main panel snapshot
|   |-- dashboard_views.py            -> panel HTTP layer
|   |-- urls.py                  -> panel routes
|   `-- __init__.py              -> dashboard package marker
|-- guide/
|   |-- urls.py                  -> internal system map route
|   `-- views.py                 -> pedagogical context for the visual map
|-- management/commands/
|   |-- bootstrap_roles.py       -> creates access groups
|   `-- import_students_csv.py   -> imports students by CSV using WhatsApp as the key
|-- models/
|   |-- audit.py                 -> audit events and traceability
|   |-- base.py                  -> shared base classes
|   |-- communications.py        -> contact base and WhatsApp logs
|   |-- finance.py               -> plans, enrollments, and payments
|   |-- onboarding.py            -> intake and provisional entry
|   |-- operations.py            -> classes, attendance, and incidents
|   |-- students.py              -> students and registration data
|   `-- __init__.py              -> exports app models
|-- operations/
|   |-- workspace_snapshot_queries.py -> operational area snapshots by role
|   |-- base_views.py                -> shared operations HTTP base
|   |-- workspace_views.py           -> owner, dev, manager, and coach workspaces
|   |-- action_views.py              -> mutable operation endpoints
|   |-- actions.py                   -> operational action handlers
|   |-- urls.py                  -> operational area routes by role
|   `-- __init__.py              -> operational package marker
`-- tests/
	|-- test_access.py           -> login and roles
	|-- test_catalog.py          -> students, billing, enrollments, and visual class grid
	|-- test_catalog_services.py -> catalog services and workflows
	|-- test_dashboard.py        -> main panel
	|-- test_finance.py          -> visual finance center
	|-- test_guide.py            -> system map
	|-- test_import_students.py  -> CSV import
	|-- test_operations_services.py -> operation handlers and services
	`-- test_operations.py       -> role-based operation

templates/
|-- access/                      -> login and access views
|-- catalog/                     -> students, student form, finance, class grid, and plan editing
|-- dashboard/                   -> main panel
|-- guide/                       -> visual system map
|-- layouts/                     -> base layout and global navigation
`-- operations/                  -> operational screens by role
```

## Most important visual routes

- /dashboard/ -> operation summary
- /alunos/ -> main student base, funnel, and commercial search
- /alunos/novo/ -> lightweight student creation with plan and billing
- /alunos/<id>/editar/ -> commercial student record
- /financeiro/ -> management view of plans, revenue, churn, and finance queue
- /grade-aulas/ -> visual class grid

## Technical boundaries already opened for growth

- /api/ -> official entry point of the product API
- /api/v1/ -> first version API manifesto
- /api/v1/health/ -> basic health for the external boundary
- channel identity already prefers explicit WhatsApp contact and external provider id before the legacy phone fallback
- intake payloads and message logs are now stored as sanitized JSON, with limits and sensitive key masking

## What the class grid delivers today

The [templates/catalog/class-grid.html](templates/catalog/class-grid.html) screen already works as an operational scheduling hub outside the admin.

Today it delivers:

1. today's schedule with coach, time, status, and occupancy reading
2. the next two weeks calendar with quick access to editing
3. compact monthly view and expanded calendar
4. recurring planner with time sequences and blocking by daily, weekly, and monthly limits
5. quick class editing with protection against improper reopening and deletion with history
6. visual indicators for capacity and real-time state during class execution

## Comment and header convention

## License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0). See [LICENSE](LICENSE).

Every relevant file should quickly explain its role at the top.

Markdown files use HTML comments. Python files use docstrings in the same format. The full reference is [docs/reference/new-file-template.md](docs/reference/new-file-template.md).

Standard for Python files:

```python
"""
FILE: file name and general purpose.

WHY IT EXISTS:
- reason why the file exists in the project.

WHAT THIS FILE DOES:
1. main block 1
2. main block 2
3. main block 3

CRITICAL POINTS:
- what is risky to touch
- what can break if changed carelessly
"""
```

Standard for HTML templates:

```html
<!--
FILE: template name and general purpose.

WHY IT EXISTS:
- reason why the template exists.

WHAT THIS FILE DOES:
1. main block 1
2. main block 2
3. main block 3
 
CRITICAL POINTS:
- what is risky to touch
- what can break if changed carelessly
-->
```

Standard for Markdown files:

```html
<!--
FILE: file name and general purpose.

WHY IT EXISTS:
- reason why the document exists.

WHAT THIS FILE DOES:
1. gives context about the system area.
2. guides reading, maintenance, or operation.
3. records risks and cautions for whoever edits it.

CRITICAL POINTS:
- keep it aligned with the real project structure.
- always review when files or flows are renamed.
-->
```

## Current system roles

- owner: strategic view of the box and maximum business access
- dev: technical maintenance, inspection, support, and controlled auditing
- manager: administrative, commercial, finance, and student operations
- reception: front desk, scheduling, intake, and short-cycle billing inside the operational flow
- coach: technical class routine, attendance, and follow-up

The command to prepare the base groups is:

```bash
python manage.py bootstrap_roles
```

## How to run

1. Create and activate the virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and adjust the minimum required values.
4. Run `python manage.py migrate`.
5. Run `python manage.py bootstrap_roles`.
6. Create an administrative user with `python manage.py createsuperuser`.
7. Start the server with `python manage.py runserver`.
8. Run `python manage.py test` to automatically use the project's test configuration path.

Notes:

- login, logout, admin changes, and sensitive commercial actions already feed the audit trail
- for local environments, the project automatically reads `.env` when it exists
- `python manage.py test` prefers `config.settings.test` and also accepts a local `.env.test` as an optional complement
- for local environments, you can define `DJANGO_SECRET_KEY` in a `.env` file or in system variables
- for environments that use WhatsApp channel identity, also define `PHONE_BLIND_INDEX_KEY`
- the project now accepts `DJANGO_ENV=development` or `DJANGO_ENV=production` to separate local configuration from staging/production
- for staging/production, the recommended path is using `DATABASE_URL` with PostgreSQL, `REDIS_URL` for shared cache, running `collectstatic`, and publishing behind HTTPS
- the public admin path must be defined by `DJANGO_ADMIN_URL_PATH`, not by `/admin/`
- to expose the server on the local network, use the `Run Django Server (LAN)` task or run `python manage.py runserver 0.0.0.0:8000`
- for CI or staging with PostgreSQL, use Postgres 14 or newer

New guides:

- staging deploy: [docs/rollout/deploy-homologation.md](docs/rollout/deploy-homologation.md)
- minimum database backup: [docs/rollout/backup-guide.md](docs/rollout/backup-guide.md)
- production security baseline: [docs/reference/production-security-baseline.md](docs/reference/production-security-baseline.md)
- real mobile validation checklist: [docs/experience/mobile-real-validation-checklist.md](docs/experience/mobile-real-validation-checklist.md)
- backup scripts: [scripts/backup_sqlite.ps1](scripts/backup_sqlite.ps1) and [scripts/backup_postgres.ps1](scripts/backup_postgres.ps1)

## Initial student import

The project includes a command to import students by CSV using WhatsApp as the deduplication key.

Supported columns:

- full_name
- whatsapp or phone
- email
- gender
- birth_date in YYYY-MM-DD format
- health_issue_status
- cpf
- status
- notes

Execution:

```bash
python manage.py import_students_csv path/to/students.csv
```

## Ideas that may be smart next steps

- add export for financial and commercial reports
- deepen the recurring follow-up and renegotiation layer
- expand auditing for role-based operational review
- prepare future integrations with WhatsApp, physical assessment, and external billing
