"""
ARQUIVO: corredor autenticado principal do app do aluno.

POR QUE ELE EXISTE:
- concentra as telas recorrentes de uso do aluno sem misturar onboarding, PWA e treino publico.

O QUE ESTE ARQUIVO FAZ:
1. expõe Home, Grade, WOD, RM e Perfil.
2. trata a confirmacao de presenca pelo app.
"""

from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import FormView, TemplateView, View

from shared_support.box_runtime import get_box_runtime_slug
from student_app.application.use_cases import GetStudentDashboard, GetStudentWorkoutPrescription
from student_app.forms import StudentProfileEditForm, WorkoutPrescriptionForm
from student_app.models import StudentExerciseMax
from student_app.workflows import AttendanceNotAvailableError, confirm_student_attendance
from .base import StudentIdentityRequiredMixin
from .wod_context import build_student_wod_context
from .wod_tracking import track_student_workout_view


class StudentHomeView(StudentIdentityRequiredMixin, TemplateView):
    template_name = 'student_app/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dashboard = GetStudentDashboard().execute(identity=self.request.student_identity)
        context['dashboard'] = dashboard
        context['student_shell_nav'] = 'home'
        context['student_shell_title'] = 'Inicio'
        context['student_home_mode'] = dashboard.home_mode
        context['student_next_session'] = dashboard.focal_session
        context['student_active_wod_session'] = dashboard.active_wod_session
        return self._attach_student_shell_context(context)


class StudentGradeView(StudentIdentityRequiredMixin, TemplateView):
    template_name = 'student_app/grade.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dashboard = GetStudentDashboard().execute(identity=self.request.student_identity)
        context['dashboard'] = dashboard
        context['student_shell_nav'] = 'grade'
        context['student_shell_title'] = 'Grade'
        context['student_next_session'] = dashboard.next_sessions[0] if dashboard.next_sessions else None
        return self._attach_student_shell_context(context)


class StudentWodView(StudentIdentityRequiredMixin, FormView):
    template_name = 'student_app/wod.html'
    form_class = WorkoutPrescriptionForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['student'] = self.request.student_identity.student
        return kwargs

    def form_valid(self, form):
        result = GetStudentWorkoutPrescription().execute(
            student=self.request.student_identity.student,
            exercise_slug=form.cleaned_data['exercise_slug'],
            percentage=form.cleaned_data['percentage'],
        )
        context = self.get_context_data(form=form, prescription=result)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        payload = build_student_wod_context(self, **kwargs)
        context = payload['context']
        if payload['workout'] is not None and payload['workout_day'] is not None:
            track_student_workout_view(
                student=self.request.student_identity.student,
                workout=payload['workout'],
            )
        return self._attach_student_shell_context(context)


class StudentRmView(StudentIdentityRequiredMixin, TemplateView):
    template_name = 'student_app/rm.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student_shell_nav'] = 'rm'
        context['student_shell_title'] = 'RM'
        context['rm_records'] = tuple(
            StudentExerciseMax.objects.filter(student=self.request.student_identity.student).order_by('exercise_label')
        )
        return self._attach_student_shell_context(context)


class StudentSettingsView(StudentIdentityRequiredMixin, FormView):
    template_name = 'student_app/settings.html'
    form_class = StudentProfileEditForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        student = self.request.student_identity.student
        kwargs['instance'] = student
        initial = kwargs.setdefault('initial', {})
        initial.setdefault('email', self.request.student_identity.email or student.email)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['box_runtime_slug'] = get_box_runtime_slug()
        context['student_shell_nav'] = 'settings'
        context['student_shell_title'] = 'Perfil'
        return self._attach_student_shell_context(context)

    def form_valid(self, form):
        student = form.save(commit=False)
        email = form.cleaned_data.get('email', '')
        student.email = email
        student.save()
        if self.request.student_identity.email != email and email:
            self.request.student_identity.email = email
            self.request.student_identity.save(update_fields=['email', 'updated_at'])
        messages.success(self.request, 'Seu perfil foi atualizado.')
        return redirect('student-app-settings')


class StudentConfirmAttendanceView(StudentIdentityRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        session_id = request.POST.get('session_id')
        if not session_id:
            messages.error(request, 'Nao consegui identificar a aula para confirmar sua presenca.')
            return redirect('student-app-grade')

        try:
            result = confirm_student_attendance(
                student=request.student_identity.student,
                session_id=session_id,
            )
        except AttendanceNotAvailableError:
            messages.error(request, 'Nao consegui identificar a aula para confirmar sua presenca.')
            return redirect(request.POST.get('next') or request.META.get('HTTP_REFERER') or 'student-app-grade')

        messages.success(
            request,
            f'Sua presenca em {result.session.title} foi confirmada. Quando a janela do treino abrir, o WOD sobe para o Inicio.',
        )
        return redirect(request.POST.get('next') or request.META.get('HTTP_REFERER') or 'student-app-grade')
