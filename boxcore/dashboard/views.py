"""
ARQUIVO: lógica do dashboard principal.

POR QUE ELE EXISTE:
- Centraliza as métricas que resumem a operação do box.

O QUE ESTE ARQUIVO FAZ:
1. Calcula indicadores de alunos, aulas, presença, financeiro e ocorrências.
2. Monta listas úteis para o painel, como alertas e próximas aulas.
3. Injeta o papel atual do usuário para o layout e para o painel.

PONTOS CRITICOS:
- Alterações erradas nas queries podem quebrar o painel inteiro ou degradar performance.
- O contexto current_role e role_capabilities é usado também pelo layout base.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.views.generic import TemplateView

from boxcore.access.roles import ROLE_DEFINITIONS, get_user_capabilities, get_user_role
from boxcore.models import Attendance, AttendanceStatus, BehaviorNote, ClassSession, Payment, PaymentStatus, Student, StudentStatus


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        month_start = today.replace(day=1)
        current_role = get_user_role(self.request.user)

        # Essas queries são a base do painel. Qualquer mudança aqui afeta números e leitura do negócio.
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

        context['metrics'] = {
            'active_students': active_students.count(),
            'sessions_today': sessions_today.count(),
            'overdue_payments': overdue_payments.count(),
            'attendance_this_month': monthly_attendance.count(),
            # Receita do mês considera apenas pagamentos confirmados como pagos.
            'monthly_revenue_paid': Payment.objects.filter(
                status=PaymentStatus.PAID,
                due_date__gte=month_start,
            ).aggregate(total=Sum('amount'))['total'] or 0,
            'occurrences_this_month': BehaviorNote.objects.filter(
                happened_at__date__gte=month_start,
            ).count(),
        }
        context['upcoming_sessions'] = (
            ClassSession.objects.filter(scheduled_at__date__gte=today)
            .select_related('coach')
            .annotate(occupied_slots=Count('attendances'))
            .order_by('scheduled_at')[:5]
        )
        context['payment_alerts'] = overdue_payments.select_related('student').order_by('due_date')[:5]
        context['student_health'] = (
            # Essa agregação alimenta a visão de risco operacional por frequência e faltas.
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
        )
        context['current_role'] = current_role
        context['role_capabilities'] = get_user_capabilities(self.request.user)
        context['role_definitions'] = ROLE_DEFINITIONS
        return context