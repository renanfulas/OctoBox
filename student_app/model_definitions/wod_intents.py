"""Persistence models for recoverable daily and weekly WOD intents."""

from __future__ import annotations

from uuid import uuid4

from django.conf import settings
from django.db import models

from model_support.base import TimeStampedModel


class WodInputDraft(TimeStampedModel):
    """Texto recuperável antes da confirmação; nunca é o WOD publicado."""

    class Scope(models.TextChoices):
        DAILY = 'daily', 'Diário'
        WEEKLY = 'weekly', 'Semanal'

    class State(models.TextChoices):
        ACTIVE = 'active', 'Ativo'
        DISCARDED = 'discarded', 'Descartado'
        EXPIRED = 'expired', 'Expirado'

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING,
        related_name='wod_input_drafts',
    )
    scope_kind = models.CharField(max_length=8, choices=Scope.choices)
    scope_key = models.CharField(max_length=96)
    session = models.ForeignKey(
        'boxcore.ClassSession', on_delete=models.CASCADE, null=True, blank=True,
        related_name='input_drafts',
    )
    weekly_plan = models.ForeignKey(
        'student_app.WeeklyWodPlan', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='input_drafts',
    )
    workout_program = models.ForeignKey(
        'boxcore.WorkoutProgram', on_delete=models.PROTECT, null=True, blank=True,
        related_name='wod_input_drafts',
    )
    week_start = models.DateField(null=True, blank=True)
    source_text = models.TextField(blank=True)
    version = models.PositiveIntegerField(default=1)
    parser_version = models.CharField(max_length=32, default='wod-input-v1')
    create_request_id = models.UUIDField()
    last_request_id = models.UUIDField(null=True, blank=True)
    state = models.CharField(max_length=12, choices=State.choices, default=State.ACTIVE)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        indexes = [models.Index(fields=['author', 'state', 'expires_at'], name='wod_draft_author_state_exp')]
        constraints = [
            models.UniqueConstraint(
                fields=['author', 'scope_key'], condition=models.Q(state='active'),
                name='wod_draft_active_author_scope',
            ),
            models.UniqueConstraint(
                fields=['author', 'create_request_id'],
                name='wod_draft_author_request',
            ),
        ]


class WodApplyIntent(TimeStampedModel):
    """Prévia diária tenant-local e recibo durável de uma confirmação."""

    class State(models.TextChoices):
        PREPARED = 'prepared', 'Preparada'
        CONFIRMED = 'confirmed', 'Confirmada'

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING,
        related_name='wod_apply_intents',
    )
    target_date = models.DateField()
    workout_program = models.ForeignKey('boxcore.WorkoutProgram', on_delete=models.PROTECT)
    template = models.ForeignKey('operations.WorkoutTemplate', on_delete=models.PROTECT)
    mode = models.CharField(max_length=16)
    fingerprint = models.CharField(max_length=64)
    preview_snapshot = models.JSONField(default=dict)
    response_payload = models.JSONField(default=dict, blank=True)
    state = models.CharField(max_length=12, choices=State.choices, default=State.PREPARED)
    expires_at = models.DateTimeField()
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['author', 'state', 'expires_at'], name='wod_intent_author_state_exp')]



__all__ = ['WodApplyIntent', 'WodInputDraft']

