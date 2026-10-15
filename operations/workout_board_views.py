"""
ARQUIVO: corredor HTTP de leitura e apoio operacional do WOD.

POR QUE ELE EXISTE:
- separa board, historico, resumo, smart paste e quick edit de RM do arquivo geral de workspace.
"""

import re
from uuid import uuid4

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import FormView

from access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER
from operations.model_definitions import ClassType
from shared_support.page_payloads import attach_page_payload

from operations.operations_executive_summary_context import build_operations_executive_summary_context
from operations.workout_approval_board_context import build_workout_approval_board_context
from operations.workout_smart_paste_context import (
    build_weekly_wod_smart_paste_context,
    count_unresolved_smart_paste_movements,
    list_unlinked_projection_movements,
    _max_week_start,
)
from operations.workout_publication_history_context import build_workout_publication_history_context
from operations.workout_rm_quick_edit_actions import save_workout_student_rm_quick_edit
from operations.workout_rm_quick_edit_context import (
    build_workout_student_rm_quick_edit_context,
    build_workout_student_rm_quick_edit_form_kwargs,
)
from operations.workout_rm_quick_edit_loader import load_workout_student_rm_quick_edit_context
from operations.forms import (
    WeeklyWodProjectionForm,
    WeeklyWodReviewMovementForm,
    WeeklyWodSmartPasteForm,
    WeeklyWodUndoReplicationForm,
    WorkoutCreateStoredTemplateForm,
    WorkoutStudentRmQuickForm,
)
from operations.services.wod_paste_parser import load_wod_movement_dictionary, parse_weekly_wod_text, resolve_movement_slug
from operations.services.wod_paste_freeform_parser import _freeform_should_take_over, parse_weekly_wod_freeform
from operations.services.wod_slug_resolver import apply_llm_slug_resolution
from operations.services.wod_weekly_normalizer import normalize_weekly_wod
from operations.services.smart_paste_rate_limit import smart_paste_rate_limit_exceeded
from operations.services.wod_smartplan_weekly_parser import detect_and_convert_smartplan_weekly
from operations.services.wod_projection import build_projection_preview, project_plan_to_sessions
from operations.services.wod_replication_batches import undo_replication_batch
from operations.workout_templates import create_persisted_template_from_weekly_plan
from student_app.models import WeeklyWodPlan, WeeklyWodPlanStatus

from .base_views import OperationBaseView


SMARTPLAN_CHATGPT_FALLBACK_URL = 'https://chatgpt.com/g/g-69f3b858af6c819197c4c1be8010bad6-octobox-smartplan'
SMART_PASTE_AUTO_CLASS_TYPES = (
    ClassType.CROSS,
    ClassType.MOBILITY,
    ClassType.OLY,
    ClassType.STRENGTH,
    ClassType.OPEN_GYM,
)


def _first_form_error(form, fallback_message):
    if not form.errors:
        return fallback_message
    first_errors = next(iter(form.errors.values()), [])
    if first_errors:
        return first_errors[0]
    return fallback_message


def _blocking_parse_errors(parsed_payload):
    """Return format errors without treating SmartPlan's advisory warnings as fatal."""
    errors = list(parsed_payload.get('parse_errors') or [])
    if parsed_payload.get('source_format'):
        return errors
    errors.extend(
        (
            f"Linha {warning.get('line_number', '?')}: "
            f"{warning.get('message', 'trecho não reconhecido')} — "
            f"“{warning.get('line_text', '')}”"
        )
        for warning in parsed_payload.get('parse_warnings') or []
    )
    return list(dict.fromkeys(errors))


def _smartplan_v2_uncertainty_errors(normalized_text):
    """Require the coach to resolve explicit uncertainty markers from SmartPlan."""
    errors = []
    for line in (normalized_text or '').splitlines():
        if re.search(r'\[\?[^\]]*\]', line):
            excerpt = re.sub(r'^\s*(?:[▸•*-]\s*)?', '', line).strip()
            if excerpt:
                errors.append(
                    f'Especifique o movimento ou a prescrição marcada como dúvida: “{excerpt}”.'
                )
    return errors


