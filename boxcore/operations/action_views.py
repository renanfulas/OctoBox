"""
ARQUIVO: views de acoes operacionais por papel.

POR QUE ELE EXISTE:
- Isola a camada HTTP das acoes que alteram estado real em operations.

O QUE ESTE ARQUIVO FAZ:
1. Orquestra vinculo financeiro do manager.
2. Orquestra ocorrencia tecnica e presenca do coach.
3. Mantem os redirects de retorno ao workspace de origem.

PONTOS CRITICOS:
- Essas rotas disparam mutacoes reais e precisam manter permissoes e side effects intactos.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views import View

from boxcore.access.permissions import RoleRequiredMixin
from boxcore.access.roles import ROLE_COACH, ROLE_MANAGER
from boxcore.models import Attendance, Payment, Student, BehaviorCategory

from .actions import handle_attendance_action, handle_payment_enrollment_link_action, handle_technical_behavior_note_action


class PaymentEnrollmentLinkView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_MANAGER,)

    def post(self, request, payment_id, *args, **kwargs):
        payment = get_object_or_404(Payment.objects.select_related('student'), pk=payment_id)
        handle_payment_enrollment_link_action(actor=request.user, payment=payment)
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/operacao/manager/'))


class TechnicalBehaviorNoteCreateView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_COACH,)

    def post(self, request, student_id, *args, **kwargs):
        student = get_object_or_404(Student, pk=student_id)
        handle_technical_behavior_note_action(
            actor=request.user,
            student=student,
            category=request.POST.get('category', BehaviorCategory.SUPPORT),
            description=request.POST.get('description', '').strip(),
        )
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/operacao/coach/'))


class AttendanceActionView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = (ROLE_COACH,)

    def post(self, request, attendance_id, action, *args, **kwargs):
        attendance = get_object_or_404(Attendance.objects.select_related('session'), pk=attendance_id)
        if handle_attendance_action(actor=request.user, attendance=attendance, action=action) is None:
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/operacao/coach/'))
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/operacao/coach/'))