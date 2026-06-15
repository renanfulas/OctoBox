"""Seed de demonstração do app do aluno — relativo a HOJE.

Idempotente: limpa sessões/filler [demo] e recria a semana corrente.
Uso (cluster local 5433):
  manage.py shell --command "exec(open(r'scripts/seed_demo_week.py', encoding='utf-8').read())"
"""
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context

from control.models import Box

box = Box.objects.get(schema_name='box_test')
slug = getattr(box, 'slug', None) or box.schema_name

with schema_context(box.schema_name):
    from students.models import Student
    from operations.models import ClassSession, Attendance, ClassType, SessionStatus, AttendanceStatus
    from student_app.models import (
        SessionWorkout, SessionWorkoutBlock, SessionWorkoutMovement,
        SessionWorkoutStatus, WorkoutBlockKind, WorkoutLoadType,
        StudentExerciseMax, StudentExerciseMaxHistory,
        StudentAppActivity, StudentAppActivityKind,
    )

    student = Student.objects.filter(full_name__in=['Aluno Demo', 'Renan Demo']).first()
    # Nome de exibição alinhado ao protótipo ("Boa tarde, Renan").
    if student and student.full_name != 'Renan Demo':
        student.full_name = 'Renan Demo'
        student.save(update_fields=['full_name'])
    User = get_user_model()
    coach = User.objects.first()
    if coach and not coach.get_full_name().strip():
        coach.first_name = 'Carla'
        coach.last_name = 'Souza'
        coach.save(update_fields=['first_name', 'last_name'])

    # Limpa demo anterior (idempotência)
    old = ClassSession.objects.filter(title__startswith='[demo]')
    Attendance.objects.filter(session__in=old).delete()
    old.delete()
    Student.objects.filter(full_name__startswith='Aluno Filler').delete()
    StudentAppActivity.objects.filter(student=student).delete()

    now = timezone.localtime()
    today = now.date()
    base_today = now.replace(minute=0, second=0, microsecond=0)

    # 16 filler students para preencher ocupação
    filler = [Student.objects.create(full_name=f'Aluno Filler {i+1:02d}', phone=f'+551199997{i:04d}') for i in range(16)]

    def make_session(title, ctype, when, cap, occupied, book_demo=False):
        s = ClassSession.objects.create(
            title=title, class_type=ctype, coach=coach, scheduled_at=when,
            duration_minutes=60, capacity=cap, status=SessionStatus.SCHEDULED,
        )
        for f in filler[:max(0, occupied - (1 if book_demo else 0))]:
            Attendance.objects.create(student=f, session=s, status=AttendanceStatus.BOOKED)
        if book_demo:
            Attendance.objects.create(student=student, session=s, status=AttendanceStatus.BOOKED)
        return s

    # Hoje: próxima aula às +2h. NÃO reservada de propósito, para o hero da Home
    # mostrar a CTA de ação "Confirmar presença" (foco do protótipo).
    next_at = base_today + timedelta(hours=2)
    s_next = make_session('[demo] CrossFit 18h', ClassType.CROSS, next_at, 16, 14, book_demo=False)
    make_session('[demo] CrossFit 19h', ClassType.CROSS, base_today + timedelta(hours=3), 16, 8)
    make_session('[demo] Open Gym', ClassType.OPEN_GYM, base_today + timedelta(hours=4), 25, 25)
    # Amanhã
    make_session('[demo] Halterofilia', ClassType.OLY, base_today + timedelta(days=1, hours=2), 12, 5)
    make_session('[demo] Mobilidade', ClassType.MOBILITY, base_today + timedelta(days=1, hours=4), 20, 3)

    # WOD rico na próxima aula
    wod = SessionWorkout.objects.create(
        session=s_next, title='Engine Builder', status=SessionWorkoutStatus.PUBLISHED,
        coach_notes='Ritmo constante. Escala o peso se perder a técnica.',
        created_by=coach, approved_by=coach, approved_at=now, is_normalized=True,
    )
    b1 = SessionWorkoutBlock.objects.create(workout=wod, kind=WorkoutBlockKind.WARMUP, title='Aquecimento', sort_order=1, notes='2 rounds leves')
    SessionWorkoutMovement.objects.create(block=b1, movement_slug='row', movement_label='Remo', sets=2, load_type=WorkoutLoadType.FREE, notes='250m ritmo leve', sort_order=1)
    SessionWorkoutMovement.objects.create(block=b1, movement_slug='air-squat', movement_label='Air Squat', sets=2, reps=15, load_type=WorkoutLoadType.FREE, sort_order=2)
    b2 = SessionWorkoutBlock.objects.create(workout=wod, kind=WorkoutBlockKind.STRENGTH, title='Força', sort_order=2, notes='Back Squat 5x5')
    SessionWorkoutMovement.objects.create(block=b2, movement_slug='back-squat', movement_label='Back Squat', sets=5, reps=5, load_type=WorkoutLoadType.PERCENTAGE_OF_RM, load_value=Decimal('75'), sort_order=1)
    b3 = SessionWorkoutBlock.objects.create(workout=wod, kind=WorkoutBlockKind.METCON, title='Metcon — AMRAP 12min', sort_order=3, notes='AMRAP 12 minutos')
    SessionWorkoutMovement.objects.create(block=b3, movement_slug='wall-ball', movement_label='Wall Ball', reps=15, load_type=WorkoutLoadType.FIXED_KG, load_value=Decimal('9'), sort_order=1)
    SessionWorkoutMovement.objects.create(block=b3, movement_slug='box-jump', movement_label='Box Jump', reps=12, load_type=WorkoutLoadType.FREE, sort_order=2)
    SessionWorkoutMovement.objects.create(block=b3, movement_slug='burpee', movement_label='Burpee', reps=9, load_type=WorkoutLoadType.FREE, sort_order=3)

    # WOD de amanhã
    SessionWorkout.objects.create(
        session=ClassSession.objects.filter(title='[demo] Halterofilia').first(),
        title='Snatch Day', status=SessionWorkoutStatus.PUBLISHED,
        coach_notes='Técnica acima de carga.', created_by=coach, approved_by=coach, approved_at=now,
    )

    # Streak: treinos nos dias já vividos desta semana + hoje (para o demo
    # sempre mostrar checks, mesmo numa segunda-feira). Pula um dia no meio.
    week_start = today - timedelta(days=today.weekday())
    for offset in range(today.weekday() + 1):  # seg..hoje (inclusive)
        day = week_start + timedelta(days=offset)
        if offset == 2:  # pula quarta, para o placar não ser "cheio"
            continue
        StudentAppActivity.objects.create(
            student=student, kind=StudentAppActivityKind.ATTENDANCE_CONFIRMED, activity_date=day,
        )

    # RMs
    rms = [
        ('back-squat', 'Back Squat', '142.50'),
        ('deadlift', 'Deadlift', '180.00'),
        ('clean-and-jerk', 'Clean & Jerk', '95.00'),
        ('snatch', 'Snatch', '72.50'),
        ('bench-press', 'Bench Press', '105.00'),
    ]
    for s, label, kg in rms:
        m, created = StudentExerciseMax.objects.get_or_create(
            student=student, exercise_slug=s,
            defaults={'exercise_label': label, 'one_rep_max_kg': Decimal(kg)},
        )
        if created:
            StudentExerciseMaxHistory.objects.create(
                student=student, exercise_max=m, exercise_slug=s, exercise_label=label,
                previous_kg=Decimal(kg) - Decimal('5'), new_kg=Decimal(kg), delta_kg=Decimal('5'),
            )

    print('seed ok:', ClassSession.objects.filter(title__startswith='[demo]').count(), 'sessions,',
          StudentAppActivity.objects.filter(student=student).count(), 'activities,',
          StudentExerciseMax.objects.filter(student=student).count(), 'RMs · today=', today, 'weekday=', today.weekday())
