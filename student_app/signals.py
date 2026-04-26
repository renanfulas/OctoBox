"""
ARQUIVO: sinais de cache do app do aluno.

POR QUE ELE EXISTE:
- Conecta mudancas transacionais de aula, presenca e WOD a invalidacao dos snapshots.

O QUE ESTE ARQUIVO FAZ:
1. Limpa agenda compartilhada quando uma aula muda.
2. Limpa agenda compartilhada quando uma reserva muda.
3. Limpa agenda compartilhada quando o WOD publicado ou seus blocos mudam.

PONTOS CRITICOS:
- Estes sinais nao autorizam regras de negocio; so limpam cache de leitura.
- Se a invalidacao falhar, o request seguinte ainda pode montar pelo banco em cache miss futuro.
"""

from __future__ import annotations

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from finance.models import Enrollment
from operations.models import Attendance, ClassSession
from student_app.application.cache_invalidation import (
    invalidate_student_agenda_snapshots,
    invalidate_student_home_snapshots,
    invalidate_student_rm_snapshots,
    resolve_student_box_slug,
)
from student_app.models import (
    SessionWorkout,
    SessionWorkoutBlock,
    SessionWorkoutMovement,
    StudentAppActivity,
    StudentExerciseMax,
    StudentExerciseMaxHistory,
)


@receiver([post_save, post_delete], sender=ClassSession)
def invalidate_agenda_for_class_session(sender, instance, **kwargs):
    invalidate_student_agenda_snapshots(
        box_root_slug=resolve_student_box_slug(),
        session_scheduled_at=instance.scheduled_at,
    )
    invalidate_student_home_snapshots(
        box_root_slug=resolve_student_box_slug(),
    )


@receiver([post_save, post_delete], sender=Attendance)
def invalidate_agenda_for_attendance(sender, instance, **kwargs):
    invalidate_student_agenda_snapshots(
        box_root_slug=resolve_student_box_slug(instance.student),
        session_scheduled_at=instance.session.scheduled_at,
    )
    invalidate_student_home_snapshots(
        box_root_slug=resolve_student_box_slug(instance.student),
        student_id=instance.student_id,
    )


@receiver([post_save, post_delete], sender=SessionWorkout)
def invalidate_agenda_for_workout(sender, instance, **kwargs):
    invalidate_student_agenda_snapshots(
        box_root_slug=resolve_student_box_slug(),
        session_scheduled_at=instance.session.scheduled_at,
    )
    invalidate_student_home_snapshots(
        box_root_slug=resolve_student_box_slug(),
    )


@receiver([post_save, post_delete], sender=SessionWorkoutBlock)
def invalidate_agenda_for_workout_block(sender, instance, **kwargs):
    invalidate_student_agenda_snapshots(
        box_root_slug=resolve_student_box_slug(),
        session_scheduled_at=instance.workout.session.scheduled_at,
    )
    invalidate_student_home_snapshots(
        box_root_slug=resolve_student_box_slug(),
    )


@receiver([post_save, post_delete], sender=SessionWorkoutMovement)
def invalidate_agenda_for_workout_movement(sender, instance, **kwargs):
    invalidate_student_agenda_snapshots(
        box_root_slug=resolve_student_box_slug(),
        session_scheduled_at=instance.block.workout.session.scheduled_at,
    )
    invalidate_student_home_snapshots(
        box_root_slug=resolve_student_box_slug(),
    )


@receiver([post_save, post_delete], sender=StudentExerciseMax)
@receiver([post_save, post_delete], sender=StudentExerciseMaxHistory)
@receiver([post_save, post_delete], sender=StudentAppActivity)
@receiver([post_save, post_delete], sender=Enrollment)
def invalidate_home_for_student_state(sender, instance, **kwargs):
    student = getattr(instance, 'student', None)
    student_id = getattr(instance, 'student_id', None)
    invalidate_student_home_snapshots(
        box_root_slug=resolve_student_box_slug(student),
        student_id=student_id,
    )
    if sender in {StudentExerciseMax, StudentExerciseMaxHistory}:
        invalidate_student_rm_snapshots(
            box_root_slug=resolve_student_box_slug(student),
            student_id=student_id,
        )
