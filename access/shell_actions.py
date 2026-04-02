"""
ARQUIVO: helpers do shell autenticado.

POR QUE ELE EXISTE:
- centraliza o escopo semantico do shell e os counts globais usados pelo runtime.

O QUE ESTE ARQUIVO FAZ:
1. resolve o scope da pagina atual;
2. entrega counts globais com cache curto para topbar e leituras de apoio.
"""

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


def get_shell_counts(*, use_cache=True):
    """Retorna os counts globais usados pelo shell com cache curto."""
    from django.db.models import Count, Q
    from django.utils import timezone
    from finance.models import Enrollment, EnrollmentStatus, Payment
    from operations.models import ClassSession
    from students.models import Student, StudentStatus

    today = timezone.localdate()
    cache_key = f'octobox:shell-counts:{today}'

    if use_cache:
        cached_counts = cache.get(cache_key)
        if cached_counts is not None:
            return cached_counts

    overdue_payments = get_overdue_payments_queryset(Payment.objects.all(), today=today)
    student_summary = Student.objects.aggregate(
        active=Count('id', filter=Q(status=StudentStatus.ACTIVE)),
        lead=Count('id', filter=Q(status=StudentStatus.LEAD)),
    )

    counts = {
        'overdue_payments': overdue_payments.count(),
        'overdue_students': count_overdue_students(Payment.objects.all(), today=today),
        'pending_intakes': count_pending_intakes(),
        'sessions_today': ClassSession.objects.filter(scheduled_at__date=today).count(),
        'active_students': student_summary['active'],
        'lead_students': student_summary['lead'],
        'active_enrollments': Enrollment.objects.filter(status=EnrollmentStatus.ACTIVE).count(),
    }

    if use_cache:
        from shared_support.performance import get_cache_ttl_with_jitter

        ttl = getattr(settings, 'SHELL_COUNTS_CACHE_TTL_SECONDS', 60)
        cache.set(cache_key, counts, timeout=get_cache_ttl_with_jitter(ttl))

    return counts


__all__ = ['get_shell_counts', 'resolve_shell_scope']
