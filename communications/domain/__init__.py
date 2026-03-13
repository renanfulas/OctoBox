"""
ARQUIVO: namespace das regras puras do dominio de communications.

POR QUE ELE EXISTE:
- Hospeda decisoes de negocio e politicas operacionais sem depender de Django, ORM ou delivery.

O QUE ESTE ARQUIVO FAZ:
1. Organiza a camada de dominio puro de communications.

PONTOS CRITICOS:
- Esta camada nao deve importar `django.*` nem models ORM.
"""

from .contact_reconciliation import (
	build_inbound_contact_notes,
	plan_inbound_contact_mutation,
	plan_outbound_contact_mutation,
	resolve_contact_status,
)
from .channel_identity import (
	build_channel_identity_lookup_plan,
	resolve_student_from_identity_sources,
)
from .operational_rules import should_mark_payment_overdue

__all__ = [
	'build_channel_identity_lookup_plan',
	'build_inbound_contact_notes',
	'plan_inbound_contact_mutation',
	'plan_outbound_contact_mutation',
	'resolve_student_from_identity_sources',
	'resolve_contact_status',
	'should_mark_payment_overdue',
]