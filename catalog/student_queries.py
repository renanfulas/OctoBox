"""
ARQUIVO: leituras de alunos do catalogo.

POR QUE ELE EXISTE:
- centraliza snapshots e filtros da area de alunos no app real do catalogo.

O QUE ESTE ARQUIVO FAZ:
1. monta o snapshot do diretorio de alunos com filtros e funil.
2. monta o snapshot financeiro da ficha do aluno.

PONTOS CRITICOS:
- mudancas aqui afetam listagens, busca comercial e leitura financeira por aluno.
"""

from datetime import timedelta

from django.db.models import Case, CharField, Exists, OuterRef, Q, Subquery, Value, When, Sum, Count, IntegerField
from django.db.models.functions import Coalesce
from django.utils import timezone
from operations.models import Attendance
from finance.models import Enrollment, EnrollmentStatus, Payment, PaymentStatus
from onboarding.queries import count_pending_intakes, get_intake_conversion_queue
from shared_support.kpi_icons import build_kpi_icon
from students.models import Student, StudentStatus

from catalog.forms import StudentDirectoryFilterForm
from shared_support.redis_snapshots import get_student_snapshot, update_student_snapshot


def _catalog_kpi_icon(name):
    icon_map = {
        'active': 'active',
        'overdue': 'alert',
        'growth': 'trend',
        'inactive': 'inactive',
    }
    return build_kpi_icon(icon_map.get(name, ''))


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


