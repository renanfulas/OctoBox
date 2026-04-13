"""
ARQUIVO: chaves de disponibilidade das superficies operacionais.

POR QUE ELE EXISTE:
- centraliza o estado de ligamento de workspaces que podem ser temporariamente retirados de circulacao.

O QUE ESTE ARQUIVO FAZ:
1. expone helpers de disponibilidade para as views e para o shell.
2. evita espalhar acesso direto a settings por varios pontos da feature.
"""

from django.conf import settings


def is_manager_workspace_enabled() -> bool:
    return getattr(settings, 'OPERATIONS_MANAGER_WORKSPACE_ENABLED', False)


__all__ = ['is_manager_workspace_enabled']
