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
        # debug via logger only
        if role is None or role.slug not in self.allowed_roles:
            ACCESS_LOGGER.warning('permission_denied user_id=%s role=%s allowed=%s path=%s',
                                  getattr(getattr(request, 'user', None), 'pk', None),
                                  getattr(role, 'slug', None),
                                  self.allowed_roles,
                                  getattr(request, 'path', None))
            # additional debug: persist request info to disk to help headless reproductions
            try:
                logfile = 'playwright_debug.log'
                with open(logfile, 'a', encoding='utf-8') as f:
                    f.write('\n---- PLAYWRIGHT DEBUG ----\n')
                    f.write(f'user_authenticated={getattr(request.user, "is_authenticated", False)}\n')
                    f.write(f'user_id={getattr(getattr(request, "user", None), "pk", None)}\n')
                    f.write(f'role_slug={getattr(role, "slug", None)}\n')
                    f.write(f'path={getattr(request, "path", None)}\n')
                    f.write('COOKIES:\n')
                    for k, v in request.COOKIES.items():
                        f.write(f'  {k}={v}\n')
                    f.write('HEADERS:\n')
                    for k, v in request.META.items():
                        if k.startswith('HTTP_'):
                            f.write(f'  {k}={v}\n')
            except Exception:
                pass
            raise PermissionDenied('Este usuário não tem permissão para acessar esta área.')
        return super().dispatch(request, *args, **kwargs)
