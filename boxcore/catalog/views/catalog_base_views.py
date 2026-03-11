"""
ARQUIVO: base das views do catalogo.

POR QUE ELE EXISTE:
- Centraliza comportamento comum das views leves do catalogo.

O QUE ESTE ARQUIVO FAZ:
1. Define a view base com autenticacao e papeis permitidos.
2. Entrega contexto base compartilhado entre alunos, financeiro e grade.

PONTOS CRITICOS:
- Mudancas aqui afetam todas as views do catalogo.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import TemplateView

from boxcore.access.permissions import RoleRequiredMixin
from boxcore.access.roles import ROLE_COACH, ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, get_user_role


class CatalogBaseView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    allowed_roles = (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER, ROLE_COACH)

    def get_base_context(self):
        return {
            'current_role': get_user_role(self.request.user),
            'today': timezone.localdate(),
        }