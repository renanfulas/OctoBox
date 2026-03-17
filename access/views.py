"""
ARQUIVO: views do modulo de acesso.

POR QUE ELE EXISTE:
- Concentra as telas e redirecionamentos ligados ao login e aos Papéis do sistema.

O QUE ESTE ARQUIVO FAZ:
1. Redireciona a raiz para login ou dashboard.
2. Monta a tela de visao geral de Papéis e capacidades.

PONTOS CRITICOS:
- Alteracoes erradas nos redirecionamentos mudam o fluxo inicial do sistema.
- O contexto current_role e usado pelo layout e nao deve desaparecer.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import TemplateView

from access.admin import admin_changelist_url, user_can_access_admin
from access.shell_actions import attach_shell_action_buttons
from shared_support.page_payloads import build_page_hero
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
        context['page_title'] = 'Papéis e acessos'
        context['page_subtitle'] = 'Quem decide o que e onde cada papel para.'
        context['hero_stats'] = [
            {'label': 'Papel atual', 'value': current_role.label},
            {'label': 'Capacidades do papel', 'value': len(role_capabilities)},
            {'label': 'Papéis formais', 'value': len(role_definitions)},
            {'label': 'Fronteira central', 'value': 'Governanca'},
        ]
        context['access_operational_focus'] = [
            {
                'label': 'Comece pelo seu proprio escopo',
                'chip_label': 'Papel',
                'summary': f'O papel {current_role.label} precisa ficar claro primeiro, para a leitura desta tela nao virar teoria solta sem utilidade operacional.',
                'pill_class': 'accent',
                'href': '#access-current-role',
                'href_label': 'Ver meu escopo',
            },
            {
                'label': 'Depois compare as fronteiras',
                'chip_label': 'Fronteiras',
                'summary': f'{len(role_definitions)} papel(is) ja desenham quem decide crescimento, manutencao, administracao e rotina tecnica sem mistura indevida.',
                'pill_class': 'info',
                'href': '#access-role-map',
                'href_label': 'Ver mapa de Papéis',
            },
            {
                'label': 'Feche com a governanca pratica',
                'chip_label': 'GovernanÃ§a',
                'summary': 'Grupos e permissoes devem sustentar o desenho do produto, nunca obrigar a operacao a adivinhar limite por tentativa e erro.',
                'pill_class': 'warning',
                'href': '#access-governance-board',
                'href_label': 'Ver governanca',
            },
        ]
        context['access_hero'] = build_page_hero(
            eyebrow='Fronteiras do sistema',
            title='Quem age, quem nÃ£o invade e onde cada papel comeÃ§a.',
            copy='Autoridade, fronteira e papel sem ambiguidade.',
            actions=[
                {'label': 'Ver meu escopo', 'href': '#access-current-role'},
                {'label': 'Ver mapa de Papéis', 'href': '#access-role-map', 'kind': 'secondary'},
                *([
                    {'label': 'Gerenciar grupos', 'href': admin_changelist_url('auth', 'group'), 'kind': 'secondary'},
                ] if user_can_access_admin(self.request.user) else []),
            ],
            aria_label='Panorama de acessos',
        )
        context['governance_points'] = [
            'Manager nao vira coach por atalho.',
            'Coach nao carrega rotina financeira ou administrativa.',
            'DEV investiga e mantem sem virar operador do box.',
            'Owner enxerga amplitude sem dissolver fronteiras entre Papéis.',
        ]
        context['group_admin_url'] = admin_changelist_url('auth', 'group') if user_can_access_admin(self.request.user) else ''
        attach_shell_action_buttons(context, focus=context['access_operational_focus'], scope='access')
        return context


