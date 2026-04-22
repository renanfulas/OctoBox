# Architecture Docs Routing Map

Use this file to choose the smallest set of project docs needed for the task.

## Core route

Read these first for almost every architecture task:

1. `README.md`
2. `docs/reference/documentation-authority-map.md`
3. `docs/architecture/octobox-architecture-model.md`
4. `docs/architecture/architecture-growth-plan.md`
5. `docs/reference/personal-architecture-framework.md`

## If the task is about conceptual boundaries

Read:

1. `docs/architecture/octobox-conceptual-core.md`
2. `docs/architecture/center-layer.md`
3. `docs/architecture/signal-mesh.md`

Use when:

- defining domain boundaries
- deciding public facades
- separating entrypoints from core behavior
- discussing what belongs in the center vs the edge

## If the task is about Django decoupling or long-term evolution

Read:

1. `docs/architecture/django-core-strategy.md`
2. `docs/architecture/django-decoupling-blueprint.md`
3. `docs/architecture/boxcore-model-state-plan.md`

Use when:

- planning extractions
- isolating legacy coupling
- deciding what should stay in Django and what should move out

## If the task is about mobile, API, or external contracts

Read:

1. `docs/architecture/architecture-growth-plan.md`
2. `docs/plans/octobox-mobile-screen-blueprint.md`
3. `docs/reference/reading-guide.md`

Use when:

- defining API contracts
- planning payload stability
- preparing mobile-facing boundaries

## If the task is about ML, scoring, or operational intelligence

Read:

1. `docs/architecture/operational-intelligence-ml-layer.md`
2. `docs/architecture/finance-churn-ml-foundation.md`

Use when:

- adding predictions
- adding recommendation systems
- deciding where intelligence can live without corrupting transactional truth

## If the task is about front-end architecture and visible system shape

Read:

1. `docs/experience/front-display-wall.md`
2. `docs/plans/front-end-restructuring-guide.md`
3. `docs/plans/catalog-page-payload-presenter-blueprint.md`

Use when:

- defining presenter or page-payload contracts
- separating UI composition from domain logic
- deciding what should be stable at the presentation boundary

## If the task is about production risk and platform hardening

Read:

1. `docs/reference/production-security-baseline.md`
2. `docs/reference/external-security-edge-playbook.md`
3. `docs/reference/cloudflare-edge-rules.md`

Use when:

- reviewing attack surface
- deciding trust boundaries
- introducing edge controls, throttling, or safe rollout posture

## Rule of restraint

- prefer one canonical doc over five overlapping docs
- do not load historical docs unless the question is explicitly historical
- when in doubt, prefer the highest-authority architecture doc plus runtime evidence
