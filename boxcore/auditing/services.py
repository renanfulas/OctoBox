"""
ARQUIVO: serviços de auditoria.

POR QUE ELE EXISTE:
- Evita espalhar criação manual de eventos sensíveis pelo projeto.

O QUE ESTE ARQUIVO FAZ:
1. Traduz um alvo opcional em dados persistíveis.
2. Cria eventos padronizados de auditoria.
3. Mantém a escrita da trilha de auditoria em um único ponto.

PONTOS CRITICOS:
- O formato do evento precisa permanecer estável para futuras consultas e relatórios.
"""

from boxcore.access.roles import get_user_role
from boxcore.models import AuditEvent


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