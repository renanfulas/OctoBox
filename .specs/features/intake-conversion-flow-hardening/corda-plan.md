# C.O.R.D.A.

**Status**: Approved

## Contexto

The OctoBox already hardened the canonical theme, shared metric cards, and the reception workspace. The next strongest ROI is the intake conversion flow because it sits at the intersection of:

1. commercial conversion
2. student creation
3. operational speed
4. onboarding confidence

Today that flow still mixes structural debt and live business behavior in the same surface.

## Objetivo

Harden the intake conversion flow so it becomes:

1. easier to maintain
2. safer to evolve
3. cleaner in HTML/JS responsibility boundaries
4. aligned with named-route and canonical front-end discipline

## Riscos

1. breaking the express conversion path while trying to clean the markup
2. moving behavior out of the template but losing the current low-friction flow
3. cleaning the queue handoff but leaving the presenter building URLs manually
4. over-expanding this mountain into a full onboarding redesign

## Direcao

Treat this as a hardening pass, not a redesign.

The correct order is:

1. prove the live runtime path
2. define the new event contract
3. move inline behavior into the asset layer
4. normalize the conversion links and payload generation
5. validate that the business flow still feels fast

## Acoes

### Wave 1: Evidence

1. map where conversion starts
2. map how plan selection and payment selection are triggered
3. map how the presenter currently builds conversion URLs

### Wave 2: Behavior Extraction

1. remove inline `onclick`
2. move interaction hooks into `conversion_drawer.js`
3. reduce `window` surface as much as the current runtime allows

### Wave 3: Route Canonicalization

1. replace hardcoded conversion links in templates
2. normalize conversion href generation in `onboarding/presentation.py`

### Wave 4: Validation

1. verify the queue handoff still opens the right student form
2. verify express conversion still supports the expected payment paths
3. run `manage.py check`
