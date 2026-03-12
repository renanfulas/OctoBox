"""
ARQUIVO: views do modulo de acesso.

POR QUE ELE EXISTE:
- Concentra as telas e redirecionamentos ligados ao login e aos papeis do sistema.

O QUE ESTE ARQUIVO FAZ:
1. Redireciona a raiz para login ou dashboard.
2. Monta a tela de visao geral de papeis e capacidades.

PONTOS CRITICOS:
- Alteracoes erradas nos redirecionamentos mudam o fluxo inicial do sistema.
- O contexto current_role e usado pelo layout e nao deve desaparecer.
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
