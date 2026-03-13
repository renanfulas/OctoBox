"""
ARQUIVO: base das views do catalogo.

POR QUE ELE EXISTE:
- centraliza autenticacao, papeis permitidos e contexto base do catalog dentro do app real.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import TemplateView

from access.permissions import RoleRequiredMixin
from access.roles import ROLE_COACH, ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, get_user_role


class CatalogBaseView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    allowed_roles = (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER, ROLE_COACH)

    def get_base_context(self):
        return {
            'current_role': get_user_role(self.request.user),
            'today': timezone.localdate(),
        }
