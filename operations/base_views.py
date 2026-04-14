"""
ARQUIVO: base das views operacionais por papel.

POR QUE ELE EXISTE:
- centraliza redirecionamento por papel e contexto base compartilhado dentro do app operations.

O QUE ESTE ARQUIVO FAZ:
1. redireciona o usuario para sua area principal.
2. entrega contexto base comum das telas operacionais.

PONTOS CRITICOS:
- mudancas aqui impactam todas as rotas operacionais por papel.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.utils.functional import cached_property
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView
from django.http import Http404

from access.permissions import RoleRequiredMixin
from access.roles import ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION, get_user_role
from operations.availability import is_manager_workspace_enabled


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
            if not is_manager_workspace_enabled():
                return redirect('dashboard')
            return redirect('manager-workspace')
        if role.slug == ROLE_RECEPTION:
            return redirect('reception-workspace')
        return redirect('coach-workspace')


class ManagerWorkspaceAvailabilityMixin:
    def dispatch(self, request, *args, **kwargs):
        if not is_manager_workspace_enabled():
            raise Http404()
        return super().dispatch(request, *args, **kwargs)


class OperationBaseView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    allowed_roles = ()
    page_title = ''
    page_subtitle = ''

    @cached_property
    def base_context(self):
        context = {
            'current_role': get_user_role(self.request.user),
            'today': timezone.localdate(),
        }
        if self.page_title:
            context['page_title'] = self.page_title
        if self.page_subtitle:
            context['page_subtitle'] = self.page_subtitle
        return context

    def get_base_context(self):
        return dict(self.base_context)
