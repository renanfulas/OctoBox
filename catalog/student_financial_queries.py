"""
ARQUIVO: leituras do corredor financeiro da ficha do aluno.

POR QUE ELE EXISTE:
- tira de `student_queries.py` o miolo financeiro e deixa a fachada publica mais leve.
"""

from datetime import timedelta

from django.db.models import Count, DecimalField, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from finance.models import EnrollmentStatus, PaymentStatus
from operations.models import Attendance
from shared_support.redis_snapshots import get_student_snapshot, update_student_snapshot


def get_operational_enrollment(student):
    """
    Resolve a matricula que deve governar a leitura operacional atual.

    Regra:
    1. prioriza matricula ativa
    2. depois uma pendente
    3. se nao houver nenhuma das duas, usa a mais recente
    """
    enrollments = list(
        student.enrollments.select_related('plan').order_by('-start_date', '-created_at')
    )
    if not enrollments:
        return None

    for enrollment in enrollments:
        if enrollment.status == EnrollmentStatus.ACTIVE:
            return enrollment

    for enrollment in enrollments:
        if enrollment.status == EnrollmentStatus.PENDING:
            return enrollment

    return enrollments[0]


def get_operational_payment_status(payment, *, today=None):
    """
    Resolve o status financeiro operacional real da cobranca.

    Regra:
    1. se estiver aberta e a data ja passou, lemos como atrasada
    2. se estiver aberta e a data ainda nao passou, lemos como pendente
    3. status fechados preservam o valor persistido
    """
    if not payment:
        return ''

    today = today or timezone.localdate()
    if payment.status in [PaymentStatus.PENDING, PaymentStatus.OVERDUE]:
        if payment.due_date and payment.due_date < today:
            return PaymentStatus.OVERDUE
        return PaymentStatus.PENDING

    return payment.status


def get_operational_payment_status_label(payment, *, today=None):
    status = get_operational_payment_status(payment, today=today)
    try:
        return PaymentStatus(status).label
    except Exception:
        return getattr(payment, 'get_status_display', lambda: status)()


def compute_fidalgometro_score(student):
    """
    Computa o score de saude (Fidalgometro) do aluno:
    - RED: Inadimplente (cobranca vencida).
    - YELLOW: Sumido (pago mas sem treino ha > 7 dias).
    - BLUE: Fiel (pago e treinou recentemente).
    """
    if not student:
        return {'code': 'gray', 'label': 'Sem dados', 'detail': 'Dados insuficientes.'}

    has_overdue = student.payments.filter(
        status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE],
        due_date__lt=timezone.localdate(),
    ).exists()

    if has_overdue:
        return {'code': 'red', 'label': 'Inadimplente', 'detail': 'Ha cobrancas vencidas.'}

    last_attendance = Attendance.objects.filter(student=student, check_in_at__isnull=False).order_by('-check_in_at').first()
    if not last_attendance:
        return {'code': 'orange', 'label': 'Sem Treino', 'detail': 'Ainda nao registrou check-in no Box.'}

    days_ago = (timezone.now() - last_attendance.check_in_at).days
    if days_ago > 7:
        return {'code': 'yellow', 'label': f'Sumido ({days_ago} dias)', 'detail': 'Nao treina ha mais de uma semana.'}

    return {'code': 'blue', 'label': 'Fiel & Ativo', 'detail': 'Pagamentos em dia e treinou recentemente.'}


