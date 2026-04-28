"""
ARQUIVO: endpoints HTTP de aplicação de template por dia.

POR QUE ELE EXISTE:
- separa as rotas de day-apply do workout_planner_views.py já populado,
  seguindo o padrão de um módulo por aspecto do corredor WOD.

O QUE ESTE ARQUIVO FAZ:
1. WodDayApplyView       — POST: aplica template em todas as sessões de um dia,
                           retorna JSON com undo_token e resumo.
2. WodDayApplyUndoView   — POST: desfaz dentro da janela de 60s.

PONTOS CRÍTICOS:
- retorna JSON (não redirect) para permitir toast + undo no client sem reload.
- instância única por box (single-tenant); ACL garantida pelo OperationBaseView.
- apenas roles COACH, MANAGER, OWNER podem chamar; COACH filtrado por aula própria.
"""

from django.http import JsonResponse
from django.views import View

from access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER
from operations.forms_wod_day_apply import WodDayApplyForm, WodDayApplyUndoForm
from operations.services.wod_day_apply_executor import execute_day_apply
from operations.services.wod_day_apply_undo import execute_undo

from .base_views import OperationBaseView


class WodDayApplyView(OperationBaseView, View):
    allowed_roles = (ROLE_COACH, ROLE_MANAGER, ROLE_OWNER)

    def post(self, request, *args, **kwargs):
        form = WodDayApplyForm(request.POST)
        if not form.is_valid():
            return JsonResponse({'ok': False, 'errors': form.errors}, status=400)

        result = execute_day_apply(
            actor=request.user,
            target_date=form.cleaned_data['target_date'],
            template_id=form.cleaned_data['template_id'],
            mode=form.cleaned_data['mode'],
        )

        return JsonResponse({
            'ok': True,
            'applied_count': result.applied_count,
            'skipped_count': result.skipped_count,
            'undo_token': result.undo_token,
            'skipped_reasons': result.skipped_reasons,
        })


class WodDayApplyUndoView(OperationBaseView, View):
    allowed_roles = (ROLE_COACH, ROLE_MANAGER, ROLE_OWNER)

    def post(self, request, *args, **kwargs):
        form = WodDayApplyUndoForm(request.POST)
        if not form.is_valid():
            return JsonResponse({'ok': False, 'errors': form.errors}, status=400)

        result = execute_undo(undo_token=form.cleaned_data['undo_token'])
        return JsonResponse(result)


__all__ = ['WodDayApplyView', 'WodDayApplyUndoView']
