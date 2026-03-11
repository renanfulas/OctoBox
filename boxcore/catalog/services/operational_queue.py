"""
ARQUIVO: snapshot e metricas da regua operacional de cobranca e retencao.

POR QUE ELE EXISTE:
- Explicita pelo nome do arquivo que esta camada entrega build_operational_queue_snapshot e build_operational_queue_metrics.

O QUE ESTE ARQUIVO FAZ:
1. Monta fila de lembretes de vencimento, atraso e reativacao.
2. Resume a regua em metricas operacionais simples.
3. Expoe mensagens sugeridas para o time agir rapido.

PONTOS CRITICOS:
- A priorizacao precisa permanecer previsivel e objetiva para o time.
"""

from django.utils import timezone

from boxcore.models import Enrollment, EnrollmentStatus, Payment, PaymentStatus

from .communications import build_message_body, normalize_payment_status


def build_operational_queue_snapshot(*, limit=9):
    today = timezone.localdate()
    soon_threshold = today + timezone.timedelta(days=3)

    upcoming_payments = list(
        Payment.objects.select_related('student', 'enrollment__plan')
        .filter(status=PaymentStatus.PENDING, due_date__gte=today, due_date__lte=soon_threshold)
        .order_by('due_date', 'student__full_name')[:3]
    )
    overdue_payments = [
        normalize_payment_status(payment)
        for payment in Payment.objects.select_related('student', 'enrollment__plan')
        .filter(status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE], due_date__lt=today)
        .order_by('due_date', 'student__full_name')[:3]
    ]
    reactivation_candidates = list(
        Enrollment.objects.select_related('student', 'plan')
        .filter(status__in=[EnrollmentStatus.CANCELED, EnrollmentStatus.EXPIRED], end_date__isnull=False)
        .order_by('-end_date', '-updated_at')[:3]
    )

    queue = []
    for payment in upcoming_payments:
        queue.append(
            {
                'kind': 'upcoming',
                'title': 'Lembrete de vencimento',
                'student': payment.student,
                'payment': payment,
                'enrollment': payment.enrollment,
                'pill': 'Vence em breve',
                'summary': f'{payment.student.full_name} | vence em {payment.due_date:%d/%m/%Y} | R$ {payment.amount}',
                'suggested_message': build_message_body(action_kind='upcoming', student=payment.student, payment=payment),
            }
        )
    for payment in overdue_payments:
        queue.append(
            {
                'kind': 'overdue',
                'title': 'Cobranca em atraso',
                'student': payment.student,
                'payment': payment,
                'enrollment': payment.enrollment,
                'pill': 'Atrasado',
                'pill_class': 'warning',
                'summary': f'{payment.student.full_name} | venceu em {payment.due_date:%d/%m/%Y} | R$ {payment.amount}',
                'suggested_message': build_message_body(action_kind='overdue', student=payment.student, payment=payment),
            }
        )
    for enrollment in reactivation_candidates:
        queue.append(
            {
                'kind': 'reactivation',
                'title': 'Tentativa de reativacao',
                'student': enrollment.student,
                'payment': None,
                'enrollment': enrollment,
                'pill': 'Retencao',
                'pill_class': 'info',
                'summary': f'{enrollment.student.full_name} | plano {enrollment.plan.name} | fim em {enrollment.end_date:%d/%m/%Y}',
                'suggested_message': build_message_body(action_kind='reactivation', student=enrollment.student, enrollment=enrollment),
            }
        )
    return queue[:limit]


def build_operational_queue_metrics(queue):
    return {
        'vencendo': sum(1 for item in queue if item['kind'] == 'upcoming'),
        'atrasados': sum(1 for item in queue if item['kind'] == 'overdue'),
        'reativacao': sum(1 for item in queue if item['kind'] == 'reactivation'),
    }


build_operational_queue = build_operational_queue_snapshot
summarize_operational_queue = build_operational_queue_metrics