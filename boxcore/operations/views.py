"""
ARQUIVO: views operacionais por papel.

POR QUE ELE EXISTE:
- Dá telas reais e diferentes para Owner, DEV, Manager e Coach.
- Isola também ações operacionais críticas para cada papel.
- Reserva um espaço técnico para manutenção segura do sistema.

O QUE ESTE ARQUIVO FAZ:
1. Redireciona cada papel para sua própria área.
2. Mostra uma visão executiva para Owner.
3. Mostra uma área técnica para DEV.
4. Mostra uma central de entrada e operação para Manager.
5. Mostra uma tela prática de aula e presença para Coach.
6. Restringe ações como vínculo financeiro e ocorrência técnica ao papel correto.
7. Gera eventos de auditoria nas ações sensíveis já operacionais.

PONTOS CRITICOS:
- Essas telas dependem da definição correta de papéis.
- As ações operacionais mudam estado real do sistema e precisam manter fronteiras rígidas.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from boxcore.access.permissions import RoleRequiredMixin
from boxcore.access.roles import ROLE_COACH, ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, get_user_role
from boxcore.auditing import log_audit_event
from boxcore.models import (
    AuditEvent,
    Attendance,
    AttendanceStatus,
    BehaviorCategory,
    BehaviorNote,
    ClassSession,
    Enrollment,
    EnrollmentStatus,
    IntakeStatus,
    Payment,
    PaymentStatus,
    Student,
    StudentIntake,
    WhatsAppContact,
    WhatsAppContactStatus,
    WhatsAppMessageLog,
)


class RoleOperationRedirectView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        role = get_user_role(request.user)
        if role is None:
            return redirect('login')
        if role.slug == ROLE_OWNER:
            return redirect('owner-workspace')
        if role.slug == ROLE_DEV:
            return redirect('dev-workspace')
        if role.slug == ROLE_MANAGER:
            return redirect('manager-workspace')
        return redirect('coach-workspace')


class OperationBaseView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    allowed_roles = ()

    def get_base_context(self):
        return {
            'current_role': get_user_role(self.request.user),
            'today': timezone.localdate(),
        }


class OwnerWorkspaceView(OperationBaseView):
    allowed_roles = (ROLE_OWNER,)
    template_name = 'operations/owner.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        today = context['today']
        context['headline_metrics'] = {
            'students': Student.objects.count(),
            'pending_intakes': StudentIntake.objects.filter(status__in=[IntakeStatus.NEW, IntakeStatus.REVIEWING]).count(),
            'whatsapp_contacts': WhatsAppContact.objects.count(),
            'messages_logged': WhatsAppMessageLog.objects.count(),
            'overdue_payments': Payment.objects.filter(status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE], due_date__lt=today).count(),
        }
        context['decision_board'] = [
            'Central de entrada pronta para receber alunos antes do cadastro definitivo.',
            'Base de WhatsApp pronta para armazenar contatos, vínculo e logs.',
            'Permissões reais por papel já separadas em áreas operacionais.',
        ]
        return context


class DevWorkspaceView(OperationBaseView):
    allowed_roles = (ROLE_DEV,)
    template_name = 'operations/dev.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        context['technical_metrics'] = {
            'eventos_auditados': AuditEvent.objects.count(),
            'eventos_24h': AuditEvent.objects.filter(created_at__gte=timezone.now() - timedelta(days=1)).count(),
            'usuarios_com_papel': get_user_model().objects.filter(groups__isnull=False).distinct().count(),
        }
        context['recent_audit_events'] = AuditEvent.objects.select_related('actor')[:10]
        context['dev_boundaries'] = [
            'DEV investiga e mantém o sistema, mas não assume rotina de manager ou coach.',
            'O papel técnico deve operar com leitura ampla e escrita mínima, sempre com rastreabilidade.',
            'Acesso GOD continua fora da rotina e deve nascer depois com regra de contingência.',
        ]
        return context


class ManagerWorkspaceView(OperationBaseView):
    allowed_roles = (ROLE_MANAGER,)
    template_name = 'operations/manager.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        context['pending_intakes'] = StudentIntake.objects.select_related('linked_student', 'assigned_to').order_by('status', '-created_at')[:8]
        context['unlinked_whatsapp'] = WhatsAppContact.objects.filter(status=WhatsAppContactStatus.NEW, linked_student__isnull=True).order_by('display_name', 'phone')[:8]
        context['financial_alerts'] = Payment.objects.select_related('student').filter(status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE]).order_by('due_date')[:8]
        context['payments_without_enrollment'] = Payment.objects.select_related('student').filter(
            enrollment__isnull=True,
            status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE],
        ).order_by('due_date')[:8]
        context['manager_steps'] = [
            'Revisar entradas vindas de CSV, WhatsApp ou cadastro manual.',
            'Vincular contatos ao aluno definitivo quando houver match.',
            'Acompanhar inadimplência e preparar ações de retenção.',
        ]
        context['manager_boundaries'] = [
            'Esta área não executa presença de aula em nome do coach.',
            'O foco aqui é entrada, vínculo, retenção e rotina financeira.',
            'A operação técnica do treino continua isolada na área do coach.',
        ]
        return context


class CoachWorkspaceView(OperationBaseView):
    allowed_roles = (ROLE_COACH,)
    template_name = 'operations/coach.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        today = context['today']
        sessions = ClassSession.objects.filter(scheduled_at__date=today).prefetch_related('attendances__student').order_by('scheduled_at')
        context['sessions_today'] = sessions
        context['coach_notes'] = [
            'Use check-in ao iniciar presença real do aluno.',
            'Use check-out ao encerrar a aula ou saída do aluno.',
            'Use falta quando a reserva existia e o aluno não compareceu.',
        ]
        context['behavior_categories'] = BehaviorCategory.choices
        context['coach_boundaries'] = [
            'Esta área não mostra fila financeira nem central de entrada.',
            'O foco do coach aqui é turma, presença e leitura do dia.',
            'Ocorrências técnicas podem ser registradas sem expor dados administrativos.',
        ]
        return context


class PaymentEnrollmentLinkView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_MANAGER,)

    def post(self, request, payment_id, *args, **kwargs):
        payment = get_object_or_404(Payment.objects.select_related('student'), pk=payment_id)
        active_enrollment = Enrollment.objects.filter(
            student=payment.student,
            status=EnrollmentStatus.ACTIVE,
        ).order_by('-start_date').first()

        if active_enrollment is not None:
            payment.enrollment = active_enrollment
            if not payment.notes:
                payment.notes = 'Vinculo operacional aplicado pela area do manager.'
            payment.save(update_fields=['enrollment', 'notes', 'updated_at'])
            log_audit_event(
                actor=request.user,
                action='payment_linked_to_active_enrollment',
                target=payment,
                description='Manager vinculou pagamento a matricula ativa.',
                metadata={'enrollment_id': active_enrollment.id},
            )

        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/operacao/manager/'))


class TechnicalBehaviorNoteCreateView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_COACH,)

    def post(self, request, student_id, *args, **kwargs):
        student = get_object_or_404(Student, pk=student_id)
        description = request.POST.get('description', '').strip()
        category = request.POST.get('category', BehaviorCategory.SUPPORT)

        valid_categories = {choice for choice, _ in BehaviorCategory.choices}
        if description and category in valid_categories:
            note = BehaviorNote.objects.create(
                student=student,
                author=request.user,
                category=category,
                description=description,
            )
            log_audit_event(
                actor=request.user,
                action='technical_behavior_note_created',
                target=note,
                description='Coach registrou ocorrencia tecnica.',
                metadata={'student_id': student.id, 'category': category},
            )

        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/operacao/coach/'))


class AttendanceActionView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_COACH,)

    def post(self, request, attendance_id, action, *args, **kwargs):
        attendance = get_object_or_404(Attendance.objects.select_related('session'), pk=attendance_id)
        now = timezone.now()

        if action == 'check-in':
            attendance.status = AttendanceStatus.CHECKED_IN
            attendance.check_in_at = now
        elif action == 'check-out':
            attendance.status = AttendanceStatus.CHECKED_OUT
            attendance.check_out_at = now
            if attendance.check_in_at is None:
                attendance.check_in_at = now
        elif action == 'absent':
            attendance.status = AttendanceStatus.ABSENT
        else:
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/operacao/coach/'))

        attendance.save(update_fields=['status', 'check_in_at', 'check_out_at', 'updated_at'])
        log_audit_event(
            actor=request.user,
            action=f'attendance_{action}',
            target=attendance,
            description='Coach alterou status operacional de presenca.',
            metadata={'status': attendance.status},
        )
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/operacao/coach/'))