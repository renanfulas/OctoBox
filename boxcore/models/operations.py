"""
ARQUIVO: modelos da operação diária do box.

POR QUE ELE EXISTE:
- Isola o que acontece em aula, presença e ocorrências do dia a dia.

O QUE ESTE ARQUIVO FAZ:
1. Define status de aula e presença.
2. Define as aulas/sessões do box.
3. Registra reservas, check-in, check-out e faltas.
4. Registra ocorrências e observações comportamentais.

PONTOS CRITICOS:
- A constraint de student + session evita presença duplicada para o mesmo aluno.
- Mudanças nesses relacionamentos afetam dashboard, risco operacional e histórico do aluno.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from .base import TimeStampedModel
from .students import Student


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
        ordering = ['scheduled_at']

    def __str__(self):
        return f'{self.title} - {self.scheduled_at:%d/%m %H:%M}'


class Attendance(TimeStampedModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendances')
    session = models.ForeignKey(ClassSession, on_delete=models.CASCADE, related_name='attendances')
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
        ordering = ['-session__scheduled_at', 'student__full_name']
        constraints = [
            models.UniqueConstraint(fields=['student', 'session'], name='unique_student_session')
        ]

    def __str__(self):
        return f'{self.student} - {self.session}'


class BehaviorNote(TimeStampedModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='behavior_notes')
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
        ordering = ['-happened_at']

    def __str__(self):
        return f'{self.student} - {self.get_category_display()}'