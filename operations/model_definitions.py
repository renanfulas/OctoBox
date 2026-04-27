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


class ClassType(models.TextChoices):
    CROSS = 'cross', 'CrossFit'
    MOBILITY = 'mobility', 'Mobilidade / Alongamento'
    OLY = 'oly', 'Halterofilia'
    STRENGTH = 'strength', 'Forca'
    OPEN_GYM = 'open_gym', 'Open Gym'
    OTHER = 'other', 'Outro'


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


class LeadImportSourceType(models.TextChoices):
    WHATSAPP_LIST = 'whatsapp_list', 'Lista do WhatsApp'
    TECNOFIT_EXPORT = 'tecnofit_export', 'Exportacao Tecnofit'
    NEXTFIT_EXPORT = 'nextfit_export', 'Exportacao Nextfit'
    IPHONE_VCF = 'iphone_vcf', 'VCF - iPhone'


class LeadImportDeclaredRange(models.TextChoices):
    UP_TO_200 = 'up_to_200', 'Ate 200'
    FROM_201_TO_500 = 'from_201_to_500', '201 a 500'
    FROM_501_TO_2000 = 'from_501_to_2000', '501 a 2000'


class LeadImportProcessingMode(models.TextChoices):
    SYNC = 'sync', 'Processamento imediato'
    ASYNC_NOW = 'async_now', 'Background imediato'
    ASYNC_NIGHT = 'async_night', 'Agendamento noturno'


class LeadImportJobStatus(models.TextChoices):
    RECEIVED = 'received', 'Recebido'
    VALIDATING = 'validating', 'Validando'
    QUEUED = 'queued', 'Na fila'
    SCHEDULED = 'scheduled', 'Agendado'
    RUNNING = 'running', 'Processando'
    COMPLETED = 'completed', 'Concluido'
    COMPLETED_WITH_WARNINGS = 'completed_with_warnings', 'Concluido com alertas'
    REJECTED = 'rejected', 'Rejeitado'
    FAILED = 'failed', 'Falha'


class ClassSession(TimeStampedModel):
    title = models.CharField(max_length=100)
    class_type = models.CharField(
        max_length=24,
        choices=ClassType.choices,
        default=ClassType.OTHER,
        db_index=True,
    )
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
        indexes = [
            models.Index(fields=['status', 'scheduled_at'], name='class_session_status_time'),
        ]

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


class LeadImportJob(TimeStampedModel):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lead_import_jobs',
    )
    source_type = models.CharField(
        max_length=32,
        choices=LeadImportSourceType.choices,
        db_index=True,
    )
    declared_range = models.CharField(
        max_length=24,
        choices=LeadImportDeclaredRange.choices,
        db_index=True,
    )
    processing_mode = models.CharField(
        max_length=16,
        choices=LeadImportProcessingMode.choices,
        default=LeadImportProcessingMode.SYNC,
        db_index=True,
    )
    status = models.CharField(
        max_length=32,
        choices=LeadImportJobStatus.choices,
        default=LeadImportJobStatus.RECEIVED,
        db_index=True,
    )
    original_filename = models.CharField(max_length=255, blank=True, default='')
    file_path = models.CharField(max_length=500, blank=True, default='')
    detected_lead_count = models.PositiveIntegerField(default=0)
    success_count = models.PositiveIntegerField(default=0)
    duplicate_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    duplicate_details = models.JSONField(blank=True, default=list)
    error_details = models.JSONField(blank=True, default=list)
    scheduled_for = models.DateTimeField(null=True, blank=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = HISTORICAL_BOXCORE_APP_LABEL
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_source_type_display()} - {self.get_status_display()}'


class WorkoutApprovalPolicySetting(TimeStampedModel):
    box_id = models.PositiveIntegerField(unique=True, db_index=True)
    approval_policy = models.CharField(
        max_length=32,
        choices=(
            ('strict', 'Aprovacao obrigatoria'),
            ('trusted_template', 'Template confiavel publica direto'),
            ('coach_autonomy', 'Coach confiavel publica direto'),
        ),
        default='strict',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='workout_approval_policies_updated',
    )

    class Meta:
        ordering = ['box_id']

    def __str__(self):
        return f'Box {self.box_id} - {self.approval_policy}'


