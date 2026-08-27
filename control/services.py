"""
ARQUIVO: serviços de controle do ciclo de vida de Box (provisioning, archiving).

POR QUE ELE EXISTE:
- Encapsula toda a lógica de CREATE SCHEMA, migrate, bootstrap e seed em um lugar testável.
- Usa BoxProvisioningEvent como checkpoint de idempotência (DDL não é transacional no Postgres).

O QUE ESTE ARQUIVO FAZ:
1. derive_slug(box_name) — slugifica + sufixo numérico em colisão.
2. provision_box(pending_signup, owner_user, display_name, plan) — cria Box + schema + roles + plans.
3. archive_box(box) — muda status para ARCHIVED e renomeia schema.
4. unarchive_box(box) — desfaz o archive: schema volta ao nome original, Box vai a SUSPENDED.
5. activate_box(box) — reativa SUSPENDED->ACTIVE manualmente, com reason obrigatório e audit.
6. reprovision_box(box) — retoma provisioning a partir do step pendente.

PONTOS CRITICOS:
- CREATE SCHEMA não é transacional — cada step tem checkpoint em BoxProvisioningEvent.
- provision_box é idempotente: chamar 2x com mesmo pending_signup retorna mesmo Box.
- schema_name = f'box_{slug}' — slug máx 59 chars para respeitar limite de 63 do Postgres.
- archive_box NÃO deleta dados — apenas renomeia schema para archived_box_<slug>_<ts>.
- Nome de schema não é parametrizável em SQL: tudo que entra em DDL passa por
  _validate_schema_ident() antes de ser interpolado.
- unarchive_box devolve SUSPENDED, nunca ACTIVE: acesso só volta por billing (ou por activate_box).
- reprovision_box NÃO promove SUSPENDED/ARCHIVED->ACTIVE: só PROVISIONING->ACTIVE, e via UPDATE
  atômico condicionado no banco (não checagem em memória) — imune à corrida com webhook de billing
  suspendendo o box durante os steps de provisioning (que levam minutos).
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

# Schema de box arquivado: archived_box_<slug>_<YYYYMMDDHHMMSS>
ARCHIVED_SCHEMA_RE = re.compile(r'^archived_box_[a-z][a-z0-9-]{1,58}_\d{14}$')

# Quanto do slug cabe no nome do schema arquivado sem estourar os 63 chars do
# Postgres: 63 - len('archived_box_') - len('_') - len('YYYYMMDDHHMMSS') = 35.
MAX_SLUG_EM_SCHEMA_ARQUIVADO = 35

# Identificador aceito em DDL. Nome de schema NÃO é parametrizável em SQL
# (%s não funciona para identificadores), então todo nome que chega a um
# CREATE/ALTER SCHEMA passa por aqui antes de ser interpolado. Whitelist
# estrita: sem aspas, sem espaço, sem ponto, sem maiúscula — nada que possa
# escapar do par de aspas duplas e virar SQL.
SCHEMA_IDENT_RE = re.compile(r'^[a-z][a-z0-9_-]{1,62}$')


def _validate_schema_ident(name: str) -> str:
    """Valida um nome de schema antes de interpolá-lo em DDL. Levanta ValueError.

    Defesa em profundidade: os nomes já vêm de slugs validados, mas esta função
    é o único ponto por onde eles entram em SQL — se um dia um nome vier de
    outra fonte (import, admin, fixture), ele para aqui e não no banco.
    """
    if not isinstance(name, str) or not SCHEMA_IDENT_RE.match(name):
        raise ValueError(f'Nome de schema inválido para DDL: {name!r}')
    return name

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

    Retorna Box com status ACTIVE se todos os steps passaram — válido aqui porque
    o Box criado acima sempre nasce PROVISIONING, e é esse status que a promoção
    final de reprovision_box exige. Chamar reprovision_box() isoladamente (resume/
    backfill) NÃO tem essa garantia — ver contrato na docstring de reprovision_box.
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

    CONTRATO: NÃO promete devolver Box com status ACTIVE. Só promove
    PROVISIONING -> ACTIVE (fluxo novo / resume de provisioning incompleto).
    Box SUSPENDED (inadimplência ou cancelamento) ou ARCHIVED permanece como
    está — reprovision_box é o chokepoint de cura do superdev/schema (attach
    de Membership + steps de provisioning), não um caminho de billing. Só o
    webhook `invoice.payment_succeeded` (integrations/stripe/router.py) ou
    `manage.py activate_box` reativam um box suspenso.

    Antes desta guarda, `update(status=ACTIVE)` era incondicional: rodar este
    comando num box SUSPENDED — inclusive um que acabou de ser suspenso por
    `customer.subscription.deleted` — devolvia acesso sem passar por
    pagamento. O UPDATE abaixo é condicionado a `status=PROVISIONING` no
    próprio banco (não numa checagem em memória no início da função) de
    propósito: `_migrate_schema` leva minutos, e um webhook de cancelamento
    pode suspender o box PROVISIONING nesse intervalo. Checar em memória no
    topo da função leria um status velho e promoveria por cima da suspensão
    de qualquer forma.
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

    # Todos os steps concluídos → promover, MAS só se ainda estiver
    # PROVISIONING. `filter(status=PROVISIONING).update(...)` é atômico no
    # banco: se o status já mudou (SUSPENDED por webhook durante os steps,
    # ou ARCHIVED por offboarding manual), o UPDATE afeta zero linhas e o
    # status atual do banco vence — sem corrida, sem checagem em memória.
    from django.utils import timezone as dj_tz
    Box = box.__class__
    promoted = Box.objects.filter(pk=box.pk, status=Box.Status.PROVISIONING).update(
        status=Box.Status.ACTIVE,
        provisioned_at=dj_tz.now(),
    )
    box.refresh_from_db()
    if promoted:
        logger.info('provision_box: Box %s ATIVO em %s', box.slug, box.schema_name)
    else:
        logger.info(
            'provision_box: Box %s NÃO promovido (status atual=%s, não era PROVISIONING) — '
            'steps de provisioning concluídos, mas ativação de billing preservada.',
            box.slug, box.status,
        )

    # Anexar a conta de suporte (superdev) — SEMPRE, para a equipe OctoBox poder
    # dar suporte sem pedir credencial ao cliente. Chamado aqui (e nao em
    # provision_box) porque reprovision_box e o chokepoint comum do caminho novo
    # e do resume idempotente: assim boxes provisionados antes da conta superdev
    # existir tambem sao curados num reprovision posterior. A prova de falha.
    _attach_support_membership(box)

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
        cursor.execute(f'CREATE SCHEMA "{_validate_schema_ident(box.schema_name)}"')
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

    Reversível via unarchive_box() / manage.py unarchive_box, que devolve o
    schema ao nome original e o Box para SUSPENDED (não ACTIVE — ver lá o porquê).
    provision_box continua não servindo para reativar: o schema mudou de nome.
    """
    from django.utils import timezone as dj_tz
    from django.db import connections, transaction
    from django_tenants.utils import get_tenant_database_alias

    if box.status == box.__class__.Status.ARCHIVED:
        logger.warning('archive_box: Box %s já está ARCHIVED.', box.slug)
        return box

    ts = datetime.now(tz=timezone.utc).strftime('%Y%m%d%H%M%S')

    # 'archived_box_' (13) + slug + '_' (1) + timestamp (14) = 28 + len(slug).
    # Postgres corta identificador em 63 chars SILENCIOSAMENTE: com slug > 35 o
    # schema real ficaria com nome diferente do gravado em Box.schema_name — o
    # tenant vira inalcançável. Truncar aqui é seguro porque o slug nunca é
    # extraído de volta deste nome: unarchive_box reconstrói o destino a partir
    # de Box.slug, que continua íntegro na linha.
    slug_no_nome = box.slug[:MAX_SLUG_EM_SCHEMA_ARQUIVADO]
    archived_schema = f'archived_box_{slug_no_nome}_{ts}'

    origem = _validate_schema_ident(box.schema_name)
    destino = _validate_schema_ident(archived_schema)

    db_alias = get_tenant_database_alias()

    # Mesma razão do unarchive_box: o RENAME e o UPDATE da linha precisam entrar
    # ou sair juntos. Sem isso, uma falha entre os dois deixa Box.schema_name
    # apontando para um schema que não existe mais.
    with transaction.atomic(using=db_alias):
        with connections[db_alias].cursor() as cursor:
            cursor.execute(f'ALTER SCHEMA "{origem}" RENAME TO "{destino}"')

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


