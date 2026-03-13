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

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views import View

from access.permissions import RoleRequiredMixin
from access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER
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
        payment = get_object_or_404(Payment.objects.select_related('student'), pk=payment_id)
        action = request.POST.get('action')
        form = PaymentManagementForm(request.POST)

        if not form.is_valid():
            messages.error(request, 'A cobranca curta nao foi aplicada. Revise vencimento, metodo e referencia.')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/operacao/recepcao-preview/'))

        if action not in ('update-payment', 'mark-paid'):
            messages.error(request, 'A Recepcao em preparo so permite ajuste curto ou confirmacao de pagamento.')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/operacao/recepcao-preview/'))

        handle_student_payment_action(
            actor=request.user,
            student=payment.student,
            payment=payment,
            action=action,
            payload=form.cleaned_data,
        )

        if action == 'mark-paid':
            messages.success(request, f'Pagamento de {payment.student.full_name} confirmado pelo preview da Recepcao.')
        else:
            messages.success(request, f'Cobranca curta de {payment.student.full_name} ajustada sem sair do preview.')

        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/operacao/recepcao-preview/'))