class WorkoutTemplate(TimeStampedModel):
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='workout_templates_created',
    )
    source_workout = models.ForeignKey(
        'student_app.SessionWorkout',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='derived_templates',
    )
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_trusted = models.BooleanField(default=False)
    usage_count = models.PositiveIntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-is_featured', '-is_active', '-usage_count', '-last_used_at', 'name', '-created_at']

    def __str__(self):
        return self.name


class WorkoutTemplateBlock(TimeStampedModel):
    template = models.ForeignKey(WorkoutTemplate, on_delete=models.CASCADE, related_name='blocks')
    kind = models.CharField(max_length=24, choices=(
        ('warmup', 'Aquecimento'),
        ('strength', 'Forca'),
        ('skill', 'Skill'),
        ('metcon', 'Metcon'),
        ('cooldown', 'Cooldown'),
        ('custom', 'Livre'),
    ), default='custom')
    title = models.CharField(max_length=120)
    notes = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'{self.template.name} - {self.title}'


class WorkoutTemplateMovement(TimeStampedModel):
    block = models.ForeignKey(WorkoutTemplateBlock, on_delete=models.CASCADE, related_name='movements')
    movement_slug = models.SlugField(max_length=64)
    movement_label = models.CharField(max_length=120)
    sets = models.PositiveIntegerField(null=True, blank=True)
    reps = models.PositiveIntegerField(null=True, blank=True)
    load_type = models.CharField(
        max_length=32,
        choices=(
            ('free', 'Livre'),
            ('fixed_kg', 'Carga fixa'),
            ('percentage_of_rm', 'Percentual do RM'),
        ),
        default='free',
    )
    load_value = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'{self.block} - {self.movement_label}'


class SessionCancellationEvent(TimeStampedModel):
    """
    Fato imutavel registrado quando uma ClassSession muda para status 'canceled'
    com pelo menos uma presenca ativa.

    Fonte de verdade consumida por:
    - push delivery (Onda 3): envia notificacao para assinantes.
    - banner in-app (Onda 4): exibe alerta na grade do aluno.

    Ambos os consumidores sao independentes; o evento persiste mesmo se push falhar.
    """

    session_id = models.PositiveIntegerField(db_index=True)
    box_root_slug = models.CharField(max_length=64, db_index=True)
    copy_variant = models.CharField(
        max_length=24,
        default='ahead',
    )
    attendance_count_at_cancel = models.PositiveIntegerField(default=0)
    push_sent_count = models.PositiveIntegerField(default=0)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    session_title = models.CharField(max_length=100, blank=True)

    class Meta:
        app_label = 'operations'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['session_id'],
                name='ops_session_cancel_evt_unique_session',
            )
        ]
        indexes = [
            models.Index(fields=['box_root_slug', 'created_at'], name='ops_sess_cancel_box_idx'),
        ]

    def __str__(self):
        return f'CancellationEvent session={self.session_id} variant={self.copy_variant}'


class WorkoutPlannerTemplatePickerEvent(TimeStampedModel):
    event_name = models.CharField(max_length=24, db_index=True)
    session_id = models.PositiveIntegerField(db_index=True)
    template = models.ForeignKey(
        WorkoutTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='planner_picker_events',
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='workout_planner_template_picker_events',
    )
    action_outcome = models.CharField(max_length=32, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_name', 'created_at'], name='ops_tpl_evt_name_idx'),
            models.Index(fields=['session_id', 'created_at'], name='ops_tpl_evt_sess_idx'),
        ]

    def __str__(self):
        return f'{self.event_name} - session {self.session_id}'


__all__ = [
    'Attendance',
    'AttendanceStatus',
    'BehaviorCategory',
    'BehaviorNote',
    'ClassType',
    'ClassSession',
    'HISTORICAL_BOXCORE_APP_LABEL',
    'HISTORICAL_BOXCORE_CLASS_SESSION_MODEL',
    'HISTORICAL_BOXCORE_STUDENT_MODEL',
    'LeadImportDeclaredRange',
    'LeadImportJob',
    'LeadImportJobStatus',
    'LeadImportProcessingMode',
    'LeadImportSourceType',
    'SessionStatus',
    'WorkoutApprovalPolicySetting',
    'WorkoutTemplate',
    'WorkoutTemplateBlock',
    'WorkoutTemplateMovement',
    'WorkoutPlannerTemplatePickerEvent',
]
