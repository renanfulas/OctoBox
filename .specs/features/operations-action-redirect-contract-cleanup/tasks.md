# Operations Action Redirect Contract Cleanup Tasks

**Design**: `.specs/features/operations-action-redirect-contract-cleanup/design.md`  
**Status**: Completed

## Tasks

### T1: Map Live Fallback Redirects [Done]

Confirm every live handwritten fallback in `operations/action_views.py`.

### T2: Canonicalize Manager Redirects [Done]

Replace handwritten manager fallbacks with named routes.

### T3: Canonicalize Coach Redirects [Done]

Replace handwritten coach fallbacks with named routes.

### T4: Validate Redirect Contract [Done]

Check that referer-first behavior, fragments, and role return semantics remain intact.