def _projection_guard_error(preview, cleaned_projection):
    """Mensagem acionavel quando nao ha aulas para projetar; None se pode prosseguir.

    Distingue 'nenhuma aula na semana' (precisa cadastrar a grade) de 'nenhuma aula do(s)
    tipo(s) selecionado(s)' (precisa ajustar o filtro ou criar aulas desse tipo).
    """
    week_label = cleaned_projection['target_week_start'].strftime('%d/%m/%Y')
    grade_path = reverse('class-grid')
    if preview.get('sessions_in_week_total', 0) == 0:
        return (
            f'Nenhuma aula cadastrada na semana de {week_label}. '
            f'Cadastre a grade em Grade de aulas ({grade_path}) antes de projetar.'
        )
    if (
        preview.get('totals', {}).get('sessions_found', 0) == 0
        and preview.get('sessions_canceled_selected_total', 0) > 0
    ):
        canceled_count = preview['sessions_canceled_selected_total']
        return (
            f'{canceled_count} aula(s) do(s) tipo(s) selecionado(s) na semana de {week_label} '
            f'estão canceladas e não receberão WOD. Reative essas aulas ou ajuste os tipos '
            f'em Grade de aulas ({grade_path}) antes de projetar.'
        )
    if preview.get('sessions_active_in_week_total', 0) == 0:
        canceled_count = preview.get('sessions_canceled_total', 0)
        return (
            f'As {canceled_count} aula(s) cadastrada(s) na semana de {week_label} '
            f'estão canceladas e não receberão WOD. Reative as aulas ou ajuste a grade '
            f'em Grade de aulas ({grade_path}) antes de projetar.'
        )
    if preview.get('totals', {}).get('sessions_found', 0) == 0:
        labels = ', '.join(str(ClassType(value).label) for value in cleaned_projection['class_types'])
        return (
            f'Nenhuma aula do(s) tipo(s) {labels} na semana de {week_label}. '
            f'Ajuste os tipos de aula ou cadastre aulas desse tipo na Grade de aulas ({grade_path}).'
        )
    return None


def _clear_unknown_review_slugs(parsed_payload, slug_dictionary):
    """Reabre slugs legados digitados fora do catálogo para Haiku ou revisão manual."""
    valid_slugs = {slug for slug, _aliases in slug_dictionary}
    valid_slugs.add('custom')
    for day in parsed_payload.get('days', []):
        for block in day.get('blocks', []):
            for movement in block.get('movements', []):
                slug = (movement.get('movement_slug') or '').strip()
                if slug and slug not in valid_slugs:
                    movement['movement_slug'] = ''


def _resolve_known_weekly_movement_slugs(parsed_payload):
    """Resolve exact catalog aliases locally before paying for Haiku slug review.

    The structural normalizer intentionally leaves every slug empty. Recovering a
    broken week must not turn every already-known exercise into an LLM candidate.
    """
    for day in parsed_payload.get('days', []):
        for block in day.get('blocks', []):
            for movement in block.get('movements', []):
                if movement.get('movement_slug'):
                    continue
                slug = resolve_movement_slug(movement.get('movement_label_raw') or '')
                if slug:
                    movement['movement_slug'] = slug


class WorkoutApprovalBoardView(OperationBaseView):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)
    template_name = 'operations/workout_approval_board.html'
    page_title = 'Aprovacao de WOD'
    page_subtitle = 'Revise os treinos pendentes antes de liberar para os alunos.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        board_context = build_workout_approval_board_context(
            request=self.request,
            today=context['today'],
            current_role=context['current_role'],
            page_title=self.page_title,
            page_subtitle=self.page_subtitle,
        )
        attach_page_payload(
            context,
            payload_key='operation_page',
            payload=board_context.pop('operation_page_payload'),
        )
        context.update(board_context)
        return context


class WorkoutPublicationHistoryView(OperationBaseView):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER, ROLE_COACH)
    template_name = 'operations/workout_publication_history.html'
    page_title = 'Historico do WOD'
    page_subtitle = 'Acompanhe o que foi ao ar e as pendencias reais do corredor.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        history_context = build_workout_publication_history_context(
            request=self.request,
            today=context['today'],
            current_role=context['current_role'],
            page_title=self.page_title,
            page_subtitle=self.page_subtitle,
        )
        attach_page_payload(
            context,
            payload_key='operation_page',
            payload=history_context.pop('operation_page_payload'),
        )
        context.update(history_context)
        return context


