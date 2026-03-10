"""
ARQUIVO: contexto global de navegação por papel.

POR QUE ELE EXISTE:
- Evita repetir lógica de sidebar em cada view autenticada.
- Mantém o menu coerente com o papel efetivo do usuário.

O QUE ESTE ARQUIVO FAZ:
1. Descobre o papel atual do usuário logado.
2. Monta os links permitidos para a sidebar.
3. Inclui links técnicos e de auditoria quando o papel permite.
4. Expõe isso para todos os templates.

PONTOS CRITICOS:
- Mudanças aqui impactam a navegação do sistema inteiro.
- Os links devem refletir a fronteira operacional e técnica real de cada papel.
"""

from boxcore.access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER, get_user_role
from boxcore.access.roles import ROLE_DEV


def _build_navigation(role_slug):
    base_links = [
        {'label': 'Dashboard', 'href': '/dashboard/'},
        {'label': 'Alunos', 'href': '/alunos/'},
        {'label': 'Financeiro', 'href': '/financeiro/'},
        {'label': 'Grade de aulas', 'href': '/grade-aulas/'},
        {'label': 'Minha operação', 'href': '/operacao/'},
        {'label': 'Papéis e acessos', 'href': '/acessos/'},
        {'label': 'Mapa do sistema', 'href': '/mapa-sistema/'},
    ]

    role_links = {
        ROLE_OWNER: [
            {'label': 'Admin Django', 'href': '/admin/'},
            {'label': 'Auditoria', 'href': '/admin/boxcore/auditevent/'},
        ],
        ROLE_DEV: [
            {'label': 'Auditoria', 'href': '/admin/boxcore/auditevent/'},
            {'label': 'Admin Django', 'href': '/admin/'},
        ],
        ROLE_MANAGER: [
            {'label': 'Alunos', 'href': '/admin/boxcore/student/'},
            {'label': 'Central de entrada', 'href': '/admin/boxcore/studentintake/'},
            {'label': 'Pagamentos', 'href': '/admin/boxcore/payment/'},
            {'label': 'WhatsApp', 'href': '/admin/boxcore/whatsappcontact/'},
        ],
        ROLE_COACH: [
            {'label': 'Aulas', 'href': '/admin/boxcore/classsession/'},
            {'label': 'Ocorrências', 'href': '/admin/boxcore/behaviornote/'},
        ],
    }

    return [*base_links, *role_links.get(role_slug, [])]


def role_navigation(request):
    role = get_user_role(request.user)
    role_slug = getattr(role, 'slug', '')

    return {
        'current_role': role,
        'sidebar_navigation': _build_navigation(role_slug) if request.user.is_authenticated else [],
    }