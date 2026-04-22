# Docs Routing Map

Open only the docs needed for the database question.

## Always start here

1. `README.md`
2. `docs/reference/documentation-authority-map.md`
3. `docs/reference/reading-guide.md`

## If the topic is scale, isolation, or multitenancy

1. `docs/architecture/architecture-growth-plan.md`
2. `docs/architecture/django-core-strategy.md`
3. `docs/plans/scale-transition-20-100-open-multitenancy-plan.md`
4. `docs/plans/phase1-closed-beta-20-boxes-corda.md`
5. `docs/plans/unit-cascade-architecture-plan.md`

## If the topic is current code ownership vs historical schema

1. `docs/architecture/app-split-plan.md`
2. `docs/architecture/django-decoupling-blueprint.md`
3. `docs/architecture/promoted-public-facades-map.md`

## If the topic is rollout, backup, restore, or rollback safety

1. `docs/rollout/first-box-production-execution-checklist.md`
2. `docs/rollout/postgres-homolog-provisioning-checklist.md`
3. `docs/rollout/postgres-homolog-restore-runbook.md`
4. `docs/rollout/hostinger-vps-production-deploy.md`

## If the topic is security and sensitive data

1. `docs/reference/production-security-baseline.md`
2. `docs/reference/external-security-edge-playbook.md`
3. `docs/reference/cloudflare-edge-rules.md`

## If the topic is operational signals, queues, or read-model pressure

1. `docs/architecture/signal-mesh.md`
2. `docs/architecture/center-layer.md`
3. `docs/plans/operations-queries-and-published-history-corda.md`
4. `docs/plans/finance-ml-foundation-refactor-watch-plan.md`

## Decision rule

- docs explain intent
- model files and migrations explain persisted truth
- runtime and tests win if they disagree with docs
