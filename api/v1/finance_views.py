"""
ARQUIVO: views da capacidade financeira na API v1.

POR QUE ELE EXISTE:
- Reune endpoints financeiros versionados sem misturar manifesto, integracao ou jobs.

O QUE ESTE ARQUIVO FAZ:
1. expõe operacoes financeiras controladas na API.
2. concentra fluxos HTTP que pertencem ao dominio financeiro.

PONTOS CRITICOS:
- endpoints daqui devem continuar pequenos e previsiveis.
"""
import json
import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import F
from django.http import JsonResponse
from django.utils import timezone
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from api.v1.bulk_views import GenericBulkActionView
from catalog.forms import EnrollmentManagementForm, PaymentManagementForm
from catalog.presentation.student_financial_fragments import render_student_financial_fragments
from catalog.student_queries import build_student_financial_snapshot
from finance.models import EnrollmentStatus, Payment, PaymentStatus
from integrations.stripe.services import create_checkout_session
from shared_support.security.fintech_throttles import checkout_rate_limit_exceeded
from students.models import Student

logger = logging.getLogger(__name__)


def _build_payment_management_form(student):
    latest_payment = student.payments.order_by('-due_date', '-created_at').first()
    if latest_payment is None:
        return PaymentManagementForm(
            initial={
                'amount': '',
                'due_date': timezone.localdate().strftime('%d/%m/%Y'),
            }
        )

    return PaymentManagementForm(
        instance=latest_payment,
        initial={
            'payment_id': latest_payment.id,
            'amount': latest_payment.amount,
            'due_date': latest_payment.due_date,
            'method': latest_payment.method,
            'reference': latest_payment.reference,
            'notes': latest_payment.notes,
        },
    )


def _build_enrollment_management_form(student):
    latest_enrollment = student.enrollments.order_by('-start_date', '-created_at').first()
    if latest_enrollment is None:
        return None

    return EnrollmentManagementForm(
        initial={
            'enrollment_id': latest_enrollment.id,
            'action_date': timezone.localdate(),
        }
    )


def _build_financial_fragment_page(student):
    financial_overview = build_student_financial_snapshot(student)
    return {
        'data': {
            'student_object': student,
            'financial_overview': financial_overview,
            'payment_management_form': _build_payment_management_form(student),
            'enrollment_management_form': _build_enrollment_management_form(student),
        }
    }


def _render_financial_fragments(request, student):
    fragments = render_student_financial_fragments(student, request=request)
    fragments['ledger'] = (
        '<div class="student-financial-ledger">'
        f"{fragments.get('ledger', '')}"
        '</div>'
    )
    if not fragments.get('management'):
        fragments['management'] = (
            '<div id="student-payment-management-root">'
            f"{fragments.get('checkout', '')}"
            '</div>'
    )
    return fragments


class PaymentLinkView(LoginRequiredMixin, View):
    """Gera um link de checkout do Stripe para compartilhamento manual."""

    def get(self, request, payment_id, *args, **kwargs):
        # Mesmo guard de card-testing do StripeCheckoutRedirectView: sem isto a
        # API podia cunhar Sessions Stripe ilimitadas (vetor de teste de cartao).
        if checkout_rate_limit_exceeded(request):
            return JsonResponse(
                {'error': 'Muitas tentativas. Tente novamente em instantes.'},
                status=429,
            )

        payment = Payment.objects.filter(pk=payment_id).first()
        if not payment:
            return JsonResponse({'error': 'Payment not found'}, status=404)

        if payment.status == PaymentStatus.PAID:
            return JsonResponse({'error': 'Payment already paid'}, status=400)

        try:
            url = create_checkout_session(payment, request)
            return JsonResponse({'url': url})
        except ValueError as exc:
            # Erro de negocio (ex.: pagamento ja consta como pago) — mensagem
            # ja e segura para o usuario final.
            return JsonResponse({'error': str(exc)}, status=400)
        except Exception:
            # Falha do gateway (Stripe fora do ar, egress bloqueado, etc): loga o
            # detalhe interno e devolve 502 com mensagem de negocio, sem vazar o
            # texto cru do provedor para quem esta na tela.
            logger.exception('PaymentLinkView: falha ao gerar link de pagamento para payment_id=%s', payment_id)
            return JsonResponse(
                {'error': 'Não foi possível gerar o link agora. Tente novamente em instantes ou confirme o pagamento pelo balcão.'},
                status=502,
            )

