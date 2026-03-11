"""
ARQUIVO: queries do snapshot principal do dashboard.

POR QUE ELE EXISTE:
- Centraliza as leituras e agregacoes do painel principal fora da camada HTTP.

O QUE ESTE ARQUIVO FAZ:
1. Monta metricas do painel.
2. Monta proximas aulas, alertas financeiros e saude da base.
3. Devolve um snapshot unico para a view do dashboard.

PONTOS CRITICOS:
- Mudancas aqui afetam numeros, alertas e desempenho do painel principal.
"""

from django.db.models import Count, Q, Sum

from boxcore.models import Attendance, AttendanceStatus, BehaviorNote, ClassSession, Payment, PaymentStatus, Student, StudentStatus


def build_dashboard_snapshot(*, today, month_start):
    active_students = Student.objects.filter(status=StudentStatus.ACTIVE)
    sessions_today = ClassSession.objects.filter(scheduled_at__date=today)
    overdue_payments = Payment.objects.filter(
        status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE],
        due_date__lt=today,
    )
    monthly_attendance = Attendance.objects.filter(
        session__scheduled_at__date__gte=month_start,
        status__in=[AttendanceStatus.CHECKED_IN, AttendanceStatus.CHECKED_OUT],
    )

    return {
        'metrics': {
            'active_students': active_students.count(),
            'sessions_today': sessions_today.count(),
            'overdue_payments': overdue_payments.count(),
            'attendance_this_month': monthly_attendance.count(),
            'monthly_revenue_paid': Payment.objects.filter(
                status=PaymentStatus.PAID,
                due_date__gte=month_start,
            ).aggregate(total=Sum('amount'))['total'] or 0,
            'occurrences_this_month': BehaviorNote.objects.filter(
                happened_at__date__gte=month_start,
            ).count(),
        },
        'upcoming_sessions': (
            ClassSession.objects.filter(scheduled_at__date__gte=today)
            .select_related('coach')
            .annotate(occupied_slots=Count('attendances'))
            .order_by('scheduled_at')[:5]
        ),
        'payment_alerts': overdue_payments.select_related('student').order_by('due_date')[:5],
        'student_health': (
            Student.objects.annotate(
                total_attendances=Count(
                    'attendances',
                    filter=Q(attendances__status__in=[AttendanceStatus.CHECKED_IN, AttendanceStatus.CHECKED_OUT]),
                ),
                total_absences=Count(
                    'attendances',
                    filter=Q(attendances__status=AttendanceStatus.ABSENT),
                ),
            )
            .order_by('-total_absences', '-total_attendances', 'full_name')[:8]
        ),
    }