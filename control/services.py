"""
ARQUIVO: serviços de controle do ciclo de vida de Box (provisioning, archiving).

POR QUE ELE EXISTE:
- Encapsula toda a lógica de CREATE SCHEMA, migrate, bootstrap e seed em um lugar testável.
- Usa BoxProvisioningEvent como checkpoint de idempotência (DDL não é transacional no Postgres).

O QUE ESTE ARQUIVO FAZ:
1. derive_slug(box_name) — slugifica + sufixo numérico em colisão.
2. provision_box(pending_signup, owner_user, display_name, plan) — cria Box + schema + roles + plans.
3. archive_box(box) — muda status para ARCHIVED e renomeia schema.
4. reprovision_box(box) — retoma provisioning a partir do step pendente.

PONTOS CRITICOS:
- CREATE SCHEMA não é transacional — cada step tem checkpoint em BoxProvisioningEvent.
- provision_box é idempotente: chamar 2x com mesmo pending_signup retorna mesmo Box.
- schema_name = f'box_{slug}' — slug máx 59 chars para respeitar limite de 63 do Postgres.
- archive_box NÃO deleta dados — apenas renomeia schema para archived_box_<slug>_<ts>.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from django.db import connection
from django_tenants.utils import schema_context

logger = logging.getLogger('control.services')

User = get_user_model()

# Regex validação: 2 a 59 chars, começa com letra, só lowercase + dígitos + hífens
SLUG_RE = re.compile(r'^[a-z][a-z0-9-]{1,58}$')

PROVISIONING_STEPS = [
    'create_schema',
    'migrate',
    'bootstrap_roles',
    'seed_plans',
]

DEFAULT_MEMBERSHIP_PLANS = [
    # Campos reais de MembershipPlan: name, price (Decimal), billing_cycle, sessions_per_week, active
    {'name': 'Mensal Standard', 'price': '150.00', 'billing_cycle': 'monthly'},
    {'name': 'Trimestral', 'price': '420.00', 'billing_cycle': 'quarterly'},
    {'name': 'Anual', 'price': '1500.00', 'billing_cycle': 'annual'},
]

BOOTSTRAP_ROLES = ['Owner', 'Manager', 'Coach', 'Recepcao']


# ---------------------------------------------------------------------------
# Slug
# ---------------------------------------------------------------------------

def derive_slug(box_name: str) -> str:
    """
    Gera slug único a partir do nome do box.

    1. django.utils.text.slugify → lowercase ASCII + hífens.
    2. Truncar para 55 chars (folga para sufixo '-NN').
    3. Sufixar -2, -3, ... se colisão.

    Retorna slug já salvo como único (não cria o Box ainda).
    """
    from django.utils.text import slugify
    from control.models import Box

    base = slugify(box_name)[:55] or 'box'
    candidate = base
    counter = 2
    while True:
        if not Box.objects.filter(slug=candidate).exists():
            return candidate
        candidate = f'{base}-{counter}'
        counter += 1
        if counter > 999:
            raise ValueError(f'Impossível gerar slug único para "{box_name}" após 999 tentativas.')


# ---------------------------------------------------------------------------
# Provisioning
# ---------------------------------------------------------------------------

def provision_box(
    *,
    owner_user,
    display_name: str,
    slug: str | None = None,
    plan: str = 'monthly',
    pending_signup=None,
    stripe_customer_id: str = '',
    stripe_subscription_id: str = '',
) -> 'Box':
    """
    Cria e provisiona um Box completo.

    Idempotente: se Box com mesmo pending_signup já existe, retoma steps pendentes.

    Steps:
    1. create_schema  — CREATE SCHEMA box_<slug>
    2. migrate        — migrate_schemas --schema=box_<slug>
    3. bootstrap_roles — criar Groups no schema
    4. seed_plans     — criar MembershipPlan default

    Retorna Box com status ACTIVE se todos os steps passaram.
    """
    from control.models import Box, Membership

    # Idempotência: Box já existe para este pending_signup?
    if pending_signup is not None:
        try:
            box = Box.objects.get(pending_signup=pending_signup)
            logger.info('provision_box: Box %s já existe, retomando.', box.slug)
            return reprovision_box(box)
        except Box.DoesNotExist:
            pass

    if slug is None:
        slug = derive_slug(display_name)

    if not SLUG_RE.match(slug):
        raise ValueError(f'Slug inválido: {slug!r}. Deve ser ^[a-z][a-z0-9-]{{1,58}}$')

    schema_name = f'box_{slug}'
    logger.info('provision_box: iniciando Box slug=%s schema=%s', slug, schema_name)

    # Criar Box em public (sem schema ainda)
    box = Box.objects.create(
        slug=slug,
        schema_name=schema_name,
        display_name=display_name,
        status=Box.Status.PROVISIONING,
        owner_user=owner_user,
        plan=plan,
        pending_signup=pending_signup,
        stripe_customer_id=stripe_customer_id,
        stripe_subscription_id=stripe_subscription_id,
    )

    # Criar Membership do owner
    Membership.objects.create(
        user=owner_user,
        box=box,
        role=Membership.Role.OWNER,
        is_primary_box=True,
    )

    return reprovision_box(box)


def reprovision_box(box: 'Box') -> 'Box':
    """
    Retoma provisioning a partir do step pendente (idempotente).
    Pula steps com evento status='ok'. Recria steps com status='failed'.
    """
    from control.models import BoxProvisioningEvent

    for step in PROVISIONING_STEPS:
        ok_exists = BoxProvisioningEvent.objects.filter(
            box=box, step=step, status='ok'
        ).exists()
        if ok_exists:
            logger.debug('provision_box: step=%s ja concluido para %s — pulando.', step, box.slug)
            continue

        evt = BoxProvisioningEvent.objects.create(box=box, step=step, status='started')
        try:
            _run_step(step, box)
            evt.status = 'ok'
            evt.save(update_fields=['status'])
            logger.info('provision_box: step=%s OK para %s', step, box.slug)
        except Exception as exc:
            evt.status = 'failed'
            evt.detail = str(exc)
            evt.save(update_fields=['status', 'detail'])
            logger.error('provision_box: step=%s FALHOU para %s: %s', step, box.slug, exc)
            raise

    # Todos os steps concluídos → ativar
    from django.utils import timezone as dj_tz
    Box = box.__class__
    Box.objects.filter(pk=box.pk).update(
        status=Box.Status.ACTIVE,
        provisioned_at=dj_tz.now(),
    )
    box.refresh_from_db()
    logger.info('provision_box: Box %s ATIVO em %s', box.slug, box.schema_name)

    _record_platform_audit(box, 'box.provisioned')
    return box


def _run_step(step: str, box: 'Box') -> None:
    """Executa um step de provisioning."""
    if step == 'create_schema':
        _create_schema(box)
    elif step == 'migrate':
        _migrate_schema(box)
    elif step == 'bootstrap_roles':
        _bootstrap_roles(box)
    elif step == 'seed_plans':
        _seed_plans(box)
    else:
        raise ValueError(f'Step desconhecido: {step!r}')


def _create_schema(box: 'Box') -> None:
    """Cria o schema Postgres para o tenant."""
    from django_tenants.utils import get_tenant_database_alias
    from django.db import connections

    db_alias = get_tenant_database_alias()
    with connections[db_alias].cursor() as cursor:
        # Verificar se schema já existe (idempotente a nível DDL)
        cursor.execute(
            "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
            [box.schema_name],
        )
        if cursor.fetchone():
            logger.info('_create_schema: schema %s já existe — pulando CREATE.', box.schema_name)
            return
        cursor.execute(f'CREATE SCHEMA "{box.schema_name}"')
    logger.info('_create_schema: schema %s criado.', box.schema_name)


def _migrate_schema(box: 'Box') -> None:
    """Aplica todas as migrations TENANT_APPS no schema do tenant."""
    from django.core.management import call_command

    # migrate_schemas com --schema=xxx aplica apenas as TENANT_APPS no schema indicado
    call_command('migrate_schemas', schema=box.schema_name, verbosity=0, interactive=False)
    logger.info('_migrate_schema: migrations aplicadas em %s.', box.schema_name)


def _bootstrap_roles(box: 'Box') -> None:
    """Cria Groups padrão no schema do tenant (Owner, Manager, Coach, Recepcao)."""
    with schema_context(box.schema_name):
        from django.contrib.auth.models import Group
        for role_name in BOOTSTRAP_ROLES:
            Group.objects.get_or_create(name=role_name)
    logger.info('_bootstrap_roles: grupos criados em %s.', box.schema_name)


def _seed_plans(box: 'Box') -> None:
    """Cria MembershipPlan default no schema do tenant."""
    with schema_context(box.schema_name):
        # Import via apps histórico para evitar circular imports
        from django.apps import apps
        MembershipPlan = apps.get_model('boxcore', 'MembershipPlan')
        for plan_data in DEFAULT_MEMBERSHIP_PLANS:
            MembershipPlan.objects.get_or_create(
                name=plan_data['name'],
                defaults={
                    'price': plan_data['price'],
                    'billing_cycle': plan_data['billing_cycle'],
                },
            )
    logger.info('_seed_plans: planos default criados em %s.', box.schema_name)


# ---------------------------------------------------------------------------
# Archiving
# ---------------------------------------------------------------------------

def archive_box(box: 'Box', *, reason: str = '') -> 'Box':
    """
    Arquiva um Box: status ARCHIVED + renomeia schema.

    NÃO deleta dados — schema fica acessível como archived_box_<slug>_<timestamp>.
    Reversível manualmente via SQL (renomear schema de volta + status=ACTIVE).

    AVISO: depois de archived, o Box não pode mais ser ativado via provision_box.
    Criar novo Box com novo slug se necessário.
    """
    from django.utils import timezone as dj_tz
    from django.db import connections
    from django_tenants.utils import get_tenant_database_alias

    if box.status == box.__class__.Status.ARCHIVED:
        logger.warning('archive_box: Box %s já está ARCHIVED.', box.slug)
        return box

    ts = datetime.now(tz=timezone.utc).strftime('%Y%m%d%H%M%S')
    archived_schema = f'archived_box_{box.slug}_{ts}'

    db_alias = get_tenant_database_alias()
    with connections[db_alias].cursor() as cursor:
        cursor.execute(
            f'ALTER SCHEMA "{box.schema_name}" RENAME TO "{archived_schema}"'
        )

    now = dj_tz.now()
    box.__class__.objects.filter(pk=box.pk).update(
        status=box.__class__.Status.ARCHIVED,
        archived_at=now,
        schema_name=archived_schema,
    )
    box.refresh_from_db()
    logger.info('archive_box: %s arquivado como %s.', box.slug, archived_schema)

    _record_platform_audit(box, 'box.archived', {'reason': reason})
    return box


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _record_platform_audit(box: 'Box', kind: str, payload: dict | None = None) -> None:
    """Registra evento de plataforma em public."""
    try:
        from control.models import PlatformAuditEvent
        PlatformAuditEvent.objects.create(
            target_box=box,
            kind=kind,
            payload=payload or {},
        )
    except Exception:
        logger.exception('_record_platform_audit: falha ao registrar %s para %s', kind, box.slug)
