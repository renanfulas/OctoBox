"""
ARQUIVO: modelos do control plane da plataforma.

POR QUE ELE EXISTE:
- Define Box (tenant django-tenants), Domain, Membership e eventos de provisioning.
- Vive em SHARED_APPS (schema public) — cross-tenant por design.

O QUE ESTE ARQUIVO FAZ:
1. Box: tenant principal, 1:1 com schema Postgres box_<slug>.
2. Domain: mapeamento de host para tenant (Fase 2, subdomain). Placeholder em Fase 1.
3. Membership: User <-> Box m:n. Role por box.
4. BoxProvisioningEvent: checkpoint idempotente de provisioning (CREATE SCHEMA + MIGRATE).
5. PlatformAuditEvent: log cross-tenant de operações da plataforma.

PONTOS CRITICOS:
- slug max_length=59: schema_name = f'box_{slug}' -> max 63 chars (limite Postgres).
- auto_create_schema=False: provisioning explícito via control.services.provision_box.
- auto_drop_schema=False: offboarding via manage.py archive_box.
- Box.status PROVISIONING durante schema creation — nunca exposto ao tenant até ACTIVE.
"""

from __future__ import annotations

from django.db import models
from django_tenants.models import DomainMixin, TenantMixin


class Box(TenantMixin):
    """
    Tenant principal. 1 Box = 1 box de CrossFit = 1 schema Postgres.

    schema_name = f'box_{slug}' — calculado automaticamente pelo serviço de provisioning.
    Nunca alterar schema_name depois de criado (renomear schema = ofboarding via archive_box).

    Slug: max 59 chars para respeitar limite do Postgres (4 + 59 = 63 chars).
    Regex válida: ^[a-z][a-z0-9-]{1,55}$ (slugify + sufixo numérico em colisão).
    """

    class Status(models.TextChoices):
        PROVISIONING = 'provisioning', 'Provisionando'
        ACTIVE = 'active', 'Ativo'
        SUSPENDED = 'suspended', 'Suspenso'      # billing falhou
        ARCHIVED = 'archived', 'Arquivado'         # offboarding concluído

    # C3 FIX: max_length=59 (não 63) — schema_name = 'box_' + slug = 4 + 59 = 63 chars máx
    slug = models.SlugField(max_length=59, unique=True, db_index=True)
    display_name = models.CharField(max_length=120)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PROVISIONING,
        db_index=True,
    )

    owner_user = models.ForeignKey(
        'auth.User',
        on_delete=models.PROTECT,
        related_name='owned_boxes',
    )

    # Stripe — conta única Fase 1 (sem Connect)
    stripe_customer_id = models.CharField(max_length=255, blank=True, db_index=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, db_index=True)
    plan = models.CharField(max_length=16, blank=True)  # 'monthly' | 'annual'

    # Origem do signup (rastreabilidade Early Adopters)
    pending_signup = models.OneToOneField(
        'signup.PendingSignup',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='box',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    provisioned_at = models.DateTimeField(null=True, blank=True)
    suspended_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    # Célula de infraestrutura (escalonamento horizontal futuro)
    cell = models.CharField(max_length=32, default='cell-1', db_index=True)

    # django-tenants: provisioning explícito via manage.py provision_box
    auto_create_schema = False
    auto_drop_schema = False

    class Meta:
        verbose_name = 'Box'
        verbose_name_plural = 'Boxes'
        indexes = [
            models.Index(fields=['status', 'cell']),
            models.Index(fields=['stripe_subscription_id']),
        ]

    def __str__(self) -> str:
        return f'{self.display_name} [{self.schema_name}]'


class Domain(DomainMixin):
    """
    Mapeamento host → Box (Fase 2, subdomain).
    Em Fase 1 (session-based), esta tabela existe mas não é usada para roteamento.
    """

    class Meta:
        verbose_name = 'Domínio'
        verbose_name_plural = 'Domínios'


class Membership(models.Model):
    """
    Vínculo User <-> Box (m:n). 1 usuário pode ser Owner/Manager de N boxes.

    is_primary_box=True: box padrão ao fazer login (sem session['active_box_id']).
    O TenantBySessionMiddleware usa este campo para resolver o schema inicial.
    """

    class Role(models.TextChoices):
        OWNER = 'owner', 'Owner'
        MANAGER = 'manager', 'Manager'
        COACH = 'coach', 'Coach'
        RECEPTION = 'reception', 'Recepção'

    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    box = models.ForeignKey(
        Box,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    role = models.CharField(max_length=16, choices=Role.choices)
    is_primary_box = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'box')]
        indexes = [
            models.Index(fields=['user', 'is_primary_box']),
            models.Index(fields=['box', 'role']),
        ]
        verbose_name = 'Membership'
        verbose_name_plural = 'Memberships'

    def __str__(self) -> str:
        return f'{self.user.username} @ {self.box.slug} ({self.role})'


class BoxProvisioningEvent(models.Model):
    """
    Checkpoint idempotente de provisioning.

    Passos conhecidos:
    - 'create_schema':    CREATE SCHEMA box_xxx (DDL não-transacional)
    - 'migrate':          python manage.py migrate_schemas --schema=box_xxx
    - 'bootstrap_roles':  criar Groups Owner/Manager/Coach/Recepção
    - 'seed_plans':       criar MembershipPlan default do tenant

    Fluxo de idempotência:
    1. Verificar se existe evento com step + status='ok' → pular.
    2. Criar evento com status='started'.
    3. Executar step.
    4. Atualizar evento para status='ok' ou 'failed' + detail.

    Se provision_box for chamado novamente (ex.: retry após falha), os steps já
    concluídos (status='ok') são pulados automaticamente.
    """

    box = models.ForeignKey(
        Box,
        on_delete=models.CASCADE,
        related_name='provisioning_events',
    )
    step = models.CharField(max_length=64)   # 'create_schema' | 'migrate' | 'bootstrap_roles' | 'seed_plans'
    status = models.CharField(max_length=16) # 'started' | 'ok' | 'failed'
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['box', 'step', 'status']),
        ]
        verbose_name = 'BoxProvisioningEvent'
        verbose_name_plural = 'BoxProvisioningEvents'

    def __str__(self) -> str:
        return f'{self.box.slug} | {self.step} | {self.status}'


class PlatformAuditEvent(models.Model):
    """
    Log cross-tenant de operações da plataforma.

    Separado de boxcore.AuditEvent (per-tenant) porque:
    - Provisioning, suspension e archiving acontecem fora de qualquer schema de tenant.
    - Renan (admin) precisa ver histórico de TODOS os boxes em uma view unificada.
    - Investigação de incidentes em public não pode exigir switch de tenant.

    Exemplos de kind:
    - 'box.provisioned'
    - 'box.suspended'
    - 'box.archived'
    - 'membership.granted'
    - 'membership.revoked'
    - 'billing.payment_failed'
    """

    actor_user = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='platform_audit_events',
    )
    target_box = models.ForeignKey(
        Box,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='platform_audit_events',
    )
    kind = models.CharField(max_length=64, db_index=True)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['kind', '-created_at']),
            models.Index(fields=['target_box', '-created_at']),
        ]
        verbose_name = 'PlatformAuditEvent'
        verbose_name_plural = 'PlatformAuditEvents'

    def __str__(self) -> str:
        box_label = self.target_box.slug if self.target_box_id else 'platform'
        actor_label = self.actor_user.username if self.actor_user_id else 'system'
        return f'[{box_label}] {self.kind} by {actor_label}'
