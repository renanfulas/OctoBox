"""
ARQUIVO: corredor HTTP do planner operacional de WOD.

POR QUE ELE EXISTE:
- separa o cockpit de planejamento do arquivo geral de workspace.

O QUE ESTE ARQUIVO FAZ:
1. publica a tela do planner.
2. recebe telemetria do picker de templates.
3. aplica template confiavel e duplica o slot anterior.
4. remove todos os SessionWorkout de uma semana inteira (clear-week).
"""

from datetime import timedelta

from django.contrib import messages
from django.db import OperationalError, ProgrammingError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View

from access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER
from shared_support.page_payloads import attach_page_payload

from operations.models import ClassSession, WorkoutTemplate
from operations.workout_planner_actions import apply_trusted_template_to_session, duplicate_previous_slot_workout
from operations.workout_planner_builders import resolve_week_start
from operations.workout_planner_context import build_workout_planner_context
from student_app.models import SessionWorkout
from operations.workout_telemetry import emit_wod_planner_picker_event

from .base_views import OperationBaseView


TEMPLATE_STORAGE_EXCEPTIONS = (OperationalError, ProgrammingError)


def _handle_template_storage_unavailable(request, *, redirect_name='workout-planner'):
    messages.warning(
        request,
        'A base de templates ainda nao esta pronta neste banco. Rode as migrations de operations para liberar esse fluxo.',
    )
    return redirect(redirect_name)


class WorkoutPlannerView(OperationBaseView):
    allowed_roles = (ROLE_COACH, ROLE_MANAGER, ROLE_OWNER)
    template_name = 'operations/workout_planner.html'
    page_title = 'Planner de WOD'
    page_subtitle = 'Semana, aulas e status do treino em uma grade operacional.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        planner_context = build_workout_planner_context(
            request=self.request,
            current_role=context['current_role'],
            page_title=self.page_title,
            page_subtitle=self.page_subtitle,
        )
        attach_page_payload(
            context,
            payload_key='operation_page',
            payload=planner_context.pop('operation_page_payload'),
        )
        context.update(planner_context)
        return context


class WorkoutPlannerTemplatePickerTelemetryView(OperationBaseView, View):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)

    def post(self, request, *args, **kwargs):
        event_name = (request.POST.get('event_name') or '').strip()
        session_id = request.POST.get('session_id') or None
        template_id = request.POST.get('template_id') or None
        if event_name not in {'opened', 'selected'}:
            return HttpResponse(status=204)
        emit_wod_planner_picker_event(
            actor=request.user,
            event_name=event_name,
            session_id=session_id,
            template_id=template_id,
        )
        return HttpResponse(status=204)


class WorkoutPlannerApplyTrustedTemplateView(OperationBaseView, View):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)

    def post(self, request, session_id, template_id, *args, **kwargs):
        session = get_object_or_404(ClassSession.objects.select_related('coach', 'workout'), pk=session_id)
        try:
            template = get_object_or_404(
                WorkoutTemplate.objects.prefetch_related('blocks__movements'),
                pk=template_id,
                is_active=True,
            )
        except TEMPLATE_STORAGE_EXCEPTIONS:
            return _handle_template_storage_unavailable(request)

        emit_wod_planner_picker_event(
            actor=request.user,
            event_name='applied',
            session_id=session_id,
            template_id=template_id,
        )

        result = apply_trusted_template_to_session(
            actor=request.user,
            template=template,
            target_session=session,
        )
        if result['ok']:
            if result['submission_result']['status'] == 'published':
                emit_wod_planner_picker_event(
                    actor=request.user,
                    event_name='completed',
                    session_id=session_id,
                    template_id=template_id,
                    action_outcome='published',
                )
                messages.success(request, 'Template confiavel aplicado direto no planner e publicado pela politica ativa.')
            else:
                emit_wod_planner_picker_event(
                    actor=request.user,
                    event_name='completed',
                    session_id=session_id,
                    template_id=template_id,
                    action_outcome='pending_approval',
                )
                messages.success(request, 'Template confiavel aplicado no planner e enviado para aprovacao pela politica ativa.')
        elif result['reason'] == 'target_has_blocks':
            messages.warning(request, 'Essa celula ja tem WOD. Nao aplicamos template por cima.')
        elif result['reason'] == 'template_not_trusted':
            messages.warning(request, 'Somente templates confiaveis podem ser aplicados direto no planner.')
        else:
            messages.warning(request, 'Nao foi possivel aplicar o template confiavel nesta celula.')
        return redirect('workout-planner')


