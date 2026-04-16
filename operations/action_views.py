"""
ARQUIVO: views de acoes operacionais por papel.

POR QUE ELE EXISTE:
- expõe as mutacoes reais de manager e coach a partir do app operations.

O QUE ESTE ARQUIVO FAZ:
1. vincula pagamento a matricula.
2. registra ocorrencia tecnica.
3. aplica acoes de presenca.

PONTOS CRITICOS:
- essas rotas disparam mutacoes reais e precisam manter permissao e side effects.
"""

from datetime import timedelta
from urllib.parse import quote, urlsplit, urlunsplit

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View

from access.permissions import RoleRequiredMixin
from access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION
from auditing import log_audit_event
from auditing.models import AuditEvent
from catalog.forms import ReceptionPaymentManagementForm
from catalog.services.student_payment_actions import handle_student_payment_action
from finance.models import Payment
from onboarding.models import StudentIntake
from shared_support.cascade.contracts import build_cascade_intent, merge_cascade_metadata
from shared_support.cascade.ownership import resolve_actor_box_id, resolve_box_owner_user_id
from shared_support.manager_event_stream import publish_manager_stream_event
from shared_support.operational_contact_memory import (
    CONTACT_COOLDOWN_DAYS,
    CONTACT_OWNERSHIP_MANAGER_OWNER,
    CONTACT_STAGE_FIRST_TOUCH_OPENED,
    CONTACT_STAGE_FOLLOW_UP_ACTIVE,
    CONTACT_STAGE_UNREACHED,
    INTAKE_CONTACT_ACTIONS,
    MANAGER_INTAKE_FIRST_TOUCH_ACTION,
    MANAGER_INTAKE_FOLLOW_UP_ACTION,
    build_contact_memory_metadata,
)
from operations.facade import (
    run_apply_attendance_action,
    run_create_technical_behavior_note,
    run_link_payment_enrollment,
)
from operations.forms import TechnicalBehaviorNoteForm
from operations.models import Attendance
from students.models import Student
from communications.application.message_templates import build_operational_message_body
from shared_support.phone_numbers import normalize_phone_number
from .base_views import ManagerWorkspaceAvailabilityMixin


def _append_fragment_to_url(url, fragment):
    if not fragment:
        return url
    parsed_url = urlsplit(url)
    return urlunsplit((parsed_url.scheme, parsed_url.netloc, parsed_url.path, parsed_url.query, fragment))


def _redirect_back(request, *, fallback_url, fragment=''):
    target_url = request.META.get('HTTP_REFERER', fallback_url)
    # 🚀 Segurança de Elite (Ghost Hardening): Host Header Protection
    # Em vez de confiar no Host vindo do Request (que pode ser envenenado),
    # usamos o ALLOWED_HOSTS configurado no servidor.
    allowed_hosts = set(getattr(settings, 'ALLOWED_HOSTS', []))
    if not url_has_allowed_host_and_scheme(target_url, allowed_hosts=allowed_hosts, require_https=request.is_secure()):
        target_url = fallback_url
    return HttpResponseRedirect(_append_fragment_to_url(target_url, fragment))


class PaymentEnrollmentLinkView(ManagerWorkspaceAvailabilityMixin, LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_MANAGER,)

    def post(self, request, payment_id, *args, **kwargs):
        payment = get_object_or_404(Payment.objects.select_related('student'), pk=payment_id)
        result = run_link_payment_enrollment(actor_id=request.user.id, payment_id=payment_id)
        student_financial_url = _append_fragment_to_url(
            reverse('student-quick-update', args=[payment.student_id]),
            'student-financial-overview',
        )
        if result is not None:
            publish_manager_stream_event(
                event_type='student.enrollment.updated',
                meta={
                    'student_id': payment.student_id,
                    'payment_id': result.payment_id,
                    'enrollment_id': result.enrollment_id,
                    'action': 'link-payment-enrollment',
                },
            )
            messages.success(request, 'Pagamento vinculado a matricula ativa e ficha financeira pronta para revisao.')
            return HttpResponseRedirect(student_financial_url)
        messages.error(request, 'Nenhuma matricula ativa foi encontrada para esse aluno. Revise a ficha antes de tentar vincular.')
        return HttpResponseRedirect(student_financial_url)


