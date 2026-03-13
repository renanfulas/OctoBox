"""
ARQUIVO: fachada legada do papel Recepcao dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto a implementacao real vive em access.roles.reception.
"""

from access.roles.reception import RECEPTION_PERMISSIONS, RECEPTION_ROLE, ROLE_RECEPTION

__all__ = ['RECEPTION_PERMISSIONS', 'RECEPTION_ROLE', 'ROLE_RECEPTION']