def build_student_financial_snapshot(student):
    if not student:
        return {
            'has_student': False,
            'summary': 'Salve o aluno primeiro para conectar plano, matricula e rotina financeira.',
            'latest_enrollment': None,
            'enrollment_history': [],
            'payments': [],
            'metrics': {},
            'fidalgometro': compute_fidalgometro_score(None),
        }

    ghost = get_student_snapshot(student.id)
    if not ghost:
        ghost = update_student_snapshot(student.id)

    enrollments = student.enrollments.select_related('plan').order_by('-start_date', '-created_at')
    raw_payments = student.payments.select_related('enrollment').order_by('due_date', 'created_at')[:6]
    latest_enrollment = get_operational_enrollment(student)

    today = timezone.localdate()
    seven_days_from_now = today + timezone.timedelta(days=7)
    all_payments_qs = student.payments.all()
    open_payments_queryset = all_payments_qs.filter(status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE])
    next_charge = open_payments_queryset.order_by('due_date', 'created_at').first()
    recent_presence_total = Attendance.objects.filter(student=student, session__scheduled_at__date__gte=today - timedelta(days=30)).count()
    recent_presence_attended = Attendance.objects.filter(
        student=student,
        session__scheduled_at__date__gte=today - timedelta(days=30),
        status='attended',
    ).count()
    presenca_percentual_30d = round((recent_presence_attended / recent_presence_total) * 100) if recent_presence_total else 0

    proximos_vencimentos_count = 0
    payments_list = []
    for payment in raw_payments:
        payment.operational_status = get_operational_payment_status(payment, today=today)
        payment.operational_status_label = get_operational_payment_status_label(payment, today=today)
        payment.is_next_actionable = False
        if payment.operational_status == PaymentStatus.OVERDUE:
            payment.is_next_actionable = True
        elif payment.operational_status == PaymentStatus.PENDING and payment.due_date <= seven_days_from_now:
            payment.is_next_actionable = True
            proximos_vencimentos_count += 1
        payments_list.append(payment)

    payments_list.sort(key=lambda item: item.due_date, reverse=True)

    if next_charge:
        next_charge.days_overdue = max((today - next_charge.due_date).days, 0) if next_charge.due_date and next_charge.due_date < today else 0

    payment_totals = all_payments_qs.aggregate(
        total_recebido=Coalesce(Sum('amount', filter=Q(status=PaymentStatus.PAID)), 0, output_field=DecimalField(max_digits=10, decimal_places=2)),
        total_pendente=Coalesce(Sum('amount', filter=Q(status=PaymentStatus.PENDING)), 0, output_field=DecimalField(max_digits=10, decimal_places=2)),
        total_atrasado=Coalesce(Sum('amount', filter=Q(status=PaymentStatus.OVERDUE)), 0, output_field=DecimalField(max_digits=10, decimal_places=2)),
        total_historico=Coalesce(Sum('amount'), 0, output_field=DecimalField(max_digits=10, decimal_places=2)),
        transacoes_totais=Count('id'),
        pagamentos_pendentes=Count('id', filter=Q(status=PaymentStatus.PENDING)),
        pagamentos_atrasados=Count('id', filter=Q(status=PaymentStatus.OVERDUE)),
    )

    return {
        'has_student': True,
        'summary': 'Aqui fica a leitura de plano, status comercial e ultimos movimentos financeiros do aluno.',
        'latest_enrollment': latest_enrollment,
        'enrollment_history': enrollments[:6],
        'payments': payments_list,
        'next_charge': next_charge,
        'fidalgometro': compute_fidalgometro_score(student),
        'metrics': {
            'matriculas_ativas': enrollments.filter(status=EnrollmentStatus.ACTIVE).count(),
            'pagamentos_pendentes': payment_totals['pagamentos_pendentes'],
            'pagamentos_atrasados': payment_totals['pagamentos_atrasados'],
            'proximos_vencimentos_count': proximos_vencimentos_count,
            'total_recebido': payment_totals['total_recebido'],
            'total_pendente': payment_totals['total_pendente'],
            'total_atrasado': payment_totals['total_atrasado'],
            'total_historico': payment_totals['total_historico'],
            'transacoes_totais': payment_totals['transacoes_totais'],
            'proximo_vencimento': next_charge.due_date if next_charge else None,
            'presenca_total_30d': recent_presence_total,
            'presenca_atendida_30d': recent_presence_attended,
            'presenca_percentual_30d': presenca_percentual_30d,
        },
    }


__all__ = [
    'build_student_financial_snapshot',
    'compute_fidalgometro_score',
    'get_operational_enrollment',
    'get_operational_payment_status',
    'get_operational_payment_status_label',
]