def unarchive_box(box: 'Box', *, reason: str = '', actor=None) -> 'Box':
    """
    Reverte archive_box: devolve o schema ao nome original e o Box ao ciclo de vida.

    Renomeia archived_box_<slug>_<ts> de volta para box_<slug> e coloca o Box em
    SUSPENDED — deliberadamente NÃO em ACTIVE.

    POR QUE SUSPENDED E NÃO ACTIVE:
    Arquivar significa que a cobrança acabou. Se unarchive devolvesse ACTIVE,
    existiria um caminho que restaura acesso completo sem nenhuma assinatura
    viva do outro lado — e esse caminho seria acionável por quem tem acesso ao
    management command, sem passar por billing. Em SUSPENDED os dados voltam
    intactos e a reativação continua sendo o mesmo caminho de sempre:
    invoice.payment_succeeded → ACTIVE. Um único portão para dar acesso.

    Não mexe em Membership: archive_box nunca apagou vínculo (o Box permanece na
    linha, só muda de status), então o dono continua sendo dono ao voltar.

    Idempotente por guarda, não por repetição: chamar em Box não-ARCHIVED levanta
    ValueError em vez de fazer algo silencioso.
    """
    from django.db import transaction
    from django.utils import timezone as dj_tz
    from django.db import connections
    from django_tenants.utils import get_tenant_database_alias

    Box = box.__class__

    if box.status != Box.Status.ARCHIVED:
        raise ValueError(
            f'unarchive_box: Box {box.slug!r} está {box.status!r}, não ARCHIVED. '
            f'Nada a restaurar.'
        )

    origem = box.schema_name
    if not ARCHIVED_SCHEMA_RE.match(origem or ''):
        raise ValueError(
            f'unarchive_box: schema atual {origem!r} não tem forma de schema '
            f'arquivado (archived_box_<slug>_<timestamp>). Recusando renomear — '
            f'restaure à mão e confira o que gravou esse nome.'
        )

    if not SLUG_RE.match(box.slug or ''):
        raise ValueError(f'unarchive_box: slug inválido {box.slug!r}.')

    destino = f'box_{box.slug}'
    _validate_schema_ident(origem)
    _validate_schema_ident(destino)

    db_alias = get_tenant_database_alias()

    # ALTER SCHEMA RENAME é transacional no Postgres, então o rename e o UPDATE
    # da linha do Box entram ou saem juntos. Sem isso, uma falha entre os dois
    # deixaria Box.schema_name apontando para um schema que não existe mais —
    # o pior estado possível para um tenant.
    with transaction.atomic(using=db_alias):
        with connections[db_alias].cursor() as cursor:
            cursor.execute(
                'SELECT 1 FROM information_schema.schemata WHERE schema_name = %s',
                [origem],
            )
            if cursor.fetchone() is None:
                raise ValueError(
                    f'unarchive_box: schema {origem!r} não existe no banco. '
                    f'O Box está marcado ARCHIVED mas o schema sumiu — '
                    f'restaure do backup antes de tentar de novo.'
                )

            # Nunca sobrescrever um schema vivo. Se box_<slug> já existe, algo
            # recriou o tenant enquanto este estava arquivado: abortar e deixar
            # os dois lados intactos para inspeção humana.
            cursor.execute(
                'SELECT 1 FROM information_schema.schemata WHERE schema_name = %s',
                [destino],
            )
            if cursor.fetchone() is not None:
                raise ValueError(
                    f'unarchive_box: schema destino {destino!r} JÁ EXISTE. '
                    f'Restaurar por cima destruiria dados. Abortado.'
                )

            cursor.execute(f'ALTER SCHEMA "{origem}" RENAME TO "{destino}"')

        Box.objects.filter(pk=box.pk).update(
            status=Box.Status.SUSPENDED,
            schema_name=destino,
            archived_at=None,
            suspended_at=dj_tz.now(),
        )

    box.refresh_from_db()
    logger.warning(
        'unarchive_box: %s restaurado de %s para %s — status SUSPENDED '
        '(reativa via pagamento).', box.slug, origem, destino,
    )

    _record_platform_audit(box, 'box.unarchived', {
        'reason': reason,
        'schema_origem': origem,
        'schema_destino': destino,
        'actor_user_id': getattr(actor, 'pk', None),
    })
    return box


