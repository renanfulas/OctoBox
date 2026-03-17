"""
ARQUIVO: mixins de permissao por papel.

POR QUE ELE EXISTE:
- Tira a logica de permissao das views e deixa a regra reutilizavel.

O QUE ESTE ARQUIVO FAZ:
1. Verifica se o usuario tem papel permitido.
2. Retorna 403 quando a tela nao deve ser acessada.

PONTOS CRITICOS:
- Se a lista de allowed_roles estiver errada, a tela pode abrir para a pessoa errada.
"""

from django.core.exceptions import PermissionDenied
from logging import getLogger

from access.roles import get_user_role

ACCESS_LOGGER = getLogger('octobox.access')


class RoleRequiredMixin:
    allowed_roles = ()

    def dispatch(self, request, *args, **kwargs):
        role = get_user_role(request.user)
        ACCESS_LOGGER.debug('RoleRequiredMixin dispatch user_id=%s role=%s allowed=%s path=%s',
                            getattr(getattr(request, 'user', None), 'pk', None),
                            getattr(role, 'slug', None),
                            self.allowed_roles,
                            getattr(request, 'path', None))
        if role is None or role.slug not in self.allowed_roles:
            ACCESS_LOGGER.warning('permission_denied user_id=%s role=%s allowed=%s path=%s',
                                  getattr(getattr(request, 'user', None), 'pk', None),
                                  getattr(role, 'slug', None),
                                  self.allowed_roles,
                                  getattr(request, 'path', None))
            raise PermissionDenied('Este usuário não tem permissão para acessar esta área.')
        return super().dispatch(request, *args, **kwargs)
