"""
ARQUIVO: views do módulo de acesso.

POR QUE ELE EXISTE:
- Concentra as telas e redirecionamentos ligados ao login e aos papéis do sistema.

O QUE ESTE ARQUIVO FAZ:
1. Redireciona a raiz para login ou dashboard.
2. Monta a tela de visão geral de papéis e capacidades.

PONTOS CRITICOS:
- Alterações erradas nos redirecionamentos mudam o fluxo inicial do sistema.
- O contexto current_role é usado pelo layout e não deve desaparecer.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import TemplateView

from .roles import ROLE_DEFINITIONS, get_user_capabilities, get_user_role


class HomeRedirectView(TemplateView):
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('role-operations')
        return redirect('login')


class AccessOverviewView(LoginRequiredMixin, TemplateView):
    template_name = 'access/overview.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_role'] = get_user_role(self.request.user)
        context['role_capabilities'] = get_user_capabilities(self.request.user)
        context['role_definitions'] = ROLE_DEFINITIONS
        return context