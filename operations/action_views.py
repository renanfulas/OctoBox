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

from urllib.parse import urlsplit, urlunsplit

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View

from access.permissions import RoleRequiredMixin
from access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION
from catalog.forms import ReceptionPaymentManagementForm
from catalog.services.student_payment_actions import handle_student_payment_action
from finance.models import Payment
from operations.facade import (
    run_apply_attendance_action,
    run_create_technical_behavior_note,
    run_link_payment_enrollment,
)
from operations.forms import TechnicalBehaviorNoteForm
from operations.models import Attendance
from students.models import Student


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


class PaymentEnrollmentLinkView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_MANAGER,)

    def post(self, request, payment_id, *args, **kwargs):
        get_object_or_404(Payment.objects.select_related('student'), pk=payment_id)
        run_link_payment_enrollment(actor_id=request.user.id, payment_id=payment_id)
        return _redirect_back(request, fallback_url='/operacao/manager/')


class TechnicalBehaviorNoteCreateView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_COACH,)

    def post(self, request, student_id, *args, **kwargs):
        get_object_or_404(Student, pk=student_id)
        form = TechnicalBehaviorNoteForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'A ocorrencia tecnica nao foi registrada. Revise categoria e descricao curta.')
            return _redirect_back(request, fallback_url='/operacao/coach/')
        run_create_technical_behavior_note(
            actor_id=request.user.id,
            student_id=student_id,
            category=form.cleaned_data['category'],
            description=form.cleaned_data['description'],
        )
        return _redirect_back(request, fallback_url='/operacao/coach/')


class AttendanceActionView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_COACH,)
    allowed_actions = {'check-in', 'check-out', 'absent'}

    def post(self, request, attendance_id, action, *args, **kwargs):
        get_object_or_404(Attendance.objects.select_related('session'), pk=attendance_id)
        if action not in self.allowed_actions:
            messages.error(request, 'A acao de presenca enviada nao e permitida nesse fluxo.')
            return _redirect_back(request, fallback_url='/operacao/coach/')
        if run_apply_attendance_action(
            actor_id=request.user.id,
            attendance_id=attendance_id,
            action=action,
        ) is None:
            return _redirect_back(request, fallback_url='/operacao/coach/')
        return _redirect_back(request, fallback_url='/operacao/coach/')


class ReceptionPaymentActionView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER, ROLE_RECEPTION)

    def post(self, request, payment_id, *args, **kwargs):
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
        messages.success(request, f'Pagamento de {payment.student.full_name} confirmado pela {success_context}.')
    else:
        messages.success(request, f'Cobranca curta de {payment.student.full_name} ajustada sem sair da {success_context}.')

    return _redirect_back(request, fallback_url=fallback_url, fragment='reception-payment-board')