class WorkoutSmartPasteView(OperationBaseView):
    allowed_roles = (ROLE_COACH, ROLE_MANAGER, ROLE_OWNER)
    template_name = 'operations/workout_smart_paste.html'
    page_title = 'WOD Semana'
    page_subtitle = 'Cole a semana, confira a leitura e feche um rascunho organizado.'

    def _load_plan(self, plan_id):
        if not plan_id:
            return None
        return get_object_or_404(WeeklyWodPlan, pk=plan_id, created_by=self.request.user)

    def _is_hx_request(self):
        return self.request.headers.get('HX-Request') == 'true'

    def _render_partial(self, template_name, context):
        return render(self.request, template_name, context)

    def _build_context(
        self,
        *,
        plan=None,
        form=None,
        projection_form=None,
        review_form=None,
        undo_form=None,
        parsed_payload=None,
        projection_preview=None,
        projection_preview_auto_open=None,
        auto_open_review_target=None,
    ):
        base_context = self.get_base_context()
        context = build_weekly_wod_smart_paste_context(
            request=self.request,
            today=base_context['today'],
            current_role=base_context['current_role'],
            plan=plan,
            form=form,
            projection_form=projection_form,
            review_form=review_form,
            undo_form=undo_form,
            parsed_payload=parsed_payload,
            projection_preview=projection_preview,
            projection_preview_auto_open=projection_preview_auto_open,
            auto_open_review_target=auto_open_review_target,
        )
        base_context.update(context)
        configured_gpt_url = getattr(settings, 'SMARTPLAN_GPT_URL', '') or ''
        base_context['smartplan_gpt_url'] = configured_gpt_url or SMARTPLAN_CHATGPT_FALLBACK_URL
        # O GPT especifico do SmartPlan e o destino padrao; o botao nao deve
        # desaparecer so porque o ambiente nao redefiniu SMARTPLAN_GPT_URL.
        return base_context

    def _update_review_item(self, *, plan, cleaned_data):
        payload = plan.parsed_payload or {}
        days = payload.get('days') or []
        day = days[cleaned_data['day_index']]
        block = day['blocks'][cleaned_data['block_index']]
        movement = block['movements'][cleaned_data['movement_index']]
        movement['movement_label_raw'] = cleaned_data['movement_label_raw']
        chosen_slug = (cleaned_data.get('movement_slug') or '').strip()
        movement['movement_slug'] = chosen_slug or resolve_movement_slug(cleaned_data['movement_label_raw'])
        movement['reps_spec'] = (cleaned_data.get('reps_spec') or '').strip() or None
        movement['load_spec'] = (cleaned_data.get('load_spec') or '').strip() or None
        movement['notes'] = (cleaned_data.get('notes') or '').strip() or None
        resolution_status = payload.get('movement_resolution')
        if resolution_status and not count_unresolved_smart_paste_movements(payload):
            resolution_status['state'] = 'manual_resolved'
        plan.parsed_payload = payload
        plan.save(update_fields=['parsed_payload', 'updated_at'])
        return plan

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self._build_context())
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        plan = self._load_plan(request.POST.get('plan_id'))

        if action in {'retry_auto_resolution', 'retry_resolution'}:
            if plan is None or plan.status != WeeklyWodPlanStatus.DRAFT or not (plan.parsed_payload or {}).get('days'):
                messages.error(request, 'Cole e organize a semana antes de tentar outra correção.')
                return redirect('workout-smart-paste')
            payload = plan.parsed_payload or {}
            if smart_paste_rate_limit_exceeded(request):
                payload['movement_resolution'] = {'provider': 'haiku', 'state': 'rate_limited'}
                messages.error(request, 'Aguarde alguns minutos antes de tentar novamente.')
            else:
                slug_dictionary = load_wod_movement_dictionary()
                _clear_unknown_review_slugs(payload, slug_dictionary)
                apply_llm_slug_resolution(payload, slug_dictionary, retry=True)
                remaining = count_unresolved_smart_paste_movements(payload)
                if remaining:
                    messages.warning(request, f'{remaining} movimento(s) ainda precisam de revisão. Use o catálogo ou mantenha o nome original.')
                else:
                    messages.success(request, 'Movimentos corrigidos. A semana está pronta para conferir no Calendário.')
            plan.parsed_payload = payload
            plan.save(update_fields=['parsed_payload', 'updated_at'])
            context = self._build_context(plan=plan, parsed_payload=payload)
            if self._is_hx_request():
                return self._render_partial('operations/includes/wod_smart_paste_preview.html', context)
            return self.render_to_response(context)

        if action == 'update_review_item':
            review_form = WeeklyWodReviewMovementForm(
                request.POST,
                slug_choices=load_wod_movement_dictionary(),
            )
            if not review_form.is_valid():
                messages.error(request, _first_form_error(review_form, 'Revise o item antes de salvar a correção.'))
                context = self._build_context(plan=plan, review_form=review_form)
                if self._is_hx_request():
                    return self._render_partial('operations/includes/wod_smart_paste_preview.html', context)
                return self.render_to_response(context)
            plan = self._load_plan(review_form.cleaned_data['plan_id'])
            plan = self._update_review_item(plan=plan, cleaned_data=review_form.cleaned_data)
            messages.success(request, 'Item revisado no preview semanal.')
            next_target = ''
            for day_index, day in enumerate((plan.parsed_payload or {}).get('days', [])):
                for block_index, block in enumerate(day.get('blocks', [])):
                    for movement_index, movement in enumerate(block.get('movements', [])):
                        if not movement.get('movement_slug'):
                            next_target = f'review-item-{day_index}-{block_index}-{movement_index}'
                            break
                    if next_target:
                        break
                if next_target:
                    break
            # The queue form is already visible in the preview. Keep advancing
            # that form inline instead of opening a second, nested dialog.
            next_target = next_target if request.POST.get('review_source') != 'queue' else ''
            context = self._build_context(
                plan=plan,
                parsed_payload=plan.parsed_payload,
                auto_open_review_target=next_target,
            )
            if self._is_hx_request():
                return self._render_partial('operations/includes/wod_smart_paste_preview.html', context)
            return self.render_to_response(context)

        if action == 'undo_projection':
            undo_form = WeeklyWodUndoReplicationForm(request.POST)
            if not undo_form.is_valid():
                messages.error(request, _first_form_error(undo_form, 'Nao foi possivel identificar o lote para desfazer.'))
                context = self._build_context(plan=plan, undo_form=undo_form)
                if self._is_hx_request():
                    return self._render_partial('operations/includes/wod_smart_paste_projection.html', context)
                return self.render_to_response(context)
            batch = get_object_or_404(plan.replication_batches, pk=undo_form.cleaned_data['batch_id'])
            try:
                deleted_count = undo_replication_batch(batch=batch)
            except ValidationError as exc:
                messages.error(request, exc.message)
            else:
                messages.success(request, f'{deleted_count} registro(s) relacionados ao lote foram desfeitos.')
            context = self._build_context(plan=plan)
            if self._is_hx_request():
                return self._render_partial('operations/includes/wod_smart_paste_projection.html', context)
            return self.render_to_response(context)

        if action in {'preview_projection', 'create_projection'}:
            if plan is None or getattr(plan, 'status', '') != WeeklyWodPlanStatus.CONFIRMED:
                messages.error(request, 'Confirme o rascunho semanal antes de montar a replicacao.')
                context = self._build_context(plan=plan, parsed_payload=getattr(plan, 'parsed_payload', {}) or {})
                if self._is_hx_request():
                    return self._render_partial('operations/includes/wod_smart_paste_projection.html', context)
                return self.render_to_response(context)
            projection_form = WeeklyWodProjectionForm(request.POST)
            if not projection_form.is_valid():
                messages.error(request, _first_form_error(projection_form, 'Revise a semana alvo e os tipos de aula antes de projetar.'))
                context = self._build_context(plan=plan, projection_form=projection_form)
                if self._is_hx_request():
                    return self._render_partial('operations/includes/wod_smart_paste_projection.html', context)
                return self.render_to_response(context)
            cleaned_projection = projection_form.cleaned_data
            plan = self._load_plan(cleaned_projection['plan_id'])
            preview = build_projection_preview(
                weekly_plan=plan,
                target_week_start=cleaned_projection['target_week_start'],
                class_types=cleaned_projection['class_types'],
            )
            guard_error = _projection_guard_error(preview, cleaned_projection)
            if guard_error:
                messages.error(request, guard_error)
                context = self._build_context(
                    plan=plan,
                    projection_form=projection_form,
                    parsed_payload=plan.parsed_payload,
                    projection_preview=preview,
                )
                if self._is_hx_request():
                    return self._render_partial('operations/includes/wod_smart_paste_projection.html', context)
                return self.render_to_response(context)
            unlinked_movements = list_unlinked_projection_movements(preview)
            if (
                action == 'create_projection'
                and preview['totals']['sessions_creatable']
                and unlinked_movements
                and request.POST.get('acknowledge_unlinked_movements') != 'yes'
            ):
                messages.warning(
                    request,
                    'Confirme que deseja distribuir apesar de movimentos sem compatibilidade validada ou sem vídeo de referência.',
                )
                context = self._build_context(
                    plan=plan,
                    projection_form=projection_form,
                    parsed_payload=plan.parsed_payload,
                    projection_preview=preview,
                    projection_preview_auto_open=True,
                )
                if self._is_hx_request():
                    return self._render_partial('operations/includes/wod_smart_paste_projection.html', context)
                return self.render_to_response(context)
            if action == 'create_projection':
                if not preview['totals']['sessions_creatable'] and not cleaned_projection.get('idempotency_key'):
                    messages.warning(request, 'Nenhuma aula nova esta pronta para receber WOD. Atualize a previa antes de distribuir.')
                    context = self._build_context(
                        plan=plan,
                        projection_form=projection_form,
                        parsed_payload=plan.parsed_payload,
                        projection_preview=preview,
                    )
                    if self._is_hx_request():
                        return self._render_partial('operations/includes/wod_smart_paste_projection.html', context)
                    return self.render_to_response(context)
                distribution_warning = None
                projection_distribution_result = None
                try:
                    batch, preview = project_plan_to_sessions(
                        weekly_plan=plan,
                        target_week_start=cleaned_projection['target_week_start'],
                        class_types=cleaned_projection['class_types'],
                        actor=request.user,
                        idempotency_key=cleaned_projection.get('idempotency_key') or uuid4(),
                    )
                except ValidationError as exc:
                    distribution_warning = exc.message
                except IntegrityError:
                    distribution_warning = 'Uma aula mudou enquanto a distribuicao era salva. Confira os destinos atualizados antes de tentar novamente.'
                if distribution_warning:
                    messages.warning(request, distribution_warning)
                    preview = build_projection_preview(
                        weekly_plan=plan,
                        target_week_start=cleaned_projection['target_week_start'],
                        class_types=cleaned_projection['class_types'],
                    )
                    context = self._build_context(
                        plan=plan,
                        projection_form=projection_form,
                        parsed_payload=plan.parsed_payload,
                        projection_preview=preview,
                        projection_distribution_warning=distribution_warning,
                    )
                    if self._is_hx_request():
                        return self._render_partial('operations/includes/wod_smart_paste_projection.html', context)
                    return self.render_to_response(context)
                projection_distribution_result = {
                    'sessions_created': batch.sessions_created,
                    'sessions_pending_approval': preview['totals'].get('sessions_pending_approval', 0),
                    'sessions_published': preview['totals'].get('sessions_published', 0),
                    'replayed': preview.get('idempotent_replay', False),
                }
                # Return a post-write preview. Keeping the pre-write snapshot
                # made a successful destination look creatable again, inviting
                # a confusing retry after a slow/lost response. The unique
                # constraint prevented a duplicate, but the UI should reflect
                # the committed state and disable distribution for this batch.
                preview = build_projection_preview(
                    weekly_plan=plan,
                    target_week_start=cleaned_projection['target_week_start'],
                    class_types=cleaned_projection['class_types'],
                )
                # A successfully completed request gets a fresh token for any
                # later, intentional distribution after the schedule changes.
                # If the response is lost, the browser still holds the old token
                # and the server can replay the original result safely.
                projection_form = WeeklyWodProjectionForm(
                    initial={
                        'plan_id': plan.id,
                        'idempotency_key': uuid4(),
                        'target_week_start': cleaned_projection['target_week_start'].strftime('%d/%m/%Y'),
                        'class_types': cleaned_projection['class_types'],
                    }
                )
                if not self._is_hx_request():
                    messages.success(
                        request,
                        f"{batch.sessions_created} WOD(s) criados: "
                        f"{projection_distribution_result['sessions_pending_approval']} aguardando aprovacao e "
                        f"{projection_distribution_result['sessions_published']} publicados conforme a politica do box.",
                    )
            else:
                messages.success(request, 'Preview de replicacao montado sem criar WODs ainda.')
            context = self._build_context(
                plan=plan,
                projection_form=projection_form,
                parsed_payload=plan.parsed_payload,
                projection_preview=preview,
                projection_preview_auto_open=action != 'create_projection',
            )
            if action == 'create_projection':
                context['projection_distribution_result'] = projection_distribution_result
            if self._is_hx_request():
                return self._render_partial('operations/includes/wod_smart_paste_projection.html', context)
            return self.render_to_response(context)

        if action == 'create_stored_template':
            template_form = WorkoutCreateStoredTemplateForm(request.POST)
            if not template_form.is_valid():
                messages.error(request, _first_form_error(template_form, 'Escolha um nome valido para o template salvo.'))
                context = self._build_context(plan=plan, parsed_payload=getattr(plan, 'parsed_payload', {}) or {})
                return self.render_to_response(context)
            if plan is None or not (getattr(plan, 'parsed_payload', {}) or {}).get('days'):
                messages.error(request, 'Organize e confirme a semana antes de salvar como template.')
                return redirect('workout-smart-paste')
            template = create_persisted_template_from_weekly_plan(
                actor=request.user,
                weekly_plan=plan,
                name=template_form.cleaned_data['template_name'],
                description=f'Base criada a partir do Smart Paste semanal de {plan.week_start:%d/%m/%Y}.',
            )
            messages.success(request, f'Template salvo "{template.name}" criado a partir do Smart Paste.')
            return redirect('workout-template-management')

        if action not in {'confirm_plan', 'confirm_and_project'} and smart_paste_rate_limit_exceeded(request):
            messages.error(
                request,
                'Muitas submissoes em pouco tempo. Espere alguns minutos antes de organizar outro texto.',
            )
            context = self._build_context(plan=plan)
            if self._is_hx_request():
                return self._render_partial('operations/includes/wod_smart_paste_preview.html', context)
            return self.render_to_response(context)

        today_date = self.get_base_context().get('today') or timezone.localdate()
        form = WeeklyWodSmartPasteForm(request.POST, max_week_start=_max_week_start(today_date))
        if not form.is_valid():
            messages.error(request, _first_form_error(form, 'Revise a semana e o texto antes de continuar.'))
            context = self._build_context(plan=plan, form=form)
            if self._is_hx_request():
                return self._render_partial('operations/includes/wod_smart_paste_preview.html', context)
            return self.render_to_response(context)

        cleaned = form.cleaned_data
        if (
            plan is not None
            and plan.workout_program_id != cleaned['workout_program'].pk
            and action not in {'confirm_plan', 'confirm_and_project'}
        ):
            # A modality switch starts or resumes an independent draft; never
            # overwrite another track's weekly programming with this paste.
            plan = WeeklyWodPlan.objects.filter(
                created_by=request.user,
                week_start=cleaned['week_start'],
                workout_program=cleaned['workout_program'],
                status=WeeklyWodPlanStatus.DRAFT,
            ).order_by('-updated_at', '-id').first()
        if action in {'confirm_plan', 'confirm_and_project'} and plan is not None:
            # The confirmation form carries the persisted source as a hidden
            # value, separate from the editable composer form. Reject a stale
            # or tampered source rather than confirm a preview that no longer
            # matches the text sent with this request.
            if (
                cleaned['source_text'] != plan.source_text
                or cleaned['week_start'] != plan.week_start
                or (
                    plan.workout_program_id is not None
                    and cleaned['workout_program'].pk != plan.workout_program_id
                )
            ):
                messages.error(
                    request,
                    'O texto ou a semana mudou depois desta prévia. Organize o treino novamente antes de confirmar.',
                )
                context = self._build_context(
                    plan=plan,
                    form=form,
                    parsed_payload=plan.parsed_payload,
                )
                if self._is_hx_request():
                    return self._render_partial('operations/includes/wod_smart_paste_preview.html', context)
                return self.render_to_response(context)
        plan = plan or WeeklyWodPlan(created_by=request.user)
        plan.week_start = cleaned['week_start']
        plan.workout_program = cleaned['workout_program']
        plan.label = cleaned['label']
        plan.source_text = cleaned['source_text']
        if action in {'confirm_plan', 'confirm_and_project'}:
            # Guarda server-side: o botao "Confirmar rascunho semanal" fica
            # disabled no template quando ha pendencia, mas isso e so client-side
            # (atributo HTML inspecionavel/removivel). Sem esta checagem, um
            # plano com movimento nao resolvido confirmado e depois replicado
            # grava o texto cru digitado pelo coach como rotulo do exercicio no
            # WOD real do aluno (slug generico 'custom' em wod_projection.py).
            retry_payload = plan.parsed_payload or {}
            weekly_normalization = retry_payload.get('weekly_normalization') or {}
            if (
                weekly_normalization.get('status') == 'awaiting_coach_review'
                and request.POST.get('normalization_reviewed') != 'yes'
            ):
                messages.error(
                    request,
                    'Confira a organização sugerida e marque a confirmação antes de continuar.',
                )
                context = self._build_context(plan=plan, parsed_payload=retry_payload)
                if self._is_hx_request():
                    return self._render_partial('operations/includes/wod_smart_paste_preview.html', context)
                return self.render_to_response(context)
            parse_errors = _blocking_parse_errors(retry_payload)
            if parse_errors:
                retry_payload['parse_errors'] = parse_errors
            if parse_errors or not retry_payload.get('days'):
                plan.created_by = plan.created_by or request.user
                plan.save()
                message = (
                    'A semana ainda tem erro de dia ou formato. Corrija o texto antes de distribuir.'
                    if parse_errors else
                    'Nenhum dia válido foi organizado. Cole e organize uma semana antes de confirmar.'
                )
                messages.error(request, message)
                context = self._build_context(plan=plan, parsed_payload=retry_payload)
                if self._is_hx_request():
                    return self._render_partial('operations/includes/wod_smart_paste_preview.html', context)
                return self.render_to_response(context)
            slug_dictionary = load_wod_movement_dictionary()
            _clear_unknown_review_slugs(retry_payload, slug_dictionary)
            if action == 'confirm_and_project':
                if count_unresolved_smart_paste_movements(retry_payload) and smart_paste_rate_limit_exceeded(request):
                    retry_payload['movement_resolution'] = {
                        'provider': 'haiku',
                        'state': 'rate_limited',
                        'retry_attempted': True,
                    }
                else:
                    apply_llm_slug_resolution(
                        retry_payload,
                        slug_dictionary,
                        retry=True,
                    )
            plan.parsed_payload = retry_payload
            unresolved_count = count_unresolved_smart_paste_movements(plan.parsed_payload or {})
            if unresolved_count:
                resolution_state = (plan.parsed_payload or {}).get('movement_resolution', {}).get('state')
                haiku_unavailable = resolution_state in {
                    'provider_unavailable', 'provider_error', 'empty_response', 'dictionary_unavailable',
                }
                if action == 'confirm_and_project':
                    if resolution_state == 'rate_limited':
                        retry_summary = 'O limite de tentativas foi atingido; aguarde alguns minutos.'
                    elif haiku_unavailable:
                        retry_summary = 'Nao foi possivel concluir a nova tentativa automatica.'
                    else:
                        retry_summary = 'O Haiku revisou novamente.'
                    error_message = (
                        f'{retry_summary} Ainda ha {unresolved_count} pendencia(s); '
                        'escolha um movimento do catalogo ou mantenha o nome original como personalizado.'
                    )
                else:
                    error_message = f'Feche as {unresolved_count} pendencia(s) de revisao antes de confirmar a semana.'
                messages.error(
                    request,
                    error_message,
                )
                plan.save(update_fields=['parsed_payload', 'updated_at'])
                context = self._build_context(plan=plan, parsed_payload=plan.parsed_payload)
                if self._is_hx_request():
                    return self._render_partial('operations/includes/wod_smart_paste_preview.html', context)
                return self.render_to_response(context)
            if weekly_normalization.get('status') == 'awaiting_coach_review':
                weekly_normalization['status'] = 'coach_accepted'
                retry_payload['weekly_normalization'] = weekly_normalization
            plan.status = WeeklyWodPlanStatus.CONFIRMED
        else:
            plan.status = WeeklyWodPlanStatus.DRAFT
            source_text = cleaned['source_text']
            parsed = detect_and_convert_smartplan_weekly(source_text)
            is_smartplan_v2 = bool(
                parsed and parsed.get('source_format') == 'smartplan_text_v2'
            )
            if parsed is None:
                parsed = parse_weekly_wod_text(source_text)
                freeform = parse_weekly_wod_freeform(source_text)
                if _freeform_should_take_over(parsed, freeform):
                    parsed = freeform
            elif is_smartplan_v2:
                normalized_text = parsed.pop('normalized_text', '')
                uncertainty_errors = _smartplan_v2_uncertainty_errors(normalized_text)
                if uncertainty_errors:
                    parsed['parse_errors'] = uncertainty_errors
                    parsed['weekly_normalization'] = {
                        'status': 'needs_review',
                        'error': 'O coach precisa especificar os trechos marcados como dúvida antes de continuar.',
                    }
                elif not parsed.get('parse_errors'):
                    normalization = normalize_weekly_wod(
                        source_text=normalized_text,
                        parse_diagnostics=[
                            'Saída normalizada do SmartPlan v2 precisa ser convertida para a semana estruturada.'
                        ],
                    )
                    if normalization.get('status') == 'normalized' and normalization.get('candidate'):
                        parsed = normalization['candidate']
                        parsed['parse_errors'] = []
                        parsed['source_format'] = 'haiku_weekly_normalizer'
                        parsed['weekly_normalization'] = {
                            'status': 'awaiting_coach_review',
                            'changes': normalization['changes'],
                            'prompt_version': normalization.get('prompt_version'),
                            'schema_version': normalization.get('schema_version'),
                        }
                    else:
                        error = normalization.get('error') or (
                            'Não foi possível transformar a resposta normalizada em uma semana segura.'
                        )
                        parsed['parse_errors'] = [error]
                        parsed['weekly_normalization'] = {
                            'status': 'needs_review',
                            'error': error,
                            'prompt_version': normalization.get('prompt_version'),
                            'schema_version': normalization.get('schema_version'),
                        }
            # Linhas ignoradas pelos parsers legados podem apagar parte do WOD;
            # no fluxo semanal isso bloqueia a confirmação até revisão.
            parsed_errors = _blocking_parse_errors(parsed)
            if parsed_errors and not is_smartplan_v2:
                normalization = normalize_weekly_wod(
                    source_text=source_text,
                    parse_diagnostics=parsed_errors,
                )
                if normalization.get('status') == 'normalized' and normalization.get('candidate'):
                    parsed = normalization['candidate']
                    parsed['parse_errors'] = []
                    parsed['source_format'] = 'haiku_weekly_normalizer'
                    parsed['weekly_normalization'] = {
                        'status': 'awaiting_coach_review',
                        'changes': normalization['changes'],
                        'prompt_version': normalization.get('prompt_version'),
                        'schema_version': normalization.get('schema_version'),
                    }
                else:
                    parsed['parse_errors'] = parsed_errors
                    parsed['weekly_normalization'] = {
                        'status': 'needs_review',
                        'error': normalization.get('error') or 'Nao foi possivel organizar a estrutura com seguranca.',
                        'prompt_version': normalization.get('prompt_version'),
                        'schema_version': normalization.get('schema_version'),
                    }
            # Resolver movimento só depois de fechar a estrutura da semana.
            # Não gastar uma chamada separada nem atuar sobre payload parcial
            # quando o Haiku normalizador falhou ou pediu revisão manual.
            if not _blocking_parse_errors(parsed):
                slug_dictionary = load_wod_movement_dictionary()
                _resolve_known_weekly_movement_slugs(parsed)
                apply_llm_slug_resolution(parsed, slug_dictionary)
            plan.parsed_payload = parsed
        plan.created_by = plan.created_by or request.user
        plan.save()

        if action == 'confirm_plan':
            messages.success(request, 'Plano semanal confirmado. Revise as aulas da semana antes de aplicar os WODs.')
        elif action == 'confirm_and_project':
            preview = build_projection_preview(
                weekly_plan=plan,
                target_week_start=plan.week_start,
                class_types=SMART_PASTE_AUTO_CLASS_TYPES,
            )
            if preview['totals']['sessions_creatable']:
                messages.info(
                    request,
                    'Confira as aulas e os WODs abaixo. Nada foi enviado ainda; confirme a distribuicao quando estiver pronto.',
                )
            else:
                messages.warning(
                    request,
                    'Semana organizada, mas nenhuma aula pode receber estes WODs. '
                    'Confira a grade de aulas ou os treinos que ja existem antes de distribuir.',
                )
            context = self._build_context(
                plan=plan,
                parsed_payload=plan.parsed_payload,
                projection_preview=preview,
            )
            return self.render_to_response(context)
        else:
            messages.success(request, 'Texto organizado em rascunho semanal.')

        refreshed_form = WeeklyWodSmartPasteForm(
            initial={
                'plan_id': plan.id,
                'week_start': plan.week_start.strftime('%d/%m'),
                'label': plan.label,
                'source_text': plan.source_text,
            }
        )
        context = self._build_context(plan=plan, form=refreshed_form, parsed_payload=plan.parsed_payload)
        if self._is_hx_request():
            return self._render_partial('operations/includes/wod_smart_paste_preview.html', context)
        return self.render_to_response(context)


