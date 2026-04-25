"""
ARQUIVO: corredor autenticado principal do app do aluno.

POR QUE ELE EXISTE:
- concentra as telas recorrentes de uso do aluno sem misturar onboarding, PWA e treino publico.

O QUE ESTE ARQUIVO FAZ:
1. expõe Home, Grade, WOD, RM e Perfil.
2. trata a confirmacao de presenca pelo app.
"""

from __future__ import annotations

import re
from collections import OrderedDict
from datetime import date, timedelta

from django.contrib import messages
from django.db import OperationalError, ProgrammingError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import FormView, TemplateView, View

from student_app.application.activity import record_student_app_activity
from student_app.application.use_cases import GetStudentDashboard, GetStudentMonthSchedule, GetStudentWorkoutPrescription
from student_app.forms import (
    StudentExerciseMaxForm,
    StudentExerciseMaxUpdateForm,
    StudentProfileEditForm,
    WorkoutPrescriptionForm,
)
from student_app.models import (
    SessionWorkout,
    SessionWorkoutStatus,
    StudentAppActivityKind,
    StudentExerciseMax,
    StudentExerciseMaxHistory,
    StudentProfileChangeRequest,
    StudentProfileChangeRequestStatus,
)
from student_app.workflows import AttendanceNotAvailableError, cancel_student_attendance, confirm_student_attendance
from .base import StudentIdentityRequiredMixin
from .wod_context import build_student_wod_context
from .wod_tracking import track_student_workout_view


RM_ACTIVITY_STORAGE_EXCEPTIONS = (OperationalError, ProgrammingError)


def _safe_redirect(request, fallback: str):
    candidate = (request.POST.get('next') or '').strip()
    if candidate and url_has_allowed_host_and_scheme(
        url=candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(candidate)
    return redirect(fallback)


def _slugify_exercise(label: str) -> str:
    slug = label.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s]+', '-', slug)
    return slug[:64]


def _get_dashboard_session_or_404(*, identity, session_id: int):
    dashboard = GetStudentDashboard().execute(identity=identity)
    visible_session_ids = {session.session_id for session in dashboard.next_sessions}
    if session_id not in visible_session_ids:
        raise Http404('Sessao fora do radar atual do aluno.')
    return dashboard


def _build_day_sections(*, sessions):
    if not sessions:
        return ()
    sections = OrderedDict()
    for session in sessions:
        bucket = sections.setdefault(
            session.scheduled_at.date(),
            {
                'date': session.scheduled_at.date(),
                'label': session.scheduled_at.strftime('%d/%m'),
                'sessions': [],
                'workouts': [],
            },
        )
        bucket['sessions'].append(session)
    workout_by_session_id = {}
    session_ids = [session.session_id for session in sessions]
    for workout in SessionWorkout.objects.filter(session_id__in=session_ids, status=SessionWorkoutStatus.PUBLISHED).select_related('session'):
        workout_by_session_id.setdefault(workout.session_id, []).append(
            {
                'title': workout.title,
                'notes': workout.coach_notes,
            }
        )
    for bucket in sections.values():
        for session in bucket['sessions']:
            for workout in workout_by_session_id.get(session.session_id, ()):
                bucket['workouts'].append(workout)
        bucket['sessions'] = tuple(bucket['sessions'])
        bucket['workouts'] = tuple(bucket['workouts'])
    return tuple(sections.values())


class StudentHomeView(StudentIdentityRequiredMixin, TemplateView):
    template_name = 'student_app/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_date = None
        raw_date = (self.request.GET.get('date') or '').strip()
        if raw_date:
            try:
                selected_date = date.fromisoformat(raw_date)
            except ValueError:
                selected_date = None
        dashboard = GetStudentDashboard().execute(identity=self.request.student_identity, selected_date=selected_date)
        context['dashboard'] = dashboard
        context['student_shell_nav'] = 'home'
        context['student_shell_title'] = 'Inicio'
        context['student_home_mode'] = dashboard.home_mode
        context['student_next_session'] = dashboard.focal_session
        context['student_active_wod_session'] = dashboard.active_wod_session
        context['student_day_sections'] = _build_day_sections(sessions=dashboard.next_sessions)
        context['student_selected_date'] = selected_date
        return self._attach_student_shell_context(context)


