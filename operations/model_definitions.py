"""
ARQUIVO: implementacao real dos models de operations.

POR QUE ELE EXISTE:
- Move o ownership de codigo da operacao diaria para o app real operations sem trocar ainda o estado historico do Django.

O QUE ESTE ARQUIVO FAZ:
1. Define enums operacionais.
2. Define models concretos de aula, presenca e ocorrencia.
3. Preserva o app label historico de boxcore e as referencias estruturais necessarias.

PONTOS CRITICOS:
- O ownership de codigo muda aqui, mas o ownership de estado continua em boxcore nesta etapa.
- Ordering, constraint e relacionamentos precisam permanecer identicos para evitar migration estrutural.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from model_support.base import TimeStampedModel


HISTORICAL_BOXCORE_APP_LABEL = 'boxcore'
HISTORICAL_BOXCORE_STUDENT_MODEL = 'boxcore.Student'
HISTORICAL_BOXCORE_CLASS_SESSION_MODEL = 'boxcore.ClassSession'


class SessionStatus(models.TextChoices):
    SCHEDULED = 'scheduled', 'Agendada'
    OPEN = 'open', 'Liberada'
    COMPLETED = 'completed', 'Concluída'
    CANCELED = 'canceled', 'Cancelada'


class AttendanceStatus(models.TextChoices):
    BOOKED = 'booked', 'Reservado'
    CHECKED_IN = 'checked_in', 'Check-in'
    CHECKED_OUT = 'checked_out', 'Check-out'
    ABSENT = 'absent', 'Falta'
    CANCELED = 'canceled', 'Cancelado'


class BehaviorCategory(models.TextChoices):
    POSITIVE = 'positive', 'Positivo'
    ATTENTION = 'attention', 'Atenção'
    INJURY = 'injury', 'Lesão'
    DISCIPLINE = 'discipline', 'Disciplina'
    SUPPORT = 'support', 'Acompanhamento'


class ClassSession(TimeStampedModel):
    title = models.CharField(max_length=100)
    coach = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='class_sessions',
    )
    scheduled_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    capacity = models.PositiveIntegerField(default=20)
    status = models.CharField(
        max_length=16,
        choices=SessionStatus.choices,
        default=SessionStatus.SCHEDULED,
    )
    notes = models.TextField(blank=True)

    class Meta:
        app_label = HISTORICAL_BOXCORE_APP_LABEL
        ordering = ['scheduled_at']

    def __str__(self):
        return f'{self.title} - {self.scheduled_at:%d/%m %H:%M}'


class Attendance(TimeStampedModel):
    student = models.ForeignKey(
        HISTORICAL_BOXCORE_STUDENT_MODEL,
        on_delete=models.CASCADE,
        related_name='attendances',
    )
    session = models.ForeignKey(
        HISTORICAL_BOXCORE_CLASS_SESSION_MODEL,
        on_delete=models.CASCADE,
        related_name='attendances',
    )
    status = models.CharField(
        max_length=16,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.BOOKED,
    )
    reservation_source = models.CharField(max_length=50, blank=True)
    check_in_at = models.DateTimeField(null=True, blank=True)
    check_out_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        app_label = HISTORICAL_BOXCORE_APP_LABEL
        ordering = ['-session__scheduled_at', 'student__full_name']
        constraints = [
            models.UniqueConstraint(fields=['student', 'session'], name='unique_student_session')
        ]

    def __str__(self):
        return f'{self.student} - {self.session}'


class BehaviorNote(TimeStampedModel):
    student = models.ForeignKey(
        HISTORICAL_BOXCORE_STUDENT_MODEL,
        on_delete=models.CASCADE,
        related_name='behavior_notes',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='behavior_notes',
    )
    category = models.CharField(
        max_length=16,
        choices=BehaviorCategory.choices,
        default=BehaviorCategory.SUPPORT,
    )
    happened_at = models.DateTimeField(default=timezone.now)
    description = models.TextField()
    action_taken = models.TextField(blank=True)

    class Meta:
        app_label = HISTORICAL_BOXCORE_APP_LABEL
        ordering = ['-happened_at']

    def __str__(self):
        return f'{self.student} - {self.get_category_display()}'


__all__ = [
    'Attendance',
    'AttendanceStatus',
    'BehaviorCategory',
    'BehaviorNote',
    'ClassSession',
    'HISTORICAL_BOXCORE_APP_LABEL',
    'HISTORICAL_BOXCORE_CLASS_SESSION_MODEL',
    'HISTORICAL_BOXCORE_STUDENT_MODEL',
    'SessionStatus',
]