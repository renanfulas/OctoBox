"""
ARQUIVO: facade publica do student_identity (Center Layer).

POR QUE EXISTE:
- ponto de entrada estavel do CENTER para fluxos de autenticacao do aluno.
- esconde commands, use cases, oauth_journeys e wiring interno das views.

REGRA DE CENTER LAYER (docs/architecture/center-layer.md):
- esta facade organiza COMUNICACAO entre borda (views, API) e nucleo (use_cases).
- nao reimplementa regra de negocio do domain.
- devolve results pequenos e previsiveis para a borda.
"""

from .tenant_resolver import (
    StudentAuthTenantStrategy,
    resolve_tenant_for_student_oauth_callback,
    resolve_tenant_for_student_invite_landing,
)

__all__ = [
    'StudentAuthTenantStrategy',
    'resolve_tenant_for_student_oauth_callback',
    'resolve_tenant_for_student_invite_landing',
]