class ManagerIntakeContactView(ManagerWorkspaceAvailabilityMixin, LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_MANAGER,)

    def post(self, request, intake_id, *args, **kwargs):
        intake = get_object_or_404(StudentIntake, pk=intake_id)
        fallback_url = _append_fragment_to_url(reverse('intake-center'), 'tab-intake-queue')
        clean_phone = normalize_phone_number(getattr(intake, 'phone', ''))
        if not clean_phone:
            messages.warning(request, f'{intake.full_name} ainda nao tem telefone valido para abrir contato pelo WhatsApp.')
            return HttpResponseRedirect(fallback_url)

        if len(clean_phone) in (10, 11):
            clean_phone = f'55{clean_phone}'

        has_prior_touch = AuditEvent.objects.filter(
            action__in=INTAKE_CONTACT_ACTIONS,
            target_model='studentintake',
            target_id=str(intake.id),
        ).exists()
        action_name = MANAGER_INTAKE_FIRST_TOUCH_ACTION if not has_prior_touch else MANAGER_INTAKE_FOLLOW_UP_ACTION
        message_action_kind = 'intake-first-touch' if not has_prior_touch else 'intake-follow-up'
        cascade_action_kind = 'intake_first_touch' if not has_prior_touch else 'intake_follow_up'
        stage_before = CONTACT_STAGE_UNREACHED if not has_prior_touch else CONTACT_STAGE_FOLLOW_UP_ACTIVE
        stage_after = CONTACT_STAGE_FIRST_TOUCH_OPENED if not has_prior_touch else CONTACT_STAGE_FOLLOW_UP_ACTIVE
        cooldown_until = (timezone.now() + timedelta(days=CONTACT_COOLDOWN_DAYS)).isoformat()
        message_body = build_operational_message_body(
            action_kind=message_action_kind,
            first_name=(intake.full_name or 'Aluno').split()[0],
        )
        box_id = resolve_actor_box_id(request.user)
        cascade_intent = build_cascade_intent(
            box_id=box_id,
            owner_user_id=resolve_box_owner_user_id(box_id),
            requested_by_user_id=request.user.id,
            requested_by_role=ROLE_MANAGER,
            subject_type='intake',
            subject_id=intake.id,
            action_kind=cascade_action_kind,
            channel='whatsapp',
            surface='manager',
        )

        log_audit_event(
            actor=request.user,
            action=action_name,
            target=intake,
            description=f'Contato operacional de intake aberto para {intake.full_name}.',
            metadata=merge_cascade_metadata(
                build_contact_memory_metadata(
                    board_key='intake',
                    channel='whatsapp',
                    subject_type='intake',
                    subject_id=intake.id,
                    subject_label=intake.full_name,
                    intake_id=intake.id,
                    stage_before=stage_before,
                    stage_after=stage_after,
                    ownership_scope=CONTACT_OWNERSHIP_MANAGER_OWNER,
                    cooldown_until=cooldown_until,
                    is_first_touch=not has_prior_touch,
                ),
                intent=cascade_intent,
            ),
        )
        publish_manager_stream_event(
            event_type='intake.updated',
            meta={
                'intake_id': intake.id,
                'action': action_name,
            },
        )
        whatsapp_url = f'https://wa.me/{clean_phone}?text={quote(message_body)}'
        return HttpResponseRedirect(whatsapp_url)


class TechnicalBehaviorNoteCreateView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_COACH,)

    def post(self, request, student_id, *args, **kwargs):
        get_object_or_404(Student, pk=student_id)
        form = TechnicalBehaviorNoteForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'A ocorrencia tecnica nao foi registrada. Revise categoria e descricao curta.')
            return _redirect_back(request, fallback_url=reverse('coach-workspace'))
        run_create_technical_behavior_note(
            actor_id=request.user.id,
            student_id=student_id,
            category=form.cleaned_data['category'],
            description=form.cleaned_data['description'],
        )
        return _redirect_back(request, fallback_url=reverse('coach-workspace'))


class AttendanceActionView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_COACH,)
    allowed_actions = {'check-in', 'check-out', 'absent'}

    def post(self, request, attendance_id, action, *args, **kwargs):
        get_object_or_404(Attendance.objects.select_related('session'), pk=attendance_id)
        if action not in self.allowed_actions:
            messages.error(request, 'A acao de presenca enviada nao e permitida nesse fluxo.')
            return _redirect_back(request, fallback_url=reverse('coach-workspace'))
        if run_apply_attendance_action(
            actor_id=request.user.id,
            attendance_id=attendance_id,
            action=action,
        ) is None:
            return _redirect_back(request, fallback_url=reverse('coach-workspace'))
        return _redirect_back(request, fallback_url=reverse('coach-workspace'))


class ReceptionPaymentActionView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER, ROLE_RECEPTION)

    def post(self, request, payment_id, *args, **kwargs):
        # Esta rota mora em operations por ergonomia de shell, mas a mutacao
        # continua pertencendo ao corredor financeiro canonico do catalogo.
        return _handle_reception_payment_action(
            request,
            payment_id=payment_id,
            fallback_url=reverse('reception-workspace'),
            success_context='Recepcao',
        )


def _handle_reception_payment_action(request, *, payment_id, fallback_url, success_context):
    payment = get_object_or_404(Payment.objects.select_related('student'), pk=payment_id)
    form = ReceptionPaymentManagementForm(request.POST)

    if not form.is_valid():
        messages.error(request, 'A cobranca curta nao foi aplicada. Revise vencimento, metodo e referencia.')
        return _redirect_back(request, fallback_url=fallback_url, fragment='reception-payment-board')

    action = form.cleaned_data['action']

    handle_student_payment_action(
        actor=request.user,
        student=payment.student,
        payment=payment,
        action=action,
        payload=form.cleaned_data,
    )

    if action == 'mark-paid':
        messages.success(request, f'Pagamento de {payment.student.full_name} confirmado com sucesso no balcao.')
    else:
        messages.success(request, f'Ajustes rapidos de {payment.student.full_name} salvos sem sair do balcao.')

    publish_manager_stream_event(
        event_type='student.payment.updated',
        meta={
            'student_id': payment.student_id,
            'payment_id': payment.id,
            'action': action,
            'surface': 'reception-payment-board',
        },
    )

    return _redirect_back(request, fallback_url=fallback_url, fragment='reception-payment-board')
