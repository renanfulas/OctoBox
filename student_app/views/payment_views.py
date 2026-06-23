"""
ARQUIVO: views de pagamento do aluno (self-service).

POR QUE ELE EXISTE:
- Permite o aluno pagar a PROPRIA fatura em aberto, iniciando um checkout Stripe
  a partir do app. Roda no schema do box ativo, entao a baixa segue pelo webhook
  ja existente (router._handle_student_payment).

PONTOS CRITICOS:
- Seguranca: a fatura precisa ser do proprio aluno e estar em aberto
  (resolve_payable_student_invoice). Nunca confiar so no payment_id da URL.
- O aluno nao e request.user do Django; create_checkout_session ja trata ator
  anonimo e recebe as rotas de retorno do /aluno/.
"""

import logging

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from integrations.stripe.services import create_checkout_session
from shared_support.security.fintech_throttles import checkout_rate_limit_exceeded
from student_app.student_payments_presentation import resolve_payable_student_invoice

from .base import StudentIdentityRequiredMixin

logger = logging.getLogger(__name__)


class StudentPayInvoiceView(StudentIdentityRequiredMixin, View):
    def post(self, request, payment_id, *args, **kwargs):
        if checkout_rate_limit_exceeded(request):
            messages.error(request, 'Muitas tentativas em pouco tempo. Tente de novo em instantes.')
            return redirect('student-app-settings')

        student = request.student_identity.student
        payment = resolve_payable_student_invoice(student, payment_id)
        if payment is None:
            messages.error(request, 'Esta cobranca nao esta disponivel para pagamento.')
            return redirect('student-app-settings')

        try:
            success_url = request.build_absolute_uri(reverse('student-app-pay-success'))
            cancel_url = request.build_absolute_uri(reverse('student-app-pay-cancel'))
            checkout_url = create_checkout_session(
                payment, request, success_url=success_url, cancel_url=cancel_url
            )
            return redirect(checkout_url)
        except Exception:
            logger.exception('StudentPayInvoiceView: falha ao abrir checkout. payment=%s', payment_id)
            messages.error(request, 'Nao foi possivel abrir o pagamento agora. Tente de novo em instantes.')
            return redirect('student-app-settings')


class StudentPaySuccessView(StudentIdentityRequiredMixin, TemplateView):
    template_name = 'student_app/pay_success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student_shell_nav'] = 'settings'
        context['student_shell_title'] = 'Pagamento'
        return self._attach_student_shell_context(context)


class StudentPayCancelView(StudentIdentityRequiredMixin, TemplateView):
    template_name = 'student_app/pay_cancel.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student_shell_nav'] = 'settings'
        context['student_shell_title'] = 'Pagamento'
        return self._attach_student_shell_context(context)


__all__ = ['StudentPayInvoiceView', 'StudentPaySuccessView', 'StudentPayCancelView']
