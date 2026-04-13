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

from django.db.models import Case, CharField, DecimalField, Exists, OuterRef, Q, Subquery, Value, When, Sum, Count, IntegerField, Max
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

    students = students.defer('cpf', 'notes', 'health_issue_status', 'updated_at').order_by('full_name')
    filter_form = StudentDirectoryFilterForm(params or None)

    if filter_form.is_valid():
        query = (filter_form.cleaned_data.get('query') or '').strip()
        if query == '/':
            query = ''
        created_window = filter_form.cleaned_data.get('created_window')
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
        if created_window == '30d':
            students = students.filter(created_at__gte=thirty_days_ago)

    metrics = students.aggregate(
        total=Count('id', distinct=True),
        ativos=Count('id', filter=Q(status=StudentStatus.ACTIVE), distinct=True),
        em_dia=Count('id', filter=Q(status=StudentStatus.ACTIVE, operational_payment_status=PaymentStatus.PAID), distinct=True),
        inadimplentes=Count('id', filter=Q(operational_payment_status=PaymentStatus.OVERDUE), distinct=True),
        pendentes=Count('id', filter=Q(operational_payment_status=PaymentStatus.PENDING), distinct=True),
        inativos=Count('id', filter=Q(status=StudentStatus.INACTIVE), distinct=True),
        novos_30d=Count('id', filter=Q(created_at__gte=thirty_days_ago), distinct=True),
        latest_student_updated_at=Max('updated_at'),
        latest_enrollment_updated_at=Max('enrollments__updated_at'),
        latest_payment_updated_at=Max('payments__updated_at'),
        latest_attendance_updated_at=Max('attendances__updated_at'),
    )

    total_students = metrics['total']
    ativos_count = metrics['ativos']
    em_dia_count = metrics['em_dia']
    inadimplentes_count = metrics['inadimplentes']
    pendentes_count = metrics['pendentes']
    inativos_count = metrics['inativos']
    novos_30d_count = metrics['novos_30d']
    directory_refresh_token = '{total}:{student}:{enrollment}:{payment}:{attendance}'.format(
        total=total_students or 0,
        student=(metrics['latest_student_updated_at'].isoformat() if metrics['latest_student_updated_at'] else ''),
        enrollment=(metrics['latest_enrollment_updated_at'].isoformat() if metrics['latest_enrollment_updated_at'] else ''),
        payment=(metrics['latest_payment_updated_at'].isoformat() if metrics['latest_payment_updated_at'] else ''),
        attendance=(metrics['latest_attendance_updated_at'].isoformat() if metrics['latest_attendance_updated_at'] else ''),
    )

    pending_intakes_count = count_pending_intakes()
    intake_queue = list(get_intake_conversion_queue(limit=6))

    priority_students_queryset = students.filter(
        Q(operational_payment_status=PaymentStatus.OVERDUE)
        | Q(status=StudentStatus.LEAD)
        | Q(latest_enrollment_status=EnrollmentStatus.PENDING)
    )
    priority_students = priority_students_queryset.order_by('full_name')[:6]

    visible_students = list(students)
    for student in visible_students:
        student.is_new_30d = bool(student.created_at and student.created_at >= thirty_days_ago)
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
                'label': 'Ativos',
                'display_value': ativos_count,
                'note': 'Mostra a leitura da base ativa e abre o diretorio principal sem navegar para outra URL.',
                'icon': _catalog_kpi_icon('active'),
                'tone_class': 'kpi-green',
                'data_action': 'open-tab-students-active',
                'target_panel': 'tab-students-directory',
                'student_filter': 'active',
                'is_selected': True,
            },
            {
                'label': 'Inadimplentes',
                'display_value': inadimplentes_count,
                'note': 'Mostra a leitura de atraso e aplica o recorte financeiro no diretorio sem trocar de pagina.',
                'icon': _catalog_kpi_icon('overdue'),
                'tone_class': 'kpi-red',
                'data_action': 'open-tab-students-overdue',
                'target_panel': 'tab-students-directory',
                'student_filter': 'overdue',
                'is_selected': False,
            },
            {
                'label': 'Novos (30D)',
                'display_value': novos_30d_count,
                'note': 'Mostra alunos criados nos ultimos 30 dias e aplica o recorte no diretorio sem navegar.',
                'icon': _catalog_kpi_icon('growth'),
                'tone_class': 'kpi-cyan',
                'data_action': 'open-tab-students-new',
                'target_panel': 'tab-students-directory',
                'student_filter': 'new-30d',
                'is_selected': False,
            },
            {
                'label': 'Inativos',
                'display_value': inativos_count,
                'note': 'Mostra a leitura de alunos inativos e abre a base principal sem trocar de pagina.',
                'icon': _catalog_kpi_icon('inactive'),
                'tone_class': 'kpi-purple',
                'data_action': 'open-tab-students-inactive',
                'target_panel': 'tab-students-directory',
                'student_filter': 'inactive',
                'is_selected': False,
            },
        ],
        'priority_students': priority_students,
        'intake_queue': intake_queue,
        'pending_intakes_count': pending_intakes_count,
        'em_dia_count': em_dia_count,
        'pendentes_count': pendentes_count,
        'directory_refresh_token': directory_refresh_token,
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


__all__ = ['build_student_directory_snapshot', 'build_student_financial_snapshot', 'compute_fidalgometro_score', 'get_operational_enrollment', 'get_operational_payment_status', 'get_operational_payment_status_label']