def build_student_directory_snapshot(params=None, for_export=False):
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    latest_enrollment_status = Enrollment.objects.filter(student=OuterRef('pk')).order_by('-start_date', '-created_at').values('status')[:1]
    latest_plan_name = Enrollment.objects.filter(student=OuterRef('pk')).order_by('-start_date', '-created_at').values('plan__name')[:1]
    latest_payment_status = Payment.objects.filter(student=OuterRef('pk')).order_by('-due_date', '-created_at').values('status')[:1]
    latest_payment_due_date = Payment.objects.filter(student=OuterRef('pk')).order_by('-due_date', '-created_at').values('due_date')[:1]
    overdue_payment_exists = Payment.objects.filter(student=OuterRef('pk'), status=PaymentStatus.OVERDUE)
    pending_payment_exists = Payment.objects.filter(student=OuterRef('pk'), status=PaymentStatus.PENDING)

    students = Student.objects.annotate(
        latest_enrollment_status=Subquery(latest_enrollment_status),
        latest_plan_name=Subquery(latest_plan_name),
        latest_payment_status=Subquery(latest_payment_status),
        latest_payment_due_date=Subquery(latest_payment_due_date),
        has_overdue_payment=Exists(overdue_payment_exists),
        has_pending_payment=Exists(pending_payment_exists),
    ).annotate(
        operational_payment_status=Case(
            When(has_overdue_payment=True, then=Value(PaymentStatus.OVERDUE)),
            When(has_pending_payment=True, then=Value(PaymentStatus.PENDING)),
            default=Subquery(latest_payment_status),
            output_field=CharField(),
        ),
        recent_presence_total=Coalesce(
            Count(
                'attendances',
                filter=Q(
                    attendances__session__scheduled_at__gte=thirty_days_ago,
                    attendances__status__in=['checked_in', 'checked_out', 'absent'],
                ),
                distinct=True,
            ),
            0,
            output_field=IntegerField(),
        ),
        recent_presence_attended=Coalesce(
            Count(
                'attendances',
                filter=Q(
                    attendances__session__scheduled_at__gte=thirty_days_ago,
                    attendances__status__in=['checked_in', 'checked_out'],
                ),
                distinct=True,
            ),
            0,
            output_field=IntegerField(),
        ),
    )

    if for_export:
        last_check_in = Attendance.objects.filter(
            student=OuterRef('pk'),
            check_in_at__isnull=False,
        ).order_by('-check_in_at').values('check_in_at')[:1]
        amount_paid_sum = Payment.objects.filter(student=OuterRef('pk'), status=PaymentStatus.PAID).order_by().values('student').annotate(total=Sum('amount')).values('total')
        amount_open_sum = Payment.objects.filter(student=OuterRef('pk'), status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE]).order_by().values('student').annotate(total=Sum('amount')).values('total')
        overdue_count = Payment.objects.filter(student=OuterRef('pk'), status=PaymentStatus.OVERDUE).order_by().values('student').annotate(c=Count('id')).values('c')

        students = students.annotate(
            report_last_check_in=Subquery(last_check_in),
            report_amount_paid=Subquery(amount_paid_sum),
            report_amount_open=Subquery(amount_open_sum),
            report_overdue_count=Subquery(overdue_count),
        )

    students = students.defer('cpf', 'notes', 'health_issue_status', 'created_at', 'updated_at').order_by('full_name')
    filter_form = StudentDirectoryFilterForm(params or None)

    if filter_form.is_valid():
        query = (filter_form.cleaned_data.get('query') or '').strip()
        student_status = filter_form.cleaned_data.get('student_status')
        commercial_status = filter_form.cleaned_data.get('commercial_status')
        payment_status = filter_form.cleaned_data.get('payment_status')

        if query:
            normalized_query = query.lower()
            clean_digits = ''.join(filter(str.isdigit, query))

            query_filter = Q(full_name__icontains=query) | Q(email__icontains=query)

            if clean_digits:
                query_filter |= Q(phone__icontains=clean_digits)
                query_filter |= Q(whatsapp__icontains=clean_digits)
                query_filter |= Q(cpf__icontains=clean_digits)

            query_filter |= Q(enrollments__plan__name__icontains=query)
            query_filter |= Q(status__icontains=normalized_query)

            students = students.filter(query_filter).distinct()
        if student_status:
            students = students.filter(status=student_status)
        if commercial_status:
            students = students.filter(latest_enrollment_status=commercial_status)
        if payment_status:
            students = students.filter(operational_payment_status=payment_status)

    metrics = students.aggregate(
        total=Count('id'),
        ativos=Count('id', filter=Q(status=StudentStatus.ACTIVE)),
        em_dia=Count('id', filter=Q(status=StudentStatus.ACTIVE, operational_payment_status=PaymentStatus.PAID)),
        inadimplentes=Count('id', filter=Q(operational_payment_status=PaymentStatus.OVERDUE)),
        pendentes=Count('id', filter=Q(operational_payment_status=PaymentStatus.PENDING)),
        inativos=Count('id', filter=Q(status=StudentStatus.INACTIVE)),
        novos_30d=Count('id', filter=Q(created_at__gte=thirty_days_ago)),
    )

    total_students = metrics['total']
    ativos_count = metrics['ativos']
    em_dia_count = metrics['em_dia']
    inadimplentes_count = metrics['inadimplentes']
    pendentes_count = metrics['pendentes']
    inativos_count = metrics['inativos']
    novos_30d_count = metrics['novos_30d']

    pending_intakes_count = count_pending_intakes()
    intake_queue = list(get_intake_conversion_queue(limit=6))

    priority_students = students.filter(
        Q(operational_payment_status=PaymentStatus.OVERDUE)
        | Q(status=StudentStatus.LEAD)
        | Q(latest_enrollment_status=EnrollmentStatus.PENDING)
    ).order_by('full_name')[:6]

    visible_students = list(students)
    for student in visible_students:
        total_presence = getattr(student, 'recent_presence_total', 0) or 0
        attended_presence = getattr(student, 'recent_presence_attended', 0) or 0
        if total_presence > 0:
            student.presence_percent = round((attended_presence / total_presence) * 100)
        else:
            student.presence_percent = 0

    return {
        'students': visible_students,
        'total_students': total_students,
        'filter_form': filter_form,
        'interactive_kpis': [
            {
                'label': 'Alunos ativos',
                'display_value': ativos_count,
                'icon': _catalog_kpi_icon('active'),
                'tone_class': 'kpi-green',
                'data_action': 'open-tab-students-directory',
            },
            {
                'label': 'Inadimplentes',
                'display_value': inadimplentes_count,
                'icon': _catalog_kpi_icon('overdue'),
                'tone_class': 'kpi-red',
                'href': '?payment_status=overdue#tab-students-directory',
                'data_action': 'open-tab-students-priority',
            },
            {
                'label': 'Novos (30D)',
                'display_value': novos_30d_count,
                'icon': _catalog_kpi_icon('growth'),
                'tone_class': 'kpi-cyan',
                'href': '?created_window=30d#tab-students-directory',
                'data_action': 'open-tab-students-intake',
            },
            {
                'label': 'Inativos',
                'display_value': inativos_count,
                'icon': _catalog_kpi_icon('inactive'),
                'tone_class': 'kpi-purple',
                'href': '?student_status=inactive#tab-students-directory',
                'data_action': 'open-tab-students-filters',
            },
        ],
        'priority_students': priority_students,
        'intake_queue': intake_queue,
        'pending_intakes_count': pending_intakes_count,
        'em_dia_count': em_dia_count,
        'pendentes_count': pendentes_count,
    }


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
    latest_enrollment = enrollments.first()

    today = timezone.localdate()
    seven_days_from_now = today + timezone.timedelta(days=7)

    proximos_vencimentos_count = 0
    payments_list = []
    for payment in raw_payments:
        payment.is_next_actionable = False
        if payment.status == PaymentStatus.OVERDUE:
            payment.is_next_actionable = True
        elif payment.status == PaymentStatus.PENDING and payment.due_date <= seven_days_from_now:
            payment.is_next_actionable = True
            proximos_vencimentos_count += 1
        payments_list.append(payment)

    payments_list.sort(key=lambda item: item.due_date, reverse=True)

    return {
        'has_student': True,
        'summary': 'Aqui fica a leitura de plano, status comercial e ultimos movimentos financeiros do aluno.',
        'latest_enrollment': latest_enrollment,
        'enrollment_history': enrollments[:6],
        'payments': payments_list,
        'fidalgometro': compute_fidalgometro_score(student),
        'metrics': {
            'matriculas_ativas': enrollments.filter(status=EnrollmentStatus.ACTIVE).count(),
            'pagamentos_pendentes': student.payments.filter(status=PaymentStatus.PENDING).count(),
            'pagamentos_atrasados': student.payments.filter(status=PaymentStatus.OVERDUE).count(),
            'proximos_vencimentos_count': proximos_vencimentos_count,
        },
    }


__all__ = ['build_student_directory_snapshot', 'build_student_financial_snapshot', 'compute_fidalgometro_score']
