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
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views import View

from access.permissions import RoleRequiredMixin
from access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION
from catalog.forms import PaymentManagementForm
from catalog.services.student_payment_actions import handle_student_payment_action
from finance.models import Payment
from operations.facade import (
    run_apply_attendance_action,
    run_create_technical_behavior_note,
    run_link_payment_enrollment,
)
from operations.models import Attendance, BehaviorCategory
from students.models import Student


def _append_fragment_to_url(url, fragment):
    if not fragment:
        return url
    parsed_url = urlsplit(url)
    return urlunsplit((parsed_url.scheme, parsed_url.netloc, parsed_url.path, parsed_url.query, fragment))


def _redirect_back(request, *, fallback_url, fragment=''):
    target_url = request.META.get('HTTP_REFERER', fallback_url)
    return HttpResponseRedirect(_append_fragment_to_url(target_url, fragment))


class PaymentEnrollmentLinkView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_MANAGER,)

    def post(self, request, payment_id, *args, **kwargs):
        get_object_or_404(Payment.objects.select_related('student'), pk=payment_id)
        run_link_payment_enrollment(actor_id=request.user.id, payment_id=payment_id)
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/operacao/manager/'))


class TechnicalBehaviorNoteCreateView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_COACH,)

    def post(self, request, student_id, *args, **kwargs):
        get_object_or_404(Student, pk=student_id)
        run_create_technical_behavior_note(
            actor_id=request.user.id,
            student_id=student_id,
            category=request.POST.get('category', BehaviorCategory.SUPPORT),
            description=request.POST.get('description', '').strip(),
        )
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/operacao/coach/'))


class AttendanceActionView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_COACH,)

    def post(self, request, attendance_id, action, *args, **kwargs):
        get_object_or_404(Attendance.objects.select_related('session'), pk=attendance_id)
        if run_apply_attendance_action(
            actor_id=request.user.id,
            attendance_id=attendance_id,
            action=action,
        ) is None:
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/operacao/coach/'))
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/operacao/coach/'))


class ReceptionPreviewPaymentActionView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER,)

    def post(self, request, payment_id, *args, **kwargs):
        return _handle_reception_payment_action(request, payment_id=payment_id, fallback_url='/operacao/recepcao-preview/', success_context='preview da Recepcao')


class ReceptionPaymentActionView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_OWNER, ROLE_RECEPTION)

    def post(self, request, payment_id, *args, **kwargs):
        return _handle_reception_payment_action(request, payment_id=payment_id, fallback_url='/operacao/recepcao/', success_context='Recepcao')


def _handle_reception_payment_action(request, *, payment_id, fallback_url, success_context):
        payment = get_object_or_404(Payment.objects.select_related('student'), pk=payment_id)
        action = request.POST.get('action')
        form = PaymentManagementForm(request.POST)

        if not form.is_valid():
            messages.error(request, 'A cobranca curta nao foi aplicada. Revise vencimento, metodo e referencia.')
            return _redirect_back(request, fallback_url=fallback_url, fragment='reception-payment-board')

        if action not in ('update-payment', 'mark-paid'):
            messages.error(request, 'A Recepcao so permite ajuste curto ou confirmacao de pagamento nesse fluxo.')
            return _redirect_back(request, fallback_url=fallback_url, fragment='reception-payment-board')

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
