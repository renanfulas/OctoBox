"""
ARQUIVO: endpoints HTTP de aplicação de template por dia.

POR QUE ELE EXISTE:
- separa as rotas de day-apply do workout_planner_views.py já populado,
  seguindo o padrão de um módulo por aspecto do corredor WOD.

O QUE ESTE ARQUIVO FAZ:
1. WodProgramApplyPreviewView — prepara prévia com programa explícito e intent durável.
2. WodProgramApplyConfirmView — confirma intent/fingerprint com replay idempotente.
3. WodDayApplyView — adapter legado por ClassType; retorna resumo e undo_token.
4. WodDayApplyUndoView — undo complementar dentro da janela de 60s.

PONTOS CRÍTICOS:
- retorna JSON para o client; a confirmação da UI usa intent durável, enquanto undo é temporário.
- instância única por box (single-tenant); ACL garantida pelo OperationBaseView.
- apenas roles COACH, MANAGER, OWNER podem chamar; COACH filtrado por aula própria.
"""

from django.http import JsonResponse
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

from access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER, get_user_role
from operations.forms_wod_day_apply import (
    WodDayApplyForm, WodDayApplyUndoForm,
    WodProgramApplyPreviewForm, WodProgramApplyConfirmForm,
)
from operations.services.wod_apply_intents import WodApplyConflict, prepare_program_apply, confirm_program_apply
from operations.services.wod_input_adapters import build_day_apply_preview
from operations.services.wod_day_apply_executor import execute_day_apply
from operations.services.wod_day_apply_undo import execute_undo

from .base_views import OperationBaseView


class WodDayApplyView(OperationBaseView, View):
    allowed_roles = (ROLE_COACH, ROLE_MANAGER, ROLE_OWNER)

    def post(self, request, *args, **kwargs):
        form = WodDayApplyForm(request.POST)
        if not form.is_valid():
            return JsonResponse({'ok': False, 'errors': form.errors}, status=400)

        try:
            result = execute_day_apply(
                actor=request.user,
                target_date=form.cleaned_data['target_date'],
                template_id=form.cleaned_data['template_id'],
                class_type=form.cleaned_data['class_type'],
                mode=form.cleaned_data['mode'],
            )
        except (PermissionDenied, ValidationError) as error:
            reason = error.messages[0] if isinstance(error, ValidationError) else str(error)
            return JsonResponse({'ok': False, 'reason': reason}, status=403 if isinstance(error, PermissionDenied) else 400)

        return JsonResponse({
            'ok': True,
            'applied_count': result.applied_count,
            'skipped_count': result.skipped_count,
            'undo_token': result.undo_token,
            'skipped_reasons': result.skipped_reasons,
        })


class WodDayApplyPreviewView(OperationBaseView, View):
    allowed_roles = (ROLE_COACH, ROLE_MANAGER, ROLE_OWNER)

    def post(self, request, *args, **kwargs):
        form = WodDayApplyForm(request.POST)
        if not form.is_valid():
            return JsonResponse({'ok': False, 'errors': form.errors}, status=400)
        try:
            preview = build_day_apply_preview(actor=request.user, **form.cleaned_data)
        except (PermissionDenied, ValidationError) as error:
            reason = error.messages[0] if isinstance(error, ValidationError) else str(error)
            return JsonResponse({'ok': False, 'reason': reason}, status=403 if isinstance(error, PermissionDenied) else 400)
        return JsonResponse(preview)


class WodDayApplyUndoView(OperationBaseView, View):
    allowed_roles = (ROLE_COACH, ROLE_MANAGER, ROLE_OWNER)

    def post(self, request, *args, **kwargs):
        form = WodDayApplyUndoForm(request.POST)
        if not form.is_valid():
            return JsonResponse({'ok': False, 'errors': form.errors}, status=400)

        result = execute_undo(actor=request.user, undo_token=form.cleaned_data['undo_token'])
        return JsonResponse(result)


@method_decorator(never_cache, name='dispatch')
@method_decorator(csrf_protect, name='dispatch')
class _WodProgramApplyJsonView(View):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'ok': False, 'code': 'unauthenticated'}, status=401)
        role = get_user_role(request.user)
        if role is None or role.slug not in {ROLE_COACH, ROLE_MANAGER, ROLE_OWNER}:
            return JsonResponse({'ok': False, 'code': 'forbidden'}, status=403)
        return super().dispatch(request, *args, **kwargs)


class WodProgramApplyPreviewView(_WodProgramApplyJsonView):

    def post(self, request, *args, **kwargs):
        form = WodProgramApplyPreviewForm(request.POST)
        if not form.is_valid():
            return JsonResponse({'ok': False, 'code': 'invalid_payload', 'errors': form.errors}, status=400)
        try:
            result = prepare_program_apply(actor=request.user, **form.cleaned_data)
        except (PermissionDenied, ValidationError) as error:
            reason = error.messages[0] if isinstance(error, ValidationError) else str(error)
            return JsonResponse({'ok': False, 'reason': reason}, status=403 if isinstance(error, PermissionDenied) else 400)
        response = JsonResponse(result)
        response['Cache-Control'] = 'no-store'
        return response


class WodProgramApplyConfirmView(_WodProgramApplyJsonView):

    def post(self, request, *args, **kwargs):
        form = WodProgramApplyConfirmForm(request.POST)
        if not form.is_valid():
            return JsonResponse({'ok': False, 'code': 'invalid_payload', 'errors': form.errors}, status=400)
        try:
            result = confirm_program_apply(
                actor=request.user, intent_id=form.cleaned_data['intent_id'],
                request_fingerprint=form.cleaned_data['fingerprint'],
            )
        except WodApplyConflict as error:
            return JsonResponse({'ok': False, 'code': error.code, 'reason': str(error)}, status=404 if error.code == 'not_found' else 409)
        except (PermissionDenied, ValidationError) as error:
            reason = error.messages[0] if isinstance(error, ValidationError) else str(error)
            return JsonResponse({'ok': False, 'reason': reason}, status=403 if isinstance(error, PermissionDenied) else 400)
        response = JsonResponse(result)
        response['Cache-Control'] = 'no-store'
        return response


__all__ = [
    'WodDayApplyView', 'WodDayApplyPreviewView', 'WodDayApplyUndoView',
    'WodProgramApplyPreviewView', 'WodProgramApplyConfirmView',
]
