# CORDA Plan

## North

Make live operational mutations return through canonical route contracts instead of handwritten fallback paths.

## Why now

This is the smallest remaining change with real structural leverage:

1. it sits in mutation code, not decorative templates
2. it affects manager and coach operational loops
3. it finishes a redirect hardening story we already completed elsewhere in reception and finance

## Risks

The risk is not visual breakage. The risk is subtle navigation drift:

1. a route rename can silently desynchronize handwritten fallback strings
2. a future maintainer may assume redirects are already canonical everywhere
3. one hardened role flow and one non-hardened role flow create inconsistent trust in the mutation layer

## Execution sequence

1. map every live fallback in `operations/action_views.py`
2. replace handwritten strings with named routes
3. validate role return semantics and fragments
4. classify any residual as intentional or debt

## Success bar

This pass is done when:

1. no live manager or coach mutation fallback depends on handwritten path strings
2. the redirect contract remains referer-first and safe
3. runtime behavior stays functionally unchanged for users
