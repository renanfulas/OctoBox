"""
ARQUIVO: fachada legada do contexto global de acesso dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto a implementacao real vive em access.context_processors.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta o contexto global real de acesso.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar comportamento novo.
"""

from access.context_processors import role_navigation

__all__ = ['role_navigation']