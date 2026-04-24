"""
ARQUIVO: estado proprio do app do aluno.

POR QUE ELE EXISTE:
- guarda dados que pertencem a experiencia do aluno, como RM base por exercicio.
"""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models

from model_support.base import TimeStampedModel
from operations.models import ClassSession
from students.models import Student


class StudentExerciseMax(TimeStampedModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='exercise_maxes')
    exercise_slug = models.SlugField(max_length=64)
    exercise_label = models.CharField(max_length=120)
    one_rep_max_kg = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['exercise_label']
        constraints = [
            models.UniqueConstraint(fields=['student', 'exercise_slug'], name='unique_student_exercise_max')
        ]

    def __str__(self):
        return f'{self.student.full_name} - {self.exercise_label}'


class StudentExerciseMaxHistory(TimeStampedModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='exercise_max_history')
    exercise_max = models.ForeignKey(StudentExerciseMax, on_delete=models.CASCADE, related_name='history')
    exercise_slug = models.SlugField(max_length=64)
    exercise_label = models.CharField(max_length=120)
    previous_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    new_kg = models.DecimalField(max_digits=6, decimal_places=2)
    delta_kg = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    source = models.CharField(max_length=32, default='student_app')

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['student', 'exercise_slug', '-created_at'], name='student_rm_history_lookup'),
        ]

    def __str__(self):
        return f'{self.student.full_name} - {self.exercise_label} {self.delta_kg} kg'


class StudentAppActivityKind(models.TextChoices):
    ATTENDANCE_CONFIRMED = 'attendance_confirmed', 'Presenca confirmada'
    WOD_VIEWED = 'wod_viewed', 'WOD aberto'
    RM_CREATED = 'rm_created', 'RM criado'
    RM_UPDATED = 'rm_updated', 'RM atualizado'


class StudentAppActivity(TimeStampedModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='student_app_activities')
    kind = models.CharField(max_length=32, choices=StudentAppActivityKind.choices)
    activity_date = models.DateField()
    source_object_id = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-activity_date', '-created_at', '-id']
        indexes = [
            models.Index(fields=['student', 'activity_date'], name='student_activity_day_lookup'),
            models.Index(fields=['student', 'kind', 'activity_date'], name='student_activity_kind_day'),
        ]

    def __str__(self):
        return f'{self.student.full_name} - {self.kind} - {self.activity_date:%d/%m/%Y}'


class StudentProfileChangeRequestStatus(models.TextChoices):
    PENDING = 'pending', 'Pendente'
    APPROVED = 'approved', 'Aprovado'
    REJECTED = 'rejected', 'Rejeitado'


class StudentProfileChangeRequest(TimeStampedModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='profile_change_requests')
    identity = models.ForeignKey(
        'student_identity.StudentIdentity',
        on_delete=models.CASCADE,
        related_name='profile_change_requests',
    )
    requested_payload = models.JSONField(default=dict)
    status = models.CharField(
        max_length=16,
        choices=StudentProfileChangeRequestStatus.choices,
        default=StudentProfileChangeRequestStatus.PENDING,
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_profile_change_requests_resolved',
    )
    resolution_note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['student', 'status', '-created_at'], name='student_profile_request_lookup'),
        ]

    def __str__(self):
        return f'{self.student.full_name} - {self.status}'


class WorkoutLoadType(models.TextChoices):
    FREE = 'free', 'Livre'
    FIXED_KG = 'fixed_kg', 'Carga fixa'
    PERCENTAGE_OF_RM = 'percentage_of_rm', 'Percentual do RM'


class WorkoutBlockKind(models.TextChoices):
    WARMUP = 'warmup', 'Aquecimento'
    STRENGTH = 'strength', 'Forca'
    SKILL = 'skill', 'Skill'
    METCON = 'metcon', 'Metcon'
    COOLDOWN = 'cooldown', 'Cooldown'
    CUSTOM = 'custom', 'Livre'


class SessionWorkoutStatus(models.TextChoices):
    DRAFT = 'draft', 'Rascunho'
    PENDING_APPROVAL = 'pending_approval', 'Aguardando aprovacao'
    PUBLISHED = 'published', 'Publicado'
    REJECTED = 'rejected', 'Rejeitado'


