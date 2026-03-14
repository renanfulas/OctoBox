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

from access.shell_actions import attach_shell_action_buttons
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
        current_role = get_user_role(self.request.user)
        role_capabilities = get_user_capabilities(self.request.user)
        role_definitions = ROLE_DEFINITIONS

        context['current_role'] = current_role
        context['role_capabilities'] = role_capabilities
        context['role_definitions'] = role_definitions
        context['page_title'] = 'Papeis e acessos'
        context['page_subtitle'] = 'Mapa de fronteiras do produto para deixar claro quem deve decidir o que, onde cada rotina comeca e onde cada papel precisa parar.'
        context['hero_stats'] = [
            {'label': 'Papel atual', 'value': current_role.label},
            {'label': 'Capacidades do papel', 'value': len(role_capabilities)},
            {'label': 'Papeis formais', 'value': len(role_definitions)},
            {'label': 'Fronteira central', 'value': 'Governanca'},
        ]
        context['access_operational_focus'] = [
            {
                'label': 'Comece pelo seu proprio escopo',
                'summary': f'O papel {current_role.label} precisa ficar claro primeiro, para a leitura desta tela nao virar teoria solta sem utilidade operacional.',
                'pill_class': 'accent',
                'href': '#access-current-role',
                'href_label': 'Ver meu escopo',
            },
            {
                'label': 'Depois compare as fronteiras',
                'summary': f'{len(role_definitions)} papel(is) ja desenham quem decide crescimento, manutencao, administracao e rotina tecnica sem mistura indevida.',
                'pill_class': 'info',
                'href': '#access-role-map',
                'href_label': 'Ver mapa de papeis',
            },
            {
                'label': 'Feche com a governanca pratica',
                'summary': 'Grupos e permissoes devem sustentar o desenho do produto, nunca obrigar a operacao a adivinhar limite por tentativa e erro.',
                'pill_class': 'warning',
                'href': '#access-governance-board',
                'href_label': 'Ver governanca',
            },
        ]
        context['governance_points'] = [
            'Manager nao vira coach por atalho.',
            'Coach nao carrega rotina financeira ou administrativa.',
            'DEV investiga e mantem sem virar operador do box.',
            'Owner enxerga amplitude sem dissolver fronteiras entre papeis.',
        ]
        attach_shell_action_buttons(context, focus=context['access_operational_focus'], scope='access')
        return context
