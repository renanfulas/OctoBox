"""
ARQUIVO: estado proprio da identidade do app do aluno.

POR QUE ELE EXISTE:
- separa a conta de acesso do aluno da conta interna de funcionarios.
- ancora o vinculo single-box e o historico de transferencia sem reacoplar em boxcore.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from model_support.base import TimeStampedModel
from shared_support.box_runtime import get_box_runtime_slug
from students.models import Student


def _default_box_root_slug() -> str:
    return get_box_runtime_slug()


class StudentIdentityStatus(models.TextChoices):
    PENDING = 'pending', 'Pendente'
    ACTIVE = 'active', 'Ativa'
    TRANSFERRED = 'transferred', 'Transferida'
    BLOCKED = 'blocked', 'Bloqueada'


class StudentIdentityProvider(models.TextChoices):
    GOOGLE = 'google', 'Google'
    APPLE = 'apple', 'Apple'


class StudentTransferStatus(models.TextChoices):
    REQUESTED = 'requested', 'Solicitada'
    COMPLETED = 'completed', 'Concluida'
    CANCELED = 'canceled', 'Cancelada'


class StudentInvitationChannel(models.TextChoices):
    EMAIL = 'email', 'E-mail'
    WHATSAPP = 'whatsapp', 'WhatsApp'


class StudentInvitationDeliveryStatus(models.TextChoices):
    SENT = 'sent', 'Enviado'
    FAILED = 'failed', 'Falhou'
    DELIVERED = 'delivered', 'Entregue'
    DELAYED = 'delayed', 'Atrasado'
    BOUNCED = 'bounced', 'Bounce'
    COMPLAINED = 'complained', 'Reclamado'
    SUPPRESSED = 'suppressed', 'Suprimido'


class StudentIdentity(TimeStampedModel):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='app_identity')
    box_root_slug = models.CharField(max_length=64, db_index=True, default=_default_box_root_slug)
    provider = models.CharField(max_length=16, choices=StudentIdentityProvider.choices)
    provider_subject = models.CharField(max_length=255, unique=True)
    email = models.EmailField(db_index=True)
    status = models.CharField(
        max_length=16,
        choices=StudentIdentityStatus.choices,
        default=StudentIdentityStatus.PENDING,
        db_index=True,
    )
    invited_at = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    last_authenticated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['student__full_name']
        constraints = [
            models.UniqueConstraint(
                fields=['email', 'box_root_slug'],
                condition=models.Q(status__in=[StudentIdentityStatus.PENDING, StudentIdentityStatus.ACTIVE]),
                name='unique_student_identity_email_box_when_live',
            ),
        ]

    def mark_authenticated(self):
        now = timezone.now()
        self.last_authenticated_at = now
        if self.status == StudentIdentityStatus.PENDING:
            self.status = StudentIdentityStatus.ACTIVE
            self.activated_at = now

    def __str__(self):
        return f'{self.student.full_name} [{self.box_root_slug}]'


class StudentAppInvitation(TimeStampedModel):
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='app_invitations')
    box_root_slug = models.CharField(max_length=64, db_index=True, default=_default_box_root_slug)
    invited_email = models.EmailField(blank=True)
    expires_at = models.DateTimeField(db_index=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_app_invitations',
    )

    class Meta:
        ordering = ['-created_at']

    @property
    def is_expired(self) -> bool:
        return self.expires_at <= timezone.now()

    def __str__(self):
        return f'Invite {self.student.full_name} [{self.box_root_slug}]'


class StudentTransfer(TimeStampedModel):
    identity = models.ForeignKey(StudentIdentity, on_delete=models.CASCADE, related_name='transfers')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='app_transfers')
    from_box_root_slug = models.CharField(max_length=64)
    to_box_root_slug = models.CharField(max_length=64)
    status = models.CharField(
        max_length=16,
        choices=StudentTransferStatus.choices,
        default=StudentTransferStatus.REQUESTED,
        db_index=True,
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requested_student_transfers',
    )
    effective_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    reason = models.CharField(max_length=255, blank=True)
    audit_summary = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.student.full_name}: {self.from_box_root_slug} -> {self.to_box_root_slug}'


class StudentInvitationDelivery(TimeStampedModel):
    invitation = models.ForeignKey(StudentAppInvitation, on_delete=models.CASCADE, related_name='deliveries')
    channel = models.CharField(max_length=16, choices=StudentInvitationChannel.choices)
    provider = models.CharField(max_length=32, db_index=True)
    status = models.CharField(
        max_length=16,
        choices=StudentInvitationDeliveryStatus.choices,
        db_index=True,
    )
    recipient = models.CharField(max_length=255)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_invitation_deliveries',
    )
    provider_message_id = models.CharField(max_length=120, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.invitation.student.full_name} {self.channel} {self.status}'


class StudentInvitationDeliveryEvent(TimeStampedModel):
    delivery = models.ForeignKey(StudentInvitationDelivery, on_delete=models.CASCADE, related_name='events')
    provider_event_id = models.CharField(max_length=120, unique=True, db_index=True)
    provider = models.CharField(max_length=32, db_index=True)
    event_type = models.CharField(max_length=64, db_index=True)
    occurred_at = models.DateTimeField(null=True, blank=True)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.provider} {self.event_type}'
