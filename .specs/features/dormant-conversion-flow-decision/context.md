# Context

## Why This Exists

The onboarding conversion drawer has now been hardened technically, but it is still not mounted into the live intake runtime.

So the real decision is no longer:

1. can we clean it

The real decision now is:

1. should we reactivate it intentionally
2. or should we retire it cleanly and keep the direct intake-to-student path

## Locked Reality

Today the live flow is:

1. intake queue
2. canonical student quick-create route

Today the drawer is:

1. technically cleaner
2. still dormant
3. still not part of the runtime path

## Risk

Reactivating it changes conversion UX and business friction.

Retiring it closes a branch and improves clarity, but removes a future fast-lane unless we intentionally rebuild it later.

## Final Action

The drawer is now formally retired from the live code path.

That retirement includes:

1. removing the dormant template and JS
2. removing the unused express-convert API endpoint
3. renaming the live conversion handoff actions so they reflect the real quick-create flow
