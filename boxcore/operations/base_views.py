"""
ARQUIVO: base das views operacionais por papel.

POR QUE ELE EXISTE:
- Centraliza redirecionamento por papel e contexto base compartilhado das areas operacionais.

O QUE ESTE ARQUIVO FAZ:
1. Redireciona o usuario para sua area principal de operacao.
2. Entrega contexto base compartilhado entre Owner, DEV, Manager e Coach.

PONTOS CRITICOS:
- Mudancas aqui afetam todas as rotas operacionais por papel.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from boxcore.access.permissions import RoleRequiredMixin
from boxcore.access.roles import ROLE_COACH, ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, get_user_role


class RoleOperationRedirectView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        role = get_user_role(request.user)
        if role is None:
            return redirect('login')
        if role.slug == ROLE_OWNER:
            return redirect('owner-workspace')
        if role.slug == ROLE_DEV:
            return redirect('dev-workspace')
        if role.slug == ROLE_MANAGER:
            return redirect('manager-workspace')
        return redirect('coach-workspace')


class OperationBaseView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    allowed_roles = ()

    def get_base_context(self):
        return {
            'current_role': get_user_role(self.request.user),
            'today': timezone.localdate(),
        }