class StudentGradeView(StudentIdentityRequiredMixin, TemplateView):
    template_name = 'student_app/grade.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dashboard = GetStudentDashboard().execute(identity=self.request.student_identity, window_days=2)
        today = dashboard.next_sessions[0].scheduled_at.date() if dashboard.next_sessions else date.today()
        tomorrow = today + timedelta(days=1)
        context['dashboard'] = dashboard
        context['student_shell_nav'] = 'grade'
        context['student_shell_title'] = 'Grade'
        context['student_next_session'] = dashboard.focal_session or (dashboard.next_sessions[0] if dashboard.next_sessions else None)
        context['student_month_days'] = GetStudentMonthSchedule().execute(identity=self.request.student_identity)
        context['student_today_sessions'] = tuple(
            session for session in dashboard.next_sessions if session.scheduled_at.date() == today
        )
        context['student_tomorrow_sessions'] = tuple(
            session for session in dashboard.next_sessions if session.scheduled_at.date() == tomorrow
        )
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
            record_student_app_activity(
                student=self.request.student_identity.student,
                kind=StudentAppActivityKind.WOD_VIEWED,
                source_object_id=payload['workout'].id,
                metadata={'workout_title': payload['workout_day'].workout_title},
            )
        return self._attach_student_shell_context(context)


class StudentRmView(StudentIdentityRequiredMixin, TemplateView):
    template_name = 'student_app/rm.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dashboard = GetStudentDashboard().execute(identity=self.request.student_identity)
        rm_records = tuple(
            StudentExerciseMax.objects.filter(student=self.request.student_identity.student).order_by('exercise_label')
        )
        latest_delta_by_slug = {}
        try:
            history_queryset = StudentExerciseMaxHistory.objects.filter(
                student=self.request.student_identity.student,
                exercise_slug__in=[record.exercise_slug for record in rm_records],
            ).order_by('exercise_slug', '-created_at', '-id')
        except RM_ACTIVITY_STORAGE_EXCEPTIONS:
            history_queryset = ()
        for history in history_queryset:
            latest_delta_by_slug.setdefault(history.exercise_slug, history.delta_kg)
        context['student_shell_nav'] = 'rm'
        context['student_shell_title'] = 'RM'
        context['dashboard'] = dashboard
        context['rm_of_the_day'] = dashboard.rm_of_the_day
        context['rm_records'] = rm_records
        context['rm_cards'] = tuple(
            {
                'record': record,
                'delta_kg': latest_delta_by_slug.get(record.exercise_slug),
            }
            for record in rm_records
        )
        context['add_rm_form'] = StudentExerciseMaxForm()
        context['percentage_choices'] = tuple(range(5, 105, 5))
        return self._attach_student_shell_context(context)


