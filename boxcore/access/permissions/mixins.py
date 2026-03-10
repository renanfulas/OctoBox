"""
ARQUIVO: mixins de permissão por papel.

POR QUE ELE EXISTE:
- Tira a lógica de permissão das views e deixa a regra reutilizável.

O QUE ESTE ARQUIVO FAZ:
1. Verifica se o usuário tem papel permitido.
2. Retorna 403 quando a tela não deve ser acessada.

PONTOS CRITICOS:
- Se a lista de allowed_roles estiver errada, a tela pode abrir para a pessoa errada.
"""

from django.core.exceptions import PermissionDenied

from boxcore.access.roles import get_user_role


class RoleRequiredMixin:
    allowed_roles = ()

    def dispatch(self, request, *args, **kwargs):
        role = get_user_role(request.user)
        if role is None or role.slug not in self.allowed_roles:
            raise PermissionDenied('Este usuário não tem permissão para acessar esta área.')
        return super().dispatch(request, *args, **kwargs)