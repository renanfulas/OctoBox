"""
ARQUIVO: helpers do shell autenticado.

POR QUE ELE EXISTE:
- centraliza o escopo semantico do shell e os counts globais usados pelo runtime.

O QUE ESTE ARQUIVO FAZ:
1. resolve o scope da pagina atual;
2. entrega counts globais com cache curto para topbar e leituras de apoio.
"""

import time

from django.conf import settings
from django.core.cache import cache

from access.navigation_contracts import get_navigation_contract
from access.roles import ROLE_RECEPTION
from finance.overdue_metrics import count_overdue_students, get_overdue_payments_queryset
from onboarding.queries import count_pending_intakes

ADMIN_PATH_PREFIX = f"/{settings.ADMIN_URL_PATH}"


def resolve_shell_scope(*, view_name: str = '', role_slug: str | None = None, fallback_path: str = ''):
    contract = get_navigation_contract(view_name)
    scope = contract.get('scope', 'generic')

    if scope == 'dashboard' and role_slug == ROLE_RECEPTION:
        return 'dashboard-reception'

    if view_name == 'reception-workspace':
        return 'operations-reception'
    if view_name == 'manager-workspace':
        return 'operations-manager'
    if view_name == 'coach-workspace':
        return 'operations-coach'
    if view_name == 'dev-workspace':
        return 'operations-dev'
    if view_name == 'owner-workspace':
        return 'operations-owner'

    # Fallback temporario para o admin enquanto ele ainda habita o shell autenticado.
    if fallback_path.startswith(ADMIN_PATH_PREFIX):
        return 'admin'

    return scope


def get_shell_counts(*, use_cache=True, return_telemetry=False):
    """Retorna os counts globais usados pelo shell com cache curto."""
    from django.db.models import Count, Q
    from django.utils import timezone
    from finance.models import Enrollment, EnrollmentStatus, Payment
    from operations.models import ClassSession
    from students.models import Student, StudentStatus

    started_at = time.perf_counter()
    today = timezone.localdate()
    cache_key = f'octobox:shell-counts:{today}'
    telemetry = {
        'cache_key': cache_key,
        'cache_hit': False,
        'cache_lookup_ms': 0.0,
        'build_ms': 0.0,
        'total_ms': 0.0,
        'overdue_payments_ms': 0.0,
        'overdue_students_ms': 0.0,
        'pending_intakes_ms': 0.0,
        'sessions_today_ms': 0.0,
        'student_summary_ms': 0.0,
        'active_enrollments_ms': 0.0,
    }

    if use_cache:
        cache_lookup_started_at = time.perf_counter()
        cached_counts = cache.get(cache_key)
        telemetry['cache_lookup_ms'] = round((time.perf_counter() - cache_lookup_started_at) * 1000, 2)
        if cached_counts is not None:
            telemetry['cache_hit'] = True
            telemetry['total_ms'] = round((time.perf_counter() - started_at) * 1000, 2)
            if return_telemetry:
                return cached_counts, telemetry
            return cached_counts

    build_started_at = time.perf_counter()
    overdue_payments_started_at = time.perf_counter()
    overdue_payments = get_overdue_payments_queryset(Payment.objects.all(), today=today)
    overdue_payments_count = overdue_payments.count()
    telemetry['overdue_payments_ms'] = round((time.perf_counter() - overdue_payments_started_at) * 1000, 2)

    overdue_students_started_at = time.perf_counter()
    overdue_students_count = count_overdue_students(Payment.objects.all(), today=today)
    telemetry['overdue_students_ms'] = round((time.perf_counter() - overdue_students_started_at) * 1000, 2)

    pending_intakes_started_at = time.perf_counter()
    pending_intakes_count = count_pending_intakes()
    telemetry['pending_intakes_ms'] = round((time.perf_counter() - pending_intakes_started_at) * 1000, 2)

    sessions_today_started_at = time.perf_counter()
    sessions_today_count = ClassSession.objects.filter(scheduled_at__date=today).count()
    telemetry['sessions_today_ms'] = round((time.perf_counter() - sessions_today_started_at) * 1000, 2)

    student_summary_started_at = time.perf_counter()
    student_summary = Student.objects.aggregate(
        active=Count('id', filter=Q(status=StudentStatus.ACTIVE)),
        lead=Count('id', filter=Q(status=StudentStatus.LEAD)),
    )
    telemetry['student_summary_ms'] = round((time.perf_counter() - student_summary_started_at) * 1000, 2)

    active_enrollments_started_at = time.perf_counter()
    active_enrollments_count = Enrollment.objects.filter(status=EnrollmentStatus.ACTIVE).count()
    telemetry['active_enrollments_ms'] = round((time.perf_counter() - active_enrollments_started_at) * 1000, 2)

    counts = {
        'overdue_payments': overdue_payments_count,
        'overdue_students': overdue_students_count,
        'pending_intakes': pending_intakes_count,
        'sessions_today': sessions_today_count,
        'active_students': student_summary['active'],
        'lead_students': student_summary['lead'],
        'active_enrollments': active_enrollments_count,
    }
    telemetry['build_ms'] = round((time.perf_counter() - build_started_at) * 1000, 2)

    if use_cache:
        from shared_support.performance import get_cache_ttl_with_jitter

        ttl = getattr(settings, 'SHELL_COUNTS_CACHE_TTL_SECONDS', 60)
        cache.set(cache_key, counts, timeout=get_cache_ttl_with_jitter(ttl))

    telemetry['total_ms'] = round((time.perf_counter() - started_at) * 1000, 2)
    if return_telemetry:
        return counts, telemetry
    return counts


__all__ = ['get_shell_counts', 'resolve_shell_scope']
