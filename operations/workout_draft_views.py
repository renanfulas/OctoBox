"""Endpoints JSON finos para rascunhos de entrada do WOD."""

import json

from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

from access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER, get_user_role
from operations.services.wod_drafts import (
    DraftConflict, DraftQuota, DraftTooLarge, discard_draft, draft_payload, load_draft,
    resolve_draft_scope, save_draft,
)

DRAFT_SAVE_RATE_LIMIT_MAX = 90
DRAFT_SAVE_RATE_LIMIT_WINDOW_SECONDS = 300


def _error(exc):
    if isinstance(exc, DraftConflict):
        return JsonResponse({'ok': False, 'code': exc.code, 'current_version': exc.version}, status=409)
    if isinstance(exc, DraftQuota):
        return JsonResponse({'ok': False, 'code': 'draft_quota', 'reason': str(exc)}, status=429)
    if isinstance(exc, DraftTooLarge):
        return JsonResponse({'ok': False, 'code': 'draft_too_large', 'reason': str(exc)}, status=413)
    if isinstance(exc, Http404):
        return JsonResponse({'ok': False, 'code': 'scope_not_found'}, status=404)
    if isinstance(exc, PermissionDenied):
        return JsonResponse({'ok': False, 'code': 'forbidden'}, status=403)
    if isinstance(exc, ValidationError):
        return JsonResponse({'ok': False, 'code': 'invalid_input', 'reason': exc.messages[0]}, status=400)
    raise exc


def _scope(actor, values):
    return resolve_draft_scope(
        actor=actor, scope_kind=values.get('scope_kind'),
        session_id=values.get('session_id'), week_start=values.get('week_start'),
        workout_program_id=values.get('workout_program_id'), plan_id=values.get('plan_id'),
    )


def _too_many_saves(actor):
    key = f'wod-draft-save:{actor.pk}'
    if cache.add(key, 1, timeout=DRAFT_SAVE_RATE_LIMIT_WINDOW_SECONDS):
        return False
    try:
        return cache.incr(key) > DRAFT_SAVE_RATE_LIMIT_MAX
    except ValueError:
        cache.set(key, 2, timeout=DRAFT_SAVE_RATE_LIMIT_WINDOW_SECONDS)
        return False


@method_decorator(never_cache, name='dispatch')
@method_decorator(csrf_protect, name='dispatch')
class WodInputDraftView(View):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'ok': False, 'code': 'authentication_required'}, status=401)
        role = get_user_role(request.user)
        if role is None or role.slug not in {ROLE_COACH, ROLE_MANAGER, ROLE_OWNER}:
            return JsonResponse({'ok': False, 'code': 'forbidden'}, status=403)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        try:
            scope = _scope(request.user, request.GET)
            return JsonResponse(draft_payload(load_draft(actor=request.user, scope=scope)))
        except (DraftConflict, DraftQuota, DraftTooLarge, Http404, PermissionDenied, ValidationError) as exc:
            return _error(exc)

    def post(self, request, *args, **kwargs):
        if not request.content_type.startswith('application/json') or len(request.body) > 100_000:
            return JsonResponse({'ok': False, 'code': 'invalid_body'}, status=400)
        try:
            values = json.loads(request.body)
            if not isinstance(values, dict):
                raise ValidationError('Envie um objeto JSON.')
            scope = _scope(request.user, values)
            action = values.get('action')
            if action not in (None, 'save', 'discard'):
                raise ValidationError('Ação inválida.')
            if action != 'discard' and _too_many_saves(request.user):
                response = JsonResponse({'ok': False, 'code': 'rate_limited'}, status=429)
                response['Retry-After'] = str(DRAFT_SAVE_RATE_LIMIT_WINDOW_SECONDS)
                return response
            if action == 'discard':
                discard_draft(
                    actor=request.user, scope=scope,
                    draft_id=values.get('draft_id'), expected_version=values.get('expected_version'),
                )
                return JsonResponse({'ok': True, 'draft': None})
            draft = save_draft(
                actor=request.user, scope=scope, source_text=values.get('source_text'),
                request_id=values.get('request_id'),
                expected_version=values.get('expected_version'), draft_id=values.get('draft_id'),
            )
            return JsonResponse(draft_payload(draft))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({'ok': False, 'code': 'invalid_json'}, status=400)
        except (DraftConflict, DraftQuota, DraftTooLarge, Http404, PermissionDenied, ValidationError) as exc:
            return _error(exc)


__all__ = ['WodInputDraftView']
