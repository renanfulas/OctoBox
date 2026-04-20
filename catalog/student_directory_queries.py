"""
ARQUIVO: leituras do corredor de diretorio de alunos.

POR QUE ELE EXISTE:
- tira de `student_queries.py` o miolo de listagem, filtros, metricas e surfaces de apoio do diretorio.
"""

from datetime import timedelta
import time

from django.db.models import Case, CharField, Count, Exists, IntegerField, Max, OuterRef, Q, Subquery, Sum, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone

from catalog.forms import StudentDirectoryFilterForm
from finance.models import Enrollment, EnrollmentStatus, Payment, PaymentStatus
from onboarding.queries import count_pending_intakes, get_intake_conversion_queue
from operations.models import Attendance
from shared_support.kpi_icons import build_kpi_icon
from students.models import Student, StudentStatus


def _catalog_kpi_icon(name):
    icon_map = {
        'active': 'active',
        'overdue': 'alert',
        'growth': 'trend',
        'inactive': 'inactive',
    }
    return build_kpi_icon(icon_map.get(name, ''))


def _build_student_directory_base_queryset(*, today, thirty_days_ago, for_export=False):
    latest_enrollment_status = Enrollment.objects.filter(student=OuterRef('pk')).order_by('-start_date', '-created_at').values('status')[:1]
    latest_plan_name = Enrollment.objects.filter(student=OuterRef('pk')).order_by('-start_date', '-created_at').values('plan__name')[:1]
    latest_payment_status = Payment.objects.filter(student=OuterRef('pk')).order_by('-due_date', '-created_at').values('status')[:1]
    latest_payment_due_date = Payment.objects.filter(student=OuterRef('pk')).order_by('-due_date', '-created_at').values('due_date')[:1]
    overdue_payment_exists = Payment.objects.filter(student=OuterRef('pk')).filter(
        Q(status=PaymentStatus.OVERDUE)
        | Q(status=PaymentStatus.PENDING, due_date__lt=today)
    )
    pending_payment_exists = Payment.objects.filter(
        student=OuterRef('pk'),
        status=PaymentStatus.PENDING,
        due_date__gte=today,
    )

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

    if not for_export:
        return students.defer('cpf', 'notes', 'health_issue_status', 'updated_at').order_by('full_name')

    last_check_in = Attendance.objects.filter(
        student=OuterRef('pk'),
        check_in_at__isnull=False,
    ).order_by('-check_in_at').values('check_in_at')[:1]
    amount_paid_sum = Payment.objects.filter(student=OuterRef('pk'), status=PaymentStatus.PAID).order_by().values('student').annotate(total=Sum('amount')).values('total')
    amount_open_sum = Payment.objects.filter(student=OuterRef('pk'), status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE]).order_by().values('student').annotate(total=Sum('amount')).values('total')
    overdue_count = Payment.objects.filter(student=OuterRef('pk')).filter(
        Q(status=PaymentStatus.OVERDUE)
        | Q(status=PaymentStatus.PENDING, due_date__lt=today)
    ).order_by().values('student').annotate(c=Count('id')).values('c')

    return students.annotate(
        report_last_check_in=Subquery(last_check_in),
        report_amount_paid=Subquery(amount_paid_sum),
        report_amount_open=Subquery(amount_open_sum),
        report_overdue_count=Subquery(overdue_count),
    ).defer('cpf', 'notes', 'health_issue_status', 'updated_at').order_by('full_name')


def _build_student_directory_listing_base_queryset(*, today, include_commercial_status=False):
    latest_payment_status = Payment.objects.filter(student=OuterRef('pk')).order_by('-due_date', '-created_at').values('status')[:1]
    overdue_payment_exists = Payment.objects.filter(student=OuterRef('pk')).filter(
        Q(status=PaymentStatus.OVERDUE)
        | Q(status=PaymentStatus.PENDING, due_date__lt=today)
    )
    pending_payment_exists = Payment.objects.filter(
        student=OuterRef('pk'),
        status=PaymentStatus.PENDING,
        due_date__gte=today,
    )

    annotations = {
        'latest_payment_status': Subquery(latest_payment_status),
        'has_overdue_payment': Exists(overdue_payment_exists),
        'has_pending_payment': Exists(pending_payment_exists),
    }
    if include_commercial_status:
        latest_enrollment_status = Enrollment.objects.filter(student=OuterRef('pk')).order_by('-start_date', '-created_at').values('status')[:1]
        annotations['latest_enrollment_status'] = Subquery(latest_enrollment_status)

    return Student.objects.annotate(
        **annotations,
    ).annotate(
        operational_payment_status=Case(
            When(has_overdue_payment=True, then=Value(PaymentStatus.OVERDUE)),
            When(has_pending_payment=True, then=Value(PaymentStatus.PENDING)),
            default=Subquery(latest_payment_status),
            output_field=CharField(),
        ),
    ).defer('cpf', 'notes', 'health_issue_status', 'updated_at').order_by('full_name')


