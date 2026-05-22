"""
ARQUIVO: servicos de auditoria.

POR QUE ELE EXISTE:
- Evita espalhar criacao manual de eventos sensiveis pelo projeto.

O QUE ESTE ARQUIVO FAZ:
1. Traduz um alvo opcional em dados persistiveis.
2. Cria eventos padronizados de auditoria.
3. Mantem a escrita da trilha de auditoria em um unico ponto.
4. Garante que a escrita acontece num schema de tenant valido — caso a
   chamada venha de um path PUBLIC_SCHEMA (login, webhook, signup), faz
   resolucao defensiva do tenant antes da escrita.

PONTOS CRITICOS:
- O formato do evento precisa permanecer estavel para futuras consultas e relatorios.
- AuditEvent vive em TENANT_APPS (boxcore_auditevent); INSERT em schema=public
  estoura ProgrammingError. Para fluxos pre-auth ou cross-tenant (login,
  logout, webhook integration) precisamos ativar um tenant valido antes
  da escrita ou aceitar best-effort. Esse contrato esta resolvido pelo
  _ensure_tenant_for_audit_write abaixo, espelhando o padrao Center Layer
  usado em student_identity/facade/tenant_resolver.py para o aluno.
"""

from django.apps import apps
# from reporting.infrastructure.celery_app import app as celery_app


def _ensure_tenant_for_audit_write(actor):
    """Garante schema valido para escrita de boxcore.AuditEvent.

    Ordem de strategies (primeira que resolver vence):
    1. Se connection.schema_name ja e tenant (!= 'public'), no-op.
    2. Se actor tem Membership com is_primary_box=True, ativa esse Box.
    3. Se ha exatamente 1 Box ATIVO no sistema (pilot/single-box), ativa.

    Retorna o Box ativado (ou None se nada resolveu). Em caso None, o
    caller deve envolver a escrita em try/except — INSERT em public falha.
    """
    try:
        from django.db import connection
        schema = getattr(connection, 'schema_name', None)
        if schema and schema != 'public':
            return None  # ja em tenant; no-op

        from control.models import Box, Membership

        # Strategy 2: actor's primary box
        if actor is not None and getattr(actor, 'pk', None):
            try:
                membership = (
                    Membership.objects
                    .select_related('box')
                    .filter(user=actor, is_primary_box=True, box__status=Box.Status.ACTIVE)
                    .first()
                )
                if membership is not None:
                    connection.set_tenant(membership.box)
                    return membership.box
            except Exception:
                pass

        # Strategy 3: single active box (pilot fallback)
        try:
            boxes = list(Box.objects.filter(status=Box.Status.ACTIVE)[:2])
            if len(boxes) == 1:
                connection.set_tenant(boxes[0])
                return boxes[0]
        except Exception:
            pass
    except Exception:
        pass
    return None


def async_log_audit_event(actor_id, action, target_model, target_id, target_label, description, metadata):
    from django.contrib.auth.models import User
    from auditing.models import AuditEvent
    from auditing.scrubber import PIIScrubber

    actor = User.objects.filter(pk=actor_id).first() if actor_id else None
    role_slug = ''
    if actor:
        from access.roles import get_user_role
        role = get_user_role(actor)
        role_slug = getattr(role, 'slug', '')

    _ensure_tenant_for_audit_write(actor)
    try:
        AuditEvent.objects.create(
            actor=actor,
            actor_role=role_slug,
            action=action,
            target_model=target_model,
            target_id=target_id,
            target_label=target_label,
            description=description,
            metadata=PIIScrubber.sanitize(metadata or {}),
        )
    except Exception:
        # Audit best-effort: se schema sem boxcore_auditevent e
        # _ensure_tenant_for_audit_write nao conseguiu ativar tenant (ex.:
        # multi-tenant prod com actor sem primary_box), nao bloquear o
        # fluxo principal (login/logout/webhook).
        pass

def log_audit_event(*, actor=None, action, target=None, description='', metadata=None):
    # Se estivermos em produção/homologação, usamos Celery para não travar o login.
    # Em local/dev, podemos manter síncrono para facilitar debug.
    from config.settings.base import is_local_runtime_mode

    target_model = ''
    target_id = ''
    target_label = ''
    if target is not None and hasattr(target, '_meta'):
        target_model = target._meta.model_name
        target_id = str(target.pk)
        target_label = str(target)

    actor_id = getattr(actor, 'id', None)

    if is_local_runtime_mode():
        # Fallback síncrono
        from auditing.models import AuditEvent
        from auditing.scrubber import PIIScrubber
        from access.roles import get_user_role
        role = get_user_role(actor) if actor is not None else None
        _ensure_tenant_for_audit_write(actor)
        try:
            return AuditEvent.objects.create(
                actor=actor,
                actor_role=getattr(role, 'slug', ''),
                action=action,
                target_model=target_model,
                target_id=target_id,
                target_label=target_label,
                description=description,
                metadata=PIIScrubber.sanitize(metadata or {}),
            )
        except Exception:
            # Audit best-effort: ver justificativa em async_log_audit_event.
            return None
    else:
        # 🚀 Performance de Elite (Ghost Audit): Auditoria Assíncrona (Sincronizada para Testes)
        async_log_audit_event(
            actor_id=actor_id,
            action=action,
            target_model=target_model,
            target_id=target_id,
            target_label=target_label,
            description=description,
            metadata=metadata
        )
