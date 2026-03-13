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

from access.roles import get_user_role
from auditing.models import AuditEvent


def log_audit_event(*, actor=None, action, target=None, description='', metadata=None):
    role = get_user_role(actor) if actor is not None else None

    target_model = ''
    target_id = ''
    target_label = ''
    if target is not None:
        target_model = target._meta.model_name
        target_id = str(target.pk)
        target_label = str(target)

    return AuditEvent.objects.create(
        actor=actor,
        actor_role=getattr(role, 'slug', ''),
        action=action,
        target_model=target_model,
        target_id=target_id,
        target_label=target_label,
        description=description,
        metadata=metadata or {},
    )