def _enrich_student_directory_display_students(students, *, thirty_days_ago):
    student_list = list(students or [])
    if not student_list:
        return []

    student_ids = [student.id for student in student_list]
    latest_plan_name = Enrollment.objects.filter(student=OuterRef('pk')).order_by('-start_date', '-created_at').values('plan__name')[:1]
    latest_payment_due_date = Payment.objects.filter(student=OuterRef('pk')).order_by('-due_date', '-created_at').values('due_date')[:1]

    enriched_by_id = {
        student.id: student
        for student in Student.objects.filter(id__in=student_ids).annotate(
            latest_plan_name=Subquery(latest_plan_name),
            latest_payment_due_date=Subquery(latest_payment_due_date),
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
    }

    for student in student_list:
        enriched = enriched_by_id.get(student.id)
        student.latest_plan_name = getattr(enriched, 'latest_plan_name', '') or ''
        student.latest_payment_due_date = getattr(enriched, 'latest_payment_due_date', None)
        student.recent_presence_total = getattr(enriched, 'recent_presence_total', 0) or 0
        student.recent_presence_attended = getattr(enriched, 'recent_presence_attended', 0) or 0

    return student_list


def _build_student_directory_support_queryset(params=None):
    now = timezone.now()
    today = timezone.localdate()
    thirty_days_ago = now - timedelta(days=30)
    filter_form = StudentDirectoryFilterForm(params or None)
    students = _build_student_directory_base_queryset(
        today=today,
        thirty_days_ago=thirty_days_ago,
        for_export=False,
    )
    return _apply_student_directory_filters(
        students,
        filter_form,
        thirty_days_ago=thirty_days_ago,
    )


def _apply_student_directory_filters(students, filter_form, *, thirty_days_ago):
    if not filter_form.is_valid():
        return students

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

    return students


def _build_student_directory_refresh_token(*, student_ids_subquery, total_students):
    latest_student_updated_at = Student.objects.filter(pk__in=Subquery(student_ids_subquery)).aggregate(
        value=Max('updated_at')
    )['value']
    latest_enrollment_updated_at = Enrollment.objects.filter(student_id__in=Subquery(student_ids_subquery)).aggregate(
        value=Max('updated_at')
    )['value']
    latest_payment_updated_at = Payment.objects.filter(student_id__in=Subquery(student_ids_subquery)).aggregate(
        value=Max('updated_at')
    )['value']
    latest_attendance_updated_at = Attendance.objects.filter(student_id__in=Subquery(student_ids_subquery)).aggregate(
        value=Max('updated_at')
    )['value']

    return '{total}:{student}:{enrollment}:{payment}:{attendance}'.format(
        total=total_students or 0,
        student=(latest_student_updated_at.isoformat() if latest_student_updated_at else ''),
        enrollment=(latest_enrollment_updated_at.isoformat() if latest_enrollment_updated_at else ''),
        payment=(latest_payment_updated_at.isoformat() if latest_payment_updated_at else ''),
        attendance=(latest_attendance_updated_at.isoformat() if latest_attendance_updated_at else ''),
    )


def _build_student_directory_metrics(students, *, thirty_days_ago):
    filtered_students = students.order_by()
    student_ids_subquery = filtered_students.values('pk')
    student_pool = Student.objects.filter(pk__in=Subquery(student_ids_subquery))

    metrics = {
        'total': student_pool.count(),
        'ativos': student_pool.filter(status=StudentStatus.ACTIVE).count(),
        'em_dia': filtered_students.filter(
            status=StudentStatus.ACTIVE,
            operational_payment_status=PaymentStatus.PAID,
        ).count(),
        'inadimplentes': filtered_students.filter(
            operational_payment_status=PaymentStatus.OVERDUE,
        ).count(),
        'pendentes': filtered_students.filter(
            operational_payment_status=PaymentStatus.PENDING,
        ).count(),
        'inativos': student_pool.filter(status=StudentStatus.INACTIVE).count(),
        'novos_30d': student_pool.filter(created_at__gte=thirty_days_ago).count(),
    }
    metrics['directory_refresh_token'] = _build_student_directory_refresh_token(
        student_ids_subquery=student_ids_subquery,
        total_students=metrics['total'],
    )
    return metrics


def _build_student_directory_interactive_kpis(metrics):
    return [
        {
            'label': 'Ativos',
            'display_value': metrics['ativos'],
            'note': 'Mostra quem está rodando bem na base e abre o diretório já no recorte certo.',
            'icon': _catalog_kpi_icon('active'),
            'tone_class': 'kpi-green',
            'data_action': 'open-tab-students-active',
            'target_panel': 'tab-students-directory',
            'student_filter': 'active',
            'is_selected': True,
        },
        {
            'label': 'Inadimplentes',
            'display_value': metrics['inadimplentes'],
            'note': 'Mostra quem entrou em atraso para você cruzar base e caixa na mesma tela.',
            'icon': _catalog_kpi_icon('overdue'),
            'tone_class': 'kpi-red',
            'data_action': 'open-tab-students-overdue',
            'target_panel': 'tab-students-directory',
            'student_filter': 'overdue',
            'is_selected': False,
        },
        {
            'label': 'Novos (30D)',
            'display_value': metrics['novos_30d'],
            'note': 'Mostra quem entrou nos últimos 30 dias para acompanhar onboarding e consolidação.',
            'icon': _catalog_kpi_icon('growth'),
            'tone_class': 'kpi-cyan',
            'data_action': 'open-tab-students-new',
            'target_panel': 'tab-students-directory',
            'student_filter': 'new-30d',
            'is_selected': False,
        },
        {
            'label': 'Inativos',
            'display_value': metrics['inativos'],
            'note': 'Mostra quem saiu do ritmo para apoiar reativação, limpeza e revisão de carteira.',
            'icon': _catalog_kpi_icon('inactive'),
            'tone_class': 'kpi-purple',
            'data_action': 'open-tab-students-inactive',
            'target_panel': 'tab-students-directory',
            'student_filter': 'inactive',
            'is_selected': False,
        },
    ]


def _build_student_directory_support_surfaces(students, *, pending_intakes_count=None):
    priority_students_queryset = students.filter(
        Q(operational_payment_status=PaymentStatus.OVERDUE)
        | Q(status=StudentStatus.LEAD)
        | Q(latest_enrollment_status=EnrollmentStatus.PENDING)
    )
    return {
        'priority_students': priority_students_queryset.order_by('full_name')[:6],
        'pending_intakes_count': (
            pending_intakes_count if pending_intakes_count is not None else count_pending_intakes()
        ),
        'intake_queue': list(get_intake_conversion_queue(limit=6)),
    }


def build_student_directory_listing_snapshot(params=None, for_export=False):
    timing_started_at = time.perf_counter()
    now = timezone.now()
    today = timezone.localdate()
    thirty_days_ago = now - timedelta(days=30)
    form_started_at = time.perf_counter()
    filter_form = StudentDirectoryFilterForm(params or None)
    filter_form_duration_ms = round((time.perf_counter() - form_started_at) * 1000, 2)
    include_commercial_status = bool(filter_form.is_valid() and filter_form.cleaned_data.get('commercial_status'))
    base_queryset_started_at = time.perf_counter()
    if for_export:
        students = _build_student_directory_base_queryset(
            today=today,
            thirty_days_ago=thirty_days_ago,
            for_export=True,
        )
    else:
        students = _build_student_directory_listing_base_queryset(
            today=today,
            include_commercial_status=include_commercial_status,
        )
    base_queryset_duration_ms = round((time.perf_counter() - base_queryset_started_at) * 1000, 2)
    filters_started_at = time.perf_counter()
    students = _apply_student_directory_filters(
        students,
        filter_form,
        thirty_days_ago=thirty_days_ago,
    )
    filters_duration_ms = round((time.perf_counter() - filters_started_at) * 1000, 2)
    metrics_started_at = time.perf_counter()
    metrics = _build_student_directory_metrics(students, thirty_days_ago=thirty_days_ago)
    metrics_duration_ms = round((time.perf_counter() - metrics_started_at) * 1000, 2)

    return {
        'students': students,
        'total_students': metrics['total'],
        'filter_form': filter_form,
        'interactive_kpis': _build_student_directory_interactive_kpis(metrics),
        'em_dia_count': metrics['em_dia'],
        'pendentes_count': metrics['pendentes'],
        'directory_refresh_token': metrics['directory_refresh_token'],
        'timings': {
            'filter_form_ms': filter_form_duration_ms,
            'base_queryset_ms': base_queryset_duration_ms,
            'filter_application_ms': filters_duration_ms,
            'metrics_ms': metrics_duration_ms,
            'listing_snapshot_ms': round((time.perf_counter() - timing_started_at) * 1000, 2),
        },
    }


def build_student_directory_support_snapshot(params=None, *, pending_intakes_count=None):
    students = _build_student_directory_support_queryset(params)
    return _build_student_directory_support_surfaces(
        students,
        pending_intakes_count=pending_intakes_count,
    )


def build_student_directory_snapshot(params=None, for_export=False):
    listing_snapshot = build_student_directory_listing_snapshot(params=params, for_export=for_export)
    support_surfaces = build_student_directory_support_snapshot(params=params)
    return {
        **listing_snapshot,
        'priority_students': support_surfaces['priority_students'],
        'intake_queue': support_surfaces['intake_queue'],
        'pending_intakes_count': support_surfaces['pending_intakes_count'],
    }


__all__ = [
    '_enrich_student_directory_display_students',
    'build_student_directory_listing_snapshot',
    'build_student_directory_support_snapshot',
    'build_student_directory_snapshot',
]