class SessionWorkoutRevisionEvent(models.TextChoices):
    SUBMITTED = 'submitted', 'Enviado para aprovacao'
    PUBLISHED = 'published', 'Publicado'
    REJECTED = 'rejected', 'Rejeitado'
    DUPLICATED = 'duplicated', 'Duplicado'


class WorkoutFollowUpStatus(models.TextChoices):
    COMPLETED = 'completed', 'Resolvido'
    DISMISSED = 'dismissed', 'Descartado'


class WorkoutOperationalMemoryKind(models.TextChoices):
    RECEPTION_OWNED = 'reception_owned', 'Recepcao assumiu'
    COACH_ALIGNED = 'coach_aligned', 'Coach alinhado'
    WHATSAPP_SENT = 'whatsapp_sent', 'WhatsApp disparado'
    MONITORING_NOTE = 'monitoring_note', 'Nota de monitoramento'
    CUSTOM = 'custom', 'Marco livre'


class WorkoutWeeklyCheckpointStatus(models.TextChoices):
    NOT_STARTED = 'not_started', 'Nao iniciado'
    IN_PROGRESS = 'in_progress', 'Em andamento'
    COMPLETED = 'completed', 'Concluido'


class WorkoutWeeklyCheckpointOwner(models.TextChoices):
    OWNER = 'owner', 'Owner'
    MANAGER = 'manager', 'Manager'
    RECEPTION = 'reception', 'Recepcao'
    COACH = 'coach', 'Coach'


class WorkoutWeeklyCheckpointClosure(models.TextChoices):
    WORKED = 'worked', 'Funcionou'
    PARTIAL = 'partial', 'Parcial'
    DID_NOT_WORK = 'did_not_work', 'Nao funcionou'


class WorkoutWeeklyGovernanceCommitmentStatus(models.TextChoices):
    NOT_ASSUMED = 'not_assumed', 'Nao assumido'
    ASSUMED = 'assumed', 'Assumido'
    EXECUTED = 'executed', 'Executado'


class WorkoutRmGapActionStatus(models.TextChoices):
    REQUESTED = 'requested', 'RM solicitado'
    COLLECTED = 'collected', 'RM coletado'
    FREE_LOAD = 'free_load', 'Deixar carga livre'


class SessionWorkout(TimeStampedModel):
    session = models.OneToOneField(ClassSession, on_delete=models.CASCADE, related_name='workout')
    title = models.CharField(max_length=140, blank=True)
    coach_notes = models.TextField(blank=True)
    status = models.CharField(max_length=24, choices=SessionWorkoutStatus.choices, default=SessionWorkoutStatus.DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='session_workouts_created',
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='session_workouts_submitted',
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='session_workouts_approved',
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='session_workouts_rejected',
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['session__scheduled_at']

    def __str__(self):
        return self.title or f'WOD - {self.session.title}'


class SessionWorkoutRevision(TimeStampedModel):
    workout = models.ForeignKey(SessionWorkout, on_delete=models.CASCADE, related_name='revisions')
    version = models.PositiveIntegerField(default=1)
    event = models.CharField(max_length=24, choices=SessionWorkoutRevisionEvent.choices)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='session_workout_revisions_created',
    )
    snapshot = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.workout} - {self.get_event_display()} v{self.version}'


class SessionWorkoutBlock(TimeStampedModel):
    workout = models.ForeignKey(SessionWorkout, on_delete=models.CASCADE, related_name='blocks')
    kind = models.CharField(max_length=24, choices=WorkoutBlockKind.choices, default=WorkoutBlockKind.CUSTOM)
    title = models.CharField(max_length=120)
    notes = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'{self.workout} - {self.title}'


class SessionWorkoutMovement(TimeStampedModel):
    block = models.ForeignKey(SessionWorkoutBlock, on_delete=models.CASCADE, related_name='movements')
    movement_slug = models.SlugField(max_length=64)
    movement_label = models.CharField(max_length=120)
    sets = models.PositiveIntegerField(null=True, blank=True)
    reps = models.PositiveIntegerField(null=True, blank=True)
    load_type = models.CharField(max_length=32, choices=WorkoutLoadType.choices, default=WorkoutLoadType.FREE)
    load_value = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'{self.block} - {self.movement_label}'


