# Evidence Map

## Runtime evidence

### Live mutation file

- `operations/action_views.py`

### Confirmed handwritten fallback paths at package creation time

1. `'/operacao/manager/'`
2. `'/operacao/coach/'`

### Confirmed canonical example already present

1. `reverse('reception-workspace')`

### Confirmed named workspace routes

1. `reverse('manager-workspace')`
2. `reverse('coach-workspace')`
3. `reverse('reception-workspace')`

### Live mutation mapping

1. `PaymentEnrollmentLinkView.post()` -> now falls back through `reverse('manager-workspace')`
2. `TechnicalBehaviorNoteCreateView.post()` -> now falls back through `reverse('coach-workspace')` on validation error and success
3. `AttendanceActionView.post()` -> now falls back through `reverse('coach-workspace')` on invalid action, null result, and success
4. `_redirect_back()` already preserves referer-first semantics and optional fragment append

## Decision

This package exists because the remaining gap is narrow but high-authority:

- real mutations
- real role workspaces
- low implementation effort
- meaningful reduction in silent navigation drift

## Validation

1. no handwritten manager or coach fallback path remains in `operations/action_views.py`
2. `reverse('manager-workspace')` now backs manager mutation return flow
3. `reverse('coach-workspace')` now backs coach mutation return flows
4. `python manage.py check` passed clean after the changes

## Residual classification

1. `_redirect_back()` still accepts a resolved URL string, which is intentional and compatible with referer-first behavior
2. no further redirect debt was found in this mutation file after manager and coach cleanup
