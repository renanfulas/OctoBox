"""
ARQUIVO: estado proprio da identidade do app do aluno.

POR QUE ELE EXISTE:
- separa a conta de acesso do aluno da conta interna de funcionarios.
- ancora o vinculo multi-box e o historico de transferencia sem reacoplar em boxcore.

SPRINT 2 — MUDANCAS CRITICAS:
- Removidas FKs cross-schema (public -> tenant): StudentIdentity.student,
  StudentBoxMembership.student, StudentAppInvitation.student, StudentTransfer.student.
- Substituidas por student_id: IntegerField (referencia fraca, sem constraint DB).
- Adicionados student_name: CharField (denormalizado para display sem query cross-schema).
- Adicionado box: FK(control.Box, null=True) em todos os modelos que tinham box_root_slug.
- box_root_slug mantido como campo legado durante transicao (Sprint 4 remove).

POR QUE FK cross-schema e INVALIDA:
  public.student_identity_studentidentity.student_id -> box_XXX.boxcore_student.id
  Postgres nao aplica constraint referencial cross-schema. Ao trocar search_path para
  um tenant diferente do student, identity.student falha com "relation not found".
  Solucao: IntegerField(student_id) + schema_context explicito nos call sites.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from model_support.base import TimeStampedModel
from shared_support.box_runtime import get_box_runtime_slug


def _default_box_root_slug() -> str:
    return get_box_runtime_slug()


def _fetch_student_in_box_schema(*, student_id, box_id=None, box_root_slug: str = ''):
    """Sprint 2/4 compatibility shim — busca Student per-tenant a partir do
    schema correto.

    Models de identity (StudentIdentity, StudentAppInvitation,
    StudentBoxMembership, StudentTransfer) vivem em SHARED_APPS (public).
    Student vive em TENANT_APPS (box_xxx). A FK direta foi removida (era
    cross-schema fragil), entao acessar `obj.student` antes era um JOIN
    SQL ilegal. Esta funcao ativa o schema do box ANTES do lookup, evitando
    'relation boxcore_student does not exist' quando o caller esta em
    public (ex.: OAuth callback pre-auth).
    """
    if not student_id:
        return None
    from students.models import Student
    schema_name = ''
    if box_id:
        try:
            from control.models import Box
            schema_name = Box.objects.values_list('schema_name', flat=True).get(pk=box_id)
        except Exception:
            schema_name = ''
    if not schema_name and box_root_slug:
        # box_root_slug historicamente armazena o schema_name (ex.: 'box_test')
        schema_name = box_root_slug
    if not schema_name:
        # Sem info de box — tenta no schema corrente (degradacao aceitavel)
        try:
            return Student.objects.get(pk=student_id)
        except Student.DoesNotExist:
            return None
    try:
        from django_tenants.utils import schema_context
        with schema_context(schema_name):
            try:
                return Student.objects.get(pk=student_id)
            except Student.DoesNotExist:
                return None
    except Exception:
        return None


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


class StudentInvitationType(models.TextChoices):
    INDIVIDUAL = 'individual', 'Individual'
    OPEN_BOX = 'open_box', 'Box com aprovacao'


class StudentOnboardingJourney(models.TextChoices):
    MASS_BOX_INVITE = 'mass_box_invite', 'Link em massa do box'
    IMPORTED_LEAD_INVITE = 'imported_lead_invite', 'Lead importado'
    REGISTERED_STUDENT_INVITE = 'registered_student_invite', 'Aluno ja cadastrado'


class StudentInvitationDeliveryStatus(models.TextChoices):
    SENT = 'sent', 'Enviado'
    FAILED = 'failed', 'Falhou'
    DELIVERED = 'delivered', 'Entregue'
    DELAYED = 'delayed', 'Atrasado'
    BOUNCED = 'bounced', 'Bounce'
    COMPLAINED = 'complained', 'Reclamado'
    SUPPRESSED = 'suppressed', 'Suprimido'


class StudentBoxMembershipStatus(models.TextChoices):
    PENDING_APPROVAL = 'pending_approval', 'Aguardando aprovacao'
    ACTIVE = 'active', 'Ativo'
    INACTIVE = 'inactive', 'Inativo'
    SUSPENDED_FINANCIAL = 'suspended_financial', 'Suspenso financeiro'
    REVOKED = 'revoked', 'Revogado'
    EXPIRED = 'expired', 'Expirado'


class StudentIdentity(TimeStampedModel):
    # Sprint 2: student_id e referencia fraca (IntegerField, sem FK constraint).
    # A FK OneToOneField(Student) foi removida — era cross-schema (public->tenant).
    # Para buscar o Student: use schema_context(self.box.schema_name) + Student.objects.get(pk=self.student_id)
    student_id = models.IntegerField(null=True, blank=True, db_index=True)
    student_name = models.CharField(max_length=150, blank=True, db_index=True)  # denormalizado

    # box: FK para control.Box (Sprint 2). box_root_slug mantido como campo legado (remove Sprint 4).
    box = models.ForeignKey(
        'control.Box',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_identities',
        db_index=True,
    )
    box_root_slug = models.CharField(max_length=64, db_index=True, default=_default_box_root_slug)  # legado

    primary_box = models.ForeignKey(
        'control.Box',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='primary_student_identities',
        db_index=True,
    )
    primary_box_root_slug = models.CharField(max_length=64, db_index=True, default=_default_box_root_slug)  # legado

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
    photo_url = models.URLField(blank=True, max_length=500)

    class Meta:
        ordering = ['student_name']  # Sprint 2: era 'student__full_name' (cross-schema JOIN)
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

    @property
    def student(self):
        """Sprint 2 compatibility shim. Ver _fetch_student_in_box_schema."""
        return _fetch_student_in_box_schema(
            student_id=self.student_id,
            box_id=self.box_id,
            box_root_slug=self.box_root_slug or '',
        )

    def __str__(self):
        return f'{self.student_name or self.email} [{self.box_root_slug}]'


class StudentBoxMembership(TimeStampedModel):
    identity = models.ForeignKey(StudentIdentity, on_delete=models.CASCADE, related_name='memberships')
    # Sprint 2: student_id e referencia fraca (IntegerField, sem FK constraint).
    # A FK ForeignKey(Student) foi removida — era cross-schema (public->tenant).
    student_id = models.IntegerField(null=True, blank=True, db_index=True)

    # box: FK para control.Box (Sprint 2). box_root_slug mantido como campo legado (remove Sprint 4).
    box = models.ForeignKey(
        'control.Box',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_memberships',
        db_index=True,
    )
    box_root_slug = models.CharField(max_length=64, db_index=True)  # legado

    status = models.CharField(
        max_length=24,
        choices=StudentBoxMembershipStatus.choices,
        default=StudentBoxMembershipStatus.PENDING_APPROVAL,
        db_index=True,
    )
    created_from_invite = models.ForeignKey(
        'StudentAppInvitation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='memberships_created',
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_student_box_memberships',
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    last_access_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        # Sprint 2: era ['student__full_name', 'box_root_slug'] — cross-schema JOIN removido
        ordering = ['box_root_slug']
        constraints = [
            models.UniqueConstraint(
                fields=['identity', 'box_root_slug'],
                name='unique_student_membership_per_identity_box',
            ),
        ]

    @property
    def student(self):
        """Sprint 2 compatibility shim — ver _fetch_student_in_box_schema."""
        return _fetch_student_in_box_schema(
            student_id=self.student_id,
            box_id=getattr(self, 'box_id', None),
            box_root_slug=getattr(self, 'box_root_slug', '') or '',
        )

    def mark_active(self):
        now = timezone.now()
        self.status = StudentBoxMembershipStatus.ACTIVE
        self.approved_at = self.approved_at or now
        self.last_access_at = now

    def mark_suspended_financial(self):
        self.status = StudentBoxMembershipStatus.SUSPENDED_FINANCIAL

    def mark_revoked(self, *, reason: str = ''):
        self.status = StudentBoxMembershipStatus.REVOKED
        self.revoked_at = timezone.now()
        self.revoked_reason = reason

    def __str__(self):
        return f'{self.identity.student_name} [{self.box_root_slug}] ({self.status})'


class StudentAppInvitation(TimeStampedModel):
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    invite_type = models.CharField(
        max_length=16,
        choices=StudentInvitationType.choices,
        default=StudentInvitationType.INDIVIDUAL,
        db_index=True,
    )
    # Sprint 2: student_id e referencia fraca (IntegerField, sem FK constraint).
    # A FK ForeignKey(Student) foi removida — era cross-schema (public->tenant).
    student_id = models.IntegerField(null=True, blank=True, db_index=True)
    student_name = models.CharField(max_length=150, blank=True)  # denormalizado

    # box: FK para control.Box (Sprint 2). box_root_slug mantido como campo legado (remove Sprint 4).
    box = models.ForeignKey(
        'control.Box',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_invitations',
        db_index=True,
    )
    box_root_slug = models.CharField(max_length=64, db_index=True, default=_default_box_root_slug)  # legado

    invited_email = models.EmailField(blank=True)
    onboarding_journey = models.CharField(
        max_length=32,
        choices=StudentOnboardingJourney.choices,
        default=StudentOnboardingJourney.REGISTERED_STUDENT_INVITE,
        db_index=True,
    )
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

    @property
    def student(self):
        """Sprint 2 compatibility shim — ver _fetch_student_in_box_schema."""
        return _fetch_student_in_box_schema(
            student_id=self.student_id,
            box_id=getattr(self, 'box_id', None),
            box_root_slug=getattr(self, 'box_root_slug', '') or '',
        )

    def __str__(self):
        return f'Invite {self.student_name or self.student_id} [{self.box_root_slug}]'


class StudentBoxInviteLink(TimeStampedModel):
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    # box: FK para control.Box (Sprint 2). box_root_slug mantido como campo legado (remove Sprint 4).
    box = models.ForeignKey(
        'control.Box',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_invite_links',
        db_index=True,
    )
    box_root_slug = models.CharField(max_length=64, db_index=True, default=_default_box_root_slug)  # legado

    expires_at = models.DateTimeField(db_index=True)
    max_uses = models.PositiveIntegerField(default=200)
    use_count = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_box_invite_links',
    )
    paused_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def is_expired(self) -> bool:
        return self.expires_at <= timezone.now()

    @property
    def is_paused(self) -> bool:
        return self.paused_at is not None

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    @property
    def is_exhausted(self) -> bool:
        return self.use_count >= self.max_uses

    @property
    def can_accept(self) -> bool:
        return not self.is_expired and not self.is_paused and not self.is_revoked and not self.is_exhausted

    def __str__(self):
        return f'Link em massa [{self.box_root_slug}]'


class StudentTransfer(TimeStampedModel):
    identity = models.ForeignKey(StudentIdentity, on_delete=models.CASCADE, related_name='transfers')
    # Sprint 2: student_id e referencia fraca (IntegerField, sem FK constraint).
    # A FK ForeignKey(Student) foi removida — era cross-schema (public->tenant).
    student_id = models.IntegerField(null=True, blank=True, db_index=True)

    from_box_root_slug = models.CharField(max_length=64)  # legado
    to_box_root_slug = models.CharField(max_length=64)    # legado

    # box FKs para controle.Box — substituem from/to_box_root_slug no Sprint 4
    from_box = models.ForeignKey(
        'control.Box',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transfers_from',
    )
    to_box = models.ForeignKey(
        'control.Box',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transfers_to',
    )

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

    @property
    def student(self):
        """Sprint 2 compatibility shim — ver _fetch_student_in_box_schema."""
        return _fetch_student_in_box_schema(
            student_id=self.student_id,
            box_id=getattr(self, 'box_id', None),
            box_root_slug=getattr(self, 'box_root_slug', '') or '',
        )

    def __str__(self):
        return f'student_id={self.student_id}: {self.from_box_root_slug} -> {self.to_box_root_slug}'


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
        return f'{self.invitation.student_name} {self.channel} {self.status}'


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


class StudentPushSubscription(TimeStampedModel):
    identity = models.ForeignKey(StudentIdentity, on_delete=models.CASCADE, related_name='push_subscriptions')

    # box: FK para control.Box (Sprint 2). box_root_slug mantido como campo legado (remove Sprint 4).
    box = models.ForeignKey(
        'control.Box',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_push_subscriptions',
        db_index=True,
    )
    box_root_slug = models.CharField(max_length=64, db_index=True, default=_default_box_root_slug)  # legado

    endpoint = models.CharField(max_length=500, unique=True, db_index=True)
    subscription = models.JSONField(default=dict, blank=True)
    device_fingerprint = models.CharField(max_length=64, blank=True, db_index=True)
    user_agent = models.CharField(max_length=255, blank=True)
    last_seen_at = models.DateTimeField(default=timezone.now, db_index=True)
    last_push_sent_at = models.DateTimeField(null=True, blank=True)
    last_error_at = models.DateTimeField(null=True, blank=True)
    last_error_message = models.CharField(max_length=255, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ['-updated_at']

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None

    def mark_seen(self):
        self.last_seen_at = timezone.now()
        self.revoked_at = None
        self.last_error_at = None
        self.last_error_message = ''

    def mark_push_sent(self):
        self.last_push_sent_at = timezone.now()
        self.last_error_at = None
        self.last_error_message = ''

    def mark_push_failed(self, *, error_message: str):
        self.last_error_at = timezone.now()
        self.last_error_message = (error_message or '')[:255]

    def mark_revoked(self, *, error_message: str = ''):
        self.revoked_at = timezone.now()
        self.last_error_message = (error_message or '')[:255]
        self.last_error_at = timezone.now()

    def __str__(self):
        return f'{self.identity.student_name} push [{self.box_root_slug}]'