class OperationsExecutiveSummaryView(OperationBaseView):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER, ROLE_COACH)
    template_name = 'operations/operations_executive_summary.html'
    page_title = 'Resumo executivo'
    page_subtitle = 'Leia o corredor de WOD sem misturar decisao, historico e acompanhamento.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        summary_context = build_operations_executive_summary_context(
            current_role=context['current_role'],
            page_title=self.page_title,
            page_subtitle=self.page_subtitle,
        )
        attach_page_payload(
            context,
            payload_key='operation_page',
            payload=summary_context.pop('operation_page_payload'),
        )
        context.update(summary_context)
        return context


class WorkoutStudentRmQuickEditView(OperationBaseView, FormView):
    allowed_roles = (ROLE_OWNER, ROLE_MANAGER)
    template_name = 'operations/workout_student_rm_quick_edit.html'
    form_class = WorkoutStudentRmQuickForm
    page_title = 'Cadastro rapido de RM'
    page_subtitle = 'Registre o RM do aluno sem sair do corredor operacional do WOD.'

    def dispatch(self, request, *args, **kwargs):
        payload = load_workout_student_rm_quick_edit_context(
            workout_id=kwargs['workout_id'],
            student_id=kwargs['student_id'],
            exercise_slug=kwargs['exercise_slug'],
            label=request.GET.get('label', ''),
        )
        self.workout = payload['workout']
        self.student = payload['student']
        self.exercise_slug = payload['exercise_slug']
        self.exercise_label = payload['exercise_label']
        self.rm_record = payload['rm_record']
        if not payload['attendance_exists']:
            messages.error(request, 'Esse aluno nao esta mais na turma reservada deste WOD.')
            return redirect('workout-approval-board')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        return build_workout_student_rm_quick_edit_form_kwargs(self)

    def get_context_data(self, **kwargs):
        return build_workout_student_rm_quick_edit_context(self, **kwargs)

    def form_valid(self, form):
        return save_workout_student_rm_quick_edit(self, form)


__all__ = [
    'OperationsExecutiveSummaryView',
    'WorkoutApprovalBoardView',
    'WorkoutPublicationHistoryView',
    'WorkoutSmartPasteView',
    'WorkoutStudentRmQuickEditView',
]
