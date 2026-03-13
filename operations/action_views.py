"""
ARQUIVO: views de acoes operacionais por papel.

POR QUE ELE EXISTE:
- expõe as mutacoes reais de manager e coach a partir do app operations.

O QUE ESTE ARQUIVO FAZ:
1. vincula pagamento a matricula.
2. registra ocorrencia tecnica.
3. aplica acoes de presenca.

PONTOS CRITICOS:
- essas rotas disparam mutacoes reais e precisam manter permissao e side effects.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views import View

from access.permissions import RoleRequiredMixin
from access.roles import ROLE_COACH, ROLE_MANAGER
from finance.models import Payment
from operations.facade import (
    run_apply_attendance_action,
    run_create_technical_behavior_note,
    run_link_payment_enrollment,
)
from operations.models import Attendance, BehaviorCategory
from students.models import Student


class PaymentEnrollmentLinkView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_MANAGER,)

    def post(self, request, payment_id, *args, **kwargs):
        get_object_or_404(Payment.objects.select_related('student'), pk=payment_id)
        run_link_payment_enrollment(actor_id=request.user.id, payment_id=payment_id)
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/operacao/manager/'))


class TechnicalBehaviorNoteCreateView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_COACH,)

    def post(self, request, student_id, *args, **kwargs):
        get_object_or_404(Student, pk=student_id)
        run_create_technical_behavior_note(
            actor_id=request.user.id,
            student_id=student_id,
            category=request.POST.get('category', BehaviorCategory.SUPPORT),
            description=request.POST.get('description', '').strip(),
        )
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/operacao/coach/'))


class AttendanceActionView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_COACH,)

    def post(self, request, attendance_id, action, *args, **kwargs):
        get_object_or_404(Attendance.objects.select_related('session'), pk=attendance_id)
        if run_apply_attendance_action(
            actor_id=request.user.id,
            attendance_id=attendance_id,
            action=action,
        ) is None:
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/operacao/coach/'))
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/operacao/coach/'))
