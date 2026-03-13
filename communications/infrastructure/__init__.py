"""
ARQUIVO: infraestrutura Django do dominio de communications.

POR QUE ELE EXISTE:
- Isola ORM, transacao, auditoria e integrações concretas da camada de aplicação.

O QUE ESTE ARQUIVO FAZ:
1. Exporta a execução concreta dos use cases de communications.
2. Marca a fronteira de infraestrutura Django do domínio.

PONTOS CRITICOS:
- Tudo aqui pode usar Django livremente; acima daqui isso deve continuar estável.
"""

from .django_audit import DjangoOperationalMessageAuditPort
from .django_clock import DjangoClockPort
from .django_use_cases import (
	ensure_whatsapp_contact_for_student,
	execute_register_inbound_whatsapp_message_command,
	execute_register_operational_message_command,
)
from .django_inbound_idempotency import find_existing_inbound_message
from .django_catalog_operations import (
	execute_build_operational_queue_snapshot_command,
	execute_finance_communication_action_command,
	get_message_log,
)

__all__ = [
	'execute_build_operational_queue_snapshot_command',
	'execute_finance_communication_action_command',
	'ensure_whatsapp_contact_for_student',
	'execute_register_inbound_whatsapp_message_command',
	'execute_register_operational_message_command',
	'find_existing_inbound_message',
	'get_message_log',
	'DjangoOperationalMessageAuditPort',
	'DjangoClockPort',
]