def activate_box(box: 'Box', *, reason: str, actor=None) -> 'Box':
    """
    Reativa manualmente um Box SUSPENDED — para suporte, sem esperar o
    webhook de pagamento.

    POR QUE ELE EXISTE: fechar o UPDATE incondicional de reprovision_box
    (que promovia SUSPENDED->ACTIVE sem checar billing) fechou uma porta,
    mas reativação manual continua sendo uma necessidade operacional real
    (ex.: cliente pagou por fora, disputa resolvida a favor do cliente,
    erro de suspensão). Sem este comando, o primeiro chamado de suporte
    vira UPDATE manual direto no banco de produção — pior que ter um portão
    auditado.

    Só aceita origem SUSPENDED (não ARCHIVED — isso é unarchive_box; não
    PROVISIONING — isso é reprovision_box). `reason` é obrigatório: ao
    contrário de archive_box/unarchive_box, esta é a ÚNICA reativação
    manual do sistema sem confirmação de pagamento — a trilha de motivo
    não é opcional aqui.

    UPDATE condicionado a status=SUSPENDED no banco (mesmo padrão de
    reprovision_box): atômico, sem corrida com um webhook concorrente.
    """
    from django.utils import timezone as dj_tz

    Box = box.__class__

    if not (reason or '').strip():
        raise ValueError('activate_box: reason é obrigatório — reativação manual sem motivo não é permitida.')

    if box.status != Box.Status.SUSPENDED:
        raise ValueError(
            f'activate_box: Box {box.slug!r} está {box.status!r}, não SUSPENDED. '
            f'ARCHIVED usa unarchive_box; PROVISIONING resolve sozinho via reprovision_box.'
        )

    activated = Box.objects.filter(pk=box.pk, status=Box.Status.SUSPENDED).update(
        status=Box.Status.ACTIVE,
        suspended_at=None,
    )
    box.refresh_from_db()

    if not activated:
        # Corrida: o status mudou entre a checagem acima e o UPDATE (ex.: o
        # webhook de pagamento reativou no meio, ou outro operador arquivou).
        raise ValueError(
            f'activate_box: Box {box.slug!r} mudou de status durante a operação '
            f'(agora é {box.status!r}) — nada foi promovido. Rode de novo se ainda fizer sentido.'
        )

    logger.warning(
        'activate_box: Box %s REATIVADO manualmente. reason=%r actor=%s',
        box.slug, reason, getattr(actor, 'username', None) or 'sistema',
    )

    _record_platform_audit(box, 'box.activated_manual_support', {
        'reason': reason,
        'actor_user_id': getattr(actor, 'pk', None),
    })
    return box


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_superdev_user():
    """Resolve a conta unica de suporte (superdev) a anexar em todo box.

    Retorna o User do superdev, ou None se:
    - SUPERDEV_AUTO_ATTACH=False (kill-switch),
    - SUPERDEV_USERNAME vazio,
    - a conta nao existe (rode `manage.py bootstrap_superdev`), ou
    - a conta esta inativa.

    NUNCA levanta: a indisponibilidade do superdev jamais pode quebrar o
    provisionamento de um box. Apenas loga para o operador resolver.
    """
    from django.conf import settings

    if not getattr(settings, 'SUPERDEV_AUTO_ATTACH', True):
        return None

    username = (getattr(settings, 'SUPERDEV_USERNAME', '') or '').strip()
    if not username:
        return None

    user = User.objects.filter(username=username, is_active=True).first()
    if user is None:
        logger.warning(
            'get_superdev_user: conta superdev "%s" inexistente/inativa — rode '
            '"manage.py bootstrap_superdev". Box sera provisionado SEM acesso de suporte.',
            username,
        )
    return user


