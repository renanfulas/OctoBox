"""
ARQUIVO: navigation_contracts.py

POR QUE ELE EXISTE:
- Centraliza apenas as rotas compartilhadas do shell para garantir consistência visual e funcional.
- Atua como o "GPS do Prédio", resolvendoview_name -> scope -> nav_key de forma determinística.
"""

from django.urls import reverse, NoReverseMatch


class ShellRoute:
    """
    Contrato determinístico para rotas compartilhadas do shell.
    Garante que o reverse() seja resolvido dinamicamente no runtime do request.
    """
    def __init__(self, view_name, scope, nav_key, fragment=None):
        self.view_name = view_name
        self.scope = scope
        self.nav_key = nav_key
        self.fragment = fragment

    def get_url(self):
        try:
            url = reverse(self.view_name)
            if self.fragment:
                f = self.fragment.lstrip('#')
                return f"{url}#{f}"
            return url
        except NoReverseMatch:
            return "/"

    def __str__(self):
        return self.get_url()


# 🚩 GPS do Prédio: Instâncias oficiais para rotas compartilhadas
CORE_ROUTES = {
    'dashboard': ShellRoute('dashboard', 'dashboard', 'dashboard'),
    'students': ShellRoute('student-directory', 'students', 'alunos'),
    'finance': ShellRoute('finance-center', 'finance', 'financeiro'),
    'intake': ShellRoute('intake-center', 'intake', 'entradas'),
    'reception': ShellRoute('reception-workspace', 'reception', 'recepcao'),
    'classes': ShellRoute('class-grid', 'class-grid', 'grade-aulas'),
    'coach': ShellRoute('coach-workspace', 'coach-workspace', 'operacao'),
}

# 🗺️ Mapeamento estático para o context_processor/shell_actions
# Focado em resolver scope e nav_key para visual state.
_NAV_CONTRACTS = {
    'dashboard': ('dashboard', 'dashboard'),
    'student-directory': ('students', 'alunos'),
    'student-quick-create': ('student-form', 'alunos'),
    'student-quick-update': ('student-form', 'alunos'),
    'finance-center': ('finance', 'financeiro'),
    'membership-plan-quick-update': ('finance-plan-form', 'financeiro'),
    'intake-center': ('intake', 'entradas'),
    'reception-workspace': ('reception', 'recepcao'),
    'class-grid': ('class-grid', 'grade-aulas'),
    'coach-workspace': ('coach-workspace', 'operacao'),
}


def get_navigation_contract(view_name, fallback_scope='generic', fallback_nav_key=''):
    """
    Resolve o nome da view para o contrato de navegação visual.
    Retorna {'scope': str, 'nav_key': str}.
    """
    # 1. Tenta encontrar nas rotas core
    for key, route in CORE_ROUTES.items():
        if route.view_name == view_name:
            return {'scope': route.scope, 'nav_key': route.nav_key}
            
    # 2. Tenta no mapa estático (contratos locais que influenciam o shell)
    contract = _NAV_CONTRACTS.get(view_name)
    if contract:
        return {'scope': contract[0], 'nav_key': contract[1]}
    
    return {'scope': fallback_scope, 'nav_key': fallback_nav_key}


def get_shell_route_url(key, fragment=None):
    """Helper direto para obter a URL de uma rota core do shell."""
    route = CORE_ROUTES.get(key)
    if not route:
        return "/"
    
    try:
        url = reverse(route.view_name)
        if fragment:
            f = fragment.lstrip('#')
            return f"{url}#{f}"
        return url
    except NoReverseMatch:
        return "/"


__all__ = ['get_navigation_contract', 'get_shell_route_url', 'CORE_ROUTES']