class StudentAddRmView(StudentIdentityRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = StudentExerciseMaxForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Confira os dados e tente novamente.')
            return redirect('student-app-rm')
        label = form.cleaned_data['exercise_label']
        slug = _slugify_exercise(label)
        kg = form.cleaned_data['one_rep_max_kg']
        obj, created = StudentExerciseMax.objects.get_or_create(
            student=request.student_identity.student,
            exercise_slug=slug,
            defaults={'exercise_label': label, 'one_rep_max_kg': kg},
        )
        previous_kg = None if created else obj.one_rep_max_kg
        if not created:
            obj.one_rep_max_kg = kg
            obj.exercise_label = label
            obj.save(update_fields=['exercise_label', 'one_rep_max_kg', 'updated_at'])
        try:
            StudentExerciseMaxHistory.objects.create(
                student=request.student_identity.student,
                exercise_max=obj,
                exercise_slug=obj.exercise_slug,
                exercise_label=obj.exercise_label,
                previous_kg=previous_kg,
                new_kg=kg,
                delta_kg=(kg - previous_kg) if previous_kg is not None else 0,
            )
        except RM_ACTIVITY_STORAGE_EXCEPTIONS:
            messages.info(request, 'Seu RM foi salvo, mas o historico detalhado ainda nao esta ativo neste banco.')
        record_student_app_activity(
            student=request.student_identity.student,
            kind=StudentAppActivityKind.RM_CREATED if created else StudentAppActivityKind.RM_UPDATED,
            source_object_id=obj.id,
            metadata={'exercise_slug': obj.exercise_slug, 'exercise_label': obj.exercise_label},
        )
        messages.success(request, f'RM de {label} salvo como {kg} kg.')
        return redirect('student-app-rm')


class StudentUpdateRmView(StudentIdentityRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        record = get_object_or_404(
            StudentExerciseMax,
            pk=pk,
            student=request.student_identity.student,
        )
        form = StudentExerciseMaxUpdateForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Valor invalido.')
            return redirect('student-app-rm')
        previous_kg = record.one_rep_max_kg
        record.one_rep_max_kg = form.cleaned_data['one_rep_max_kg']
        record.save(update_fields=['one_rep_max_kg', 'updated_at'])
        try:
            StudentExerciseMaxHistory.objects.create(
                student=request.student_identity.student,
                exercise_max=record,
                exercise_slug=record.exercise_slug,
                exercise_label=record.exercise_label,
                previous_kg=previous_kg,
                new_kg=record.one_rep_max_kg,
                delta_kg=record.one_rep_max_kg - previous_kg,
            )
        except RM_ACTIVITY_STORAGE_EXCEPTIONS:
            messages.info(request, 'Seu RM foi atualizado, mas o historico detalhado ainda nao esta ativo neste banco.')
        record_student_app_activity(
            student=request.student_identity.student,
            kind=StudentAppActivityKind.RM_UPDATED,
            source_object_id=record.id,
            metadata={'exercise_slug': record.exercise_slug, 'exercise_label': record.exercise_label},
        )
        messages.success(request, f'RM de {record.exercise_label} atualizado para {record.one_rep_max_kg} kg.')
        return redirect('student-app-rm')


class StudentSessionAttendeesView(StudentIdentityRequiredMixin, TemplateView):
    template_name = 'student_app/session_attendees.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from operations.models import Attendance, AttendanceStatus, ClassSession
        dashboard = _get_dashboard_session_or_404(
            identity=self.request.student_identity,
            session_id=self.kwargs['session_id'],
        )
        session = get_object_or_404(ClassSession, pk=self.kwargs['session_id'])
        attendances = (
            Attendance.objects
            .filter(
                session=session,
                status__in=[
                    AttendanceStatus.BOOKED,
                    AttendanceStatus.CHECKED_IN,
                    AttendanceStatus.CHECKED_OUT,
                ],
            )
            .select_related('student__app_identity')
        )
        attendees = []
        for att in attendances:
            s = att.student
            first_name = s.full_name.split()[0] if s.full_name else ''
            photo_url = ''
            try:
                photo_url = s.app_identity.photo_url
            except Exception:
                pass
            attendees.append({'first_name': first_name, 'photo_url': photo_url})
        context['session'] = session
        context['attendees'] = attendees
        context['dashboard'] = dashboard
        context['student_shell_nav'] = 'grade'
        context['student_shell_title'] = 'Turma'
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
        context['pending_profile_request'] = (
            StudentProfileChangeRequest.objects
            .filter(
                student=self.request.student_identity.student,
                identity=self.request.student_identity,
                status=StudentProfileChangeRequestStatus.PENDING,
            )
            .first()
        )
        context['student_shell_nav'] = 'settings'
        context['student_shell_title'] = 'Perfil'
        return self._attach_student_shell_context(context)

    def form_valid(self, form):
        StudentProfileChangeRequest.objects.create(
            student=self.request.student_identity.student,
            identity=self.request.student_identity,
            requested_payload={
                'full_name': form.cleaned_data.get('full_name', ''),
                'phone': form.cleaned_data.get('phone', ''),
                'email': form.cleaned_data.get('email', ''),
                'birth_date': form.cleaned_data.get('birth_date').isoformat()
                if form.cleaned_data.get('birth_date')
                else '',
            },
        )
        messages.success(self.request, 'Pedido de alteracao enviado para aprovacao.')
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
        except AttendanceNotAvailableError as exc:
            messages.error(request, str(exc) or 'Nao consegui identificar a aula para confirmar sua presenca.')
            return _safe_redirect(request, 'student-app-grade')

        messages.success(
            request,
            f'Sua presenca em {result.session.title} foi confirmada. Quando a janela do treino abrir, o WOD sobe para o Inicio.',
        )
        record_student_app_activity(
            student=request.student_identity.student,
            kind=StudentAppActivityKind.ATTENDANCE_CONFIRMED,
            source_object_id=result.session.id,
            metadata={'session_title': result.session.title},
        )
        return _safe_redirect(request, 'student-app-grade')


class StudentCancelAttendanceView(StudentIdentityRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        session_id = request.POST.get('session_id')
        if not session_id:
            messages.error(request, 'Nao consegui identificar a aula para cancelar sua reserva.')
            return redirect('student-app-grade')

        try:
            result = cancel_student_attendance(
                student=request.student_identity.student,
                session_id=session_id,
            )
        except AttendanceNotAvailableError as exc:
            messages.error(request, str(exc) or 'Nao foi possivel cancelar esta reserva agora.')
            return _safe_redirect(request, 'student-app-grade')

        messages.success(request, f'Reserva em {result.session.title} cancelada.')
        return _safe_redirect(request, 'student-app-grade')