class WorkoutPlannerDuplicatePreviousSlotView(OperationBaseView, View):
    allowed_roles = (ROLE_COACH, ROLE_OWNER)

    def post(self, request, session_id, *args, **kwargs):
        session = get_object_or_404(ClassSession.objects.select_related('coach', 'workout'), pk=session_id)
        if request.user.groups.filter(name=ROLE_COACH).exists() and session.coach_id != request.user.id:
            messages.error(request, 'Coach so pode duplicar slot anterior para a propria aula.')
            return redirect('workout-planner')

        result = duplicate_previous_slot_workout(actor=request.user, target_session=session)
        if result['ok']:
            messages.success(request, 'WOD da semana anterior duplicado como rascunho para esta aula.')
        elif result['reason'] == 'target_has_workout':
            messages.warning(request, 'Essa aula ja possui WOD. Nao duplicamos por cima.')
        else:
            messages.warning(request, 'Nao encontramos WOD do slot anterior para duplicar.')
        return redirect('workout-planner')


class WorkoutPlannerClearWeekView(OperationBaseView, View):
    allowed_roles = (ROLE_COACH, ROLE_OWNER, ROLE_MANAGER)

    def post(self, request, *args, **kwargs):
        week_param = request.POST.get('week') or request.GET.get('week')
        week_start = resolve_week_start(week_param)
        week_end = week_start + timedelta(days=6)
        queryset = SessionWorkout.objects.filter(
            session__scheduled_at__date__range=[week_start, week_end]
        )
        if request.user.groups.filter(name=ROLE_COACH).exists():
            queryset = queryset.filter(session__coach=request.user)
        deleted_count, _ = queryset.delete()
        if deleted_count:
            messages.success(request, f'{deleted_count} WOD(s) removidos da semana de {week_start:%d/%m/%Y}.')
        else:
            messages.info(request, 'Nenhum WOD encontrado para remover nesta semana.')
        week_str = week_start.isoformat()
        return redirect(f"{reverse('workout-planner')}?week={week_str}")


class WorkoutPlannerDeleteSelectedWorkoutView(OperationBaseView, View):
    allowed_roles = (ROLE_COACH, ROLE_OWNER, ROLE_MANAGER)

    def post(self, request, session_id, *args, **kwargs):
        session = get_object_or_404(ClassSession.objects.select_related('coach', 'workout'), pk=session_id)
        if request.user.groups.filter(name=ROLE_COACH).exists() and session.coach_id != request.user.id:
            messages.error(request, 'Coach so pode remover WOD da propria aula.')
            return redirect('workout-planner')

        workout = getattr(session, 'workout', None)
        if workout is None:
            messages.info(request, 'Nenhum WOD encontrado para remover nesta aula.')
            return redirect('workout-planner')

        workout.delete()
        messages.success(request, f'WOD da aula {session.title} removido com sucesso.')
        week_start = resolve_week_start(request.POST.get('week') or request.GET.get('week'))
        return redirect(f"{reverse('workout-planner')}?week={week_start.isoformat()}")


__all__ = [
    'WorkoutPlannerApplyTrustedTemplateView',
    'WorkoutPlannerClearWeekView',
    'WorkoutPlannerDeleteSelectedWorkoutView',
    'WorkoutPlannerDuplicatePreviousSlotView',
    'WorkoutPlannerTemplatePickerTelemetryView',
    'WorkoutPlannerView',
]