class StudentFreezeView(LoginRequiredMixin, View):
    """
    "Congela" um aluno por X dias, empurrando o fim da matricula e os vencimentos futuros.
    """
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {'error': 'O corpo da requisicao nao e um JSON valido. Recarregue a pagina e tente novamente.'},
                status=400,
            )
        if not isinstance(data, dict):
            return JsonResponse(
                {'error': 'O corpo da requisicao nao e um JSON valido. Recarregue a pagina e tente novamente.'},
                status=400,
            )

        student_id = data.get('student_id')
        try:
            days = int(data.get('days', 0))
        except (TypeError, ValueError):
            days = 0

        if not student_id or days <= 0:
            return JsonResponse({'error': 'Informe o aluno e uma quantidade de dias maior que zero.'}, status=400)

        try:
            with transaction.atomic():
                student = Student.objects.get(pk=student_id)

                # 1. Update Active Enrollment
                enrollment = student.enrollments.filter(status=EnrollmentStatus.ACTIVE).first()
                if enrollment and enrollment.end_date:
                    enrollment.end_date = enrollment.end_date + timedelta(days=days)
                    enrollment.save()

                # 2. Shift Pending Payments — single UPDATE avoids partial-commit on N saves
                student.payments.filter(status=PaymentStatus.PENDING).update(
                    due_date=F('due_date') + timedelta(days=days)
                )

                return JsonResponse({
                    'status': 'success',
                    'message': f'Aluno {student.full_name} congelado por {days} dias com sucesso.',
                    'fragments': _render_financial_fragments(request, student),
                })

        except Student.DoesNotExist:
            return JsonResponse({'error': 'Student not found'}, status=404)
        except Exception:
            logger.exception('StudentFreezeView: falha ao congelar student_id=%s por %s dias', student_id, days)
            return JsonResponse(
                {'error': 'Não foi possível congelar a matrícula agora. Tente novamente em instantes.'},
                status=500,
            )


class PaymentBulkActionView(GenericBulkActionView):
    """
    Partial-commit bulk mutations for payments.
    Each item runs in its own savepoint; failures on individual payments
    do not roll back successful ones. Returns HTTP 207 when partial.

    Supported actions: mark_paid, mark_cancelled.
    """

    def perform_action(self, item_id, action, user):
        # GenericBulkActionView.post envolve cada item em transaction.atomic(),
        # entao o select_for_update aqui serializa baixas concorrentes do mesmo
        # Payment (race entre abas/operadores) dentro do savepoint do item.
        payment = Payment.objects.select_for_update().get(pk=item_id)
        if action == 'mark_paid':
            if payment.status != PaymentStatus.PAID:
                payment.status = PaymentStatus.PAID
                payment.paid_at = timezone.now()  # antes ficava nulo: quebrava relatorio/auditoria
                payment.version += 1
                payment.save(update_fields=['status', 'paid_at', 'version', 'updated_at'])
        elif action == 'mark_cancelled':
            # Bug: o enum e PaymentStatus.CANCELED (1 L). PaymentStatus.CANCELLED
            # nao existe e levantava AttributeError ao cancelar em massa.
            if payment.status != PaymentStatus.CANCELED:
                payment.status = PaymentStatus.CANCELED
                payment.save(update_fields=['status', 'updated_at'])
        else:
            raise ValueError(f'Acao desconhecida: {action}')
