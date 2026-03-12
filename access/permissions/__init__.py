"""
ARQUIVO: mixins e utilitarios de permissao por papel.

POR QUE ELE EXISTE:
- Permite aplicar restricao real por papel nas telas do sistema.

O QUE ESTE ARQUIVO FAZ:
1. Expoe mixins para paginas exclusivas por funcao.
2. Centraliza a checagem de roles do usuario.

PONTOS CRITICOS:
- Essa camada define quem entra em cada area operacional.
"""

from .mixins import RoleRequiredMixin

__all__ = ['RoleRequiredMixin']
