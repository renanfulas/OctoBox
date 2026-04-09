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

from logging import getLogger

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse

from access.roles import get_user_role

ACCESS_LOGGER = getLogger('octobox.access')


class AjaxLoginRequiredMixin(LoginRequiredMixin):
    def handle_no_permission(self):
        request = getattr(self, 'request', None)
        if request is not None and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse(
                {
                    'status': 'error',
                    'message': 'Sua sessao nao esta autenticada para esta acao. Faca login novamente e tente de novo.',
                },
                status=401,
            )
        return super().handle_no_permission()


class RoleRequiredMixin:
    allowed_roles = ()

    def dispatch(self, request, *args, **kwargs):
        role = get_user_role(request.user)
        ACCESS_LOGGER.debug(
            'RoleRequiredMixin dispatch user_id=%s role=%s allowed=%s path=%s',
            getattr(getattr(request, 'user', None), 'pk', None),
            getattr(role, 'slug', None),
            self.allowed_roles,
            getattr(request, 'path', None),
        )
        if role is None or role.slug not in self.allowed_roles:
            ACCESS_LOGGER.warning(
                'permission_denied user_id=%s role=%s allowed=%s path=%s',
                getattr(getattr(request, 'user', None), 'pk', None),
                getattr(role, 'slug', None),
                self.allowed_roles,
                getattr(request, 'path', None),
            )
            try:
                logfile = 'playwright_debug.log'
                with open(logfile, 'a', encoding='utf-8') as f:
                    f.write('\n---- PLAYWRIGHT DEBUG ----\n')
                    f.write(f'user_authenticated={getattr(request.user, "is_authenticated", False)}\n')
                    f.write(f'user_id={getattr(getattr(request, "user", None), "pk", None)}\n')
                    f.write(f'role_slug={getattr(role, "slug", None)}\n')
                    f.write(f'path={getattr(request, "path", None)}\n')
                    f.write('COOKIES:\n')
                    for key, value in request.COOKIES.items():
                        f.write(f'  {key}={value}\n')
                    f.write('HEADERS:\n')
                    for key, value in request.META.items():
                        if key.startswith('HTTP_'):
                            f.write(f'  {key}={value}\n')
            except Exception:
                pass

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse(
                    {
                        'status': 'error',
                        'message': 'Seu usuario nao tem permissao para executar esta acao. Este fluxo exige papel Owner, Manager ou Recepcao.',
                        'role': getattr(role, 'slug', None),
                        'allowed_roles': list(self.allowed_roles),
                    },
                    status=403,
                )

            raise PermissionDenied('Este usuario nao tem permissao para acessar esta area.')

        return super().dispatch(request, *args, **kwargs)