def _attach_support_membership(box: 'Box') -> None:
    """Anexa o superdev ao box como OWNER com is_primary_box=False.

    Idempotente (get_or_create sob unique_together user+box) e a prova de falha:
    qualquer erro e logado/auditado mas NUNCA propaga — provisionar o box vence.

    is_primary_box=False e critico: o superdev tem Membership em TODOS os boxes;
    se algum fosse primary, o login dele seria resolvido para uma box de cliente
    aleatoria pelo TenantBySessionMiddleware.
    """
    from control.models import Membership

    superdev = get_superdev_user()
    if superdev is None:
        _record_platform_audit(box, 'membership.support_skipped', {'reason': 'superdev_unavailable'})
        return

    if superdev.pk == box.owner_user_id:
        # Edge: o proprio superdev e o owner deste box — owner membership ja cobre.
        return

    try:
        _membership, created = Membership.objects.get_or_create(
            user=superdev,
            box=box,
            defaults={'role': Membership.Role.OWNER, 'is_primary_box': False},
        )
    except Exception:
        logger.exception('_attach_support_membership: falha ao anexar superdev a box=%s', box.slug)
        _record_platform_audit(box, 'membership.support_failed', {'superdev_user_id': superdev.pk})
        return

    if created:
        logger.info('_attach_support_membership: superdev=%s anexado a box=%s', superdev.username, box.slug)
        _record_platform_audit(
            box,
            'membership.support_granted',
            {'superdev_user_id': superdev.pk, 'role': Membership.Role.OWNER},
        )


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