class StudentWorkoutView(TimeStampedModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='workout_views')
    workout = models.ForeignKey(SessionWorkout, on_delete=models.CASCADE, related_name='student_views')
    first_viewed_at = models.DateTimeField()
    last_viewed_at = models.DateTimeField()
    view_count = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['-last_viewed_at']
        constraints = [
            models.UniqueConstraint(fields=['student', 'workout'], name='unique_student_workout_view')
        ]

    def __str__(self):
        return f'{self.student.full_name} abriu {self.workout}'


class SessionWorkoutFollowUpAction(TimeStampedModel):
    workout = models.ForeignKey(SessionWorkout, on_delete=models.CASCADE, related_name='follow_up_actions')
    action_key = models.CharField(max_length=64)
    action_label = models.CharField(max_length=120)
    status = models.CharField(max_length=24, choices=WorkoutFollowUpStatus.choices, default=WorkoutFollowUpStatus.COMPLETED)
    outcome_note = models.CharField(max_length=255, blank=True)
    baseline_metrics = models.JSONField(default=dict, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='session_workout_follow_up_actions_resolved',
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-resolved_at', '-updated_at', '-id']
        constraints = [
            models.UniqueConstraint(fields=['workout', 'action_key'], name='unique_workout_follow_up_action')
        ]

    def __str__(self):
        return f'{self.workout} - {self.action_label}'


class SessionWorkoutOperationalMemory(TimeStampedModel):
    workout = models.ForeignKey(SessionWorkout, on_delete=models.CASCADE, related_name='operational_memories')
    kind = models.CharField(max_length=32, choices=WorkoutOperationalMemoryKind.choices, default=WorkoutOperationalMemoryKind.CUSTOM)
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='session_workout_operational_memories_created',
    )

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.workout} - {self.get_kind_display()}'


class WorkoutWeeklyManagementCheckpoint(TimeStampedModel):
    week_start = models.DateField(unique=True)
    execution_status = models.CharField(
        max_length=24,
        choices=WorkoutWeeklyCheckpointStatus.choices,
        default=WorkoutWeeklyCheckpointStatus.NOT_STARTED,
    )
    responsible_role = models.CharField(
        max_length=24,
        choices=WorkoutWeeklyCheckpointOwner.choices,
        default=WorkoutWeeklyCheckpointOwner.MANAGER,
    )
    closure_status = models.CharField(
        max_length=24,
        choices=WorkoutWeeklyCheckpointClosure.choices,
        blank=True,
    )
    governance_commitment_status = models.CharField(
        max_length=24,
        choices=WorkoutWeeklyGovernanceCommitmentStatus.choices,
        default=WorkoutWeeklyGovernanceCommitmentStatus.NOT_ASSUMED,
    )
    governance_commitment_note = models.CharField(max_length=255, blank=True)
    summary_note = models.CharField(max_length=255, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='workout_weekly_management_checkpoints_updated',
    )

    class Meta:
        ordering = ['-week_start', '-updated_at', '-id']

    def __str__(self):
        return f'Checkpoint semanal WOD - {self.week_start:%d/%m/%Y}'


class SessionWorkoutRmGapAction(TimeStampedModel):
    workout = models.ForeignKey(SessionWorkout, on_delete=models.CASCADE, related_name='rm_gap_actions')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='session_workout_rm_gap_actions')
    exercise_slug = models.SlugField(max_length=64)
    exercise_label = models.CharField(max_length=120)
    status = models.CharField(
        max_length=24,
        choices=WorkoutRmGapActionStatus.choices,
        default=WorkoutRmGapActionStatus.REQUESTED,
    )
    note = models.CharField(max_length=255, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='session_workout_rm_gap_actions_updated',
    )

    class Meta:
        ordering = ['-updated_at', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['workout', 'student', 'exercise_slug'],
                name='unique_workout_student_rm_gap_action',
            )
        ]

    def __str__(self):
        return f'{self.workout} - {self.student.full_name} - {self.exercise_label}'
