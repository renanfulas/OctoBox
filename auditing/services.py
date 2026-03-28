"""
ARQUIVO: servicos de auditoria.

POR QUE ELE EXISTE:
- Evita espalhar criacao manual de eventos sensiveis pelo projeto.

O QUE ESTE ARQUIVO FAZ:
1. Traduz um alvo opcional em dados persistiveis.
2. Cria eventos padronizados de auditoria.
3. Mantem a escrita da trilha de auditoria em um unico ponto.

PONTOS CRITICOS:
- O formato do evento precisa permanecer estavel para futuras consultas e relatorios.
"""

from django.apps import apps
# from reporting.infrastructure.celery_app import app as celery_app

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

def log_audit_event(*, actor=None, action, target=None, description='', metadata=None):
    # Se estivermos em produção/homologação, usamos Celery para não travar o login.
    # Em local/dev, podemos manter síncrono para facilitar debug.
    from config.settings.base import is_local_runtime_mode
    
    target_model = ''
    target_id = ''
    target_label = ''
    if target is not None:
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
