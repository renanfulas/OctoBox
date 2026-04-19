"""
ARQUIVO: views da Central de Intake.

POR QUE ELE EXISTE:
- Publica a casca HTTP da area propria de entradas provisórias.

O QUE ESTE ARQUIVO FAZ:
1. Renderiza a Central de Intake.
2. Respeita permissao por papel.
3. Anexa page payload no contrato compartilhado do front.

PONTOS CRITICOS:
- Essa tela vira o destino canonico de links globais ligados a intake.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from access.permissions import RoleRequiredMixin
from access.roles import ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION, get_user_role
from monitoring.lead_attribution_metrics import record_lead_attribution_capture
from onboarding.attribution import build_intake_attribution_payload, normalize_acquisition_channel
from onboarding.models import IntakeStatus, StudentIntake
from shared_support.box_runtime import get_box_runtime_slug
from shared_support.manager_event_stream import publish_manager_stream_event
from shared_support.page_payloads import attach_page_payload
from shared_support.crypto_fields import generate_blind_index
from student_identity.application.commands import CreateStudentInvitationCommand
from student_identity.application.use_cases import CreateStudentInvitation
from student_identity.delivery_audit import record_student_invitation_whatsapp_handoff
from student_identity.funnel_events import record_student_onboarding_event
from student_identity.infrastructure.repositories import DjangoStudentIdentityRepository
from student_identity.models import StudentAppInvitation, StudentOnboardingJourney
from student_identity.notifications import build_invitation_whatsapp_url
from students.models import Student, StudentStatus

from .forms import IntakeQueueActionForm, IntakeQuickCreateForm
from .facade import run_intake_queue_action
from .presentation import build_intake_center_page
from .queries import build_intake_center_snapshot


INTAKE_SEARCH_BOOTSTRAP_LIMIT = 24
INTAKE_SEARCH_PAGE_LIMIT = 50


def _serialize_intake_search_entry(*, item, request):
    intake = item['object']
    conversion = item['conversion']
    permissions = item['action_permissions']
    can_manage_students = getattr(request, 'intake_page_capabilities', {}).get('can_manage_students', False)
    can_work_queue = getattr(request, 'intake_page_capabilities', {}).get('can_work_queue', False)
    conversion_href = ''
    if can_manage_students and conversion['can_convert'] and conversion['action_type'] == 'convert-student':
        conversion_href = f"{reverse('student-quick-create')}?intake={intake.id}#student-form-essential"
    return {
        'id': intake.id,
        'full_name': intake.full_name,
        'channel_label': intake.email or intake.phone or '',
        'source_label': intake.get_source_display(),
        'registration_age_days': item['registration_age_days'],
        'registration_age_label': item['registration_age_label'],
        'semantic_stage': item['semantic_state']['semantic_stage'],
        'semantic_label': item['semantic_state']['semantic_label'],
        'conversion_reason': conversion['reason'],
        'created_today': bool(getattr(intake, 'created_at', None) and intake.created_at.date() == timezone.localdate()),
        'assigned': bool(getattr(intake, 'assigned_to_id', None)),
        'assigned_label': (
            intake.assigned_to.get_full_name() or intake.assigned_to.username
            if getattr(intake, 'assigned_to', None)
            else 'Aguardando'
        ),
        'whatsapp_href': item['whatsapp_href'],
        'conversion': {
            'can_convert': bool(conversion['can_convert']),
            'action_type': conversion['action_type'],
            'action_label': conversion['action_label'],
            'href': conversion_href,
            'requires_post': bool(
                can_work_queue and conversion['can_convert'] and conversion['action_type'] == 'move-to-conversation'
            ),
        },
        'permissions': {
            'can_reject': bool(can_work_queue and permissions.get('can_reject')),
        },
    }


def _clean_intake_search_index_params(params):
    index_params = params.copy()
    for key in ('query', 'panel', 'offset', 'status', 'semantic_stage', 'created_window', 'assignment'):
        if key in index_params:
            del index_params[key]
    return index_params


def _parse_non_negative_int(value, default=0):
    try:
        parsed_value = int(value)
    except (TypeError, ValueError):
        return default
    return max(parsed_value, 0)


class IntakeCenterView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    allowed_roles = (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER, ROLE_RECEPTION)
    template_name = 'onboarding/intake_center.html'

    PANEL_QUEUE = 'tab-intake-queue'
    PANEL_CREATE_LEAD = 'tab-intake-create-lead'
    PANEL_CREATE_INTAKE = 'tab-intake-create-intake'

    def _get_current_role(self):
        return get_user_role(self.request.user)

    def _get_current_role_slug(self):
        return getattr(self._get_current_role(), 'slug', '')

    def _get_filter_params(self):
        if self.request.method == 'POST':
            return self.request.POST.copy()
        return self.request.GET

    def _get_active_panel(self):
        panel = self.request.GET.get('panel', '').strip()
        allowed_panels = {
            self.PANEL_QUEUE,
            'tab-intake-source',
            'tab-intake-filters',
            self.PANEL_CREATE_LEAD,
            self.PANEL_CREATE_INTAKE,
        }
        return panel if panel in allowed_panels else self.PANEL_QUEUE

    def _get_create_form_prefix(self, entry_kind):
        return 'lead-create' if entry_kind == 'lead' else 'intake-create'

    def _build_create_form(self, *, entry_kind, bound_data=None):
        prefix = self._get_create_form_prefix(entry_kind)
        return IntakeQuickCreateForm(bound_data, prefix=prefix) if bound_data is not None else IntakeQuickCreateForm(prefix=prefix)

    def _get_quick_create_success_url(self, entry_kind):
        panel = self.PANEL_CREATE_LEAD if entry_kind == 'lead' else self.PANEL_CREATE_INTAKE
        return f"{reverse('intake-center')}?panel={panel}"

    def _build_snapshot(self):
        params = self.request.GET if self.request.method == 'GET' else self.request.POST
        params = params.copy()
        params.pop('intake_id', None)
        params.pop('action', None)
        params.pop('return_query', None)
        return build_intake_center_snapshot(params=params, actor_role_slug=self._get_current_role_slug())

    def _get_success_url(self, return_query=''):
        url = reverse('intake-center')
        query_string = (return_query or '').strip()
        return f'{url}?{query_string}' if query_string else url

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_role = self._get_current_role()
        snapshot = kwargs.get('snapshot') or self._build_snapshot()
        index_params = _clean_intake_search_index_params(self.request.GET)
        self.request.intake_page_capabilities = {
            'can_manage_students': getattr(current_role, 'slug', '') in (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION),
            'can_work_queue': getattr(current_role, 'slug', '') in (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION),
        }
        search_snapshot = build_intake_center_snapshot(
            params=index_params,
            actor_role_slug=getattr(current_role, 'slug', ''),
            queue_limit=INTAKE_SEARCH_BOOTSTRAP_LIMIT,
        )
        page_payload = build_intake_center_page(
            snapshot=snapshot,
            current_role_slug=getattr(current_role, 'slug', ''),
            intake_search={
                'cache_key': index_params.urlencode() or 'all',
                'refresh_token': search_snapshot.get('queue_refresh_token', ''),
                'page_url': reverse('intake-search-index-page'),
                'page_size': INTAKE_SEARCH_PAGE_LIMIT,
                'total': search_snapshot.get('queue_total_count', 0),
                'has_next': search_snapshot.get('queue_has_next', False),
                'next_offset': search_snapshot.get('queue_next_offset'),
                'index': [
                    _serialize_intake_search_entry(item=item, request=self.request)
                    for item in search_snapshot.get('queue_items', [])
                ],
            },
        )
        attach_page_payload(context, payload_key='intake_center_page', payload=page_payload)
        context['active_intake_panel'] = kwargs.get('active_panel') or self._get_active_panel()
        context['lead_create_form'] = kwargs.get('lead_create_form') or self._build_create_form(entry_kind='lead')
        context['intake_create_form'] = kwargs.get('intake_create_form') or self._build_create_form(entry_kind='intake')
        return context

    def post(self, request, *args, **kwargs):
        role_slug = self._get_current_role_slug()
        if request.POST.get('action') == 'send-whatsapp-invite':
            return self._handle_send_whatsapp_invite(request, role_slug=role_slug)
        if request.POST.get('form_kind') == 'quick-create':
            if role_slug not in (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION):
                messages.error(request, 'Seu papel atual pode consultar a central, mas nao cadastrar entradas por esta tela.')
                return redirect(reverse('intake-center'))

            entry_kind = request.POST.get('entry_kind', 'lead').strip().lower()
            if entry_kind not in ('lead', 'intake'):
                entry_kind = 'lead'

            form = self._build_create_form(entry_kind=entry_kind, bound_data=request.POST)
            if not form.is_valid():
                context_kwargs = {
                    'active_panel': self.PANEL_CREATE_LEAD if entry_kind == 'lead' else self.PANEL_CREATE_INTAKE,
                    'lead_create_form': form if entry_kind == 'lead' else self._build_create_form(entry_kind='lead'),
                    'intake_create_form': form if entry_kind == 'intake' else self._build_create_form(entry_kind='intake'),
                }
                return self.render_to_response(self.get_context_data(**context_kwargs))

            with transaction.atomic():
                created_entry = form.save(commit=False)
                created_entry.status = IntakeStatus.NEW
                created_entry.raw_payload = {
                    **(created_entry.raw_payload or {}),
                    **build_intake_attribution_payload(
                        source=created_entry.source,
                        acquisition_channel=form.cleaned_data.get('acquisition_channel', ''),
                        acquisition_detail=form.cleaned_data.get('acquisition_detail', ''),
                        entry_kind=entry_kind,
                        actor_id=getattr(request.user, 'id', None),
                    ),
                }
                created_entry.save()
                record_lead_attribution_capture(
                    entry_kind=entry_kind,
                    operational_source=created_entry.source,
                    acquisition_channel=normalize_acquisition_channel(form.cleaned_data.get('acquisition_channel')),
                )
                publish_manager_stream_event(
                    event_type='intake.updated',
                    meta={
                        'intake_id': created_entry.id,
                        'action': 'quick-create',
                        'status': created_entry.status,
                        'entry_kind': entry_kind,
                        'acquisition_channel': normalize_acquisition_channel(form.cleaned_data.get('acquisition_channel')),
                    },
                )

            entry_label = 'Lead' if entry_kind == 'lead' else 'Intake'
            messages.success(request, f'{entry_label} cadastrado com sucesso na Central de Intake.')
            return redirect(self._get_quick_create_success_url(entry_kind))

        if role_slug not in (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION):
            messages.error(request, 'Seu papel atual pode consultar a central, mas nao executar a fila por esta tela.')
            return redirect(self._get_success_url())

        form = IntakeQueueActionForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'A acao de entradas nao foi entendida. Revise a fila e tente novamente.')
            return redirect(self._get_success_url(request.POST.get('return_query', '')))

        try:
            with transaction.atomic():
                result = run_intake_queue_action(
                    actor=request.user,
                    intake_id=form.cleaned_data['intake_id'],
                    action=form.cleaned_data['action'],
                )
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, result.message)
            publish_manager_stream_event(
                event_type='intake.updated',
                meta={
                    'intake_id': result.intake_id,
                    'action': form.cleaned_data['action'],
                    'status': result.status,
                    'assigned_to_id': result.assigned_to_id,
                },
            )

        return redirect(self._get_success_url(form.cleaned_data.get('return_query', '')))

    def _handle_send_whatsapp_invite(self, request, *, role_slug: str):
        if role_slug not in (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION):
            messages.error(request, 'Seu papel atual nao pode disparar convites do app para leads.')
            return redirect(self._get_success_url(request.POST.get('return_query', '')))

        daily_limit = max(1, int(getattr(settings, 'STUDENT_IMPORTED_LEAD_WHATSAPP_DAILY_LIMIT', 25)))
        invites_today = StudentAppInvitation.objects.filter(
            created_by=request.user,
            onboarding_journey=StudentOnboardingJourney.IMPORTED_LEAD_INVITE,
            created_at__date=timezone.localdate(),
        ).count()
        if invites_today >= daily_limit:
            messages.error(request, f'O limite operacional de {daily_limit} convites por dia para leads importados foi alcancado.')
            return redirect(self._get_success_url(request.POST.get('return_query', '')))

        intake = StudentIntake.objects.select_for_update().select_related('linked_student').filter(
            pk=request.POST.get('intake_id')
        ).first()
        if intake is None:
            messages.error(request, 'Nao encontrei esse lead para disparar o convite por WhatsApp.')
            return redirect(self._get_success_url(request.POST.get('return_query', '')))
        if not intake.phone:
            messages.error(request, 'Esse lead nao tem WhatsApp utilizavel para convite.')
            return redirect(self._get_success_url(request.POST.get('return_query', '')))

        student = intake.linked_student or self._resolve_or_create_student_from_intake(intake=intake)
        if intake.linked_student_id is None:
            intake.linked_student = student
            intake.status = IntakeStatus.MATCHED
            intake.save(update_fields=['linked_student', 'status', 'updated_at'])

        result = CreateStudentInvitation(DjangoStudentIdentityRepository()).execute(
            CreateStudentInvitationCommand(
                student_id=student.id,
                invited_email=(student.email or '').strip().lower(),
                box_root_slug=get_box_runtime_slug(),
                onboarding_journey=StudentOnboardingJourney.IMPORTED_LEAD_INVITE,
                actor_id=request.user.id,
            )
        )
        if not result.success or result.invitation is None:
            messages.error(request, 'Nao foi possivel preparar o convite do lead para o app agora.')
            return redirect(self._get_success_url(request.POST.get('return_query', '')))

        invitation = StudentAppInvitation.objects.select_related('student').get(pk=result.invitation.id)
        invite_url = request.build_absolute_uri(reverse('student-identity-invite', kwargs={'token': invitation.token}))
        whatsapp_url = build_invitation_whatsapp_url(invitation=invitation, invite_url=invite_url)
        if not whatsapp_url:
            messages.error(request, 'Nao foi possivel abrir o WhatsApp para esse lead agora.')
            return redirect(self._get_success_url(request.POST.get('return_query', '')))

        record_student_invitation_whatsapp_handoff(
            invitation=invitation,
            actor=request.user,
            recipient=student.phone,
            metadata={'invite_url': invite_url, 'source': 'intake_center'},
        )
        record_student_onboarding_event(
            actor=request.user,
            actor_role=role_slug,
            journey=StudentOnboardingJourney.IMPORTED_LEAD_INVITE,
            event='whatsapp_handoff_opened',
            target_model='student_identity.StudentAppInvitation',
            target_id=str(invitation.id),
            target_label=student.full_name,
            description='Handoff do WhatsApp aberto a partir da Central de Entradas.',
            metadata={
                'box_root_slug': get_box_runtime_slug(),
                'student_id': student.id,
                'invitation_id': invitation.id,
                'intake_id': intake.id,
                'source_surface': 'intake_center',
            },
        )
        return redirect(whatsapp_url)

    def _resolve_or_create_student_from_intake(self, *, intake: StudentIntake):
        phone_lookup_index = generate_blind_index(intake.phone)
        student = None
        if phone_lookup_index:
            student = Student.objects.filter(phone_lookup_index=phone_lookup_index).first()
        if student is not None:
            return student
        return Student.objects.create(
            full_name=intake.full_name,
            phone=intake.phone,
            email=getattr(intake, 'email', '') or '',
            status=StudentStatus.LEAD,
        )


class IntakeSearchIndexPageView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER, ROLE_RECEPTION)

    def get(self, request, *args, **kwargs):
        current_role = get_user_role(request.user)
        offset = _parse_non_negative_int(request.GET.get('offset'), default=0)
        index_params = _clean_intake_search_index_params(request.GET)
        snapshot = build_intake_center_snapshot(
            params=index_params,
            actor_role_slug=getattr(current_role, 'slug', ''),
            queue_limit=INTAKE_SEARCH_PAGE_LIMIT,
            queue_offset=offset,
        )
        request.intake_page_capabilities = {
            'can_manage_students': getattr(current_role, 'slug', '') in (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION),
            'can_work_queue': getattr(current_role, 'slug', '') in (ROLE_OWNER, ROLE_MANAGER, ROLE_RECEPTION),
        }
        return JsonResponse(
            {
                'cache_key': index_params.urlencode() or 'all',
                'refresh_token': snapshot.get('queue_refresh_token', ''),
                'page_size': INTAKE_SEARCH_PAGE_LIMIT,
                'total': snapshot.get('queue_total_count', 0),
                'has_next': snapshot.get('queue_has_next', False),
                'next_offset': snapshot.get('queue_next_offset'),
                'index': [
                    _serialize_intake_search_entry(item=item, request=request)
                    for item in snapshot.get('queue_items', [])
                ],
            }
        )


__all__ = ['IntakeCenterView', 'IntakeSearchIndexPageView']
