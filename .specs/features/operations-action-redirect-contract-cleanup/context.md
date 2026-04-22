# Context

## Why this exists

The UI and payload layers are now much cleaner, but a small high-authority gap still remains in the live mutation layer:

- `operations/action_views.py` still sends some manager and coach flows back through handwritten fallback URLs

That is not a visual defect. It is a contract defect.

In simple terms:

- the building already uses official maps in most places
- but a few staff-only emergency exits still have handwritten arrows taped on the wall

## Runtime facts confirmed before opening this package

1. `ReceptionPaymentActionView` already uses `reverse('reception-workspace')`
2. `PaymentEnrollmentLinkView` still falls back to `'/operacao/manager/'`
3. `TechnicalBehaviorNoteCreateView` still falls back to `'/operacao/coach/'`
4. `AttendanceActionView` still falls back to `'/operacao/coach/'`
5. `_redirect_back()` already does host validation and optional fragment append correctly

## Boundaries

This package is intentionally narrow.

It does:

1. canonicalize fallback redirects in live operations actions
2. keep role-specific return behavior explicit
3. preserve existing fragments and referer-first behavior

It does not:

1. redesign the action views
2. change permission rules
3. change mutation semantics
4. reopen unrelated template cleanup

## Non-goals

1. no presenter rewrite
2. no UX redesign of manager or coach surfaces
3. no broad navigation refactor outside the affected mutation views
