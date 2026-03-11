"""
ARQUIVO: contexto global de navegacao por papel.

POR QUE ELE EXISTE:
- evita repetir logica de sidebar, topbar e alertas em cada view autenticada.
- mantem o menu coerente com o papel efetivo do usuario e com a rota ativa.

O QUE ESTE ARQUIVO FAZ:
1. descobre o papel atual do usuario logado.
2. monta os links permitidos para a sidebar.
3. marca automaticamente o item ativo da navegacao.
4. expoe alertas globais de financeiro e intake para os templates.

PONTOS CRITICOS:
- mudancas aqui impactam a navegacao do sistema inteiro.
- os links devem refletir a fronteira operacional e tecnica real de cada papel.
"""

from boxcore.access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER, get_user_role
from boxcore.access.roles import ROLE_DEV
from boxcore.models import IntakeStatus, Payment, PaymentStatus, StudentIntake


def _pick_active_href(current_path, links):
    current_path = current_path or '/'
    matches = []

    for item in links:
        href = item['href']
        if current_path == href or current_path.startswith(href):
            matches.append(href)

    return max(matches, key=len, default='')


def _build_navigation(role_slug, current_path=''):
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

    links = [*base_links, *role_links.get(role_slug, [])]
    active_href = _pick_active_href(current_path, links)

    return [
        {
            **item,
            'is_active': item['href'] == active_href,
        }
        for item in links
    ]


def role_navigation(request):
    role = get_user_role(request.user)
    role_slug = getattr(role, 'slug', '')
    overdue_payments = 0
    pending_intakes = 0

    if request.user.is_authenticated:
        overdue_payments = Payment.objects.filter(status=PaymentStatus.OVERDUE).count()
        pending_intakes = StudentIntake.objects.filter(
            status__in=[IntakeStatus.NEW, IntakeStatus.REVIEWING],
            linked_student__isnull=True,
        ).count()

    return {
        'current_role': role,
        'sidebar_navigation': _build_navigation(role_slug, request.path) if request.user.is_authenticated else [],
        'global_search_action': '/alunos/',
        'topbar_alerts': {
            'overdue_payments': overdue_payments,
            'pending_intakes': pending_intakes,
        },
    }