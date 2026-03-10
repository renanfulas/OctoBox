"""
ARQUIVO: mixins e utilitários de permissão por papel.

POR QUE ELE EXISTE:
- Permite aplicar restrição real por papel nas telas do sistema.

O QUE ESTE ARQUIVO FAZ:
1. Expõe mixins para páginas exclusivas por função.
2. Centraliza a checagem de roles do usuário.

PONTOS CRITICOS:
- Essa camada define quem entra em cada área operacional.
"""

from .mixins import RoleRequiredMixin

__all__ = ['RoleRequiredMixin']